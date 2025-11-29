"""
Export/Import service for full-state sync.

Provides standalone export/import functionality as foundation for sync.
Can be used independently for backup/restore operations.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from taskui.logging_config import get_logger
from taskui.models import Task, TaskList
from taskui.export_schema import (
    ConflictStrategy,
    ExportedList,
    ExportedState,
    ExportedTask,
    CURRENT_SCHEMA_VERSION,
    migrate_data,
)
from taskui.services.list_service import ListService
from taskui.services.task_service import TaskService

logger = get_logger(__name__)


class ExportImportService:
    """
    Service for exporting and importing full application state.

    Supports:
    - Full state export (all lists and tasks)
    - Per-list export
    - Import with conflict resolution strategies
    - Schema migration for forward compatibility
    """

    def __init__(self, session: AsyncSession, client_id: str):
        """
        Initialize export/import service.

        Args:
            session: SQLAlchemy async session
            client_id: Unique identifier for this client/machine
        """
        self.session = session
        self.client_id = client_id
        self.list_service = ListService(session)
        self.task_service = TaskService(session)

    # =========================================================================
    # EXPORT FUNCTIONS
    # =========================================================================

    async def export_all_lists(self) -> ExportedState:
        """
        Export entire application state.

        Returns:
            ExportedState containing all lists and nested tasks
        """
        logger.info("Starting full state export")

        lists = await self.list_service.get_all_lists()
        exported_lists = []

        for task_list in lists:
            exported_list = await self._export_list_internal(task_list)
            exported_lists.append(exported_list)

        state = ExportedState(
            schema_version=CURRENT_SCHEMA_VERSION,
            exported_at=datetime.now(timezone.utc),
            client_id=self.client_id,
            lists=exported_lists,
        )

        logger.info(f"Exported {len(exported_lists)} lists")
        return state

    async def export_list(self, list_id: UUID) -> ExportedList:
        """
        Export a single list with all its tasks.

        Args:
            list_id: UUID of the list to export

        Returns:
            ExportedList containing all tasks as nested tree

        Raises:
            ValueError: If list not found
        """
        task_list = await self.list_service.get_list_by_id(list_id)
        if not task_list:
            raise ValueError(f"List not found: {list_id}")

        return await self._export_list_internal(task_list)

    async def _export_list_internal(self, task_list: TaskList) -> ExportedList:
        """
        Internal method to export a list.

        Args:
            task_list: TaskList to export

        Returns:
            ExportedList with nested tasks
        """
        # Get all tasks for this list
        all_tasks = await self.task_service.get_all_tasks_for_list(task_list.id)

        # Build nested tree structure
        nested_tasks = self._build_task_tree(all_tasks)

        # Calculate updated_at as max of all task timestamps
        updated_at = task_list.created_at
        for task in all_tasks:
            if task.created_at and task.created_at > updated_at:
                updated_at = task.created_at
            if task.completed_at and task.completed_at > updated_at:
                updated_at = task.completed_at

        return ExportedList(
            id=task_list.id,
            name=task_list.name,
            created_at=task_list.created_at,
            updated_at=updated_at,
            tasks=nested_tasks,
        )

    def _build_task_tree(self, tasks: List[Task]) -> List[ExportedTask]:
        """
        Build nested task tree from flat list.

        Args:
            tasks: Flat list of tasks

        Returns:
            List of top-level ExportedTask with nested children
        """
        # Index tasks by ID for fast lookup
        task_map: Dict[UUID, Task] = {task.id: task for task in tasks}

        # Index children by parent_id
        children_map: Dict[Optional[UUID], List[Task]] = {}
        for task in tasks:
            parent_id = task.parent_id
            if parent_id not in children_map:
                children_map[parent_id] = []
            children_map[parent_id].append(task)

        # Sort children by position
        for children in children_map.values():
            children.sort(key=lambda t: t.position)

        # Recursively build tree starting from root tasks (parent_id=None)
        def build_exported_task(task: Task) -> ExportedTask:
            children = children_map.get(task.id, [])
            return ExportedTask(
                id=task.id,
                title=task.title,
                notes=task.notes,
                url=task.url,
                is_completed=task.is_completed,
                position=task.position,
                created_at=task.created_at,
                completed_at=task.completed_at,
                children=[build_exported_task(child) for child in children],
            )

        root_tasks = children_map.get(None, [])
        return [build_exported_task(task) for task in root_tasks]

    # =========================================================================
    # IMPORT FUNCTIONS
    # =========================================================================

    async def import_all_lists(
        self,
        data: dict,
        strategy: ConflictStrategy = ConflictStrategy.NEWER_WINS,
    ) -> Tuple[int, int, List[str]]:
        """
        Import full application state.

        Args:
            data: Raw JSON data (will be migrated if needed)
            strategy: Conflict resolution strategy

        Returns:
            Tuple of (lists_imported, lists_skipped, conflict_messages)
        """
        logger.info(f"Starting full state import with strategy: {strategy}")

        # Migrate data to current schema
        data = migrate_data(data)

        # Parse into Pydantic model
        state = ExportedState.model_validate(data)

        lists_imported = 0
        lists_skipped = 0
        conflicts: List[str] = []

        for exported_list in state.lists:
            imported, conflict_msg = await self._import_list_internal(
                exported_list, strategy
            )
            if imported:
                lists_imported += 1
            else:
                lists_skipped += 1
                if conflict_msg:
                    conflicts.append(conflict_msg)

        logger.info(
            f"Import complete: {lists_imported} imported, {lists_skipped} skipped"
        )
        return lists_imported, lists_skipped, conflicts

    async def import_list(
        self,
        data: dict,
        strategy: ConflictStrategy = ConflictStrategy.NEWER_WINS,
    ) -> Tuple[bool, Optional[str]]:
        """
        Import a single list.

        Args:
            data: Raw JSON data for ExportedList
            strategy: Conflict resolution strategy

        Returns:
            Tuple of (success, conflict_message)
        """
        exported_list = ExportedList.model_validate(data)
        return await self._import_list_internal(exported_list, strategy)

    async def _import_list_internal(
        self,
        exported_list: ExportedList,
        strategy: ConflictStrategy,
    ) -> Tuple[bool, Optional[str]]:
        """
        Internal method to import a list with conflict resolution.

        Args:
            exported_list: ExportedList to import
            strategy: Conflict resolution strategy

        Returns:
            Tuple of (imported, conflict_message)
        """
        # Check if list exists locally
        local_list = await self.list_service.get_list_by_id(exported_list.id)

        if local_list:
            # Conflict resolution
            should_import, message = self._resolve_conflict(
                local_list,
                exported_list,
                strategy,
            )
            if not should_import:
                return False, message

            # Delete existing list (cascade deletes tasks)
            await self.list_service.delete_list(local_list.id)

        # Create list
        await self.list_service.create_list(
            name=exported_list.name,
            list_id=exported_list.id,
        )

        # Import tasks recursively
        await self._import_tasks_recursive(
            exported_list.id,
            exported_list.tasks,
            parent_id=None,
        )

        logger.info(f"Imported list: {exported_list.name} ({exported_list.id})")
        return True, None

    def _resolve_conflict(
        self,
        local_list: TaskList,
        remote_list: ExportedList,
        strategy: ConflictStrategy,
    ) -> Tuple[bool, Optional[str]]:
        """
        Resolve import conflict based on strategy.

        Args:
            local_list: Existing local list
            remote_list: Incoming remote list
            strategy: Resolution strategy

        Returns:
            Tuple of (should_import, conflict_message)
        """
        if strategy == ConflictStrategy.REMOTE_WINS:
            return True, None

        if strategy == ConflictStrategy.LOCAL_WINS:
            return False, f"Kept local version of '{local_list.name}'"

        if strategy == ConflictStrategy.NEWER_WINS:
            # Compare timestamps
            local_updated = local_list.created_at  # We don't track updated_at locally yet
            remote_updated = remote_list.updated_at

            # Normalize to UTC for comparison (handle tz-naive vs tz-aware)
            if local_updated.tzinfo is None:
                local_updated = local_updated.replace(tzinfo=timezone.utc)
            if remote_updated.tzinfo is None:
                remote_updated = remote_updated.replace(tzinfo=timezone.utc)

            if remote_updated > local_updated:
                return True, None
            else:
                return False, f"Local '{local_list.name}' is newer, skipped remote"

        if strategy == ConflictStrategy.PROMPT:
            # For PROMPT strategy, we return a conflict message
            # The caller should handle prompting the user
            return False, f"Conflict: List '{local_list.name}' exists locally. Remote updated: {remote_list.updated_at}"

        return True, None

    async def _import_tasks_recursive(
        self,
        list_id: UUID,
        tasks: List[ExportedTask],
        parent_id: Optional[UUID],
    ) -> None:
        """
        Recursively import tasks with proper parent relationships.

        Args:
            list_id: UUID of the parent list
            tasks: List of ExportedTask to import
            parent_id: Parent task UUID (None for root tasks)
        """
        for task in tasks:
            # Create the task
            await self.task_service.create_task(
                title=task.title,
                list_id=list_id,
                notes=task.notes,
                url=task.url,
                task_id=task.id,
                parent_id=parent_id,
                position=task.position,
                created_at=task.created_at,
            )

            # If task was completed, mark it
            if task.is_completed:
                await self.task_service.toggle_completion(task.id)

            # Recursively import children
            if task.children:
                await self._import_tasks_recursive(
                    list_id,
                    task.children,
                    parent_id=task.id,
                )

    # =========================================================================
    # FILE OPERATIONS (for CLI/backup)
    # =========================================================================

    async def export_to_file(self, filepath: str) -> None:
        """
        Export full state to a JSON file.

        Args:
            filepath: Path to output file
        """
        import json

        state = await self.export_all_lists()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(state.model_dump(mode="json"), f, indent=2, default=str)

        logger.info(f"Exported state to: {filepath}")

    async def import_from_file(
        self,
        filepath: str,
        strategy: ConflictStrategy = ConflictStrategy.NEWER_WINS,
    ) -> Tuple[int, int, List[str]]:
        """
        Import full state from a JSON file.

        Args:
            filepath: Path to input file
            strategy: Conflict resolution strategy

        Returns:
            Tuple of (lists_imported, lists_skipped, conflict_messages)
        """
        import json

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        return await self.import_all_lists(data, strategy)

    async def export_to_encrypted_file(
        self,
        filepath: str,
        encryption_key: str,
    ) -> None:
        """
        Export full state to an encrypted JSON file.

        Args:
            filepath: Path to output file
            encryption_key: Base64-encoded encryption key
        """
        from taskui.services.encryption import MessageEncryption

        state = await self.export_all_lists()
        data = state.model_dump(mode="json")

        # Encrypt the data
        encryption = MessageEncryption(encryption_key)
        encrypted_json = encryption.encrypt_message(data)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(encrypted_json)

        logger.info(f"Exported encrypted state to: {filepath}")

    async def import_from_encrypted_file(
        self,
        filepath: str,
        encryption_key: str,
        strategy: ConflictStrategy = ConflictStrategy.NEWER_WINS,
    ) -> Tuple[int, int, List[str]]:
        """
        Import full state from an encrypted JSON file.

        Args:
            filepath: Path to input file
            encryption_key: Base64-encoded encryption key
            strategy: Conflict resolution strategy

        Returns:
            Tuple of (lists_imported, lists_skipped, conflict_messages)
        """
        from taskui.services.encryption import MessageEncryption

        with open(filepath, "r", encoding="utf-8") as f:
            encrypted_json = f.read()

        # Decrypt the data
        encryption = MessageEncryption(encryption_key)
        data = encryption.decrypt_message(encrypted_json)

        return await self.import_all_lists(data, strategy)
