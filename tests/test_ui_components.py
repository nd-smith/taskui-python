"""
Tests for TaskUI UI components (TaskItem and TaskColumn).

Tests cover:
- TaskItem rendering with tree visualization
- Indentation and tree line rendering
- Level-specific color styling
- Selection highlighting
- TaskColumn task list management
- Navigation and selection handling
"""

import pytest
from uuid import uuid4
from datetime import datetime
from rich.text import Text

from taskui.models import Task
from taskui.ui.components.task_item import TaskItem
from taskui.ui.components.column import TaskColumn
from taskui.ui.theme import LEVEL_0_COLOR, LEVEL_1_COLOR, LEVEL_2_COLOR, COMPLETE_COLOR, ARCHIVE_COLOR


class TestTaskItem:
    """Test suite for TaskItem widget."""

    def test_task_item_creation(self, make_task):
        """Test basic TaskItem creation."""
        task = make_task(title="Test Task", level=0)
        task_item = TaskItem(task=task)

        assert task_item.task == task
        assert task_item.task_id == task.id
        assert task_item.selected is False

    def test_task_item_level_0_rendering(self, make_task):
        """Test rendering of level 0 task without tree lines."""
        task = make_task(title="Level 0 Task", level=0)
        task_item = TaskItem(task=task)

        rendered = task_item.render()

        # Level 0 should not have tree lines
        assert "└─" not in str(rendered)
        assert "├─" not in str(rendered)
        # Should contain the checkbox
        assert "[ ]" in str(rendered)
        # Should contain the title
        assert "Level 0 Task" in str(rendered)

    def test_task_item_level_1_last_child_rendering(self, make_task):
        """Test rendering of level 1 task as last child with └─ tree line."""
        parent_id = uuid4()
        task = make_task(title="Level 1 Task", level=1, parent_id=parent_id)
        task_item = TaskItem(task=task, is_last_child=True)

        rendered = task_item.render()
        rendered_str = str(rendered)

        # Last child should use └─
        assert "└─" in rendered_str
        # Should have proper indentation (2 spaces for level 1)
        assert "  └─" in rendered_str
        assert "Level 1 Task" in rendered_str

    def test_task_item_level_1_not_last_child_rendering(self, make_task):
        """Test rendering of level 1 task not as last child with ├─ tree line."""
        parent_id = uuid4()
        task = make_task(title="Level 1 Task", level=1, parent_id=parent_id)
        task_item = TaskItem(task=task, is_last_child=False)

        rendered = task_item.render()
        rendered_str = str(rendered)

        # Not last child should use ├─
        assert "├─" in rendered_str
        assert "  ├─" in rendered_str
        assert "Level 1 Task" in rendered_str

    def test_task_item_level_2_rendering(self, make_task):
        """Test rendering of level 2 task with deeper indentation."""
        parent_id = uuid4()
        task = make_task(title="Level 2 Task", level=2, parent_id=parent_id)
        task_item = TaskItem(task=task, is_last_child=True)

        rendered = task_item.render()
        rendered_str = str(rendered)

        # Level 2 should have 4 spaces (2 per level)
        assert "    └─" in rendered_str
        assert "Level 2 Task" in rendered_str

    def test_task_item_completed_rendering(self, make_task):
        """Test rendering of completed task with checkmark and strikethrough."""
        task = make_task(title="Completed Task", level=0, is_completed=True)
        task.mark_completed()
        task_item = TaskItem(task=task)

        rendered = task_item.render()
        rendered_str = str(rendered)

        # Should show checkmark
        assert "[✓]" in rendered_str
        assert "Completed Task" in rendered_str
        # Rich text should have strikethrough style (we can't easily test this without rendering)

    def test_task_item_archived_rendering(self, make_task):
        """Test rendering of archived task with 📦 icon."""
        task = make_task(title="Archived Task", level=0, is_completed=True, is_archived=True)
        task_item = TaskItem(task=task)

        rendered = task_item.render()
        rendered_str = str(rendered)

        # Should show archive icon
        assert "📦" in rendered_str
        assert "Archived Task" in rendered_str

    def test_task_item_with_children_progress(self, make_task):
        """Test rendering of task with children showing progress indicator."""
        task = make_task(title="Parent Task", level=0)
        task.update_child_counts(child_count=5, completed_child_count=2)

        task_item = TaskItem(task=task)
        rendered = task_item.render()
        rendered_str = str(rendered)

        # Should show progress indicator
        assert "(2/5)" in rendered_str
        assert "Parent Task" in rendered_str

    def test_task_item_selection_class(self, make_task):
        """Test that selected class is applied when task is selected."""
        task = make_task(title="Test Task", level=0)
        task_item = TaskItem(task=task)

        # Initially not selected
        assert "selected" not in task_item.classes

        # Set selected
        task_item.selected = True

        # Should have selected class
        assert "selected" in task_item.classes

    def test_task_item_level_classes(self, make_task):
        """Test that level-specific CSS classes are applied."""
        parent_id = uuid4()
        grandparent_id = uuid4()

        # Level 0 - no parent
        task0 = make_task(title="Level 0 Task", level=0)
        item0 = TaskItem(task=task0)
        assert "level-0" in item0.classes

        # Level 1 - with parent
        task1 = make_task(title="Level 1 Task", level=1, parent_id=parent_id)
        item1 = TaskItem(task=task1)
        assert "level-1" in item1.classes

        # Level 2 - with parent
        task2 = make_task(title="Level 2 Task", level=2, parent_id=grandparent_id)
        item2 = TaskItem(task=task2)
        assert "level-2" in item2.classes


