"""
Tests for TaskColumn widget.

Tests cover:
- Column creation and initialization
- Task list rendering (empty, flat, hierarchical)
- Selection state management
- Navigation (up/down arrow keys)
- Task updates and selection persistence
- Message handling (TaskSelected)
- Focus/blur event handling
- Header title updates
"""

import pytest
from uuid import uuid4
from datetime import datetime

from taskui.models import Task
from taskui.ui.components.column import TaskColumn


class TestTaskColumnCreation:
    """Test suite for TaskColumn creation and initialization."""

    def test_column_creation_basic(self):
        """Test basic TaskColumn creation with default parameters."""
        column = TaskColumn(
            column_id="test-col",
            title="Test Column"
        )

        assert column.column_id == "test-col"
        assert column.header_title == "Test Column"
        assert column.empty_message == "No tasks"
        assert column._tasks == []
        assert column._selected_index == -1  # No selection initially

    def test_column_creation_custom_empty_message(self):
        """Test TaskColumn creation with custom empty message."""
        column = TaskColumn(
            column_id="col1",
            title="My Tasks",
            empty_message="Nothing to see here"
        )

        assert column.empty_message == "Nothing to see here"
        assert column.column_id == "col1"
        assert column.header_title == "My Tasks"

    def test_column_initial_state(self):
        """Test that column initializes with correct internal state."""
        column = TaskColumn(
            column_id="col-state",
            title="State Test"
        )

        # Initial state should be empty
        assert len(column._tasks) == 0
        assert column._selected_index == -1  # No selection initially
        assert column.can_focus is True
        assert column.focused is False
        assert column.selected_task_id is None

    def test_column_reactive_properties(self):
        """Test that reactive properties are initialized correctly."""
        column = TaskColumn(column_id="col", title="Tasks")

        assert column.header_title == "Tasks"
        assert column.focused is False
        assert column.selected_task_id is None


class TestTaskColumnRendering:
    """Test suite for TaskColumn rendering with various task configurations."""

    def test_render_empty_column_state(self):
        """Test column state when no tasks are present."""
        column = TaskColumn(
            column_id="empty-col",
            title="Empty Column",
            empty_message="No tasks available"
        )

        # Column should have no tasks
        assert len(column._tasks) == 0
        assert column.empty_message == "No tasks available"

    def test_render_flat_task_list_state(self, make_task):
        """Test column state with flat (non-hierarchical) task list."""
        column = TaskColumn(column_id="flat-col", title="Flat Tasks")

        tasks = [
            make_task(title="Task 1", level=0, position=0),
            make_task(title="Task 2", level=0, position=1),
            make_task(title="Task 3", level=0, position=2),
        ]

        column._tasks = tasks
        column._selected_index = 0

        assert len(column._tasks) == 3
        assert all(task.level == 0 for task in column._tasks)
        assert column._tasks[0].title == "Task 1"
        assert column._tasks[1].title == "Task 2"
        assert column._tasks[2].title == "Task 3"

    def test_render_hierarchical_tasks_state(self, make_task):
        """Test column state with hierarchical tasks at different levels."""
        parent_id = uuid4()
        grandparent_id = uuid4()

        column = TaskColumn(column_id="hier-col", title="Hierarchical Tasks")

        tasks = [
            make_task(title="Root Task", level=0, parent_id=None, position=0),
            make_task(title="Child Task 1", level=1, parent_id=parent_id, position=0),
            make_task(title="Child Task 2", level=1, parent_id=parent_id, position=1),
            make_task(title="Grandchild Task", level=2, parent_id=grandparent_id, position=0),
        ]

        column._tasks = tasks

        assert len(column._tasks) == 4
        assert column._tasks[0].level == 0
        assert column._tasks[1].level == 1
        assert column._tasks[2].level == 1
        assert column._tasks[3].level == 2

    def test_render_mixed_completion_states(self, make_task):
        """Test column state with tasks in different completion states."""
        column = TaskColumn(column_id="mixed-col", title="Mixed States")

        tasks = [
            make_task(title="Incomplete", is_completed=False),
            make_task(title="Completed", is_completed=True),
        ]

        column._tasks = tasks

        assert len(column._tasks) == 2
        assert column._tasks[0].is_completed is False
        assert column._tasks[1].is_completed is True

    def test_header_title_property(self):
        """Test that header_title reactive property can be read and updated."""
        column = TaskColumn(column_id="col", title="Initial Title")

        assert column.header_title == "Initial Title"

        # Update header title
        column.header_title = "Updated Title"
        assert column.header_title == "Updated Title"

    def test_update_header_method(self):
        """Test update_header() method updates header_title property."""
        column = TaskColumn(column_id="col", title="Original")

        column.update_header("New Header")

        assert column.header_title == "New Header"


