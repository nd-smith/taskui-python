"""
Tests for the ListService class.

Tests CRUD operations, default list creation, and list-specific functionality.
"""

import pytest
import pytest_asyncio
from datetime import datetime
from uuid import UUID, uuid4

from taskui.services.list_service import ListService
from taskui.database import TaskListORM, TaskORM


class TestListServiceCreate:
    """Test list creation operations."""

    @pytest.mark.asyncio
    async def test_create_list_basic(self, db_session):
        """Test creating a basic task list."""
        service = ListService(db_session)

        task_list = await service.create_list(name="Work")

        assert task_list is not None
        assert task_list.name == "Work"
        assert isinstance(task_list.id, UUID)
        assert isinstance(task_list.created_at, datetime)

    @pytest.mark.asyncio
    async def test_create_list_with_custom_id(self, db_session):
        """Test creating a list with a specific UUID."""
        service = ListService(db_session)
        custom_id = uuid4()

        task_list = await service.create_list(name="Home", list_id=custom_id)

        assert task_list.id == custom_id
        assert task_list.name == "Home"

    @pytest.mark.asyncio
    async def test_create_list_duplicate_name_fails(self, db_session):
        """Test that creating a list with duplicate name fails."""
        service = ListService(db_session)

        # Create first list
        await service.create_list(name="Work")

        # Attempt to create second list with same name
        with pytest.raises(ValueError, match="List with name 'Work' already exists"):
            await service.create_list(name="Work")

    @pytest.mark.asyncio
    async def test_create_list_initializes_counts(self, db_session):
        """Test that new lists have zero task counts."""
        service = ListService(db_session)

        task_list = await service.create_list(name="Personal")

        assert task_list._task_count == 0
        assert task_list._completed_count == 0
        assert task_list.completion_percentage == 0.0


