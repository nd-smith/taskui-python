"""
Pytest configuration and fixtures for TaskUI tests.

Provides database fixtures, test data factories, and common test utilities.
"""

import pytest
import pytest_asyncio
from datetime import datetime
from uuid import UUID, uuid4

from taskui.database import DatabaseManager, TaskListORM, TaskORM
from taskui.models import Task, TaskList


@pytest_asyncio.fixture
async def db_manager():
    """
    Create an in-memory SQLite database for testing.

    Yields:
        DatabaseManager instance with in-memory database

    Example:
        async def test_something(db_manager):
            async with db_manager.get_session() as session:
                # Test database operations
    """
    # Use in-memory SQLite for tests
    manager = DatabaseManager("sqlite+aiosqlite:///:memory:")
    await manager.initialize()

    yield manager

    # Cleanup
    await manager.close()


@pytest_asyncio.fixture
async def db_session(db_manager):
    """
    Provide a database session for tests with automatic rollback.

    Args:
        db_manager: Database manager fixture

    Yields:
        AsyncSession for database operations

    Example:
        async def test_something(db_session):
            result = await db_session.execute(select(TaskORM))
    """
    async with db_manager.get_session() as session:
        yield session


@pytest.fixture
def sample_list_id():
    """Generate a consistent UUID for testing task lists."""
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def sample_task_id():
    """Generate a consistent UUID for testing tasks."""
    return UUID("87654321-4321-8765-4321-876543218765")


@pytest_asyncio.fixture
async def sample_task_list(db_session, sample_list_id):
    """
    Create a sample task list in the database.

    Args:
        db_session: Database session fixture
        sample_list_id: Sample UUID fixture

    Returns:
        TaskListORM instance
    """
    task_list = TaskListORM(
        id=str(sample_list_id),
        name="Work",
        created_at=datetime.utcnow()
    )
    db_session.add(task_list)
    await db_session.commit()
    return task_list


@pytest_asyncio.fixture
async def sample_task(db_session, sample_task_id, sample_list_id):
    """
    Create a sample task in the database.

    Args:
        db_session: Database session fixture
        sample_task_id: Sample UUID fixture
        sample_list_id: Sample list UUID fixture

    Returns:
        TaskORM instance
    """
    task = TaskORM(
        id=str(sample_task_id),
        title="Complete project documentation",
        notes="Include API docs and user guide",
        is_completed=False,
        parent_id=None,
        level=0,
        position=0,
        list_id=str(sample_list_id),
        created_at=datetime.utcnow(),
        completed_at=None
    )
    db_session.add(task)
    await db_session.commit()
    return task


@pytest_asyncio.fixture
async def task_hierarchy(db_session, sample_list_id):
    """
    Create a multi-level task hierarchy for testing nesting.

    Creates:
        - Level 0: Parent Task
          - Level 1: Child Task 1
            - Level 2: Grandchild Task 1
          - Level 1: Child Task 2

    Args:
        db_session: Database session fixture
        sample_list_id: Sample list UUID fixture

    Returns:
        Dictionary with task IDs at each level
    """
    parent_id = str(uuid4())
    child1_id = str(uuid4())
    child2_id = str(uuid4())
    grandchild_id = str(uuid4())

    # Level 0 - Parent
    parent = TaskORM(
        id=parent_id,
        title="Parent Task",
        notes="Top level task",
        is_completed=False,
        parent_id=None,
        level=0,
        position=0,
        list_id=str(sample_list_id),
        created_at=datetime.utcnow()
    )

    # Level 1 - Children
    child1 = TaskORM(
        id=child1_id,
        title="Child Task 1",
        notes="First child",
        is_completed=False,
        parent_id=parent_id,
        level=1,
        position=0,
        list_id=str(sample_list_id),
        created_at=datetime.utcnow()
    )

    child2 = TaskORM(
        id=child2_id,
        title="Child Task 2",
        notes="Second child",
        is_completed=False,
        parent_id=parent_id,
        level=1,
        position=1,
        list_id=str(sample_list_id),
        created_at=datetime.utcnow()
    )

    # Level 2 - Grandchild
    grandchild = TaskORM(
        id=grandchild_id,
        title="Grandchild Task",
        notes="Third level task",
        is_completed=False,
        parent_id=child1_id,
        level=2,
        position=0,
        list_id=str(sample_list_id),
        created_at=datetime.utcnow()
    )

    db_session.add_all([parent, child1, child2, grandchild])
    await db_session.commit()

    return {
        "parent_id": parent_id,
        "child1_id": child1_id,
        "child2_id": child2_id,
        "grandchild_id": grandchild_id,
    }


@pytest.fixture
def make_task_list():
    """
    Factory fixture for creating TaskList Pydantic models.

    Returns:
        Function that creates TaskList instances

    Example:
        def test_something(make_task_list):
            task_list = make_task_list(name="Custom List")
    """
    def _make_task_list(
        id: UUID = None,
        name: str = "Test List",
        created_at: datetime = None
    ) -> TaskList:
        return TaskList(
            id=id or uuid4(),
            name=name,
            created_at=created_at or datetime.utcnow()
        )
    return _make_task_list


@pytest.fixture
def make_task():
    """
    Factory fixture for creating Task Pydantic models.

    Returns:
        Function that creates Task instances

    Example:
        def test_something(make_task, sample_list_id):
            task = make_task(title="Custom Task", list_id=sample_list_id)
    """
    def _make_task(
        id: UUID = None,
        title: str = "Test Task",
        notes: str = None,
        is_completed: bool = False,
        parent_id: UUID = None,
        level: int = 0,
        position: int = 0,
        list_id: UUID = None,
        created_at: datetime = None,
        completed_at: datetime = None
    ) -> Task:
        if list_id is None:
            list_id = uuid4()

        return Task(
            id=id or uuid4(),
            title=title,
            notes=notes,
            is_completed=is_completed,
            parent_id=parent_id,
            level=level,
            position=position,
            list_id=list_id,
            created_at=created_at or datetime.utcnow(),
            completed_at=completed_at
        )
    return _make_task