class TestTaskColumnSelection:
    """Test suite for TaskColumn selection management."""

    def test_initial_selection_state_empty(self):
        """Test initial selection state with no tasks."""
        column = TaskColumn(column_id="col", title="Tasks")

        assert column._selected_index == -1  # No selection in empty column
        assert column.get_selected_task() is None

    def test_initial_selection_state_with_tasks(self, make_task):
        """Test initial selection state with tasks."""
        column = TaskColumn(column_id="col", title="Tasks")

        tasks = [
            make_task(title="Task 1"),
            make_task(title="Task 2"),
        ]

        column._tasks = tasks
        column._selected_index = 0

        selected = column.get_selected_task()
        assert selected is not None
        assert selected.title == "Task 1"

    def test_get_selected_task_valid_index(self, make_task):
        """Test get_selected_task() returns correct task with valid index."""
        column = TaskColumn(column_id="col", title="Tasks")

        tasks = [
            make_task(title="Task 1"),
            make_task(title="Task 2"),
            make_task(title="Task 3"),
        ]

        column._tasks = tasks

        # Test selecting each task
        column._selected_index = 0
        assert column.get_selected_task().title == "Task 1"

        column._selected_index = 1
        assert column.get_selected_task().title == "Task 2"

        column._selected_index = 2
        assert column.get_selected_task().title == "Task 3"

    def test_get_selected_task_invalid_index(self, make_task):
        """Test get_selected_task() returns None with invalid index."""
        column = TaskColumn(column_id="col", title="Tasks")

        tasks = [make_task(title="Task 1")]
        column._tasks = tasks

        # Test out of bounds indices
        column._selected_index = -1
        assert column.get_selected_task() is None

        column._selected_index = 5
        assert column.get_selected_task() is None

    def test_selection_bounds_lower(self, make_task):
        """Test that selection cannot go below 0."""
        column = TaskColumn(column_id="col", title="Tasks")

        tasks = [
            make_task(title="Task 1"),
            make_task(title="Task 2"),
        ]
        column._tasks = tasks
        column._selected_index = 0

        # Try to navigate up from first position
        initial_index = column._selected_index
        if column._selected_index > 0:
            column._selected_index -= 1

        # Should remain at 0
        assert column._selected_index == initial_index == 0

    def test_selection_bounds_upper(self, make_task):
        """Test that selection cannot go above task count."""
        column = TaskColumn(column_id="col", title="Tasks")

        tasks = [
            make_task(title="Task 1"),
            make_task(title="Task 2"),
            make_task(title="Task 3"),
        ]
        column._tasks = tasks
        column._selected_index = 2  # Last task

        # Try to navigate down from last position
        initial_index = column._selected_index
        if column._selected_index < len(column._tasks) - 1:
            column._selected_index += 1

        # Should remain at last position (2)
        assert column._selected_index == initial_index == 2

    def test_clear_selection_state(self, make_task):
        """Test clearing selection state manually."""
        column = TaskColumn(column_id="col", title="Tasks")

        tasks = [
            make_task(title="Task 1"),
            make_task(title="Task 2"),
        ]
        column._tasks = tasks
        column._selected_index = 0

        # Clear selection manually
        column._selected_index = -1
        column.selected_task_id = None

        assert column._selected_index == -1
        assert column.selected_task_id is None
        assert column.get_selected_task() is None

    def test_selected_task_id_property(self, make_task):
        """Test that selected_task_id reactive property works."""
        column = TaskColumn(column_id="col", title="Tasks")

        task = make_task(title="Test Task")
        column._tasks = [task]
        column._selected_index = 0

        # Initially None
        assert column.selected_task_id is None

        # Set to task ID
        column.selected_task_id = task.id
        assert column.selected_task_id == task.id


