"""
List service for TaskUI application.

Provides CRUD operations and business logic for managing task lists,
including default list creation and list-specific task operations.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from taskui.database import TaskListORM, TaskORM
from taskui.models import TaskList


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

    def __init__(self, session: AsyncSession):
        """
        Initialize the list service.

        Args:
            session: Active database session for operations
        """
        self.session = session

    async def create_list(self, name: str, list_id: Optional[UUID] = None) -> TaskList:
        """
        Create a new task list.

        Args:
            name: Name of the list to create
            list_id: Optional UUID for the list (auto-generated if not provided)

        Returns:
            Created TaskList model

        Raises:
            ValueError: If a list with the same name already exists
        """
        # Check if list with same name exists
        existing = await self.get_list_by_name(name)
        if existing:
            raise ValueError(f"List with name '{name}' already exists")

        # Create list
        if list_id is None:
            list_id = uuid4()

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

        return task_list

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

        task_lists = []
        for list_orm in list_orms:
            task_list = TaskList(
                id=UUID(list_orm.id),
                name=list_orm.name,
                created_at=list_orm.created_at
            )

            # Update counts
            task_count = await self._get_task_count(UUID(list_orm.id))
            completed_count = await self._get_completed_count(UUID(list_orm.id))
            task_list.update_counts(task_count, completed_count)

            task_lists.append(task_list)

        return task_lists

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

        task_list = TaskList(
            id=UUID(list_orm.id),
            name=list_orm.name,
            created_at=list_orm.created_at
        )

        # Update counts
        task_count = await self._get_task_count(list_id)
        completed_count = await self._get_completed_count(list_id)
        task_list.update_counts(task_count, completed_count)

        return task_list

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

        task_list = TaskList(
            id=UUID(list_orm.id),
            name=list_orm.name,
            created_at=list_orm.created_at
        )

        # Update counts
        task_count = await self._get_task_count(UUID(list_orm.id))
        completed_count = await self._get_completed_count(UUID(list_orm.id))
        task_list.update_counts(task_count, completed_count)

        return task_list

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
        # Check if list exists
        result = await self.session.execute(
            select(TaskListORM).where(TaskListORM.id == str(list_id))
        )
        list_orm = result.scalar_one_or_none()

        if not list_orm:
            return None

        # Check if another list with same name exists
        existing = await self.get_list_by_name(name)
        if existing and existing.id != list_id:
            raise ValueError(f"List with name '{name}' already exists")

        # Update name
        list_orm.name = name
        await self.session.flush()

        # Return updated model
        task_list = TaskList(
            id=list_id,
            name=name,
            created_at=list_orm.created_at
        )

        # Update counts
        task_count = await self._get_task_count(list_id)
        completed_count = await self._get_completed_count(list_id)
        task_list.update_counts(task_count, completed_count)

        return task_list

    async def delete_list(self, list_id: UUID) -> bool:
        """
        Delete a task list and all its tasks (cascade).

        Args:
            list_id: UUID of the list to delete

        Returns:
            True if list was deleted, False if not found
        """
        result = await self.session.execute(
            select(TaskListORM).where(TaskListORM.id == str(list_id))
        )
        list_orm = result.scalar_one_or_none()

        if not list_orm:
            return False

        await self.session.delete(list_orm)
        await self.session.flush()

        return True

    async def ensure_default_lists(self) -> List[TaskList]:
        """
        Ensure default lists (Work, Home, Personal) exist.

        Creates default lists if they don't exist, typically called on first run.

        Returns:
            List of all task lists after ensuring defaults exist
        """
        # Check which default lists exist by name
        existing_lists_by_name = {}
        all_lists = await self.get_all_lists()
        for task_list in all_lists:
            existing_lists_by_name[task_list.name] = task_list

        # Create missing default lists
        for default_list in self.DEFAULT_LISTS:
            if default_list["name"] not in existing_lists_by_name:
                task_list = await self.create_list(
                    name=default_list["name"],
                    list_id=UUID(default_list["id"])
                )

        await self.session.commit()

        # Return all lists (existing + newly created)
        return await self.get_all_lists()

    async def _get_task_count(self, list_id: UUID) -> int:
        """
        Get total number of non-archived tasks in a list.

        Args:
            list_id: UUID of the list

        Returns:
            Count of non-archived tasks
        """
        result = await self.session.execute(
            select(func.count(TaskORM.id))
            .where(TaskORM.list_id == str(list_id))
            .where(TaskORM.is_archived == False)  # noqa: E712
        )
        return result.scalar_one()

    async def _get_completed_count(self, list_id: UUID) -> int:
        """
        Get number of completed non-archived tasks in a list.

        Args:
            list_id: UUID of the list

        Returns:
            Count of completed non-archived tasks
        """
        result = await self.session.execute(
            select(func.count(TaskORM.id))
            .where(TaskORM.list_id == str(list_id))
            .where(TaskORM.is_completed == True)  # noqa: E712
            .where(TaskORM.is_archived == False)  # noqa: E712
        )
        return result.scalar_one()
