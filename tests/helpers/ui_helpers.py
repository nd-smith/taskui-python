"""UI helper functions for TaskUI integration tests.

This module provides reusable helper functions that encapsulate common
test operations to reduce code duplication and improve test maintainability.
"""

from typing import Optional, List
from uuid import UUID

from textual.pilot import Pilot

from taskui.ui.app import TaskUI
from taskui.ui.components.column import TaskColumn
from taskui.ui.components.task_modal import TaskCreationModal
from taskui.models import Task
from taskui.services.task_service import TaskService


# ==============================================================================
# Task Creation Helpers
# ==============================================================================


async def create_task_via_modal(
    pilot: Pilot,
    title: str,
    notes: str = "",
    mode: str = "create_sibling",
    **kwargs
) -> None:
    """Create a task through the modal interface.

    This helper encapsulates the complete flow of:
    1. Opening the modal (caller should do this before calling)
    2. Filling in the title and notes fields
    3. Saving the modal
    4. Waiting for UI updates

    Args:
        pilot: The Textual pilot instance for the test
        title: The task title
        notes: Optional task notes (default: "")
        mode: Modal mode - "create_sibling", "create_child", or "edit"
        **kwargs: Additional fields to set on the modal

    Example:
        >>> async with TaskUI().run_test() as pilot:
        ...     app = pilot.app
        ...     app.action_new_sibling_task()
        ...     await pilot.pause()
        ...     await create_task_via_modal(pilot, "My Task", "Some notes")
        ...     # Task is now created and modal is closed
    """
    app = pilot.app
    modal = app.screen
    assert isinstance(modal, TaskCreationModal), f"Expected TaskCreationModal, got {type(modal)}"

    # Fill in the modal fields
    await fill_task_modal(pilot, title=title, notes=notes, **kwargs)

    # Save the modal
    await save_modal(pilot)


async def create_sibling_task(
    pilot: Pilot,
    title: str,
    notes: str = ""
) -> Task:
    """Create a sibling task using the N key shortcut.

    This helper encapsulates the complete workflow:
    1. Trigger the sibling task creation action
    2. Fill in the modal with provided data
    3. Save the modal
    4. Return the created task

    Args:
        pilot: The Textual pilot instance for the test
        title: The task title
        notes: Optional task notes (default: "")

    Returns:
        The created Task object

    Example:
        >>> async with TaskUI().run_test() as pilot:
        ...     task = await create_sibling_task(pilot, "New Task", "Task notes")
        ...     assert task.title == "New Task"
    """
    app = pilot.app

    # Trigger sibling task creation
    app.action_new_sibling_task()
    await pilot.pause()

    # Fill and save modal
    await create_task_via_modal(pilot, title, notes, mode="create_sibling")

    # Get the created task from Column 1
    column1 = app.query_one("#column-1", TaskColumn)
    tasks = column1._tasks

    # Find the task we just created (should be the one with matching title)
    created_task = next((t for t in tasks if t.title == title), None)
    assert created_task is not None, f"Task '{title}' not found after creation"

    return created_task


async def create_child_task(
    pilot: Pilot,
    title: str,
    notes: str = ""
) -> Task:
    """Create a child task using the C key shortcut.

    This helper encapsulates the complete workflow:
    1. Trigger the child task creation action (requires a task to be selected)
    2. Fill in the modal with provided data
    3. Save the modal
    4. Return the created task

    Note: A task must be selected before calling this helper.

    Args:
        pilot: The Textual pilot instance for the test
        title: The task title
        notes: Optional task notes (default: "")

    Returns:
        The created Task object

    Example:
        >>> async with TaskUI().run_test() as pilot:
        ...     parent = await create_sibling_task(pilot, "Parent")
        ...     await select_task_in_column(pilot, "column-1", 0)
        ...     child = await create_child_task(pilot, "Child Task")
        ...     assert child.parent_id == parent.id
    """
    app = pilot.app

    # Trigger child task creation
    app.action_new_child_task()
    await pilot.pause()

    # Fill and save modal
    await create_task_via_modal(pilot, title, notes, mode="create_child")

    # The child task will be in the database, we need to get it
    # from the current focused column after the operation
    focused_column_id = app._focused_column_id
    column = app.query_one(f"#{focused_column_id}", TaskColumn)

    # Find the task we just created
    created_task = next((t for t in column._tasks if t.title == title), None)
    assert created_task is not None, f"Child task '{title}' not found after creation"

    return created_task


