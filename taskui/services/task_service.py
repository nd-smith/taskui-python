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
from taskui.models import Task, TaskList
from taskui.services.nesting_rules import Column, NestingRules


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

    def __init__(self, session: AsyncSession):
        """
        Initialize task service with database session.

        Args:
            session: Active async database session
        """
        self.session = session

    @staticmethod
    def _orm_to_pydantic(task_orm: TaskORM) -> Task:
        """
        Convert TaskORM to Pydantic Task model.

        Args:
            task_orm: SQLAlchemy ORM task instance

        Returns:
            Pydantic Task instance
        """
        return Task(
            id=UUID(task_orm.id),
            title=task_orm.title,
            notes=task_orm.notes,
            is_completed=task_orm.is_completed,
            is_archived=task_orm.is_archived,
            parent_id=UUID(task_orm.parent_id) if task_orm.parent_id else None,
            level=task_orm.level,
            position=task_orm.position,
            list_id=UUID(task_orm.list_id),
            created_at=task_orm.created_at,
            completed_at=task_orm.completed_at,
            archived_at=task_orm.archived_at,
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
        # Verify list exists
        await self._verify_list_exists(list_id)

        # Get next position
        position = await self._get_next_position(list_id, parent_id=None)

        # Create task
        task = Task(
            title=title,
            notes=notes,
            list_id=list_id,
            level=0,
            position=position,
            parent_id=None,
        )

        # Convert to ORM and save
        task_orm = self._pydantic_to_orm(task)
        self.session.add(task_orm)
        await self.session.flush()  # Flush to get the ID

        return task

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
        # Get parent task
        parent_orm = await self._get_task_or_raise(parent_id)
        parent_task = self._orm_to_pydantic(parent_orm)

        # Validate nesting rules
        if not NestingRules.can_create_child(parent_task, column):
            max_depth = NestingRules.get_max_depth(column)
            raise NestingLimitError(
                f"Cannot create child task. Parent task at level {parent_task.level} "
                f"has reached maximum nesting depth ({max_depth}) for {column.value}."
            )

        # Get the allowed child level
        child_level = NestingRules.get_allowed_child_level(parent_task, column)
        if child_level is None:
            raise NestingLimitError(
                f"Cannot determine child level for parent at level {parent_task.level} "
                f"in {column.value}."
            )

        # Get next position among siblings
        position = await self._get_next_position(parent_task.list_id, parent_id=parent_id)

        # Create child task
        child_task = Task(
            title=title,
            notes=notes,
            list_id=parent_task.list_id,
            parent_id=parent_id,
            level=child_level,
            position=position,
        )

        # Convert to ORM and save
        task_orm = self._pydantic_to_orm(child_task)
        self.session.add(task_orm)
        await self.session.flush()

        return child_task

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

        # Build query
        query = select(TaskORM).where(
            TaskORM.list_id == str(list_id),
            TaskORM.parent_id.is_(None),  # Only top-level tasks
        )

        if not include_archived:
            query = query.where(TaskORM.is_archived == False)

        query = query.order_by(TaskORM.position)

        # Execute query
        result = await self.session.execute(query)
        task_orms = result.scalars().all()

        # Convert to Pydantic and update child counts
        tasks = []
        for task_orm in task_orms:
            task = self._orm_to_pydantic(task_orm)

            # Get child counts
            child_count, completed_child_count = await self._get_child_counts(task.id)
            task.update_child_counts(child_count, completed_child_count)

            tasks.append(task)

        return tasks

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

        # Build query
        query = select(TaskORM).where(TaskORM.parent_id == str(parent_id))

        if not include_archived:
            query = query.where(TaskORM.is_archived == False)

        query = query.order_by(TaskORM.position)

        # Execute query
        result = await self.session.execute(query)
        task_orms = result.scalars().all()

        # Convert to Pydantic and update child counts
        tasks = []
        for task_orm in task_orms:
            task = self._orm_to_pydantic(task_orm)

            # Get child counts
            child_count, completed_child_count = await self._get_child_counts(task.id)
            task.update_child_counts(child_count, completed_child_count)

            tasks.append(task)

        return tasks

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
        async def collect_descendants(current_parent_id: UUID):
            children = await self.get_children(current_parent_id, include_archived=include_archived)
            for child in children:
                descendants.append(child)
                # Recursively get this child's descendants
                await collect_descendants(child.id)

        await collect_descendants(parent_id)

        return descendants

    async def _get_child_counts(self, parent_id: UUID) -> tuple[int, int]:
        """
        Get the total and completed child counts for a task.

        Args:
            parent_id: UUID of the parent task

        Returns:
            Tuple of (total_children, completed_children)
        """
        # Get all direct children (not archived)
        query = select(TaskORM).where(
            TaskORM.parent_id == str(parent_id),
            TaskORM.is_archived == False,
        )

        result = await self.session.execute(query)
        children = result.scalars().all()

        total_count = len(children)
        completed_count = sum(1 for child in children if child.is_completed)

        return total_count, completed_count

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

        task = self._orm_to_pydantic(task_orm)

        # Get child counts
        child_count, completed_child_count = await self._get_child_counts(task.id)
        task.update_child_counts(child_count, completed_child_count)

        return task

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

        # Get existing task
        task_orm = await self._get_task_or_raise(task_id)

        # Update fields
        if title is not None:
            task_orm.title = title
        if notes is not None:
            task_orm.notes = notes

        # Flush changes to database
        await self.session.flush()

        # Convert back to Pydantic model
        task = self._orm_to_pydantic(task_orm)

        # Get child counts
        child_count, completed_child_count = await self._get_child_counts(task.id)
        task.update_child_counts(child_count, completed_child_count)

        return task

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
        # Get task to delete
        task_orm = await self._get_task_or_raise(task_id)

        # Get all descendants for cascade deletion
        descendants = await self.get_all_descendants(task_id, include_archived=True)

        # Delete descendants in reverse hierarchical order (deepest first)
        # This ensures we don't violate foreign key constraints
        for descendant in reversed(descendants):
            descendant_orm = await self._get_task_or_raise(descendant.id)
            await self.session.delete(descendant_orm)

        # Delete the task itself
        await self.session.delete(task_orm)

        # Flush the deletions
        await self.session.flush()

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

        # Return updated task
        task = self._orm_to_pydantic(task_orm)
        child_count, completed_child_count = await self._get_child_counts(task.id)
        task.update_child_counts(child_count, completed_child_count)

        return task

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
