"""
List service for TaskUI application.

Provides CRUD operations and business logic for managing task lists,
including default list creation and list-specific task operations.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from taskui.database import TaskListORM, TaskORM
from taskui.logging_config import get_logger
from taskui.models import TaskList

if TYPE_CHECKING:
    from taskui.services.pending_operations import PendingOperationsQueue

logger = get_logger(__name__)


class ListService:
    """
    Service layer for task list management.

    Handles creation, retrieval, updating, and deletion of task lists,
    as well as initialization of default lists on first run.
    """

    # Default lists to create on first run
    DEFAULT_LISTS = [
        {"name": "Work", "id": "00000000-0000-0000-0000-000000000001"},
        {"name": "Home", "id": "00000000-0000-0000-0000-000000000002"},
        {"name": "Personal", "id": "00000000-0000-0000-0000-000000000003"},
    ]

    def __init__(
        self,
        session: AsyncSession,
        pending_queue: Optional["PendingOperationsQueue"] = None
    ) -> None:
        """
        Initialize the list service.

        Args:
            session: Active database session for operations
            pending_queue: Optional PendingOperationsQueue for sync support
        """
        self.session = session
        self.pending_queue = pending_queue

    async def create_list(
        self,
        name: str,
        list_id: Optional[UUID] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> TaskList:
        """
        Create a new task list.

        Args:
            name: Name of the list to create
            list_id: Optional UUID for the list (auto-generated if not provided)
            created_at: Optional creation timestamp (for sync operations)
            updated_at: Optional update timestamp (for sync operations)

        Returns:
            Created TaskList model

        Raises:
            ValueError: If a list with the same name already exists
        """
        try:
            logger.debug(f"Creating list: name='{name}', list_id={list_id}")

            # Check if list with same name exists
            existing = await self.get_list_by_name(name)
            if existing:
                logger.warning(f"List creation failed - name already exists: '{name}'")
                raise ValueError(f"List with name '{name}' already exists")

            # Create list
            if list_id is None:
                list_id = uuid4()

            # Use provided timestamp or generate now
            if created_at is None:
                created_at = datetime.utcnow()

            list_orm = TaskListORM(
                id=str(list_id),
                name=name,
                created_at=created_at
            )

            self.session.add(list_orm)
            await self.session.flush()  # Ensure ID is available

            # Convert to Pydantic model
            task_list = TaskList(
                id=list_id,
                name=name,
                created_at=created_at
            )

            # Update counts
            task_count = await self._get_task_count(list_id)
            completed_count = await self._get_completed_count(list_id)
            task_list.update_counts(task_count, completed_count)

            # Queue for sync
            await self._queue_sync_operation(
                "LIST_CREATE",
                list_id,
                {
                    "list": {
                        "id": str(list_id),
                        "name": name,
                        "created_at": created_at.isoformat()
                    }
                }
            )

            logger.info(f"Created list: id={list_id}, name='{name}'")
            return task_list
        except ValueError:
            # Already logged, just re-raise
            raise
        except Exception as e:
            logger.error(f"Failed to create list: {e}", exc_info=True)
            raise

    async def get_all_lists(self) -> List[TaskList]:
        """
        Retrieve all task lists ordered by creation date.

        Returns:
            List of TaskList models with updated counts
        """
        result = await self.session.execute(
            select(TaskListORM).order_by(TaskListORM.created_at)
        )
        list_orms = result.scalars().all()

        return await self._orms_to_pydantic_with_counts(list_orms)

    async def get_list_by_id(self, list_id: UUID) -> Optional[TaskList]:
        """
        Retrieve a specific task list by ID.

        Args:
            list_id: UUID of the list to retrieve

        Returns:
            TaskList model if found, None otherwise
        """
        result = await self.session.execute(
            select(TaskListORM).where(TaskListORM.id == str(list_id))
        )
        list_orm = result.scalar_one_or_none()

        if not list_orm:
            return None

        return await self._orm_to_pydantic_with_counts(list_orm)

    async def get_list_by_name(self, name: str) -> Optional[TaskList]:
        """
        Retrieve a task list by name.

        Args:
            name: Name of the list to find

        Returns:
            TaskList model if found, None otherwise
        """
        result = await self.session.execute(
            select(TaskListORM).where(TaskListORM.name == name)
        )
        list_orm = result.scalar_one_or_none()

        if not list_orm:
            return None

        return await self._orm_to_pydantic_with_counts(list_orm)

    async def update_list(self, list_id: UUID, name: str) -> Optional[TaskList]:
        """
        Update a task list's name.

        Args:
            list_id: UUID of the list to update
            name: New name for the list

        Returns:
            Updated TaskList model if found, None otherwise

        Raises:
            ValueError: If a different list with the same name already exists
        """
        try:
            logger.debug(f"Updating list {list_id}: name='{name}'")

            # Check if list exists
            result = await self.session.execute(
                select(TaskListORM).where(TaskListORM.id == str(list_id))
            )
            list_orm = result.scalar_one_or_none()

            if not list_orm:
                logger.warning(f"Update failed - list not found: {list_id}")
                return None

            # Check if another list with same name exists
            existing = await self.get_list_by_name(name)
            if existing and existing.id != list_id:
                logger.warning(f"Update failed - name already exists: '{name}'")
                raise ValueError(f"List with name '{name}' already exists")

            # Update name
            old_name = list_orm.name
            list_orm.name = name
            await self.session.flush()

            # Return updated model
            task_list = await self._orm_to_pydantic_with_counts(list_orm)

            # Queue for sync
            await self._queue_sync_operation(
                "LIST_UPDATE",
                list_id,
                {
                    "list_id": str(list_id),
                    "changes": {
                        "name": name
                    }
                }
            )

            logger.info(f"Updated list: id={list_id}, '{old_name}' → '{name}'")
            return task_list
        except ValueError:
            # Already logged, just re-raise
            raise
        except Exception as e:
            logger.error(f"Failed to update list {list_id}: {e}", exc_info=True)
            raise

    async def _queue_sync_operation(
        self,
        operation: str,
        list_id: UUID,
        data: dict
    ) -> None:
        """
        Queue operation for sync if pending_queue is configured.

        Args:
            operation: Operation type (LIST_CREATE, LIST_UPDATE)
            list_id: UUID of the list
            data: Operation-specific data
        """
        if self.pending_queue:
            try:
                await self.pending_queue.add(operation, str(list_id), data)
                logger.debug(f"Queued {operation} for list {list_id}")
            except Exception as e:
                logger.warning(f"Failed to queue sync operation: {e}")

    async def delete_list(self, list_id: UUID) -> bool:
        """
        Delete a task list and all its tasks (cascade).

        Args:
            list_id: UUID of the list to delete

        Returns:
            True if list was deleted, False if not found
        """
        try:
            logger.debug(f"Deleting list {list_id}")

            result = await self.session.execute(
                select(TaskListORM).where(TaskListORM.id == str(list_id))
            )
            list_orm = result.scalar_one_or_none()

            if not list_orm:
                logger.warning(f"Delete failed - list not found: {list_id}")
                return False

            list_name = list_orm.name
            await self.session.delete(list_orm)
            await self.session.flush()

            logger.info(f"Deleted list: id={list_id}, name='{list_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to delete list {list_id}: {e}", exc_info=True)
            raise

    async def get_list_count(self) -> int:
        """
        Get the total number of task lists.

        Returns:
            Count of task lists
        """
        result = await self.session.execute(
            select(func.count(TaskListORM.id))
        )
        return result.scalar_one()

    async def migrate_tasks_and_delete_list(
        self,
        source_list_id: UUID,
        target_list_id: UUID
    ) -> bool:
        """
        Migrate all tasks from source list to target list, then delete source list.

        This operation is atomic - if any step fails, the entire operation is rolled back.

        Args:
            source_list_id: UUID of the list to delete
            target_list_id: UUID of the list to migrate tasks to

        Returns:
            True if successful, False if source list not found

        Raises:
            ValueError: If source and target are the same, target doesn't exist,
                       or attempting to delete the last list
        """
        try:
            logger.debug(
                f"Migrating tasks from list {source_list_id} to {target_list_id} "
                f"and deleting source list"
            )

            # Validate source and target are different
            if source_list_id == target_list_id:
                raise ValueError("Source and target lists must be different")

            # Verify source list exists
            source_list = await self.get_list_by_id(source_list_id)
            if not source_list:
                logger.warning(f"Migration failed - source list not found: {source_list_id}")
                return False

            # Verify target list exists
            target_list = await self.get_list_by_id(target_list_id)
            if not target_list:
                raise ValueError(f"Target list with id {target_list_id} not found")

            # Prevent deletion of last list
            list_count = await self.get_list_count()
            if list_count <= 1:
                raise ValueError("Cannot delete the last remaining list")

            # Migrate all tasks from source to target
            from taskui.services.task_service import TaskService
            task_service = TaskService(self.session)
            migrated_count = await task_service.bulk_migrate_tasks(
                source_list_id,
                target_list_id
            )

            # Delete the source list (now empty)
            await self.delete_list(source_list_id)

            logger.info(
                f"Successfully migrated {migrated_count} tasks from list "
                f"'{source_list.name}' to '{target_list.name}' and deleted source list"
            )
            return True
        except ValueError:
            # Already logged, just re-raise
            raise
        except Exception as e:
            logger.error(
                f"Failed to migrate tasks and delete list {source_list_id}: {e}",
                exc_info=True
            )
            raise


    async def ensure_default_lists(self) -> List[TaskList]:
        """
        Ensure default lists (Work, Home, Personal) exist.

        Creates default lists if they don't exist, typically called on first run.

        Returns:
            List of all task lists after ensuring defaults exist
        """
        try:
            logger.debug("Ensuring default lists exist")

            # Check which default lists exist by name
            existing_lists_by_name = {}
            all_lists = await self.get_all_lists()
            for task_list in all_lists:
                existing_lists_by_name[task_list.name] = task_list

            # Create missing default lists
            created_lists = []
            for default_list in self.DEFAULT_LISTS:
                if default_list["name"] not in existing_lists_by_name:
                    task_list = await self.create_list(
                        name=default_list["name"],
                        list_id=UUID(default_list["id"])
                    )
                    created_lists.append(default_list["name"])

            await self.session.commit()

            if created_lists:
                logger.info(f"Created default lists: {created_lists}")
            else:
                logger.debug("All default lists already exist")

            # Return all lists (existing + newly created)
            return await self.get_all_lists()
        except Exception as e:
            logger.error(f"Failed to ensure default lists: {e}", exc_info=True)
            raise

    async def _orm_to_pydantic_with_counts(
        self,
        list_orm: TaskListORM
    ) -> TaskList:
        """
        Convert TaskListORM to Pydantic with counts populated.

        Args:
            list_orm: SQLAlchemy task list instance

        Returns:
            Pydantic TaskList with counts
        """
        list_id = UUID(list_orm.id)

        task_list = TaskList(
            id=list_id,
            name=list_orm.name,
            created_at=list_orm.created_at
        )

        # Get counts
        task_count = await self._get_task_count(list_id)
        completed_count = await self._get_completed_count(list_id)
        task_list.update_counts(task_count, completed_count)

        return task_list

    async def _orms_to_pydantic_with_counts(
        self,
        list_orms: List[TaskListORM]
    ) -> List[TaskList]:
        """
        Convert list of TaskListORMs to Pydantic with counts.

        Args:
            list_orms: List of SQLAlchemy task list instances

        Returns:
            List of Pydantic TaskLists with counts
        """
        task_lists = []
        for list_orm in list_orms:
            task_list = await self._orm_to_pydantic_with_counts(list_orm)
            task_lists.append(task_list)
        return task_lists

    async def _get_task_count(self, list_id: UUID) -> int:
        """
        Get total number of tasks in a list.

        Args:
            list_id: UUID of the list

        Returns:
            Count of tasks
        """
        result = await self.session.execute(
            select(func.count(TaskORM.id))
            .where(TaskORM.list_id == str(list_id))
        )
        return result.scalar_one()

    async def _get_completed_count(self, list_id: UUID) -> int:
        """
        Get number of completed tasks in a list.

        Args:
            list_id: UUID of the list

        Returns:
            Count of completed tasks
        """
        result = await self.session.execute(
            select(func.count(TaskORM.id))
            .where(TaskORM.list_id == str(list_id))
            .where(TaskORM.is_completed == True)  # noqa: E712
        )
        return result.scalar_one()