# ==============================================================================
# Selection Helpers
# ==============================================================================


async def select_task_in_column(
    pilot: Pilot,
    column_id: str,
    index: int
) -> Task:
    """Select a task at the specified index in a column.

    This helper:
    1. Gets the column by ID
    2. Updates the selection index
    3. Posts a TaskSelected message to trigger updates
    4. Waits for UI to update
    5. Returns the selected task

    Args:
        pilot: The Textual pilot instance for the test
        column_id: The column ID (e.g., "column-1", "column-2")
        index: The index of the task to select (0-based)

    Returns:
        The selected Task object

    Example:
        >>> async with TaskUI().run_test() as pilot:
        ...     # Create some tasks first
        ...     task = await select_task_in_column(pilot, "column-1", 0)
        ...     assert task is not None
    """
    app = pilot.app
    column = app.query_one(f"#{column_id}", TaskColumn)

    # Ensure index is valid
    assert 0 <= index < len(column._tasks), f"Index {index} out of range for column {column_id}"

    # Update selection
    column._selected_index = index
    task = column.get_selected_task()

    # Post selection message to trigger updates
    column.post_message(
        TaskColumn.TaskSelected(task=task, column_id=column_id)
    )
    await pilot.pause()

    return task


async def get_selected_task_from_column(
    pilot: Pilot,
    column_id: str
) -> Optional[Task]:
    """Get the currently selected task from a column.

    Args:
        pilot: The Textual pilot instance for the test
        column_id: The column ID (e.g., "column-1", "column-2")

    Returns:
        The selected Task object, or None if no task is selected

    Example:
        >>> async with TaskUI().run_test() as pilot:
        ...     task = await get_selected_task_from_column(pilot, "column-1")
        ...     if task:
        ...         print(f"Selected: {task.title}")
    """
    app = pilot.app
    column = app.query_one(f"#{column_id}", TaskColumn)
    return column.get_selected_task()


# ==============================================================================
# Navigation Helpers
# ==============================================================================


async def navigate_to_column(
    pilot: Pilot,
    column_id: str
) -> None:
    """Navigate to a specific column.

    This helper navigates from the current column to the target column
    using Tab or Shift+Tab as appropriate.

    Args:
        pilot: The Textual pilot instance for the test
        column_id: The target column ID (e.g., "column-1", "column-2", "column-3")

    Example:
        >>> async with TaskUI().run_test() as pilot:
        ...     await navigate_to_column(pilot, "column-2")
        ...     assert pilot.app._focused_column_id == "column-2"
    """
    app = pilot.app
    current = app._focused_column_id

    # Map of column IDs to their positions
    column_positions = {
        "column-1": 0,
        "column-2": 1,
        "column-3": 2,
    }

    current_pos = column_positions.get(current, 0)
    target_pos = column_positions.get(column_id, 0)

    # Navigate forward with Tab
    if target_pos > current_pos:
        steps = target_pos - current_pos
        for _ in range(steps):
            await pilot.press("tab")
            await pilot.pause()
    # Navigate backward with Shift+Tab
    elif target_pos < current_pos:
        steps = current_pos - target_pos
        for _ in range(steps):
            await pilot.press("shift+tab")
            await pilot.pause()

    # Verify we're at the right column
    assert app._focused_column_id == column_id, \
        f"Failed to navigate to {column_id}, currently at {app._focused_column_id}"