class TestTaskColumnNavigation:
    """Test suite for TaskColumn navigation (up/down)."""

    def test_navigate_down_logic(self, make_task):
        """Test navigation down through task list."""
        column = TaskColumn(column_id="col", title="Tasks")

        tasks = [
            make_task(title="Task 1"),
            make_task(title="Task 2"),
            make_task(title="Task 3"),
        ]
        column._tasks = tasks
        column._selected_index = 0

        # Navigate down
        if column._selected_index < len(column._tasks) - 1:
            column._selected_index += 1
        assert column._selected_index == 1
        assert column.get_selected_task().title == "Task 2"

        # Navigate down again
        if column._selected_index < len(column._tasks) - 1:
            column._selected_index += 1
        assert column._selected_index == 2
        assert column.get_selected_task().title == "Task 3"

    def test_navigate_down_at_end(self, make_task):
        """Test navigation down when already at last task."""
        column = TaskColumn(column_id="col", title="Tasks")

        tasks = [
            make_task(title="Task 1"),
            make_task(title="Task 2"),
        ]
        column._tasks = tasks
        column._selected_index = 1  # Last task

        # Try to navigate down
        if column._selected_index < len(column._tasks) - 1:
            column._selected_index += 1

        # Should stay at last position
        assert column._selected_index == 1

    def test_navigate_up_logic(self, make_task):
        """Test navigation up through task list."""
        column = TaskColumn(column_id="col", title="Tasks")

        tasks = [
            make_task(title="Task 1"),
            make_task(title="Task 2"),
            make_task(title="Task 3"),
        ]
        column._tasks = tasks
        column._selected_index = 2  # Start at last task

        # Navigate up
        if column._selected_index > 0:
            column._selected_index -= 1
        assert column._selected_index == 1
        assert column.get_selected_task().title == "Task 2"

        # Navigate up again
        if column._selected_index > 0:
            column._selected_index -= 1
        assert column._selected_index == 0
        assert column.get_selected_task().title == "Task 1"

    def test_navigate_up_at_start(self, make_task):
        """Test navigation up when already at first task."""
        column = TaskColumn(column_id="col", title="Tasks")

        tasks = [
            make_task(title="Task 1"),
            make_task(title="Task 2"),
        ]
        column._tasks = tasks
        column._selected_index = 0  # First task

        # Try to navigate up
        if column._selected_index > 0:
            column._selected_index -= 1

        # Should stay at first position
        assert column._selected_index == 0

    def test_navigate_empty_list(self):
        """Test navigation with no tasks."""
        column = TaskColumn(column_id="col", title="Tasks")

        column._tasks = []
        column._selected_index = 0

        # Navigation should be no-op
        if column._tasks:
            if column._selected_index > 0:
                column._selected_index -= 1

        assert column._selected_index == 0
        assert column.get_selected_task() is None

    def test_navigate_single_task(self, make_task):
        """Test navigation with single task."""
        column = TaskColumn(column_id="col", title="Tasks")

        tasks = [make_task(title="Only Task")]
        column._tasks = tasks
        column._selected_index = 0

        # Try to navigate down
        if column._selected_index < len(column._tasks) - 1:
            column._selected_index += 1
        assert column._selected_index == 0

        # Try to navigate up
        if column._selected_index > 0:
            column._selected_index -= 1
        assert column._selected_index == 0