class TestListServiceRead:
    """Test list retrieval operations."""

    @pytest.mark.asyncio
    async def test_get_all_lists_empty(self, db_session):
        """Test getting all lists when none exist."""
        service = ListService(db_session)

        lists = await service.get_all_lists()

        assert lists == []

    @pytest.mark.asyncio
    async def test_get_all_lists_multiple(self, db_session):
        """Test getting all lists with multiple entries."""
        service = ListService(db_session)

        # Create multiple lists
        await service.create_list(name="Work")
        await service.create_list(name="Home")
        await service.create_list(name="Personal")

        lists = await service.get_all_lists()

        assert len(lists) == 3
        list_names = [lst.name for lst in lists]
        assert "Work" in list_names
        assert "Home" in list_names
        assert "Personal" in list_names

    @pytest.mark.asyncio
    async def test_get_all_lists_ordered_by_created(self, db_session):
        """Test that lists are returned in creation order."""
        service = ListService(db_session)

        # Create lists in specific order
        list1 = await service.create_list(name="First")
        list2 = await service.create_list(name="Second")
        list3 = await service.create_list(name="Third")

        lists = await service.get_all_lists()

        assert lists[0].name == "First"
        assert lists[1].name == "Second"
        assert lists[2].name == "Third"

    @pytest.mark.asyncio
    async def test_get_list_by_id_found(self, db_session):
        """Test retrieving a list by its ID."""
        service = ListService(db_session)

        created_list = await service.create_list(name="Work")
        retrieved_list = await service.get_list_by_id(created_list.id)

        assert retrieved_list is not None
        assert retrieved_list.id == created_list.id
        assert retrieved_list.name == created_list.name

    @pytest.mark.asyncio
    async def test_get_list_by_id_not_found(self, db_session):
        """Test retrieving a non-existent list by ID."""
        service = ListService(db_session)
        non_existent_id = uuid4()

        result = await service.get_list_by_id(non_existent_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_list_by_name_found(self, db_session):
        """Test retrieving a list by its name."""
        service = ListService(db_session)

        await service.create_list(name="Work")
        retrieved_list = await service.get_list_by_name("Work")

        assert retrieved_list is not None
        assert retrieved_list.name == "Work"

    @pytest.mark.asyncio
    async def test_get_list_by_name_not_found(self, db_session):
        """Test retrieving a non-existent list by name."""
        service = ListService(db_session)

        result = await service.get_list_by_name("NonExistent")

        assert result is None


class TestListServiceUpdate:
    """Test list update operations."""

    @pytest.mark.asyncio
    async def test_update_list_name(self, db_session):
        """Test updating a list's name."""
        service = ListService(db_session)

        # Create a list
        original_list = await service.create_list(name="Work")

        # Update the name
        updated_list = await service.update_list(original_list.id, name="Office")

        assert updated_list is not None
        assert updated_list.id == original_list.id
        assert updated_list.name == "Office"

    @pytest.mark.asyncio
    async def test_update_list_not_found(self, db_session):
        """Test updating a non-existent list."""
        service = ListService(db_session)
        non_existent_id = uuid4()

        result = await service.update_list(non_existent_id, name="NewName")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_list_duplicate_name_fails(self, db_session):
        """Test that updating to a duplicate name fails."""
        service = ListService(db_session)

        # Create two lists
        list1 = await service.create_list(name="Work")
        list2 = await service.create_list(name="Home")

        # Try to rename list2 to "Work" (same as list1)
        with pytest.raises(ValueError, match="List with name 'Work' already exists"):
            await service.update_list(list2.id, name="Work")

    @pytest.mark.asyncio
    async def test_update_list_same_name_allowed(self, db_session):
        """Test that updating a list to its current name is allowed."""
        service = ListService(db_session)

        # Create a list
        original_list = await service.create_list(name="Work")

        # Update with same name (should succeed)
        updated_list = await service.update_list(original_list.id, name="Work")

        assert updated_list is not None
        assert updated_list.name == "Work"


class TestListServiceDelete:
    """Test list deletion operations."""

    @pytest.mark.asyncio
    async def test_delete_list_success(self, db_session):
        """Test deleting a list successfully."""
        service = ListService(db_session)

        # Create a list
        task_list = await service.create_list(name="Work")

        # Delete it
        result = await service.delete_list(task_list.id)

        assert result is True

        # Verify it's gone
        retrieved = await service.get_list_by_id(task_list.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_list_not_found(self, db_session):
        """Test deleting a non-existent list."""
        service = ListService(db_session)
        non_existent_id = uuid4()

        result = await service.delete_list(non_existent_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_list_cascades_to_tasks(self, db_session, sample_list_id):
        """Test that deleting a list also deletes its tasks."""
        service = ListService(db_session)

        # Create a list
        task_list = await service.create_list(name="Work", list_id=sample_list_id)

        # Add a task to the list
        task = TaskORM(
            id=str(uuid4()),
            title="Test Task",
            list_id=str(task_list.id),
            level=0,
            position=0,
            is_completed=False,
            is_archived=False,
            created_at=datetime.utcnow()
        )
        db_session.add(task)
        await db_session.commit()

        # Delete the list
        await service.delete_list(task_list.id)

        # Verify tasks are also deleted (cascade)
        from sqlalchemy import select
        result = await db_session.execute(
            select(TaskORM).where(TaskORM.list_id == str(task_list.id))
        )
        tasks = result.scalars().all()
        assert len(tasks) == 0


class TestListServiceDefaultLists:
    """Test default list creation functionality."""

    @pytest.mark.asyncio
    async def test_ensure_default_lists_creates_all(self, db_session):
        """Test that ensure_default_lists creates all three default lists."""
        service = ListService(db_session)

        lists = await service.ensure_default_lists()

        assert len(lists) == 3
        list_names = [lst.name for lst in lists]
        assert "Work" in list_names
        assert "Home" in list_names
        assert "Personal" in list_names

    @pytest.mark.asyncio
    async def test_ensure_default_lists_uses_fixed_ids(self, db_session):
        """Test that default lists have predictable UUIDs."""
        service = ListService(db_session)

        lists = await service.ensure_default_lists()

        # Check that the default IDs are used
        list_ids = {lst.name: str(lst.id) for lst in lists}
        assert list_ids["Work"] == "00000000-0000-0000-0000-000000000001"
        assert list_ids["Home"] == "00000000-0000-0000-0000-000000000002"
        assert list_ids["Personal"] == "00000000-0000-0000-0000-000000000003"

    @pytest.mark.asyncio
    async def test_ensure_default_lists_idempotent(self, db_session):
        """Test that ensure_default_lists is idempotent (doesn't create duplicates)."""
        service = ListService(db_session)

        # Call twice
        lists1 = await service.ensure_default_lists()
        lists2 = await service.ensure_default_lists()

        # Should still only have 3 lists
        assert len(lists1) == 3
        assert len(lists2) == 3

        # Verify in database
        all_lists = await service.get_all_lists()
        assert len(all_lists) == 3



class TestListServiceTaskCounts:
    """Test task count computation for lists."""

    @pytest.mark.asyncio
    async def test_get_list_with_task_counts(self, db_session, sample_list_id):
        """Test that retrieved lists have correct task counts."""
        service = ListService(db_session)

        # Create a list
        task_list = await service.create_list(name="Work", list_id=sample_list_id)

        # Add some tasks
        task1 = TaskORM(
            id=str(uuid4()),
            title="Task 1",
            list_id=str(task_list.id),
            level=0,
            position=0,
            is_completed=True,
            is_archived=False,
            created_at=datetime.utcnow()
        )
        task2 = TaskORM(
            id=str(uuid4()),
            title="Task 2",
            list_id=str(task_list.id),
            level=0,
            position=1,
            is_completed=False,
            is_archived=False,
            created_at=datetime.utcnow()
        )
        db_session.add_all([task1, task2])
        await db_session.commit()

        # Retrieve the list
        retrieved_list = await service.get_list_by_id(task_list.id)

        assert retrieved_list._task_count == 2
        assert retrieved_list._completed_count == 1
        assert retrieved_list.completion_percentage == 50.0

    @pytest.mark.asyncio
    async def test_get_list_excludes_archived_from_counts(self, db_session, sample_list_id):
        """Test that archived tasks are excluded from counts."""
        service = ListService(db_session)

        # Create a list
        task_list = await service.create_list(name="Work", list_id=sample_list_id)

        # Add tasks including archived
        task1 = TaskORM(
            id=str(uuid4()),
            title="Task 1",
            list_id=str(task_list.id),
            level=0,
            position=0,
            is_completed=True,
            is_archived=False,
            created_at=datetime.utcnow()
        )
        task2 = TaskORM(
            id=str(uuid4()),
            title="Task 2",
            list_id=str(task_list.id),
            level=0,
            position=1,
            is_completed=True,
            is_archived=True,  # Archived task
            created_at=datetime.utcnow()
        )
        db_session.add_all([task1, task2])
        await db_session.commit()

        # Retrieve the list
        retrieved_list = await service.get_list_by_id(task_list.id)

        # Only non-archived tasks should be counted
        assert retrieved_list._task_count == 1
        assert retrieved_list._completed_count == 1
        assert retrieved_list.completion_percentage == 100.0
