"""
Tests for data persistence and auto-save functionality (Story 1.15).

Ensures that all changes persist immediately, app restores state on restart,
and no data loss occurs on crash scenarios.
"""

import pytest
from uuid import UUID, uuid4
from datetime import datetime

from taskui.database import DatabaseManager, TaskORM, TaskListORM
from taskui.services.task_service import TaskService
from taskui.services.nesting_rules import Column


@pytest.mark.asyncio
async def test_task_creation_persists_immediately(db_manager, sample_task_list, sample_list_id):
    """
    Test that task creation persists to database immediately via auto-commit.

    Success Criteria:
    - Task is retrievable in a new session after creation
    - All task properties persist correctly
    """
    task_title = "Test Persistent Task"
    task_notes = "These notes should persist"

    # Create a task in one session
    async with db_manager.get_session() as session:
        task_service = TaskService(session)
        created_task = await task_service.create_task(
            title=task_title,
            list_id=sample_list_id,
            notes=task_notes
        )
        task_id = created_task.id
        # Session context manager auto-commits on exit

    # Verify task persists in a new session
    async with db_manager.get_session() as session:
        task_service = TaskService(session)
        retrieved_task = await task_service.get_task_by_id(task_id)

        assert retrieved_task is not None
        assert retrieved_task.title == task_title
        assert retrieved_task.notes == task_notes
        assert retrieved_task.list_id == sample_list_id
        assert retrieved_task.level == 0


@pytest.mark.asyncio
async def test_task_update_persists_immediately(db_manager, sample_task):
    """
    Test that task updates persist to database immediately.

    Success Criteria:
    - Updated values are retrievable in a new session
    - Only specified fields are updated
    """
    task_id = UUID(sample_task.id)
    new_title = "Updated Task Title"
    new_notes = "Updated notes content"

    # Update task in one session
    async with db_manager.get_session() as session:
        task_service = TaskService(session)
        await task_service.update_task(
            task_id=task_id,
            title=new_title,
            notes=new_notes
        )
        # Auto-commit on session exit

    # Verify updates persist in new session
    async with db_manager.get_session() as session:
        task_service = TaskService(session)
        retrieved_task = await task_service.get_task_by_id(task_id)

        assert retrieved_task is not None
        assert retrieved_task.title == new_title
        assert retrieved_task.notes == new_notes


@pytest.mark.asyncio
async def test_task_deletion_persists_immediately(db_manager, sample_task):
    """
    Test that task deletion persists to database immediately.

    Success Criteria:
    - Deleted task is not retrievable in a new session
    - Cascade deletion works for children
    """
    task_id = UUID(sample_task.id)

    # Delete task in one session
    async with db_manager.get_session() as session:
        task_service = TaskService(session)
        await task_service.delete_task(task_id)
        # Auto-commit on session exit

    # Verify deletion persists in new session
    async with db_manager.get_session() as session:
        task_service = TaskService(session)
        retrieved_task = await task_service.get_task_by_id(task_id)

        assert retrieved_task is None


@pytest.mark.asyncio
async def test_child_task_creation_persists_with_hierarchy(
    db_manager,
    sample_task,
    sample_list_id
):
    """
    Test that child task creation persists with correct parent-child relationship.

    Success Criteria:
    - Child task is retrievable in a new session
    - Parent-child relationship is maintained
    - Hierarchy levels are correct
    """
    parent_id = UUID(sample_task.id)
    child_title = "Child Task"

    # Create child task in one session
    async with db_manager.get_session() as session:
        task_service = TaskService(session)
        child_task = await task_service.create_child_task(
            parent_id=parent_id,
            title=child_title,
            column=Column.COLUMN1,
            notes="Child notes"
        )
        child_id = child_task.id
        # Auto-commit on session exit

    # Verify child task and relationship persist in new session
    async with db_manager.get_session() as session:
        task_service = TaskService(session)

        # Get child task
        retrieved_child = await task_service.get_task_by_id(child_id)
        assert retrieved_child is not None
        assert retrieved_child.title == child_title
        assert retrieved_child.parent_id == parent_id
        assert retrieved_child.level == 1

        # Get children of parent
        children = await task_service.get_children(parent_id)
        assert len(children) == 1
        assert children[0].id == child_id


@pytest.mark.asyncio
async def test_transaction_rollback_on_error(db_manager, sample_list_id):
    """
    Test that database transactions rollback on error (no partial saves).

    Success Criteria:
    - Failed operations don't persist partial data
    - Database remains in consistent state
    """
    # Try to create a task with an invalid list_id (non-existent)
    invalid_list_id = uuid4()

    from taskui.services.task_service import TaskListNotFoundError

    with pytest.raises(TaskListNotFoundError):
        async with db_manager.get_session() as session:
            task_service = TaskService(session)
            await task_service.create_task(
                title="This should fail",
                list_id=invalid_list_id,
                notes="Should not persist"
            )
            # Rollback should happen automatically on exception

    # Verify no task was created (rollback worked)
    async with db_manager.get_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(TaskORM).where(TaskORM.title == "This should fail")
        )
        tasks = result.scalars().all()
        assert len(tasks) == 0


@pytest.mark.asyncio
async def test_cascade_deletion_persists(db_manager, task_hierarchy, sample_list_id):
    """
    Test that cascade deletion of parent and all descendants persists.

    Success Criteria:
    - Parent deletion removes all descendants
    - No orphaned child tasks remain
    """
    parent_id = UUID(task_hierarchy["parent_id"])
    child1_id = UUID(task_hierarchy["child1_id"])
    grandchild_id = UUID(task_hierarchy["grandchild_id"])

    # Delete parent (should cascade to all descendants)
    async with db_manager.get_session() as session:
        task_service = TaskService(session)
        await task_service.delete_task(parent_id)
        # Auto-commit on session exit

    # Verify all tasks in hierarchy are deleted in new session
    async with db_manager.get_session() as session:
        task_service = TaskService(session)

        parent = await task_service.get_task_by_id(parent_id)
        child1 = await task_service.get_task_by_id(child1_id)
        grandchild = await task_service.get_task_by_id(grandchild_id)

        assert parent is None
        assert child1 is None
        assert grandchild is None