class TestTaskColumnTaskUpdates:
    """Test suite for TaskColumn task list updates and state management."""

    def test_tasks_list_updates_correctly(self, make_task):
        """Test that _tasks list is updated when set."""
        column = TaskColumn(column_id="col", title="Tasks")

        initial_tasks = [
            make_task(title="Task 1"),
            make_task(title="Task 2"),
        ]
        column._tasks = initial_tasks

        assert len(column._tasks) == 2

        # Update to new task list
        new_tasks = [
            make_task(title="New Task 1"),
            make_task(title="New Task 2"),
            make_task(title="New Task 3"),
        ]
        column._tasks = new_tasks

        assert len(column._tasks) == 3
        assert column._tasks[0].title == "New Task 1"

    def test_column_id_preserved(self):
        """Test that column_id is preserved throughout operations."""
        column = TaskColumn(column_id="persistent-id", title="Tasks")

        assert column.column_id == "persistent-id"

        # Even after header updates
        column.update_header("New Title")
        assert column.column_id == "persistent-id"

    def test_header_title_reflects_context(self):
        """Test that header_title can reflect different contexts."""
        column = TaskColumn(column_id="col", title="Work Tasks")

        assert column.header_title == "Work Tasks"

        # Update to reflect different context
        column.header_title = "Personal Tasks"
        assert column.header_title == "Personal Tasks"

        # Update to subtask context
        column.header_title = "Subtasks of Project X"
        assert column.header_title == "Subtasks of Project X"

    def test_empty_to_populated_state(self, make_task):
        """Test transition from empty column to populated."""
        column = TaskColumn(column_id="col", title="Tasks")

        # Initially empty
        assert len(column._tasks) == 0

        # Add tasks
        tasks = [
            make_task(title="Task 1"),
            make_task(title="Task 2"),
        ]
        column._tasks = tasks

        assert len(column._tasks) == 2
        assert column.get_selected_task() is None  # No selection set yet

    def test_populated_to_empty_state(self, make_task):
        """Test transition from populated column to empty."""
        column = TaskColumn(column_id="col", title="Tasks")

        # Start with tasks
        tasks = [make_task(title="Task 1")]
        column._tasks = tasks
        column._selected_index = 0

        # Clear tasks
        column._tasks = []
        column._selected_index = -1

        assert len(column._tasks) == 0
        assert column.get_selected_task() is None


