# Test Helpers - Quick Reference Guide

This directory contains reusable helper functions for TaskUI integration tests to reduce brittleness and improve maintainability.

## File Structure

```
tests/helpers/
├── __init__.py         # Package initialization with exports
├── ui_helpers.py       # Core UI helper functions
└── README.md          # This file
```

## Available Helpers

### Task Creation Helpers

#### `create_task_via_modal(pilot, title, notes="", mode="create_sibling", **kwargs)`
Low-level helper to fill and save a modal that's already open.

**Example:**
```python
async with TaskUI().run_test() as pilot:
    app = pilot.app
    app.action_new_sibling_task()
    await pilot.pause()
    await create_task_via_modal(pilot, "My Task", "Some notes")
```

#### `create_sibling_task(pilot, title, notes="") -> Task`
High-level helper that handles the complete sibling task creation workflow.

**Example:**
```python
async with TaskUI().run_test() as pilot:
    task = await create_sibling_task(pilot, "New Task", "Task notes")
    assert task.title == "New Task"
```

#### `create_child_task(pilot, title, notes="") -> Task`
High-level helper that handles the complete child task creation workflow.

**Example:**
```python
async with TaskUI().run_test() as pilot:
    parent = await create_sibling_task(pilot, "Parent")
    await select_task_in_column(pilot, "column-1", 0)
    child = await create_child_task(pilot, "Child Task")
    assert child.parent_id == parent.id
```

---

### Selection Helpers

#### `select_task_in_column(pilot, column_id, index) -> Task`
Select a task at a specific index and trigger selection updates.

**Example:**
```python
async with TaskUI().run_test() as pilot:
    task = await select_task_in_column(pilot, "column-1", 0)
    assert task is not None
```

#### `get_selected_task_from_column(pilot, column_id) -> Optional[Task]`
Get the currently selected task from a column.

**Example:**
```python
async with TaskUI().run_test() as pilot:
    task = await get_selected_task_from_column(pilot, "column-1")
    if task:
        print(f"Selected: {task.title}")
```

---

### Navigation Helpers

#### `navigate_to_column(pilot, column_id)`
Navigate to a specific column using Tab/Shift+Tab.

**Example:**
```python
async with TaskUI().run_test() as pilot:
    await navigate_to_column(pilot, "column-2")
    assert pilot.app._focused_column_id == "column-2"
```

#### `navigate_down(pilot, count=1)`
Navigate down N items in the currently focused column.

**Example:**
```python
async with TaskUI().run_test() as pilot:
    await navigate_down(pilot, count=2)
    # Now selected task is 2 positions lower
```

#### `navigate_up(pilot, count=1)`
Navigate up N items in the currently focused column.

**Example:**
```python
async with TaskUI().run_test() as pilot:
    await navigate_down(pilot, count=3)
    await navigate_up(pilot, count=1)
    # Now selected task is 2 positions from the top
```

---

### Modal Helpers

#### `fill_task_modal(pilot, title=None, notes=None, **kwargs)`
Fill in the fields of a modal that's already open.

**Example:**
```python
async with TaskUI().run_test() as pilot:
    app = pilot.app
    app.action_new_sibling_task()
    await pilot.pause()
    await fill_task_modal(pilot, title="My Task", notes="Details")
```

#### `save_modal(pilot)`
Save and close the current modal.

**Example:**
```python
async with TaskUI().run_test() as pilot:
    app = pilot.app
    app.action_new_sibling_task()
    await pilot.pause()
    await fill_task_modal(pilot, title="Task")
    await save_modal(pilot)
```

#### `cancel_modal(pilot)`
Cancel and close the modal without saving.

**Example:**
```python
async with TaskUI().run_test() as pilot:
    app = pilot.app
    app.action_new_sibling_task()
    await pilot.pause()
    await cancel_modal(pilot)
    # Modal is closed, no task was created
```

---

### Assertion Helpers

#### `assert_column_has_tasks(pilot, column_id, count)`
Assert that a column contains exactly N tasks.

**Example:**
```python
async with TaskUI().run_test() as pilot:
    await create_sibling_task(pilot, "Task 1")
    await create_sibling_task(pilot, "Task 2")
    await assert_column_has_tasks(pilot, "column-1", 2)
```