async def navigate_down(
    pilot: Pilot,
    count: int = 1
) -> None:
    """Navigate down N items in the currently focused column.

    Args:
        pilot: The Textual pilot instance for the test
        count: Number of times to press the down arrow (default: 1)

    Example:
        >>> async with TaskUI().run_test() as pilot:
        ...     # Create some tasks first
        ...     await navigate_down(pilot, count=2)
        ...     # Now selected task is 2 positions lower
    """
    for _ in range(count):
        await pilot.press("down")
        await pilot.pause()


async def navigate_up(
    pilot: Pilot,
    count: int = 1
) -> None:
    """Navigate up N items in the currently focused column.

    Args:
        pilot: The Textual pilot instance for the test
        count: Number of times to press the up arrow (default: 1)

    Example:
        >>> async with TaskUI().run_test() as pilot:
        ...     # Create some tasks first
        ...     await navigate_down(pilot, count=3)
        ...     await navigate_up(pilot, count=1)
        ...     # Now selected task is 2 positions from the top
    """
    for _ in range(count):
        await pilot.press("up")
        await pilot.pause()


# ==============================================================================
# Modal Helpers
# ==============================================================================


async def fill_task_modal(
    pilot: Pilot,
    title: Optional[str] = None,
    notes: Optional[str] = None,
    **kwargs
) -> None:
    """Fill in the fields of a task creation/edit modal.

    Args:
        pilot: The Textual pilot instance for the test
        title: The task title (if None, won't change the title)
        notes: The task notes (if None, won't change the notes)
        **kwargs: Additional fields to set (reserved for future use)

    Example:
        >>> async with TaskUI().run_test() as pilot:
        ...     app = pilot.app
        ...     app.action_new_sibling_task()
        ...     await pilot.pause()
        ...     await fill_task_modal(pilot, title="My Task", notes="Details")
    """
    app = pilot.app
    modal = app.screen
    assert isinstance(modal, TaskCreationModal), f"Expected TaskCreationModal, got {type(modal)}"

    # Fill title if provided
    if title is not None:
        title_input = modal.query_one("#title-input")
        title_input.value = title

    # Fill notes if provided
    if notes is not None:
        notes_input = modal.query_one("#notes-input")
        notes_input.text = notes

    await pilot.pause()


async def save_modal(pilot: Pilot) -> None:
    """Save and close the current modal.

    Args:
        pilot: The Textual pilot instance for the test

    Example:
        >>> async with TaskUI().run_test() as pilot:
        ...     app = pilot.app
        ...     app.action_new_sibling_task()
        ...     await pilot.pause()
        ...     await fill_task_modal(pilot, title="Task")
        ...     await save_modal(pilot)
        ...     # Modal is now closed and task is created
    """
    app = pilot.app
    modal = app.screen
    assert isinstance(modal, TaskCreationModal), f"Expected TaskCreationModal, got {type(modal)}"

    modal.action_save()
    await pilot.pause()


async def cancel_modal(pilot: Pilot) -> None:
    """Cancel and close the current modal without saving.

    Args:
        pilot: The Textual pilot instance for the test

    Example:
        >>> async with TaskUI().run_test() as pilot:
        ...     app = pilot.app
        ...     app.action_new_sibling_task()
        ...     await pilot.pause()
        ...     await cancel_modal(pilot)
        ...     # Modal is closed, no task was created
    """
    app = pilot.app
    modal = app.screen
    assert isinstance(modal, TaskCreationModal), f"Expected TaskCreationModal, got {type(modal)}"

    modal.action_cancel()
    await pilot.pause()


# ==============================================================================
# Assertion Helpers
# ==============================================================================