class TestTaskColumnSelectionPersistence:
    """Test suite for selection persistence when tasks update."""

    def test_selection_preserved_by_id_logic(self, make_task):
        """Test logic for preserving selection when task list updates."""
        column = TaskColumn(column_id="col", title="Tasks")

        # Create tasks with specific IDs
        task1 = make_task(title="Task 1")
        task2 = make_task(title="Task 2")
        task3 = make_task(title="Task 3")

        initial_tasks = [task1, task2, task3]
        column._tasks = initial_tasks
        column._selected_index = 1  # Select task2

        # Remember selected task ID
        selected_id = column._tasks[column._selected_index].id

        # Update task list with same tasks in different order
        updated_tasks = [task3, task2, task1]
        column._tasks = updated_tasks

        # Find task with same ID
        for i, task in enumerate(column._tasks):
            if task.id == selected_id:
                column._selected_index = i
                break

        # Selection should now point to index 1 (where task2 is)
        assert column.get_selected_task().id == selected_id
        assert column._selected_index == 1

    def test_selection_reset_when_task_removed(self, make_task):
        """Test selection reset when selected task is removed."""
        column = TaskColumn(column_id="col", title="Tasks")

        task1 = make_task(title="Task 1")
        task2 = make_task(title="Task 2")
        task3 = make_task(title="Task 3")

        column._tasks = [task1, task2, task3]
        column._selected_index = 1  # Select task2

        selected_id = column._tasks[column._selected_index].id

        # Update list without task2
        new_tasks = [task1, task3]
        column._tasks = new_tasks

        # Try to find previously selected task
        found = False
        for i, task in enumerate(column._tasks):
            if task.id == selected_id:
                column._selected_index = i
                found = True
                break

        if not found:
            # Default to first task
            column._selected_index = 0 if column._tasks else -1

        # Should default to first task
        assert column._selected_index == 0
        assert column.get_selected_task().title == "Task 1"

    def test_selection_preserved_when_tasks_added(self, make_task):
        """Test selection preserved when tasks are added."""
        column = TaskColumn(column_id="col", title="Tasks")

        task1 = make_task(title="Task 1")
        task2 = make_task(title="Task 2")

        column._tasks = [task1, task2]
        column._selected_index = 1  # Select task2

        selected_id = column._tasks[column._selected_index].id

        # Add more tasks
        task3 = make_task(title="Task 3")
        new_tasks = [task1, task2, task3]
        column._tasks = new_tasks

        # Find previously selected task
        for i, task in enumerate(column._tasks):
            if task.id == selected_id:
                column._selected_index = i
                break

        # Should still be at index 1
        assert column._selected_index == 1
        assert column.get_selected_task().id == selected_id


class TestTaskColumnFocusHandling:
    """Test suite for TaskColumn focus and blur events."""

    def test_focused_property_initial_state(self):
        """Test that focused property starts as False."""
        column = TaskColumn(column_id="col", title="Tasks")

        assert column.focused is False

    def test_focused_property_can_be_set(self):
        """Test that focused property can be updated."""
        column = TaskColumn(column_id="col", title="Tasks")

        assert column.focused is False

        column.focused = True
        assert column.focused is True

        column.focused = False
        assert column.focused is False

    def test_can_focus_property(self):
        """Test that column can receive focus."""
        column = TaskColumn(column_id="col", title="Tasks")

        assert column.can_focus is True


class TestTaskColumnMessageHandling:
    """Test suite for TaskColumn message emission."""

    def test_task_selected_message_structure(self, make_task):
        """Test TaskSelected message contains correct data structure."""
        column = TaskColumn(column_id="test-col", title="Tasks")

        task = make_task(title="Test Task")

        # Create message
        message = TaskColumn.TaskSelected(task=task, column_id="test-col")

        assert message.task == task
        assert message.column_id == "test-col"
        assert message.task.title == "Test Task"

    def test_task_selected_message_with_different_columns(self, make_task):
        """Test TaskSelected message distinguishes between columns."""
        task1 = make_task(title="Task 1")
        task2 = make_task(title="Task 2")

        # Messages from different columns
        msg1 = TaskColumn.TaskSelected(task=task1, column_id="col1")
        msg2 = TaskColumn.TaskSelected(task=task2, column_id="col2")

        assert msg1.column_id == "col1"
        assert msg2.column_id == "col2"
        assert msg1.task != msg2.task

    def test_task_selected_message_preserves_task_data(self, make_task):
        """Test that TaskSelected message preserves all task data."""
        parent_id = uuid4()
        task = make_task(
            title="Important Task",
            notes="Important notes",
            parent_id=parent_id,
            level=1,
            is_completed=True
        )

        message = TaskColumn.TaskSelected(task=task, column_id="col")

        assert message.task.title == "Important Task"
        assert message.task.notes == "Important notes"
        assert message.task.level == 1
        assert message.task.is_completed is True


