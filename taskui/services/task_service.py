"""
Task service for TaskUI application.

Implements task creation and reading operations with database persistence
and nesting validation. Handles parent-child relationships and hierarchy management.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from taskui.database import TaskORM, TaskListORM
from taskui.logging_config import get_logger
from taskui.models import Task, TaskList
from taskui.services.nesting_rules import Column, NestingRules

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
        nesting_rules: Optional[NestingRules] = None
    ) -> None:
        """
        Initialize task service with database session and optional nesting rules.

        Args:
            session: Active async database session
            nesting_rules: Optional NestingRules instance for validation.
                          If None, uses class methods (deprecated) for backward compatibility.
        """
        self.session = session
        self._nesting_rules = nesting_rules

    # ==============================================================================
    # CONVERSION HELPERS
    # ==============================================================================

    def _orm_to_pydantic(self, task_orm: TaskORM) -> Task:
        """
        Convert TaskORM to Pydantic Task model.

        Uses dynamic max_level from nesting rules config for validation.

        Args:
            task_orm: SQLAlchemy ORM task instance

        Returns:
            Pydantic Task instance
        """
        # Get max level from config for validation context
        # Use the maximum of column1 and column2 to allow loading any task
        if self._nesting_rules:
            max_level = max(
                self._nesting_rules.get_max_depth_instance(Column.COLUMN1),
                self._nesting_rules.get_max_depth_instance(Column.COLUMN2)
            )
        else:
            max_level = 2  # Backward compatibility default

        # Use model_validate with context to pass max_level to validator
        return Task.model_validate(
            {
                "id": UUID(task_orm.id),
                "title": task_orm.title,
                "notes": task_orm.notes,
                "is_completed": task_orm.is_completed,
                "is_archived": task_orm.is_archived,
                "parent_id": UUID(task_orm.parent_id) if task_orm.parent_id else None,
                "level": task_orm.level,
                "position": task_orm.position,
                "list_id": UUID(task_orm.list_id),
                "created_at": task_orm.created_at,
                "completed_at": task_orm.completed_at,
                "archived_at": task_orm.archived_at,
            },
            context={"max_level": max_level}
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
            is_completed=task.is_completed,
            is_archived=task.is_archived,
            parent_id=str(task.parent_id) if task.parent_id else None,
            level=task.level,
            position=task.position,
            list_id=str(task.list_id),
            created_at=task.created_at,
            completed_at=task.completed_at,
            archived_at=task.archived_at,
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
        Build query for active (non-archived) tasks in a list.

        Args:
            list_id: List to query

        Returns:
            SQLAlchemy select statement
        """
        return (
            select(TaskORM)
            .where(TaskORM.list_id == str(list_id))
            .where(TaskORM.is_archived == False)
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
            .where(TaskORM.is_archived == False)
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
    ) -> Task:
        """
        Create a new top-level task (level 0).

        Args:
            title: Task title
            list_id: UUID of the task list
            notes: Optional task notes

        Returns:
            Created Task instance

        Raises:
            TaskListNotFoundError: If list does not exist
        """
        try:
            logger.debug(f"Creating top-level task: title='{title}', list_id={list_id}")

            # Verify list exists
            await self._verify_list_exists(list_id)

            # Get next position
            position = await self._get_next_position(list_id, parent_id=None)

            # Determine max_level for validation context
            # Top-level tasks are in column1, so use column1's max_depth if available
            if self._nesting_rules:
                max_level = self._nesting_rules.get_max_depth_instance(Column.COLUMN1)
            else:
                # Backward compatibility: use max of all columns
                max_level = 2

            # Create task with validation context
            task = Task.model_validate(
                {
                    'title': title,
                    'notes': notes,
                    'list_id': list_id,
                    'level': 0,
                    'position': position,
                    'parent_id': None,
                },
                context={'max_level': max_level}
            )

            # Convert to ORM and save
            task_orm = self._pydantic_to_orm(task)
            self.session.add(task_orm)
            await self.session.flush()  # Flush to get the ID

            logger.info(f"Created task: id={task.id}, title='{title}', level=0")
            return task
        except TaskListNotFoundError as e:
            logger.error(f"Failed to create task - list not found: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Failed to create task: {e}", exc_info=True)
            raise

    async def create_child_task(
        self,
        parent_id: UUID,
        title: str,
        column: Column,
        notes: Optional[str] = None,
    ) -> Task:
        """
        Create a child task under a parent task with nesting validation.

        Args:
            parent_id: UUID of the parent task
            title: Child task title
            column: Column context (COLUMN1 or COLUMN2)
            notes: Optional task notes

        Returns:
            Created Task instance

        Raises:
            TaskNotFoundError: If parent task does not exist
            NestingLimitError: If nesting limit is exceeded
        """
        try:
            logger.debug(f"Creating child task: title='{title}', parent_id={parent_id}, column={column}")

            # Get parent task
            parent_orm = await self._get_task_or_raise(parent_id)
            parent_task = self._orm_to_pydantic(parent_orm)

            # Validate nesting rules (use instance if available, otherwise class methods)
            if self._nesting_rules:
                can_create = self._nesting_rules.can_create_child_instance(parent_task, column)
                max_depth = self._nesting_rules.get_max_depth_instance(column)
            else:
                # Backward compatibility: use deprecated class methods
                can_create = NestingRules.can_create_child(parent_task, column)
                max_depth = NestingRules.get_max_depth(column)

            if not can_create:
                logger.warning(f"Nesting limit reached: parent_level={parent_task.level}, max_depth={max_depth}, column={column}")
                raise NestingLimitError(
                    f"Cannot create child task. Parent task at level {parent_task.level} "
                    f"has reached maximum nesting depth ({max_depth}) for {column.value}."
                )

            # Get the allowed child level
            if self._nesting_rules:
                child_level = self._nesting_rules.get_allowed_child_level_instance(parent_task, column)
            else:
                # Backward compatibility: use deprecated class methods
                child_level = NestingRules.get_allowed_child_level(parent_task, column)
            if child_level is None:
                logger.error(f"Cannot determine child level: parent_level={parent_task.level}, column={column}")
                raise NestingLimitError(
                    f"Cannot determine child level for parent at level {parent_task.level} "
                    f"in {column.value}."
                )

            # Get next position among siblings
            position = await self._get_next_position(parent_task.list_id, parent_id=parent_id)

            # Create child task with validation context
            # Use the column's max_depth as max_level for validation
            child_task = Task.model_validate(
                {
                    'title': title,
                    'notes': notes,
                    'list_id': parent_task.list_id,
                    'parent_id': parent_id,
                    'level': child_level,
                    'position': position,
                },
                context={'max_level': max_depth}
            )

            # Convert to ORM and save
            task_orm = self._pydantic_to_orm(child_task)
            self.session.add(task_orm)
            await self.session.flush()

            logger.info(f"Created child task: id={child_task.id}, title='{title}', level={child_level}, parent_id={parent_id}")
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

    async def get_tasks_for_list(self, list_id: UUID, include_archived: bool = False) -> List[Task]:
        """
        Get all top-level tasks (level 0) for a task list.

        Args:
            list_id: UUID of the task list
            include_archived: Whether to include archived tasks

        Returns:
            List of Task instances ordered by position

        Raises:
            TaskListNotFoundError: If list does not exist
        """
        # Verify list exists
        await self._verify_list_exists(list_id)

        # Build query using helper
        if include_archived:
            # Build query manually when including archived
            query = (
                select(TaskORM)
                .where(TaskORM.list_id == str(list_id))
                .where(TaskORM.parent_id.is_(None))
                .order_by(TaskORM.position)
            )
        else:
            # Use helper for active tasks only
            query = self._query_top_level_tasks(list_id)

        # Execute query
        result = await self.session.execute(query)
        task_orms = result.scalars().all()

        # Convert to Pydantic with counts using helper
        return await self._fetch_tasks_with_counts(task_orms)

    async def get_children(self, parent_id: UUID, include_archived: bool = False) -> List[Task]:
        """
        Get all direct children of a parent task.

        Args:
            parent_id: UUID of the parent task
            include_archived: Whether to include archived tasks

        Returns:
            List of Task instances ordered by position

        Raises:
            TaskNotFoundError: If parent task does not exist
        """
        # Verify parent exists
        await self._get_task_or_raise(parent_id)

        # Build query using helper
        if include_archived:
            # Build query manually when including archived
            query = (
                select(TaskORM)
                .where(TaskORM.parent_id == str(parent_id))
                .order_by(TaskORM.position)
            )
        else:
            # Use helper for active tasks only
            query = self._query_child_tasks(parent_id)

        # Execute query
        result = await self.session.execute(query)
        task_orms = result.scalars().all()

        # Convert to Pydantic with counts using helper
        return await self._fetch_tasks_with_counts(task_orms)

    async def get_all_descendants(
        self,
        parent_id: UUID,
        include_archived: bool = False
    ) -> List[Task]:
        """
        Get all descendants (children, grandchildren, etc.) of a parent task.

        Returns tasks in hierarchical order (depth-first traversal).

        Args:
            parent_id: UUID of the parent task
            include_archived: Whether to include archived tasks

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
            children = await self.get_children(current_parent_id, include_archived=include_archived)
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
    ) -> Task:
        """
        Update a task's properties (title and/or notes).

        Args:
            task_id: UUID of the task to update
            title: New title (if provided)
            notes: New notes (if provided)

        Returns:
            Updated Task instance

        Raises:
            TaskNotFoundError: If task does not exist
            ValueError: If neither title nor notes is provided
        """
        if title is None and notes is None:
            raise ValueError("At least one of title or notes must be provided")

        try:
            logger.debug(f"Updating task {task_id}: title={title}, notes={'<provided>' if notes else None}")

            # Get existing task
            task_orm = await self._get_task_or_raise(task_id)

            # Update fields
            if title is not None:
                task_orm.title = title
            if notes is not None:
                task_orm.notes = notes

            # Flush changes to database
            await self.session.flush()

            # Convert back to Pydantic with counts using helper
            task = await self._fetch_task_with_counts(task_orm)

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

            # Get all descendants for cascade deletion
            descendants = await self.get_all_descendants(task_id, include_archived=True)
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

    async def archive_task(self, task_id: UUID) -> Task:
        """
        Archive a completed task and all its descendants.

        This operation cascades to all descendants to prevent orphaned tasks.
        Note: This only archives the parent if it's completed, but will archive
        all descendants regardless of their completion status.

        Args:
            task_id: UUID of the task to archive

        Returns:
            Updated Task instance

        Raises:
            TaskNotFoundError: If task does not exist
            ValueError: If task is not completed
        """
        # Get the task
        task_orm = await self._get_task_or_raise(task_id)

        # Check if task is completed
        if not task_orm.is_completed:
            logger.warning(
                f"Attempted to archive incomplete task: task_id={task_id}"
            )
            raise ValueError("Only completed tasks can be archived")

        archive_time = datetime.utcnow()

        # Get all descendants for cascade archiving
        descendants = await self.get_all_descendants(task_id, include_archived=False)
        descendant_count = len(descendants)

        # Archive all descendants (deepest first to maintain integrity)
        for descendant in reversed(descendants):
            descendant_orm = await self._get_task_or_raise(descendant.id)
            descendant_orm.is_archived = True
            descendant_orm.archived_at = archive_time

        # Archive the task itself
        task_orm.is_archived = True
        task_orm.archived_at = archive_time

        logger.info(
            f"Task archived: task_id={task_id}, "
            f"archive_timestamp={task_orm.archived_at.isoformat()}, "
            f"descendants_archived={descendant_count}"
        )

        # Flush changes to database
        try:
            await self.session.flush()
        except Exception as e:
            logger.error(
                f"Archive operation failed for task_id={task_id}",
                exc_info=True
            )
            raise

        # Convert back to Pydantic with counts using helper
        return await self._fetch_task_with_counts(task_orm)

    async def soft_delete_task(self, task_id: UUID) -> Task:
        """
        Soft delete a task by archiving it and all its descendants.

        This provides a "delete" operation that is recoverable via the archive/restore
        functionality. Unlike archive_task(), this does not require the task to be completed.
        This operation cascades to all descendants to prevent orphaned tasks.

        Args:
            task_id: UUID of the task to soft delete

        Returns:
            Updated Task instance

        Raises:
            TaskNotFoundError: If task does not exist
        """
        # Get the task
        task_orm = await self._get_task_or_raise(task_id)
        archive_time = datetime.utcnow()

        # Get all descendants for cascade archiving
        descendants = await self.get_all_descendants(task_id, include_archived=False)
        descendant_count = len(descendants)

        # Archive all descendants (deepest first to maintain integrity)
        for descendant in reversed(descendants):
            descendant_orm = await self._get_task_or_raise(descendant.id)
            descendant_orm.is_archived = True
            descendant_orm.archived_at = archive_time

        # Archive the task itself (soft delete - no completion check)
        task_orm.is_archived = True
        task_orm.archived_at = archive_time

        logger.info(
            f"Task soft-deleted (archived): task_id={task_id}, "
            f"archive_timestamp={task_orm.archived_at.isoformat()}, "
            f"was_completed={task_orm.is_completed}, "
            f"descendants_archived={descendant_count}"
        )

        # Flush changes to database
        try:
            await self.session.flush()
        except Exception as e:
            logger.error(
                f"Soft delete operation failed for task_id={task_id}",
                exc_info=True
            )
            raise

        # Convert back to Pydantic with counts using helper
        return await self._fetch_task_with_counts(task_orm)

    async def unarchive_task(self, task_id: UUID) -> Task:
        """
        Unarchive (restore) an archived task.

        If the task has a parent that is not active (archived or doesn't exist),
        the task will be set as a top-level task (level 0, no parent).

        Args:
            task_id: UUID of the task to unarchive

        Returns:
            Updated Task instance

        Raises:
            TaskNotFoundError: If task does not exist
        """
        # Get the task
        task_orm = await self._get_task_or_raise(task_id)

        # Check if task has a parent and if parent is active
        if task_orm.parent_id:
            parent_stmt = select(TaskORM).where(
                TaskORM.id == task_orm.parent_id
            )
            result = await self.session.execute(parent_stmt)
            parent = result.scalar_one_or_none()

            # If parent doesn't exist or is archived, make this a top-level task
            if not parent or parent.is_archived:
                logger.info(
                    f"Task {task_id} parent (id={task_orm.parent_id}) is not active. "
                    f"Setting task as top-level (level 0)."
                )
                task_orm.parent_id = None
                task_orm.level = 0

        # Unarchive the task
        task_orm.is_archived = False
        task_orm.archived_at = None

        logger.info(
            f"Task unarchived (restored): task_id={task_id}"
        )

        # Flush changes to database
        try:
            await self.session.flush()
        except Exception as e:
            logger.error(
                f"Unarchive operation failed for task_id={task_id}",
                exc_info=True
            )
            raise

        # Convert back to Pydantic with counts using helper
        return await self._fetch_task_with_counts(task_orm)

    async def get_archived_tasks(
        self,
        list_id: UUID,
        search_query: Optional[str] = None
    ) -> List[Task]:
        """
        Get all archived tasks for a list, optionally filtered by search query.

        Args:
            list_id: UUID of the task list
            search_query: Optional search string to filter by title or notes

        Returns:
            List of archived Task instances ordered by archived date (newest first)

        Raises:
            TaskListNotFoundError: If list does not exist
        """
        # Verify list exists
        await self._verify_list_exists(list_id)

        # Build query for archived tasks only
        query = select(TaskORM).where(
            TaskORM.list_id == str(list_id),
            TaskORM.is_archived == True,
        )

        # Apply search filter if provided
        if search_query:
            search_pattern = f"%{search_query}%"
            from sqlalchemy import or_
            query = query.where(
                or_(
                    TaskORM.title.ilike(search_pattern),
                    TaskORM.notes.ilike(search_pattern)
                )
            )

        # Order by archived date, newest first
        query = query.order_by(TaskORM.archived_at.desc())

        # Execute query
        result = await self.session.execute(query)
        task_orms = result.scalars().all()

        # Convert to Pydantic with counts using helper
        tasks = await self._fetch_tasks_with_counts(task_orms)

        logger.debug(
            f"Retrieved {len(tasks)} archived tasks for list_id={list_id}"
            + (f" with search query '{search_query}'" if search_query else "")
        )

        return tasks

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

    async def bulk_archive_tasks(self, list_id: UUID) -> int:
        """
        Archive all completed tasks in a list.

        Only tasks that are completed and not already archived will be archived.
        Incomplete tasks are not affected.

        Args:
            list_id: UUID of the task list

        Returns:
            Number of tasks archived

        Raises:
            TaskListNotFoundError: If list does not exist
        """
        from sqlalchemy import update

        try:
            logger.debug(f"Bulk archiving completed tasks in list {list_id}")

            # Verify list exists
            await self._verify_list_exists(list_id)

            # Get current timestamp for archived_at
            archived_at = datetime.utcnow()

            # Update all completed, non-archived tasks in the list
            result = await self.session.execute(
                update(TaskORM)
                .where(TaskORM.list_id == str(list_id))
                .where(TaskORM.is_completed == True)  # noqa: E712
                .where(TaskORM.is_archived == False)  # noqa: E712
                .values(is_archived=True, archived_at=archived_at)
            )

            archived_count = result.rowcount

            await self.session.flush()

            logger.info(
                f"Bulk archived {archived_count} completed tasks in list {list_id}"
            )

            return archived_count
        except TaskListNotFoundError:
            # Already logged, just re-raise
            raise
        except Exception as e:
            logger.error(
                f"Failed to bulk archive tasks in list {list_id}: {e}",
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
            descendants = await self.get_all_descendants(task_id, include_archived=True)
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
        children = await self.get_children(parent_id, include_archived=True)

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

        This method recursively counts all non-archived descendants, even if their
        immediate parent is archived. This handles orphaned tasks that remain visible
        when their parent is archived without cascading the archive operation.

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

                # Get ALL direct children (including archived ones for traversal)
                query = select(TaskORM).where(
                    TaskORM.parent_id == str(current_parent_id),
                )

                result = await self.session.execute(query)
                children = result.scalars().all()

                # Process each child
                for child in children:
                    # Only count non-archived children
                    if not child.is_archived:
                        total_count += 1
                        if child.is_completed:
                            completed_count += 1

                    # Always recurse to find non-archived descendants,
                    # even if this child is archived (to handle orphaned tasks)
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