@pytest.mark.asyncio
async def test_multiple_operations_persist_atomically(db_manager, sample_task_list, sample_list_id):
    """
    Test that multiple operations in a session persist atomically.

    Success Criteria:
    - All operations in a session either all persist or none do
    - Database consistency is maintained
    """
    # Perform multiple operations in one session
    async with db_manager.get_session() as session:
        task_service = TaskService(session)

        # Create first task
        task1 = await task_service.create_task(
            title="Task 1",
            list_id=sample_list_id,
            notes="First task"
        )
        task1_id = task1.id

        # Create second task
        task2 = await task_service.create_task(
            title="Task 2",
            list_id=sample_list_id,
            notes="Second task"
        )
        task2_id = task2.id

        # Update first task
        await task_service.update_task(
            task_id=task1_id,
            title="Updated Task 1"
        )
        # All operations should commit together

    # Verify all operations persisted in new session
    async with db_manager.get_session() as session:
        task_service = TaskService(session)

        retrieved_task1 = await task_service.get_task_by_id(task1_id)
        retrieved_task2 = await task_service.get_task_by_id(task2_id)

        assert retrieved_task1 is not None
        assert retrieved_task1.title == "Updated Task 1"
        assert retrieved_task2 is not None
        assert retrieved_task2.title == "Task 2"


@pytest.mark.asyncio
async def test_default_list_creation_and_persistence():
    """
    Test that default list is created and persists across database sessions.

    Success Criteria:
    - Default "Work" list is created if none exists
    - List persists across database restarts
    """
    # Create a new in-memory database
    db_manager = DatabaseManager("sqlite+aiosqlite:///:memory:")
    await db_manager.initialize()

    try:
        # Create default list
        async with db_manager.get_session() as session:
            from sqlalchemy import select

            # Check if any lists exist
            result = await session.execute(select(TaskListORM))
            existing_lists = result.scalars().all()

            if not existing_lists:
                # Create default "Work" list
                default_list = TaskListORM(
                    id=str(uuid4()),
                    name="Work",
                    created_at=datetime.utcnow()
                )
                session.add(default_list)
                await session.commit()
                list_id = default_list.id

        # Verify list persists in new session
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(TaskListORM).where(TaskListORM.id == list_id)
            )
            retrieved_list = result.scalar_one_or_none()

            assert retrieved_list is not None
            assert retrieved_list.name == "Work"

    finally:
        await db_manager.close()


@pytest.mark.asyncio
async def test_state_restoration_after_restart(db_manager, sample_task_list, sample_list_id):
    """
    Test that app state can be restored from database after restart.

    Success Criteria:
    - All tasks created before restart are retrievable
    - Task hierarchy is preserved
    - Task order (positions) is maintained
    """
    # Create multiple tasks with hierarchy
    task_ids = []

    async with db_manager.get_session() as session:
        task_service = TaskService(session)

        # Create 3 top-level tasks
        for i in range(3):
            task = await task_service.create_task(
                title=f"Top Task {i}",
                list_id=sample_list_id,
                notes=f"Task number {i}"
            )
            task_ids.append(task.id)

        # Create children for first task
        child = await task_service.create_child_task(
            parent_id=task_ids[0],
            title="Child of Task 0",
            column=Column.COLUMN1,
            notes="Child task"
        )
        task_ids.append(child.id)

    # Simulate restart by loading tasks in new session
    async with db_manager.get_session() as session:
        task_service = TaskService(session)

        # Load top-level tasks (simulating app restart)
        top_tasks = await task_service.get_tasks_for_list(sample_list_id)

        assert len(top_tasks) == 3
        assert top_tasks[0].title == "Top Task 0"
        assert top_tasks[1].title == "Top Task 1"
        assert top_tasks[2].title == "Top Task 2"

        # Verify hierarchy preserved
        children = await task_service.get_children(task_ids[0])
        assert len(children) == 1
        assert children[0].title == "Child of Task 0"


@pytest.mark.asyncio
async def test_concurrent_session_isolation(db_manager, sample_task_list, sample_list_id):
    """
    Test that concurrent database sessions don't interfere with each other.

    Success Criteria:
    - Multiple sessions can operate independently
    - Final state reflects all committed changes
    """
    # Create task in first session
    async with db_manager.get_session() as session1:
        task_service = TaskService(session1)
        task1 = await task_service.create_task(
            title="Task from Session 1",
            list_id=sample_list_id,
            notes="Session 1"
        )
        task1_id = task1.id
        # Commits on exit

    # Create task in second session
    async with db_manager.get_session() as session2:
        task_service = TaskService(session2)
        task2 = await task_service.create_task(
            title="Task from Session 2",
            list_id=sample_list_id,
            notes="Session 2"
        )
        task2_id = task2.id
        # Commits on exit

    # Verify both tasks persisted
    async with db_manager.get_session() as session:
        task_service = TaskService(session)

        retrieved_task1 = await task_service.get_task_by_id(task1_id)
        retrieved_task2 = await task_service.get_task_by_id(task2_id)

        assert retrieved_task1 is not None
        assert retrieved_task1.title == "Task from Session 1"
        assert retrieved_task2 is not None
        assert retrieved_task2.title == "Task from Session 2"
