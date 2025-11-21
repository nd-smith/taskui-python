"""
Tests for the database layer.

Tests cover database initialization, ORM models, session management,
and CRUD operations for both TaskList and Task entities.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from taskui.database import (
    DatabaseManager,
    TaskListORM,
    TaskORM,
    get_database_manager,
    init_database,
)


class TestDatabaseManager:
    """Tests for DatabaseManager class."""

    @pytest.mark.asyncio
    async def test_initialize_creates_tables(self, db_manager):
        """Test that initialize() creates all required tables."""
        # Tables should be created by the fixture
        async with db_manager.get_session() as session:
            # Try to query tables - should not raise error
            result = await session.execute(select(TaskListORM))
            assert result.scalars().all() == []

            result = await session.execute(select(TaskORM))
            assert result.scalars().all() == []

    @pytest.mark.asyncio
    async def test_get_session_context_manager(self, db_manager):
        """Test that get_session() provides working async context manager."""
        async with db_manager.get_session() as session:
            assert session is not None
            # Session is active within the context manager
            assert session.is_active

    @pytest.mark.asyncio
    async def test_get_session_auto_commit(self, db_manager, sample_list_id):
        """Test that session auto-commits on successful exit."""
        async with db_manager.get_session() as session:
            task_list = TaskListORM(
                id=str(sample_list_id),
                name="Test List",
                created_at=datetime.utcnow()
            )
            session.add(task_list)

        # Verify data was committed
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(TaskListORM).where(TaskListORM.id == str(sample_list_id))
            )
            saved_list = result.scalar_one_or_none()
            assert saved_list is not None
            assert saved_list.name == "Test List"

    @pytest.mark.asyncio
    async def test_get_session_auto_rollback_on_error(self, db_manager, sample_list_id):
        """Test that session auto-rolls back on exception."""
        try:
            async with db_manager.get_session() as session:
                task_list = TaskListORM(
                    id=str(sample_list_id),
                    name="Test List",
                    created_at=datetime.utcnow()
                )
                session.add(task_list)
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Verify data was not committed
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(TaskListORM).where(TaskListORM.id == str(sample_list_id))
            )
            saved_list = result.scalar_one_or_none()
            assert saved_list is None

    @pytest.mark.asyncio
    async def test_close_disposes_engine(self):
        """Test that close() properly disposes the engine."""
        manager = DatabaseManager("sqlite+aiosqlite:///:memory:")
        await manager.initialize()
        assert manager.engine is not None

        await manager.close()
        assert manager.engine is None
        assert manager.session_maker is None

    @pytest.mark.asyncio
    async def test_get_session_raises_when_not_initialized(self):
        """Test that get_session() raises error when manager not initialized."""
        manager = DatabaseManager("sqlite+aiosqlite:///:memory:")

        with pytest.raises(RuntimeError, match="not initialized"):
            async with manager.get_session() as session:
                pass


class TestTaskListORM:
    """Tests for TaskListORM model."""

    @pytest.mark.asyncio
    async def test_create_task_list(self, db_session, sample_list_id):
        """Test creating a task list in the database."""
        task_list = TaskListORM(
            id=str(sample_list_id),
            name="Work",
            created_at=datetime.utcnow()
        )
        db_session.add(task_list)
        await db_session.commit()

        # Verify it was saved
        result = await db_session.execute(
            select(TaskListORM).where(TaskListORM.id == str(sample_list_id))
        )
        saved_list = result.scalar_one()

        assert saved_list.id == str(sample_list_id)
        assert saved_list.name == "Work"
        assert saved_list.created_at is not None

    @pytest.mark.asyncio
    async def test_task_list_name_required(self, db_session, sample_list_id):
        """Test that task list name is required (NOT NULL constraint)."""
        task_list = TaskListORM(
            id=str(sample_list_id),
            name=None,  # Should fail
            created_at=datetime.utcnow()
        )
        db_session.add(task_list)

        with pytest.raises(IntegrityError):
            await db_session.commit()

        # Rollback to clean up the session for fixture cleanup
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_task_list_relationship_to_tasks(self, db_session, sample_list_id, sample_task_id):
        """Test that task list has relationship to tasks."""
        task_list = TaskListORM(
            id=str(sample_list_id),
            name="Work",
            created_at=datetime.utcnow()
        )
        db_session.add(task_list)

        task = TaskORM(
            id=str(sample_task_id),
            title="Test Task",
            list_id=str(sample_list_id),
            level=0,
            position=0,
            is_completed=False,
            created_at=datetime.utcnow()
        )
        db_session.add(task)
        await db_session.commit()

        # Verify relationship
        result = await db_session.execute(
            select(TaskListORM).where(TaskListORM.id == str(sample_list_id))
        )
        saved_list = result.scalar_one()

        # Access the relationship
        await db_session.refresh(saved_list, ["tasks"])
        assert len(saved_list.tasks) == 1
        assert saved_list.tasks[0].title == "Test Task"


class TestTaskORM:
    """Tests for TaskORM model."""

    @pytest.mark.asyncio
    async def test_create_task(self, db_session, sample_task_id, sample_list_id):
        """Test creating a task in the database."""
        task = TaskORM(
            id=str(sample_task_id),
            title="Complete documentation",
            notes="Include API and user guide",
            is_completed=False,
            parent_id=None,
            level=0,
            position=0,
            list_id=str(sample_list_id),
            created_at=datetime.utcnow()
        )
        db_session.add(task)
        await db_session.commit()

        # Verify it was saved
        result = await db_session.execute(
            select(TaskORM).where(TaskORM.id == str(sample_task_id))
        )
        saved_task = result.scalar_one()

        assert saved_task.id == str(sample_task_id)
        assert saved_task.title == "Complete documentation"
        assert saved_task.notes == "Include API and user guide"
        assert saved_task.is_completed is False
        # is_archived field was removed from schema
        assert saved_task.level == 0

    @pytest.mark.asyncio
    async def test_task_title_required(self, db_session, sample_task_id, sample_list_id):
        """Test that task title is required (NOT NULL constraint)."""
        task = TaskORM(
            id=str(sample_task_id),
            title=None,  # Should fail
            list_id=str(sample_list_id),
            level=0,
            position=0,
            is_completed=False,
            created_at=datetime.utcnow()
        )
        db_session.add(task)

        with pytest.raises(IntegrityError):
            await db_session.commit()

        # Rollback to clean up the session for fixture cleanup
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_task_notes_optional(self, db_session, sample_task_id, sample_list_id):
        """Test that task notes are optional."""
        task = TaskORM(
            id=str(sample_task_id),
            title="Simple task",
            notes=None,  # Should be allowed
            list_id=str(sample_list_id),
            level=0,
            position=0,
            is_completed=False,
            created_at=datetime.utcnow()
        )
        db_session.add(task)
        await db_session.commit()

        # Verify it was saved with None notes
        result = await db_session.execute(
            select(TaskORM).where(TaskORM.id == str(sample_task_id))
        )
        saved_task = result.scalar_one()
        assert saved_task.notes is None

    @pytest.mark.asyncio
    async def test_task_hierarchy_parent_child(self, db_session, sample_list_id):
        """Test creating parent-child task hierarchy."""
        parent_id = str(uuid4())
        child_id = str(uuid4())

        parent = TaskORM(
            id=parent_id,
            title="Parent Task",
            list_id=str(sample_list_id),
            level=0,
            position=0,
            is_completed=False,
            created_at=datetime.utcnow()
        )

        child = TaskORM(
            id=child_id,
            title="Child Task",
            parent_id=parent_id,
            list_id=str(sample_list_id),
            level=1,
            position=0,
            is_completed=False,
            created_at=datetime.utcnow()
        )

        db_session.add_all([parent, child])
        await db_session.commit()

        # Verify hierarchy
        result = await db_session.execute(
            select(TaskORM).where(TaskORM.parent_id == parent_id)
        )
        children = result.scalars().all()
        assert len(children) == 1
        assert children[0].title == "Child Task"

    @pytest.mark.asyncio
    async def test_task_completion_timestamps(self, db_session, sample_task_id, sample_list_id):
        """Test that completion and archive timestamps work correctly."""
        task = TaskORM(
            id=str(sample_task_id),
            title="Test Task",
            list_id=str(sample_list_id),
            level=0,
            position=0,
            is_completed=False,
            created_at=datetime.utcnow()
        )
        db_session.add(task)
        await db_session.commit()

        # Update task to completed
        task.is_completed = True
        task.completed_at = datetime.utcnow()
        await db_session.commit()

        # Verify timestamps
        result = await db_session.execute(
            select(TaskORM).where(TaskORM.id == str(sample_task_id))
        )
        saved_task = result.scalar_one()
        assert saved_task.is_completed is True
        assert saved_task.completed_at is not None

    @pytest.mark.asyncio
    async def test_query_tasks_by_level(self, db_session, task_hierarchy, sample_list_id):
        """Test querying tasks by nesting level."""
        # Query level 0 tasks
        result = await db_session.execute(
            select(TaskORM).where(
                TaskORM.list_id == str(sample_list_id),
                TaskORM.level == 0
            )
        )
        level0_tasks = result.scalars().all()
        assert len(level0_tasks) == 1

        # Query level 1 tasks
        result = await db_session.execute(
            select(TaskORM).where(
                TaskORM.list_id == str(sample_list_id),
                TaskORM.level == 1
            )
        )
        level1_tasks = result.scalars().all()
        assert len(level1_tasks) == 2

    @pytest.mark.asyncio
    async def test_query_children_of_task(self, db_session, task_hierarchy):
        """Test querying children of a specific task."""
        parent_id = task_hierarchy["parent_id"]

        result = await db_session.execute(
            select(TaskORM).where(TaskORM.parent_id == parent_id)
        )
        children = result.scalars().all()

        assert len(children) == 2
        assert all(child.level == 1 for child in children)


class TestDatabaseHelperFunctions:
    """Tests for helper functions."""

    @pytest.mark.asyncio
    async def test_init_database_helper(self):
        """Test init_database convenience function."""
        db_manager = await init_database("sqlite+aiosqlite:///:memory:")

        assert db_manager is not None
        assert db_manager.engine is not None
        assert db_manager.session_maker is not None

        # Cleanup
        await db_manager.close()
