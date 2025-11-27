"""
Sync operation handlers for applying remote operations to local database.

Handles TASK_CREATE, TASK_UPDATE, TASK_DELETE, TASK_MOVE, LIST_CREATE operations
received from other clients via SQS.
"""

from typing import Dict, Any, TYPE_CHECKING, Optional
from datetime import datetime
import uuid

from taskui.logging_config import get_logger

if TYPE_CHECKING:
    from taskui.services.task_service import TaskService
    from taskui.services.list_service import ListService

logger = get_logger(__name__)


class SyncOperationHandler:
    """Handles incoming sync operations from remote clients."""

    def __init__(self, task_service: "TaskService", list_service: "ListService"):
        """
        Initialize handler with service references.

        Args:
            task_service: TaskService for task operations
            list_service: ListService for list operations
        """
        self.task_service = task_service
        self.list_service = list_service

    async def _ensure_list_exists(self, list_id: uuid.UUID, placeholder_name: str = "(Syncing...)") -> None:
        """
        Ensure list exists, create placeholder if needed.

        This handles the edge case where a task is received before its list.
        The list will be created with a placeholder name, which will be
        corrected when the LIST_CREATE or LIST_UPDATE operation arrives.

        Args:
            list_id: UUID of the list that should exist
            placeholder_name: Temporary name if list needs to be created
        """
        try:
            existing = await self.list_service.get_list_by_id(list_id)
            if existing:
                return  # List exists, nothing to do
        except Exception:
            pass  # List doesn't exist, continue to create

        # Auto-create placeholder list
        logger.info(f"Auto-creating missing list {list_id} for incoming task")
        try:
            await self.list_service.create_list(
                name=placeholder_name,
                list_id=list_id
            )
            logger.debug(f"Created placeholder list: {list_id}")
        except Exception as e:
            # List might have been created by another operation
            logger.warning(f"Could not create placeholder list {list_id}: {e}")

    async def handle_operation(self, operation_data: Dict[str, Any]) -> bool:
        """
        Route operation to appropriate handler.

        Args:
            operation_data: Decrypted operation message from SQS

        Returns:
            True if operation applied successfully
        """
        operation = operation_data.get('operation')

        handlers = {
            'TASK_CREATE': self._handle_task_create,
            'TASK_UPDATE': self._handle_task_update,
            'TASK_DELETE': self._handle_task_delete,
            'TASK_MOVE': self._handle_task_move,
            'LIST_CREATE': self._handle_list_create,
            'LIST_UPDATE': self._handle_list_update,
        }

        handler = handlers.get(operation)
        if handler:
            try:
                await handler(operation_data)
                logger.info(f"Applied remote operation: {operation}")
                return True
            except Exception as e:
                logger.error(f"Failed to apply {operation}: {e}", exc_info=True)
                return False
        else:
            logger.warning(f"Unknown operation type: {operation}")
            return False

    async def _handle_task_create(self, data: Dict[str, Any]):
        """
        Apply task creation from remote client.

        Args:
            data: Operation data containing task details and list_id
        """
        task_data = data['data']['task']
        list_id = uuid.UUID(data['list_id'])
        task_id = uuid.UUID(task_data['id'])

        # Ensure list exists (creates placeholder if missing)
        await self._ensure_list_exists(list_id)

        logger.info(
            f"Creating task from sync: {task_data.get('title')} "
            f"(id={task_id}, list={list_id})"
        )

        # Check if task already exists to prevent duplicates
        try:
            existing_task = await self.task_service.get_task_by_id(task_id)
            if existing_task:
                logger.warning(
                    f"Task {task_id} already exists, skipping creation from sync"
                )
                return
        except Exception:
            # Task doesn't exist, continue with creation
            pass

        # Create task with remote data
        try:
            await self.task_service.create_task(
                list_id=list_id,
                title=task_data.get('title', ''),
                notes=task_data.get('notes'),
                url=task_data.get('url'),
                parent_id=uuid.UUID(task_data['parent_id']) if task_data.get('parent_id') else None,
                position=task_data.get('position', 0),
                task_id=task_id,  # Use the remote task ID
                created_at=datetime.fromisoformat(task_data['created_at']) if task_data.get('created_at') else None,
                updated_at=datetime.fromisoformat(task_data['updated_at']) if task_data.get('updated_at') else None,
            )
            logger.info(f"Successfully created task {task_id} from sync")
        except Exception as e:
            logger.error(f"Failed to create task {task_id} from sync: {e}", exc_info=True)
            raise

    async def _handle_task_update(self, data: Dict[str, Any]):
        """
        Apply task update from remote client.

        Uses last-write-wins conflict resolution based on timestamps.

        Args:
            data: Operation data containing task_id and changes
        """
        task_id = uuid.UUID(data['data']['task_id'])
        changes = data['data']['changes']
        remote_timestamp = datetime.fromisoformat(data['timestamp'])

        # If task is being moved to a different list, ensure target list exists
        if 'list_id' in changes:
            target_list_id = uuid.UUID(changes['list_id']) if isinstance(changes['list_id'], str) else changes['list_id']
            await self._ensure_list_exists(target_list_id)

        logger.info(f"Updating task from sync: {task_id}, changes={list(changes.keys())}")

        # Get current task state
        try:
            current_task = await self.task_service.get_task_by_id(task_id)
            if not current_task:
                logger.warning(f"Task {task_id} not found, cannot apply update from sync")
                return

            # Last-write-wins: check if remote change is newer
            if current_task.updated_at and current_task.updated_at > remote_timestamp:
                logger.info(
                    f"Local task {task_id} is newer, skipping remote update "
                    f"(local={current_task.updated_at}, remote={remote_timestamp})"
                )
                return

            # Apply changes
            await self.task_service.update_task(
                task_id=task_id,
                **changes
            )
            logger.info(f"Successfully updated task {task_id} from sync")
        except Exception as e:
            logger.error(f"Failed to update task {task_id} from sync: {e}", exc_info=True)
            raise

    async def _handle_task_delete(self, data: Dict[str, Any]):
        """
        Apply task deletion from remote client.

        Args:
            data: Operation data containing task_id and cascade flag
        """
        task_id = uuid.UUID(data['data']['task_id'])
        cascade = data['data'].get('cascade', True)

        logger.info(f"Deleting task from sync: {task_id}, cascade={cascade}")

        try:
            # Check if task exists
            existing_task = await self.task_service.get_task_by_id(task_id)
            if not existing_task:
                logger.warning(f"Task {task_id} not found, already deleted")
                return

            # Delete task
            await self.task_service.delete_task(task_id, cascade=cascade)
            logger.info(f"Successfully deleted task {task_id} from sync")
        except Exception as e:
            logger.error(f"Failed to delete task {task_id} from sync: {e}", exc_info=True)
            raise

    async def _handle_task_move(self, data: Dict[str, Any]):
        """
        Apply task move/reparent from remote client.

        Args:
            data: Operation data containing task_id, new_parent_id, and new_position
        """
        task_id = uuid.UUID(data['data']['task_id'])
        new_parent_id = uuid.UUID(data['data']['new_parent_id']) if data['data'].get('new_parent_id') else None
        new_position = data['data']['new_position']

        logger.info(
            f"Moving task from sync: {task_id}, "
            f"new_parent={new_parent_id}, new_position={new_position}"
        )

        try:
            # Check if task exists
            existing_task = await self.task_service.get_task_by_id(task_id)
            if not existing_task:
                logger.warning(f"Task {task_id} not found, cannot move")
                return

            # Apply move operation
            await self.task_service.move_task(
                task_id=task_id,
                new_parent_id=new_parent_id,
                new_position=new_position
            )
            logger.info(f"Successfully moved task {task_id} from sync")
        except Exception as e:
            logger.error(f"Failed to move task {task_id} from sync: {e}", exc_info=True)
            raise

    async def _handle_list_create(self, data: Dict[str, Any]):
        """
        Apply list creation from remote client.

        Args:
            data: Operation data containing list details
        """
        list_data = data['data']['list']
        list_id = uuid.UUID(list_data['id'])

        logger.info(
            f"Creating list from sync: {list_data.get('name')} (id={list_id})"
        )

        # Check if list already exists to prevent duplicates
        try:
            existing_list = await self.list_service.get_list_by_id(list_id)
            if existing_list:
                logger.warning(
                    f"List {list_id} already exists, skipping creation from sync"
                )
                return
        except Exception:
            # List doesn't exist, continue with creation
            pass

        # Create list with remote data
        try:
            await self.list_service.create_list(
                name=list_data.get('name', ''),
                list_id=list_id,  # Use the remote list ID
                created_at=datetime.fromisoformat(list_data['created_at']) if list_data.get('created_at') else None,
                updated_at=datetime.fromisoformat(list_data['updated_at']) if list_data.get('updated_at') else None,
            )
            logger.info(f"Successfully created list {list_id} from sync")
        except Exception as e:
            logger.error(f"Failed to create list {list_id} from sync: {e}", exc_info=True)
            raise

    async def _handle_list_update(self, data: Dict[str, Any]):
        """
        Apply list update (rename) from remote client.

        Uses last-write-wins conflict resolution based on timestamps.

        Args:
            data: Operation data containing list_id and changes
        """
        list_id = uuid.UUID(data['data']['list_id'])
        changes = data['data']['changes']
        remote_timestamp = datetime.fromisoformat(data['timestamp'])

        logger.info(f"Updating list from sync: {list_id}, changes={list(changes.keys())}")

        # Get current list state
        try:
            current_list = await self.list_service.get_list_by_id(list_id)
            if not current_list:
                logger.warning(f"List {list_id} not found, cannot apply update from sync")
                return

            # Last-write-wins: check if remote change is newer
            if current_list.updated_at and current_list.updated_at > remote_timestamp:
                logger.info(
                    f"Local list {list_id} is newer, skipping remote update "
                    f"(local={current_list.updated_at}, remote={remote_timestamp})"
                )
                return

            # Apply changes
            await self.list_service.update_list(
                list_id=list_id,
                **changes
            )
            logger.info(f"Successfully updated list {list_id} from sync")
        except Exception as e:
            logger.error(f"Failed to update list {list_id} from sync: {e}", exc_info=True)
            raise