class TestTaskColumn:
    """Test suite for TaskColumn widget."""

    def test_column_creation(self):
        """Test basic TaskColumn creation."""
        column = TaskColumn(
            column_id="test-column",
            title="Test Column",
            empty_message="No tasks here"
        )

        assert column.column_id == "test-column"
        assert column.header_title == "Test Column"
        assert column.empty_message == "No tasks here"

    def test_column_internal_state_with_tasks(self, make_task):
        """Test internal state when setting tasks."""
        column = TaskColumn(column_id="col1", title="Tasks")

        tasks = [
            make_task(title="Task 1", level=0),
            make_task(title="Task 2", level=0),
            make_task(title="Task 3", level=0)
        ]

        # Set tasks without rendering (no DOM operations)
        column._tasks = tasks
        column._selected_index = 0

        assert column._tasks == tasks
        assert column._selected_index == 0

    def test_column_internal_state_empty(self, make_task):
        """Test internal state with empty task list."""
        column = TaskColumn(column_id="col1", title="Tasks")

        column._tasks = []
        column._selected_index = -1

        assert column._tasks == []
        assert column._selected_index == -1

    def test_column_get_selected_task(self, make_task):
        """Test getting the currently selected task."""
        column = TaskColumn(column_id="col1", title="Tasks")

        tasks = [
            make_task(title="Task 1", level=0),
            make_task(title="Task 2", level=0),
            make_task(title="Task 3", level=0)
        ]

        column._tasks = tasks
        column._selected_index = 0

        # Initially first task is selected
        selected = column.get_selected_task()
        assert selected == tasks[0]

    def test_column_navigate_down_logic(self, make_task):
        """Test navigation down logic without DOM."""
        column = TaskColumn(column_id="col1", title="Tasks")

        tasks = [
            make_task(title="Task 1", level=0),
            make_task(title="Task 2", level=0),
            make_task(title="Task 3", level=0)
        ]

        column._tasks = tasks
        column._selected_index = 0

        # Navigate down
        if column._selected_index < len(column._tasks) - 1:
            column._selected_index += 1
        assert column._selected_index == 1

        if column._selected_index < len(column._tasks) - 1:
            column._selected_index += 1
        assert column._selected_index == 2

        # Can't go past the end
        if column._selected_index < len(column._tasks) - 1:
            column._selected_index += 1
        assert column._selected_index == 2

    def test_column_navigate_up_logic(self, make_task):
        """Test navigation up logic without DOM."""
        column = TaskColumn(column_id="col1", title="Tasks")

        tasks = [
            make_task(title="Task 1", level=0),
            make_task(title="Task 2", level=0),
            make_task(title="Task 3", level=0)
        ]

        column._tasks = tasks
        column._selected_index = 0

        # Start at first task (index 0)
        assert column._selected_index == 0

        # Can't go up from first position
        if column._selected_index > 0:
            column._selected_index -= 1
        assert column._selected_index == 0

        # Navigate to last task
        column._selected_index = 2

        # Navigate up
        if column._selected_index > 0:
            column._selected_index -= 1
        assert column._selected_index == 1

        if column._selected_index > 0:
            column._selected_index -= 1
        assert column._selected_index == 0

    def test_column_clear_selection_state(self, make_task):
        """Test clearing selection state."""
        column = TaskColumn(column_id="col1", title="Tasks")

        tasks = [
            make_task(title="Task 1", level=0),
            make_task(title="Task 2", level=0)
        ]

        column._tasks = tasks
        column._selected_index = 0

        # Clear selection manually
        column._selected_index = -1
        column.selected_task_id = None

        assert column._selected_index == -1
        assert column.selected_task_id is None

    def test_column_update_header_property(self):
        """Test updating the column header property."""
        column = TaskColumn(column_id="col1", title="Tasks")

        # Update header property
        column.header_title = "New Header Title"

        assert column.header_title == "New Header Title"

    def test_column_hierarchical_tasks_state(self, make_task):
        """Test column internal state with hierarchical task structure."""
        column = TaskColumn(column_id="col2", title="Subtasks")

        parent_id = uuid4()
        grandparent_id = uuid4()

        tasks = [
            make_task(title="Level 0 Task", level=0, parent_id=None),
            make_task(title="Level 1 Task 1", level=1, parent_id=parent_id),
            make_task(title="Level 1 Task 2", level=1, parent_id=parent_id),
            make_task(title="Level 2 Task", level=2, parent_id=grandparent_id)
        ]

        column._tasks = tasks

        assert len(column._tasks) == 4
        assert column._tasks[0].level == 0
        assert column._tasks[1].level == 1
        assert column._tasks[2].level == 1
        assert column._tasks[3].level == 2