#### `assert_task_in_column(pilot, column_id, title) -> Task`
Assert that a task with a specific title exists in a column.

**Example:**
```python
async with TaskUI().run_test() as pilot:
    await create_sibling_task(pilot, "Important Task")
    task = await assert_task_in_column(pilot, "column-1", "Important Task")
    assert task.title == "Important Task"
```

#### `assert_task_exists_in_db(pilot, task_id, expected_title=None) -> Task`
Assert that a task exists in the database.

**Example:**
```python
async with TaskUI().run_test() as pilot:
    task = await create_sibling_task(pilot, "DB Task")
    db_task = await assert_task_exists_in_db(pilot, task.id, "DB Task")
    assert db_task.id == task.id
```

---

### Database Helpers

#### `get_task_service(pilot)`
Context manager that provides a TaskService with an active database session.

**Example:**
```python
async with TaskUI().run_test() as pilot:
    async with get_task_service(pilot) as task_service:
        tasks = await task_service.get_tasks_for_list(list_id, False)
        assert len(tasks) > 0
```

#### `get_tasks_from_db(pilot, list_id, include_archived=False) -> List[Task]`
Get all tasks for a list from the database.

**Example:**
```python
async with TaskUI().run_test() as pilot:
    app = pilot.app
    tasks = await get_tasks_from_db(pilot, app._current_list_id)
    print(f"Found {len(tasks)} tasks in database")
```

---

## Complete Example Test

Here's a complete example showing how to use multiple helpers together:

```python
import pytest
from tests.helpers import (
    create_sibling_task,
    create_child_task,
    select_task_in_column,
    navigate_to_column,
    assert_column_has_tasks,
    assert_task_in_column,
    get_tasks_from_db,
)


@pytest.mark.asyncio
async def test_task_hierarchy_creation():
    """Test creating a task hierarchy using helpers."""
    async with TaskUI().run_test() as pilot:
        app = pilot.app
        await pilot.pause()

        # Create parent task
        parent = await create_sibling_task(pilot, "Parent Task", "Parent notes")
        assert parent.title == "Parent Task"

        # Verify it's in Column 1
        await assert_column_has_tasks(pilot, "column-1", 1)
        await assert_task_in_column(pilot, "column-1", "Parent Task")

        # Select the parent and create a child
        await select_task_in_column(pilot, "column-1", 0)
        child = await create_child_task(pilot, "Child Task", "Child notes")
        assert child.parent_id == parent.id

        # Navigate to Column 2 and verify child appears
        await navigate_to_column(pilot, "column-2")
        await assert_column_has_tasks(pilot, "column-2", 1)
        await assert_task_in_column(pilot, "column-2", "Child Task")

        # Verify both tasks exist in database
        tasks = await get_tasks_from_db(pilot, app._current_list_id)
        assert len(tasks) == 2
        task_titles = {t.title for t in tasks}
        assert task_titles == {"Parent Task", "Child Task"}
```

## Benefits

Using these helpers provides several benefits:

1. **Reduced Code Duplication**: Common patterns are encapsulated once
2. **Improved Readability**: Tests are more declarative and easier to understand
3. **Easier Maintenance**: Changes to UI patterns only need to be updated in one place
4. **Better Error Messages**: Helpers include detailed assertion messages
5. **Type Safety**: All helpers use type hints for better IDE support
6. **Comprehensive Documentation**: Each helper has detailed docstrings with examples

## Usage Tips

1. Import helpers at the top of your test file:
   ```python
   from tests.helpers import create_sibling_task, assert_column_has_tasks
   ```

2. Use high-level helpers (`create_sibling_task`) when possible for complete workflows

3. Use low-level helpers (`fill_task_modal`, `save_modal`) when you need fine-grained control

4. Combine assertion helpers with creation helpers for comprehensive tests

5. Always use `await pilot.pause()` after actions that trigger UI updates

## Future Enhancements

Potential future additions to this module:

- List switching helpers
- Archive/unarchive helpers
- Task editing helpers
- Bulk task creation helpers
- Tree structure validation helpers
- Performance timing helpers