async def assert_column_has_tasks(
    pilot: Pilot,
    column_id: str,
    count: int
) -> None:
    """Assert that a column contains exactly the expected number of tasks.

    Args:
        pilot: The Textual pilot instance for the test
        column_id: The column ID (e.g., "column-1", "column-2")
        count: Expected number of tasks

    Raises:
        AssertionError: If the task count doesn't match

    Example:
        >>> async with TaskUI().run_test() as pilot:
        ...     await create_sibling_task(pilot, "Task 1")
        ...     await create_sibling_task(pilot, "Task 2")
        ...     await assert_column_has_tasks(pilot, "column-1", 2)
    """
    app = pilot.app
    column = app.query_one(f"#{column_id}", TaskColumn)
    actual_count = len(column._tasks)
    assert actual_count == count, \
        f"Expected {count} tasks in {column_id}, but found {actual_count}"


async def assert_task_in_column(
    pilot: Pilot,
    column_id: str,
    title: str
) -> Task:
    """Assert that a task with the given title exists in the specified column.

    Args:
        pilot: The Textual pilot instance for the test
        column_id: The column ID (e.g., "column-1", "column-2")
        title: The task title to search for

    Returns:
        The found Task object

    Raises:
        AssertionError: If the task is not found

    Example:
        >>> async with TaskUI().run_test() as pilot:
        ...     await create_sibling_task(pilot, "Important Task")
        ...     task = await assert_task_in_column(pilot, "column-1", "Important Task")
        ...     assert task.title == "Important Task"
    """
    app = pilot.app
    column = app.query_one(f"#{column_id}", TaskColumn)
    task = next((t for t in column._tasks if t.title == title), None)
    assert task is not None, f"Task '{title}' not found in {column_id}"
    return task


async def assert_task_exists_in_db(
    pilot: Pilot,
    task_id: UUID,
    expected_title: Optional[str] = None
) -> Task:
    """Assert that a task exists in the database with optional title check.

    Args:
        pilot: The Textual pilot instance for the test
        task_id: The UUID of the task to check
        expected_title: Optional expected title to verify

    Returns:
        The Task object from the database

    Raises:
        AssertionError: If the task doesn't exist or title doesn't match

    Example:
        >>> async with TaskUI().run_test() as pilot:
        ...     task = await create_sibling_task(pilot, "DB Task")
        ...     db_task = await assert_task_exists_in_db(pilot, task.id, "DB Task")
        ...     assert db_task.id == task.id
    """
    app = pilot.app
    async with app._db_manager.get_session() as session:
        task_service = TaskService(session)
        db_task = await task_service.get_task_by_id(task_id)

    assert db_task is not None, f"Task with ID {task_id} not found in database"

    if expected_title is not None:
        assert db_task.title == expected_title, \
            f"Expected task title '{expected_title}', but found '{db_task.title}'"

    return db_task


# ==============================================================================
# Database Helpers
# ==============================================================================


async def get_task_service(pilot: Pilot):
    """Get a TaskService instance with an active database session.

    This is a context manager that provides a TaskService with an active session.
    The session will be automatically closed when the context exits.

    Args:
        pilot: The Textual pilot instance for the test

    Yields:
        TaskService instance with active database session

    Example:
        >>> async with TaskUI().run_test() as pilot:
        ...     async with get_task_service(pilot) as task_service:
        ...         tasks = await task_service.get_tasks_for_list(list_id, False)
        ...         assert len(tasks) > 0
    """
    app = pilot.app
    async with app._db_manager.get_session() as session:
        yield TaskService(session)


async def get_tasks_from_db(
    pilot: Pilot,
    list_id: UUID,
    include_archived: bool = False
) -> List[Task]:
    """Get all tasks for a list from the database.

    Args:
        pilot: The Textual pilot instance for the test
        list_id: The UUID of the list
        include_archived: Whether to include archived tasks (default: False)

    Returns:
        List of Task objects from the database

    Example:
        >>> async with TaskUI().run_test() as pilot:
        ...     app = pilot.app
        ...     tasks = await get_tasks_from_db(pilot, app._current_list_id)
        ...     print(f"Found {len(tasks)} tasks in database")
    """
    app = pilot.app
    async with app._db_manager.get_session() as session:
        task_service = TaskService(session)
        tasks = await task_service.get_tasks_for_list(list_id, include_archived)
    return tasks