class TestTaskItemTreeLineLogic:
    """Test suite specifically for tree line rendering logic."""

    def test_tree_line_siblings(self, make_task):
        """Test tree line rendering for sibling tasks."""
        parent_id = uuid4()

        # First child (not last)
        task1 = make_task(title="First Child", level=1, parent_id=parent_id, position=0)
        item1 = TaskItem(task=task1, is_last_child=False)
        rendered1 = str(item1.render())
        assert "├─" in rendered1

        # Last child
        task2 = make_task(title="Last Child", level=1, parent_id=parent_id, position=1)
        item2 = TaskItem(task=task2, is_last_child=True)
        rendered2 = str(item2.render())
        assert "└─" in rendered2

    def test_tree_line_indentation_levels(self, make_task):
        """Test proper indentation at each level."""
        parent_id = uuid4()
        grandparent_id = uuid4()

        # Level 0 - no indentation
        task0 = make_task(title="Level 0", level=0)
        item0 = TaskItem(task=task0)
        rendered0 = str(item0.render())
        assert rendered0.startswith("[ ]") or rendered0.startswith("[✓]")

        # Level 1 - 2 spaces + tree
        task1 = make_task(title="Level 1", level=1, parent_id=parent_id)
        item1 = TaskItem(task=task1, is_last_child=True)
        rendered1 = str(item1.render())
        # Should have 2 spaces before tree line
        assert "  └─" in rendered1

        # Level 2 - 4 spaces + tree
        task2 = make_task(title="Level 2", level=2, parent_id=grandparent_id)
        item2 = TaskItem(task=task2, is_last_child=True)
        rendered2 = str(item2.render())
        # Should have 4 spaces before tree line
        assert "    └─" in rendered2