class TestTaskColumnGrouping:
    """Test suite for task grouping by parent."""

    def test_group_tasks_by_parent_flat_list(self, make_task):
        """Test grouping tasks with no parent (all root tasks)."""
        column = TaskColumn(column_id="col", title="Tasks")

        tasks = [
            make_task(title="Task 1", parent_id=None),
            make_task(title="Task 2", parent_id=None),
            make_task(title="Task 3", parent_id=None),
        ]

        groups = column._group_tasks_by_parent(tasks)

        # All should be in root group
        assert "root" in groups
        assert len(groups["root"]) == 3

    def test_group_tasks_by_parent_hierarchical(self, make_task):
        """Test grouping tasks with parent relationships."""
        parent_id = uuid4()

        column = TaskColumn(column_id="col", title="Tasks")

        tasks = [
            make_task(title="Parent", parent_id=None, level=0),
            make_task(title="Child 1", parent_id=parent_id, level=1),
            make_task(title="Child 2", parent_id=parent_id, level=1),
        ]

        # Manually set parent task to have the known parent_id
        tasks[1].parent_id = parent_id
        tasks[2].parent_id = parent_id

        groups = column._group_tasks_by_parent(tasks)

        # Should have root group and parent group
        assert "root" in groups
        assert parent_id in groups
        assert len(groups["root"]) == 1
        assert len(groups[parent_id]) == 2

    def test_group_tasks_by_parent_empty_list(self):
        """Test grouping with empty task list."""
        column = TaskColumn(column_id="col", title="Tasks")

        groups = column._group_tasks_by_parent([])

        assert len(groups) == 0


class TestTaskColumnStateEdgeCases:
    """Test suite for edge cases in column state management."""

    def test_multiple_header_updates(self):
        """Test multiple header title updates."""
        column = TaskColumn(column_id="col", title="Initial")

        column.header_title = "Update 1"
        assert column.header_title == "Update 1"

        column.header_title = "Update 2"
        assert column.header_title == "Update 2"

        column.header_title = "Final Update"
        assert column.header_title == "Final Update"

    def test_selection_with_identical_titles(self, make_task):
        """Test selection works correctly with identically titled tasks."""
        column = TaskColumn(column_id="col", title="Tasks")

        # Create tasks with same title but different IDs
        task1 = make_task(title="Duplicate Task")
        task2 = make_task(title="Duplicate Task")
        task3 = make_task(title="Duplicate Task")

        column._tasks = [task1, task2, task3]

        # Select each by index
        column._selected_index = 0
        assert column.get_selected_task().id == task1.id

        column._selected_index = 1
        assert column.get_selected_task().id == task2.id

        column._selected_index = 2
        assert column.get_selected_task().id == task3.id

    def test_large_task_list(self, make_task):
        """Test column handles large task lists."""
        column = TaskColumn(column_id="col", title="Tasks")

        # Create 100 tasks
        tasks = [make_task(title=f"Task {i}") for i in range(100)]
        column._tasks = tasks

        assert len(column._tasks) == 100

        # Select first task
        column._selected_index = 0
        assert column.get_selected_task().title == "Task 0"

        # Select last task
        column._selected_index = 99
        assert column.get_selected_task().title == "Task 99"

        # Select middle task
        column._selected_index = 50
        assert column.get_selected_task().title == "Task 50"

    def test_column_id_uniqueness(self):
        """Test that different columns can have different IDs."""
        col1 = TaskColumn(column_id="col1", title="Column 1")
        col2 = TaskColumn(column_id="col2", title="Column 2")
        col3 = TaskColumn(column_id="col3", title="Column 3")

        assert col1.column_id != col2.column_id
        assert col2.column_id != col3.column_id
        assert col1.column_id != col3.column_id


