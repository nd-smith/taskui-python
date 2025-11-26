"""
Task service for TaskUI application.

Implements task creation and reading operations with database persistence
and nesting validation. Handles parent-child relationships and hierarchy management.
"""

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from taskui.database import TaskORM, TaskListORM
from taskui.logging_config import get_logger
from taskui.models import Task, TaskList

if TYPE_CHECKING:
    from taskui.services.pending_operations import PendingOperationsQueue

logger = get_logger(__name__)


class TaskServiceError(Exception):
    """Base exception for task service errors."""
    pass


class NestingLimitError(TaskServiceError):
    """Raised when nesting limit is exceeded."""
    pass


class TaskNotFoundError(TaskServiceError):
    """Raised when a task is not found."""
    pass


class TaskListNotFoundError(TaskServiceError):
    """Raised when a task list is not found."""
    pass


class TaskService:
    """
    Service layer for task operations.

    Handles CRUD operations for tasks with database persistence,
    nesting validation, and hierarchy management.
    """

    def __init__(
        self,
        session: AsyncSession,
        pending_queue: Optional["PendingOperationsQueue"] = None
    ) -> None:
        """
        Initialize task service with database session.

        Args:
            session: Active async database session
            pending_queue: Optional PendingOperationsQueue for sync support
        """
        self.session = session
        self.pending_queue = pending_queue

    async def _queue_sync_operation(
        self,
        operation: str,
        list_id: UUID,
        data: dict
    ) -> None:
        """
        Queue operation for sync if pending_queue is configured.

        Args:
            operation: Operation type (TASK_CREATE, TASK_UPDATE, etc.)
            list_id: UUID of the list
            data: Operation-specific data
        """
        if self.pending_queue:
            try:
                await self.pending_queue.add(operation, str(list_id), data)
                logger.debug(f"Queued sync operation: {operation} for list {list_id}")
            except Exception as e:
                logger.warning(f"Failed to queue sync operation {operation}: {e}")

    # ==============================================================================
    # CONVERSION HELPERS
    # ==============================================================================

    def _orm_to_pydantic(self, task_orm: TaskORM) -> Task:
        """
        Convert TaskORM to Pydantic Task model.

        Uses global MAX_NESTING_DEPTH for validation.

        Args:
            task_orm: SQLAlchemy ORM task instance

        Returns:
            Pydantic Task instance
        """
        from taskui.services.nesting_validation import MAX_NESTING_DEPTH

        # Use model_validate with context to pass max_level to validator
        return Task.model_validate(
            {
                "id": UUID(task_orm.id),
                "title": task_orm.title,
                "notes": task_orm.notes,
                "url": task_orm.url,
                "is_completed": task_orm.is_completed,
                "parent_id": UUID(task_orm.parent_id) if task_orm.parent_id else None,
                "level": task_orm.level,
                "position": task_orm.position,
                "list_id": UUID(task_orm.list_id),
                "created_at": task_orm.created_at,
                "completed_at": task_orm.completed_at,
            },
            context={"max_level": MAX_NESTING_DEPTH}
        )

    @staticmethod
    def _pydantic_to_orm(task: Task) -> TaskORM:
        """
        Convert Pydantic Task to TaskORM model.

        Args:
            task: Pydantic Task instance

        Returns:
            SQLAlchemy ORM task instance
        """
        return TaskORM(
            id=str(task.id),
            title=task.title,
            notes=task.notes,
            url=task.url,
            is_completed=task.is_completed,
            parent_id=str(task.parent_id) if task.parent_id else None,
            level=task.level,
            position=task.position,
            list_id=str(task.list_id),
            created_at=task.created_at,
            completed_at=task.completed_at,
        )

    # ==============================================================================
    # VALIDATION HELPERS
    # ==============================================================================

    async def _verify_list_exists(self, list_id: UUID) -> None:
        """
        Verify that a task list exists.

        Args:
            list_id: UUID of the task list

        Raises:
            TaskListNotFoundError: If list does not exist
        """
        result = await self.session.execute(
            select(TaskListORM).where(TaskListORM.id == str(list_id))
        )
        task_list = result.scalar_one_or_none()
        if not task_list:
            raise TaskListNotFoundError(f"Task list with id {list_id} not found")

    async def _get_task_or_raise(self, task_id: UUID) -> TaskORM:
        """
        Get a task by ID or raise an exception.

        Args:
            task_id: UUID of the task

        Returns:
            TaskORM instance

        Raises:
            TaskNotFoundError: If task does not exist
        """
        result = await self.session.execute(
            select(TaskORM).where(TaskORM.id == str(task_id))
        )
        task_orm = result.scalar_one_or_none()
        if not task_orm:
            raise TaskNotFoundError(f"Task with id {task_id} not found")
        return task_orm

    async def _get_next_position(self, list_id: UUID, parent_id: Optional[UUID] = None) -> int:
        """
        Get the next position for a task within its parent or list.

        Args:
            list_id: UUID of the task list
            parent_id: Optional parent task UUID

        Returns:
            Next position value
        """
        query = select(TaskORM).where(TaskORM.list_id == str(list_id))

        if parent_id is not None:
            query = query.where(TaskORM.parent_id == str(parent_id))
        else:
            query = query.where(TaskORM.parent_id.is_(None))

        result = await self.session.execute(query)
        siblings = result.scalars().all()

        if not siblings:
            return 0

        return max(task.position for task in siblings) + 1

    # ==============================================================================
    # QUERY HELPERS
    # ==============================================================================

    def _query_active_tasks(self, list_id: UUID):
        """
        Build query for tasks in a list.

        Args:
            list_id: List to query

        Returns:
            SQLAlchemy select statement
        """
        return (
            select(TaskORM)
            .where(TaskORM.list_id == str(list_id))
            .order_by(TaskORM.position)
        )

    def _query_top_level_tasks(self, list_id: UUID):
        """
        Build query for top-level tasks in a list.

        Args:
            list_id: List to query

        Returns:
            SQLAlchemy select statement
        """
        return (
            self._query_active_tasks(list_id)
            .where(TaskORM.parent_id.is_(None))
        )

    def _query_child_tasks(self, parent_id: UUID):
        """
        Build query for children of a parent task.

        Args:
            parent_id: Parent task ID

        Returns:
            SQLAlchemy select statement
        """
        return (
            select(TaskORM)
            .where(TaskORM.parent_id == str(parent_id))
            .order_by(TaskORM.position)
        )

    # ==============================================================================
    # FETCH HELPERS
    # ==============================================================================

    async def _fetch_task_with_counts(
        self,
        task_orm: TaskORM
    ) -> Task:
        """
        Convert ORM task to Pydantic with child counts populated.

        Args:
            task_orm: SQLAlchemy task instance

        Returns:
            Pydantic Task with child counts
        """
        task = self._orm_to_pydantic(task_orm)

        # Get child counts
        child_count, completed_child_count = await self._get_child_counts(task.id)
        task.update_child_counts(child_count, completed_child_count)

        return task

    async def _fetch_tasks_with_counts(
        self,
        task_orms: List[TaskORM]
    ) -> List[Task]:
        """
        Convert list of ORM tasks to Pydantic with child counts.

        Args:
            task_orms: List of SQLAlchemy task instances

        Returns:
            List of Pydantic Tasks with child counts
        """
        tasks = []
        for task_orm in task_orms:
            task = await self._fetch_task_with_counts(task_orm)
            tasks.append(task)
        return tasks

    # ==============================================================================
    # CREATE OPERATIONS
    # ==============================================================================

    async def create_task(
        self,
        title: str,
        list_id: UUID,
        notes: Optional[str] = None,
        url: Optional[str] = None,
        task_id: Optional[UUID] = None,
        parent_id: Optional[UUID] = None,
        position: Optional[int] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> Task:
        """
        Create a new task (top-level or child).

        Args:
            title: Task title
            list_id: UUID of the task list
            notes: Optional task notes
            url: Optional URL/link
            task_id: Optional UUID for the task (for sync operations)
            parent_id: Optional parent task UUID (for subtasks)
            position: Optional position (auto-calculated if not provided)
            created_at: Optional creation timestamp (for sync operations)
            updated_at: Optional update timestamp (for sync operations)

        Returns:
            Created Task instance

        Raises:
            TaskListNotFoundError: If list does not exist
            TaskNotFoundError: If parent task does not exist
            NestingLimitError: If nesting limit is exceeded
        """
        from taskui.services.nesting_validation import (
            can_create_child,
            get_child_level,
            NestingLimitError as ValidationNestingError,
            MAX_NESTING_DEPTH
        )

        try:
            logger.debug(f"Creating task: title='{title}', list_id={list_id}, parent_id={parent_id}")

            # Verify list exists
            await self._verify_list_exists(list_id)

            # Calculate level based on parent
            level = 0
            if parent_id is not None:
                parent_orm = await self._get_task_or_raise(parent_id)
                parent_task = self._orm_to_pydantic(parent_orm)

                # Validate nesting depth
                if not can_create_child(parent_task.level):
                    logger.warning(
                        f"Nesting limit reached: parent_level={parent_task.level}, "
                        f"max_depth={MAX_NESTING_DEPTH}"
                    )
                    raise NestingLimitError(
                        f"Cannot create child task. Parent task at level {parent_task.level} "
                        f"has reached maximum nesting depth ({MAX_NESTING_DEPTH})."
                    )

                try:
                    level = get_child_level(parent_task.level)
                except ValidationNestingError as e:
                    logger.error(f"Cannot determine child level: parent_level={parent_task.level}")
                    raise NestingLimitError(str(e))

            # Get position if not provided
            if position is None:
                position = await self._get_next_position(list_id, parent_id=parent_id)

            # Build task data
            task_data = {
                'title': title,
                'notes': notes,
                'url': url,
                'list_id': list_id,
                'level': level,
                'position': position,
                'parent_id': parent_id,
            }

            # Add optional sync fields
            if task_id is not None:
                task_data['id'] = task_id
            if created_at is not None:
                task_data['created_at'] = created_at

            # Create task with validation context
            task = Task.model_validate(
                task_data,
                context={'max_level': MAX_NESTING_DEPTH}
            )

            # Convert to ORM and save
            task_orm = self._pydantic_to_orm(task)
            self.session.add(task_orm)
            await self.session.flush()  # Flush to get the ID

            # Queue for sync (only if not from sync - i.e., task_id was not provided)
            if task_id is None:
                await self._queue_sync_operation(
                    "TASK_CREATE",
                    list_id,
                    {
                        "task": {
                            "id": str(task.id),
                            "title": task.title,
                            "notes": task.notes,
                            "url": task.url,
                            "parent_id": str(parent_id) if parent_id else None,
                            "level": task.level,
                            "position": task.position,
                            "is_completed": task.is_completed,
                            "created_at": task.created_at.isoformat() if task.created_at else None
                        }
                    }
                )

            logger.info(f"Created task: id={task.id}, title='{title}', level={level}")
            return task
        except (TaskListNotFoundError, TaskNotFoundError, NestingLimitError) as e:
            logger.error(f"Failed to create task: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Failed to create task: {e}", exc_info=True)
            raise

    async def create_child_task(
        self,
        parent_id: UUID,
        title: str,
        notes: Optional[str] = None,
        url: Optional[str] = None,
    ) -> Task:
        """
        Create a child task under a parent task with nesting validation.

        Args:
            parent_id: UUID of the parent task
            title: Child task title
            notes: Optional task notes
            url: Optional URL/link

        Returns:
            Created Task instance

        Raises:
            TaskNotFoundError: If parent task does not exist
            NestingLimitError: If nesting limit is exceeded
        """
        from taskui.services.nesting_validation import (
            can_create_child,
            get_child_level,
            NestingLimitError as ValidationNestingError,
            MAX_NESTING_DEPTH
        )

        try:
            logger.debug(f"Creating child task: title='{title}', parent_id={parent_id}")

            # Get parent task
            parent_orm = await self._get_task_or_raise(parent_id)
            parent_task = self._orm_to_pydantic(parent_orm)

            # Validate nesting depth
            if not can_create_child(parent_task.level):
                logger.warning(
                    f"Nesting limit reached: parent_level={parent_task.level}, "
                    f"max_depth={MAX_NESTING_DEPTH}"
                )
                raise NestingLimitError(
                    f"Cannot create child task. Parent task at level {parent_task.level} "
                    f"has reached maximum nesting depth ({MAX_NESTING_DEPTH})."
                )

            # Calculate child level
            try:
                child_level = get_child_level(parent_task.level)
            except ValidationNestingError as e:
                logger.error(f"Cannot determine child level: parent_level={parent_task.level}")
                raise NestingLimitError(str(e))

            # Get next position among siblings
            position = await self._get_next_position(parent_task.list_id, parent_id=parent_id)

            # Create child task
            child_task = Task.model_validate(
                {
                    'title': title,
                    'notes': notes,
                    'url': url,
                    'list_id': parent_task.list_id,
                    'parent_id': parent_id,
                    'level': child_level,
                    'position': position,
                },
                context={'max_level': MAX_NESTING_DEPTH}
            )

            # Convert to ORM and save
            task_orm = self._pydantic_to_orm(child_task)
            self.session.add(task_orm)
            await self.session.flush()

            # Queue for sync
            await self._queue_sync_operation(
                "TASK_CREATE",
                parent_task.list_id,
                {
                    "task": {
                        "id": str(child_task.id),
                        "title": child_task.title,
                        "notes": child_task.notes,
                        "url": child_task.url,
                        "parent_id": str(parent_id),
                        "level": child_task.level,
                        "position": child_task.position,
                        "is_completed": child_task.is_completed,
                        "created_at": child_task.created_at.isoformat() if child_task.created_at else None
                    }
                }
            )

            logger.info(
                f"Created child task: id={child_task.id}, title='{title}', "
                f"level={child_level}, parent_id={parent_id}"
            )
            return child_task
        except (TaskNotFoundError, NestingLimitError):
            # These are already logged above, just re-raise
            raise
        except Exception as e:
            logger.error(f"Failed to create child task: {e}", exc_info=True)
            raise

    # ==============================================================================
    # READ OPERATIONS
    # ==============================================================================

    async def get_tasks_for_list(self, list_id: UUID) -> List[Task]:
        """
        Get all top-level tasks (level 0) for a task list.

        Args:
            list_id: UUID of the task list

        Returns:
            List of Task instances ordered by position

        Raises:
            TaskListNotFoundError: If list does not exist
        """
        # Verify list exists
        await self._verify_list_exists(list_id)

        # Build query using helper for active tasks only
        query = self._query_top_level_tasks(list_id)

        # Execute query
        result = await self.session.execute(query)
        task_orms = result.scalars().all()

        # Convert to Pydantic with counts using helper
        return await self._fetch_tasks_with_counts(task_orms)

    async def get_children(self, parent_id: UUID) -> List[Task]:
        """
        Get all direct children of a parent task.

        Args:
            parent_id: UUID of the parent task

        Returns:
            List of Task instances ordered by position

        Raises:
            TaskNotFoundError: If parent task does not exist
        """
        # Verify parent exists
        await self._get_task_or_raise(parent_id)

        # Build query using helper for active tasks only
        query = self._query_child_tasks(parent_id)

        # Execute query
        result = await self.session.execute(query)
        task_orms = result.scalars().all()

        # Convert to Pydantic with counts using helper
        return await self._fetch_tasks_with_counts(task_orms)

    async def get_all_descendants(
        self,
        parent_id: UUID
    ) -> List[Task]:
        """
        Get all descendants (children, grandchildren, etc.) of a parent task.

        Returns tasks in hierarchical order (depth-first traversal).

        Args:
            parent_id: UUID of the parent task

        Returns:
            List of all descendant Task instances in hierarchical order

        Raises:
            TaskNotFoundError: If parent task does not exist
        """
        # Verify parent exists
        await self._get_task_or_raise(parent_id)

        descendants = []

        # Helper function for recursive traversal
        async def collect_descendants(current_parent_id: UUID) -> None:
            children = await self.get_children(current_parent_id)
            for child in children:
                descendants.append(child)
                # Recursively get this child's descendants
                await collect_descendants(child.id)

        await collect_descendants(parent_id)

        return descendants

    async def get_task_by_id(self, task_id: UUID) -> Optional[Task]:
        """
        Get a task by its ID.

        Args:
            task_id: UUID of the task

        Returns:
            Task instance or None if not found
        """
        result = await self.session.execute(
            select(TaskORM).where(TaskORM.id == str(task_id))
        )
        task_orm = result.scalar_one_or_none()

        if not task_orm:
            return None

        # Convert to Pydantic with counts using helper
        return await self._fetch_task_with_counts(task_orm)

    # ==============================================================================
    # UPDATE OPERATIONS
    # ==============================================================================

    async def update_task(
        self,
        task_id: UUID,
        title: Optional[str] = None,
        notes: Optional[str] = None,
        url: Optional[str] = None,
    ) -> Task:
        """
        Update a task's properties (title, notes, and/or URL).

        Args:
            task_id: UUID of the task to update
            title: New title (if provided)
            notes: New notes (if provided)
            url: New URL (if provided)

        Returns:
            Updated Task instance

        Raises:
            TaskNotFoundError: If task does not exist
            ValueError: If no fields are provided for update
        """
        if title is None and notes is None and url is None:
            raise ValueError("At least one of title, notes, or url must be provided")

        try:
            logger.debug(f"Updating task {task_id}: title={title}, notes={'<provided>' if notes else None}, url={'<provided>' if url else None}")

            # Get existing task
            task_orm = await self._get_task_or_raise(task_id)

            # Update fields
            if title is not None:
                task_orm.title = title
            if notes is not None:
                task_orm.notes = notes
            if url is not None:
                task_orm.url = url

            # Flush changes to database
            await self.session.flush()

            # Convert back to Pydantic with counts using helper
            task = await self._fetch_task_with_counts(task_orm)

            # Queue for sync
            await self._queue_sync_operation(
                "TASK_UPDATE",
                UUID(task_orm.list_id),
                {
                    "task_id": str(task_id),
                    "changes": {
                        k: v for k, v in [
                            ("title", title),
                            ("notes", notes),
                            ("url", url)
                        ] if v is not None
                    }
                }
            )

            logger.info(f"Updated task: id={task_id}, title='{task.title}'")
            return task
        except TaskNotFoundError as e:
            logger.error(f"Failed to update task - not found: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}", exc_info=True)
            raise

    async def toggle_completion(self, task_id: UUID) -> Task:
        """
        Toggle the completion status of a task.

        If the task is currently completed, it will be marked as incomplete.
        If the task is currently incomplete, it will be marked as completed.

        Args:
            task_id: UUID of the task to toggle

        Returns:
            Updated Task instance

        Raises:
            TaskNotFoundError: If task does not exist
        """
        # Get the task
        task_orm = await self._get_task_or_raise(task_id)

        # Toggle completion status
        if task_orm.is_completed:
            # Mark as incomplete
            task_orm.is_completed = False
            task_orm.completed_at = None
            new_state = False
            logger.info(
                f"Task completion toggled: task_id={task_id}, "
                f"new_state=incomplete, timestamp={datetime.utcnow().isoformat()}"
            )
        else:
            # Mark as completed
            task_orm.is_completed = True
            task_orm.completed_at = datetime.utcnow()
            new_state = True
            logger.info(
                f"Task completion toggled: task_id={task_id}, "
                f"new_state=completed, timestamp={task_orm.completed_at.isoformat()}"
            )

        # Flush changes to database
        try:
            await self.session.flush()
        except Exception as e:
            logger.error(
                f"Database update failed for task completion toggle: task_id={task_id}",
                exc_info=True
            )
            raise

        # Queue for sync
        await self._queue_sync_operation(
            "TASK_UPDATE",
            UUID(task_orm.list_id),
            {
                "task_id": str(task_id),
                "changes": {
                    "is_completed": task_orm.is_completed,
                    "completed_at": task_orm.completed_at.isoformat() if task_orm.completed_at else None
                }
            }
        )

        # Convert back to Pydantic with counts using helper
        return await self._fetch_task_with_counts(task_orm)

    # ==============================================================================
    # DELETE/ARCHIVE OPERATIONS
    # ==============================================================================

    async def delete_task(self, task_id: UUID) -> None:
        """
        Delete a task and all its descendants (cascade delete).

        This method recursively deletes the task and all its children, grandchildren, etc.,
        ensuring referential integrity is maintained.

        Args:
            task_id: UUID of the task to delete

        Raises:
            TaskNotFoundError: If task does not exist
        """
        try:
            logger.debug(f"Deleting task {task_id} and descendants")

            # Get task to delete
            task_orm = await self._get_task_or_raise(task_id)
            task_title = task_orm.title
            task_list_id = UUID(task_orm.list_id)

            # Queue for sync BEFORE deletion (need list_id)
            await self._queue_sync_operation(
                "TASK_DELETE",
                task_list_id,
                {
                    "task_id": str(task_id),
                    "cascade": True
                }
            )

            # Get all descendants for cascade deletion
            descendants = await self.get_all_descendants(task_id)
            descendant_count = len(descendants)

            # Delete descendants in reverse hierarchical order (deepest first)
            # This ensures we don't violate foreign key constraints
            for descendant in reversed(descendants):
                descendant_orm = await self._get_task_or_raise(descendant.id)
                await self.session.delete(descendant_orm)

            # Delete the task itself
            await self.session.delete(task_orm)

            # Flush the deletions
            await self.session.flush()

            logger.info(f"Deleted task: id={task_id}, title='{task_title}', descendants={descendant_count}")
        except TaskNotFoundError as e:
            logger.error(f"Failed to delete task - not found: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}", exc_info=True)
            raise





    async def bulk_migrate_tasks(
        self,
        source_list_id: UUID,
        target_list_id: UUID
    ) -> int:
        """
        Migrate all tasks from one list to another.

        This updates the list_id for all tasks (including archived tasks) from the
        source list to the target list. The task hierarchy is preserved.

        Args:
            source_list_id: UUID of the source list
            target_list_id: UUID of the target list

        Returns:
            Number of tasks migrated

        Raises:
            TaskListNotFoundError: If either list does not exist
        """
        from sqlalchemy import update

        try:
            logger.debug(
                f"Bulk migrating tasks from list {source_list_id} to {target_list_id}"
            )

            # Verify both lists exist
            await self._verify_list_exists(source_list_id)
            await self._verify_list_exists(target_list_id)

            # Update all tasks in the source list to point to the target list
            result = await self.session.execute(
                update(TaskORM)
                .where(TaskORM.list_id == str(source_list_id))
                .values(list_id=str(target_list_id))
            )

            migrated_count = result.rowcount

            await self.session.flush()

            logger.info(
                f"Bulk migrated {migrated_count} tasks from list "
                f"{source_list_id} to {target_list_id}"
            )

            return migrated_count
        except TaskListNotFoundError:
            # Already logged, just re-raise
            raise
        except Exception as e:
            logger.error(
                f"Failed to bulk migrate tasks from {source_list_id} to {target_list_id}: {e}",
                exc_info=True
            )
            raise


    # ==============================================================================
    # HIERARCHY OPERATIONS
    # ==============================================================================

    async def move_task(
        self,
        task_id: UUID,
        new_parent_id: Optional[UUID] = None,
        new_position: Optional[int] = None,
    ) -> Task:
        """
        Move a task to a new parent and/or position.

        This method handles:
        - Moving to a different parent (including moving to top-level by setting parent to None)
        - Reordering within the same parent
        - Updating positions of affected siblings

        Args:
            task_id: UUID of the task to move
            new_parent_id: New parent ID (None for top-level), if changing parent
            new_position: New position within siblings (None to append at end)

        Returns:
            Updated Task instance

        Raises:
            TaskNotFoundError: If task or new parent does not exist
            NestingLimitError: If move would violate nesting rules
            ValueError: If trying to move task to be its own descendant
        """
        from sqlalchemy import update

        # Get the task to move
        task_orm = await self._get_task_or_raise(task_id)
        old_parent_id = UUID(task_orm.parent_id) if task_orm.parent_id else None
        old_position = task_orm.position

        # Validate we're not trying to move a task to be its own descendant
        if new_parent_id is not None:
            if new_parent_id == task_id:
                raise ValueError("Cannot move task to be its own parent")

            # Check if new_parent_id is a descendant of task_id
            descendants = await self.get_all_descendants(task_id)
            if any(d.id == new_parent_id for d in descendants):
                raise ValueError("Cannot move task to be a descendant of itself")

        # Determine new parent and validate nesting
        new_parent_orm = None
        new_level = 0

        if new_parent_id is not None:
            new_parent_orm = await self._get_task_or_raise(new_parent_id)
            new_parent_task = self._orm_to_pydantic(new_parent_orm)

            # Calculate new level (parent's level + 1)
            new_level = new_parent_task.level + 1

            # Validate level is within bounds (0-2)
            if new_level > 2:
                raise NestingLimitError(
                    f"Cannot move task. New level ({new_level}) would exceed maximum (2)"
                )

        # Get siblings at the new location
        sibling_query = select(TaskORM).where(
            TaskORM.list_id == task_orm.list_id
        )

        if new_parent_id is not None:
            sibling_query = sibling_query.where(TaskORM.parent_id == str(new_parent_id))
        else:
            sibling_query = sibling_query.where(TaskORM.parent_id.is_(None))

        # Exclude the task being moved from siblings
        sibling_query = sibling_query.where(TaskORM.id != str(task_id))
        sibling_query = sibling_query.order_by(TaskORM.position)

        result = await self.session.execute(sibling_query)
        siblings = list(result.scalars().all())

        # Determine final position
        if new_position is None:
            final_position = len(siblings)
        else:
            final_position = min(max(0, new_position), len(siblings))

        # Update the task being moved
        task_orm.parent_id = str(new_parent_id) if new_parent_id else None
        task_orm.level = new_level
        task_orm.position = final_position

        # Update positions of siblings at new location
        for idx, sibling in enumerate(siblings):
            if idx >= final_position:
                sibling.position = idx + 1
            else:
                sibling.position = idx

        # If moving from a different parent, reorder old siblings
        if old_parent_id != new_parent_id:
            old_sibling_query = select(TaskORM).where(
                TaskORM.list_id == task_orm.list_id
            )

            if old_parent_id is not None:
                old_sibling_query = old_sibling_query.where(
                    TaskORM.parent_id == str(old_parent_id)
                )
            else:
                old_sibling_query = old_sibling_query.where(TaskORM.parent_id.is_(None))

            old_sibling_query = old_sibling_query.order_by(TaskORM.position)

            result = await self.session.execute(old_sibling_query)
            old_siblings = result.scalars().all()

            # Reorder old siblings
            for idx, sibling in enumerate(old_siblings):
                sibling.position = idx

        # Update descendants' levels recursively
        await self._update_descendant_levels(task_id, new_level)

        # Flush changes
        await self.session.flush()

        # Queue for sync
        await self._queue_sync_operation(
            "TASK_MOVE",
            UUID(task_orm.list_id),
            {
                "task_id": str(task_id),
                "new_parent_id": str(new_parent_id) if new_parent_id else None,
                "new_position": final_position
            }
        )

        # Return updated task with counts using helper
        return await self._fetch_task_with_counts(task_orm)

    async def _update_descendant_levels(
        self,
        parent_id: UUID,
        parent_level: int
    ) -> None:
        """
        Recursively update levels of all descendants when a parent is moved.

        Args:
            parent_id: UUID of the parent task
            parent_level: New level of the parent task
        """
        # Get direct children
        children = await self.get_children(parent_id)

        for child in children:
            # Update child level
            child_orm = await self._get_task_or_raise(child.id)
            new_child_level = parent_level + 1

            # Validate level bounds
            if new_child_level > 2:
                raise NestingLimitError(
                    f"Cannot move task. Descendant at level {new_child_level} "
                    f"would exceed maximum level (2)"
                )

            child_orm.level = new_child_level

            # Recursively update grandchildren
            await self._update_descendant_levels(child.id, new_child_level)

    # ==============================================================================
    # COUNTING HELPERS
    # ==============================================================================

    async def _get_child_counts(self, parent_id: UUID) -> tuple[int, int]:
        """
        Get the total and completed child counts for a task, including all descendants.

        Args:
            parent_id: UUID of the parent task

        Returns:
            Tuple of (total_descendants, completed_descendants)
        """
        try:
            total_count = 0
            completed_count = 0

            # Recursive helper to count descendants at all levels
            async def count_descendants(current_parent_id: UUID) -> None:
                nonlocal total_count, completed_count

                # Get all direct children
                query = select(TaskORM).where(
                    TaskORM.parent_id == str(current_parent_id),
                )

                result = await self.session.execute(query)
                children = result.scalars().all()

                # Process each child
                for child in children:
                    total_count += 1
                    if child.is_completed:
                        completed_count += 1

                    # Recursively count descendants
                    await count_descendants(UUID(child.id))

            await count_descendants(parent_id)

            logger.debug(
                f"Progress calculation updated: task_id={parent_id}, "
                f"completed_count={completed_count}, total_count={total_count}"
            )

            return total_count, completed_count
        except Exception as e:
            logger.error(
                f"Progress calculation error for task_id={parent_id}",
                exc_info=True
            )
            raise