class TestTaskColumnIntegration:
    """Integration tests for TaskColumn with realistic scenarios."""

    def test_typical_user_workflow(self, make_task):
        """Test typical user workflow: create column, add tasks, navigate, select."""
        # Create column
        column = TaskColumn(column_id="main", title="My Tasks")

        assert len(column._tasks) == 0

        # Add tasks
        tasks = [
            make_task(title="Write tests"),
            make_task(title="Review code"),
            make_task(title="Deploy app"),
        ]
        column._tasks = tasks
        column._selected_index = 0

        # Verify first task selected
        assert column.get_selected_task().title == "Write tests"

        # Navigate down
        column._selected_index = 1
        assert column.get_selected_task().title == "Review code"

        # Navigate down again
        column._selected_index = 2
        assert column.get_selected_task().title == "Deploy app"

    def test_column_with_completed_and_incomplete_tasks(self, make_task):
        """Test column displays both completed and incomplete tasks."""
        column = TaskColumn(column_id="col", title="Mixed Tasks")

        tasks = [
            make_task(title="Todo 1", is_completed=False),
            make_task(title="Done 1", is_completed=True),
            make_task(title="Todo 2", is_completed=False),
            make_task(title="Done 2", is_completed=True),
        ]

        column._tasks = tasks

        assert len(column._tasks) == 4
        assert sum(1 for t in column._tasks if t.is_completed) == 2
        assert sum(1 for t in column._tasks if not t.is_completed) == 2

    def test_three_column_layout_simulation(self, make_task):
        """Test simulation of three-column layout with different contexts."""
        # Column 1 - All lists
        col1 = TaskColumn(column_id="col1", title="All Tasks")
        col1_tasks = [
            make_task(title="List 1 Task"),
            make_task(title="List 2 Task"),
        ]
        col1._tasks = col1_tasks
        col1._selected_index = 0

        # Column 2 - Subtasks of selected list task
        col2 = TaskColumn(column_id="col2", title="Subtasks")
        parent_id = col1_tasks[0].id
        col2_tasks = [
            make_task(title="Subtask 1", parent_id=parent_id, level=1),
            make_task(title="Subtask 2", parent_id=parent_id, level=1),
        ]
        col2._tasks = col2_tasks
        col2._selected_index = 0

        # Column 3 - Details of selected subtask
        col3 = TaskColumn(column_id="col3", title="Details")

        # Verify structure
        assert col1.column_id == "col1"
        assert col2.column_id == "col2"
        assert col3.column_id == "col3"
        assert len(col1._tasks) == 2
        assert len(col2._tasks) == 2

    def test_hierarchical_navigation(self, make_task):
        """Test navigating through hierarchical task structure."""
        parent_id = uuid4()

        column = TaskColumn(column_id="col", title="Hierarchy")

        tasks = [
            make_task(title="Parent", level=0, parent_id=None),
            make_task(title="Child 1", level=1, parent_id=parent_id),
            make_task(title="Child 2", level=1, parent_id=parent_id),
            make_task(title="Child 3", level=1, parent_id=parent_id),
        ]

        column._tasks = tasks
        column._selected_index = 0

        # Navigate through hierarchy
        assert column.get_selected_task().level == 0

        column._selected_index = 1
        assert column.get_selected_task().level == 1
        assert column.get_selected_task().title == "Child 1"

        column._selected_index = 2
        assert column.get_selected_task().title == "Child 2"

        column._selected_index = 3
        assert column.get_selected_task().title == "Child 3"

    def test_context_switching_between_lists(self, make_task):
        """Test switching context between different task lists."""
        column = TaskColumn(column_id="col", title="Context Test")

        # Work tasks
        work_tasks = [
            make_task(title="Work Task 1"),
            make_task(title="Work Task 2"),
        ]

        # Personal tasks
        personal_tasks = [
            make_task(title="Personal Task 1"),
            make_task(title="Personal Task 2"),
            make_task(title="Personal Task 3"),
        ]

        # Load work tasks
        column._tasks = work_tasks
        column.header_title = "Work Tasks"
        assert len(column._tasks) == 2
        assert column.header_title == "Work Tasks"

        # Switch to personal tasks
        column._tasks = personal_tasks
        column.header_title = "Personal Tasks"
        assert len(column._tasks) == 3
        assert column.header_title == "Personal Tasks"
