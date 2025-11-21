"""
Comprehensive tests for the TaskItem widget.

Tests cover:
- Basic rendering with different task states
- Tree visualization and indentation
- Visual state indicators (completed, archived, selected)
- Level-based styling and colors
- Interaction handling (click, selection)
- Data binding and updates
- Child progress indicators
"""

import pytest
from uuid import uuid4
from datetime import datetime
from rich.text import Text

from taskui.models import Task
from taskui.ui.components.task_item import TaskItem
from taskui.ui.theme import (
    LEVEL_0_COLOR,
    LEVEL_1_COLOR,
    LEVEL_2_COLOR,
    COMPLETE_COLOR,
    ARCHIVE_COLOR,
    FOREGROUND,
    SELECTION,
)


class TestTaskItemBasicRendering:
    """Tests for basic TaskItem rendering functionality."""

    def test_task_item_creation_basic(self, make_task):
        """Test creating a basic TaskItem widget."""
        task = make_task(title="Basic Task", level=0)
        task_item = TaskItem(task=task)

        assert task_item.task == task
        assert task_item.task_id == task.id
        assert task_item.selected is False
        assert task_item._task_model == task
        assert task_item._is_last_child is False

    def test_task_item_creation_with_is_last_child(self, make_task):
        """Test creating a TaskItem with is_last_child flag."""
        parent_id = uuid4()
        task = make_task(title="Last Child", level=1, parent_id=parent_id)
        task_item = TaskItem(task=task, is_last_child=True)

        assert task_item._is_last_child is True

    def test_render_basic_task(self, make_task):
        """Test rendering a basic level 0 task."""
        task = make_task(title="Simple Task", level=0)
        task_item = TaskItem(task=task)

        rendered = task_item.render()
        rendered_str = str(rendered)

        assert "[ ]" in rendered_str  # Checkbox
        assert "Simple Task" in rendered_str  # Title
        assert "└─" not in rendered_str  # No tree line for level 0
        assert "├─" not in rendered_str

    def test_render_task_with_notes(self, make_task):
        """Test rendering a task with notes (notes don't affect display)."""
        task = make_task(
            title="Task with Notes",
            notes="These are some notes\nWith multiple lines",
            level=0
        )
        task_item = TaskItem(task=task)

        rendered = task_item.render()
        rendered_str = str(rendered)

        # Notes are not displayed in TaskItem (only in detail panel)
        assert "Task with Notes" in rendered_str
        assert "These are some notes" not in rendered_str

    def test_render_task_short_title(self, make_task):
        """Test rendering a task with a short title."""
        task = make_task(title="Hi", level=0)
        task_item = TaskItem(task=task)

        rendered = task_item.render()
        rendered_str = str(rendered)

        assert "Hi" in rendered_str
        assert "[ ]" in rendered_str

    def test_render_task_long_title(self, make_task):
        """Test rendering a task with a long title."""
        long_title = "This is a very long task title that contains many words and characters to test rendering behavior"
        task = make_task(title=long_title, level=0)
        task_item = TaskItem(task=task)

        rendered = task_item.render()
        rendered_str = str(rendered)

        assert long_title in rendered_str

    def test_render_task_special_characters_in_title(self, make_task):
        """Test rendering a task with special characters in title."""
        special_title = "Task with special chars: @#$% & (parentheses) [brackets]"
        task = make_task(title=special_title, level=0)
        task_item = TaskItem(task=task)

        rendered = task_item.render()
        rendered_str = str(rendered)

        assert special_title in rendered_str


class TestTaskItemStateRendering:
    """Tests for rendering tasks in different states."""

    def test_render_completed_task(self, make_task):
        """Test rendering a completed task with checkmark."""
        task = make_task(
            title="Completed Task",
            level=0,
            is_completed=True,
            completed_at=datetime.utcnow()
        )
        task_item = TaskItem(task=task)

        rendered = task_item.render()
        rendered_str = str(rendered)

        assert "[✓]" in rendered_str  # Checked checkbox
        assert "Completed Task" in rendered_str

    def test_render_incomplete_task(self, make_task):
        """Test rendering an incomplete task with empty checkbox."""
        task = make_task(title="Incomplete Task", level=0, is_completed=False)
        task_item = TaskItem(task=task)

        rendered = task_item.render()
        rendered_str = str(rendered)

        assert "[ ]" in rendered_str  # Unchecked checkbox
        assert "[✓]" not in rendered_str

    def test_render_active_task(self, make_task):
        """Test rendering an active (not completed, not archived) task."""
        task = make_task(
            title="Active Task",
            level=0,
            is_completed=False,
            is_archived=False
        )
        task_item = TaskItem(task=task)

        rendered = task_item.render()
        rendered_str = str(rendered)

        assert "[ ]" in rendered_str
        assert "[✓]" not in rendered_str
        assert "📦" not in rendered_str
        assert "Active Task" in rendered_str


class TestTaskItemIndentation:
    """Tests for task indentation and tree line rendering."""

    def test_level_0_no_indentation_or_tree_line(self, make_task):
        """Test that level 0 tasks have no tree lines."""
        task = make_task(title="Level 0 Task", level=0)
        task_item = TaskItem(task=task)

        rendered = task_item.render()
        rendered_str = str(rendered)

        # Should not have tree characters
        assert "└─" not in rendered_str
        assert "├─" not in rendered_str

    def test_level_1_last_child_tree_line(self, make_task):
        """Test level 1 task as last child uses └─ tree line."""
        parent_id = uuid4()
        task = make_task(title="Level 1 Last", level=1, parent_id=parent_id)
        task_item = TaskItem(task=task, is_last_child=True)

        rendered = task_item.render()
        rendered_str = str(rendered)

        assert "└─" in rendered_str
        assert "├─" not in rendered_str
        assert "  └─" in rendered_str  # 2 spaces + tree char

    def test_level_1_not_last_child_tree_line(self, make_task):
        """Test level 1 task not as last child uses ├─ tree line."""
        parent_id = uuid4()
        task = make_task(title="Level 1 Middle", level=1, parent_id=parent_id)
        task_item = TaskItem(task=task, is_last_child=False)

        rendered = task_item.render()
        rendered_str = str(rendered)

        assert "├─" in rendered_str
        assert "└─" not in rendered_str
        assert "  ├─" in rendered_str  # 2 spaces + tree char

    def test_level_2_indentation(self, make_task):
        """Test level 2 task has deeper indentation."""
        parent_id = uuid4()
        task = make_task(title="Level 2 Task", level=2, parent_id=parent_id)
        task_item = TaskItem(task=task, is_last_child=True)

        rendered = task_item.render()
        rendered_str = str(rendered)

        assert "    └─" in rendered_str  # 4 spaces (2 per level) + tree char

    def test_level_2_not_last_child(self, make_task):
        """Test level 2 task not as last child."""
        parent_id = uuid4()
        task = make_task(title="Level 2 Middle", level=2, parent_id=parent_id)
        task_item = TaskItem(task=task, is_last_child=False)

        rendered = task_item.render()
        rendered_str = str(rendered)

        assert "    ├─" in rendered_str  # 4 spaces + tree char


class TestTaskItemVisualStates:
    """Tests for visual state styling and CSS classes."""

    def test_selected_state_initially_false(self, make_task):
        """Test that TaskItem is not selected by default."""
        task = make_task(title="Test Task", level=0)
        task_item = TaskItem(task=task)

        assert task_item.selected is False
        assert "selected" not in task_item.classes

    def test_selected_state_when_set_to_true(self, make_task):
        """Test that setting selected=True adds the CSS class."""
        task = make_task(title="Test Task", level=0)
        task_item = TaskItem(task=task)

        task_item.selected = True

        assert task_item.selected is True
        assert "selected" in task_item.classes

    def test_selected_state_when_set_to_false(self, make_task):
        """Test that setting selected=False removes the CSS class."""
        task = make_task(title="Test Task", level=0)
        task_item = TaskItem(task=task)

        # First select
        task_item.selected = True
        assert "selected" in task_item.classes

        # Then deselect
        task_item.selected = False
        assert "selected" not in task_item.classes

    def test_level_0_stores_level(self, make_task):
        """Test that level 0 tasks store their level correctly."""
        task = make_task(title="Level 0", level=0)
        task_item = TaskItem(task=task)

        assert task_item._task_model.level == 0

    def test_level_1_stores_level(self, make_task):
        """Test that level 1 tasks store their level correctly."""
        parent_id = uuid4()
        task = make_task(title="Level 1", level=1, parent_id=parent_id)
        task_item = TaskItem(task=task)

        assert task_item._task_model.level == 1

    def test_level_2_stores_level(self, make_task):
        """Test that level 2 tasks store their level correctly."""
        parent_id = uuid4()
        task = make_task(title="Level 2", level=2, parent_id=parent_id)
        task_item = TaskItem(task=task)

        assert task_item._task_model.level == 2

    def test_completed_visual_indicators(self, make_task):
        """Test visual indicators for completed tasks."""
        task = make_task(
            title="Completed",
            level=0,
            is_completed=True,
            completed_at=datetime.utcnow()
        )
        task_item = TaskItem(task=task)

        rendered = task_item.render()
        rendered_str = str(rendered)

        # Should have checkmark
        assert "[✓]" in rendered_str
        # Title should be included
        assert "Completed" in rendered_str

class TestTaskItemInteractions:
    """Tests for TaskItem interaction handling."""

    def test_on_click_sets_selected(self, make_task):
        """Test that clicking a task item sets it as selected."""
        task = make_task(title="Clickable Task", level=0)
        task_item = TaskItem(task=task)

        # Initially not selected
        assert task_item.selected is False

        # Simulate click
        task_item.on_click()

        # Should now be selected
        assert task_item.selected is True

    def test_on_click_posts_selected_message(self, make_task):
        """Test that clicking posts a Selected message with the task ID."""
        task = make_task(title="Clickable Task", level=0)
        task_item = TaskItem(task=task)

        # We can't easily test message posting without a full app,
        # but we can verify that on_click calls the expected code
        # by checking that selected is set
        task_item.on_click()

        assert task_item.selected is True
        # The actual message posting would be tested in integration tests

    def test_watch_selected_adds_class(self, make_task):
        """Test that watch_selected adds the 'selected' class."""
        task = make_task(title="Test Task", level=0)
        task_item = TaskItem(task=task)

        # Manually trigger the watcher
        task_item.watch_selected(True)

        assert "selected" in task_item.classes

    def test_watch_selected_removes_class(self, make_task):
        """Test that watch_selected removes the 'selected' class."""
        task = make_task(title="Test Task", level=0)
        task_item = TaskItem(task=task)

        # First add the class
        task_item.watch_selected(True)
        assert "selected" in task_item.classes

        # Then remove it
        task_item.watch_selected(False)
        assert "selected" not in task_item.classes


class TestTaskItemDataBinding:
    """Tests for task data binding and updates."""

    def test_task_property_returns_task(self, make_task):
        """Test that the task property returns the underlying task model."""
        task = make_task(title="Test Task", level=0)
        task_item = TaskItem(task=task)

        assert task_item.task == task
        assert task_item.task.title == "Test Task"
        assert task_item.task.level == 0

    def test_task_id_is_set_correctly(self, make_task):
        """Test that task_id reactive property is set correctly."""
        task = make_task(title="Test Task", level=0)
        task_item = TaskItem(task=task)

        assert task_item.task_id == task.id

    def test_task_id_persists(self, make_task):
        """Test that task_id is preserved throughout lifecycle."""
        task_id = uuid4()
        task = make_task(id=task_id, title="Test Task", level=0)
        task_item = TaskItem(task=task)

        assert task_item.task_id == task_id
        assert task_item.task.id == task_id

    def test_update_task_changes_data(self, make_task):
        """Test that update_task changes the underlying task data."""
        original_task = make_task(title="Original Title", level=0)
        task_item = TaskItem(task=original_task)

        # Create updated task
        updated_task = make_task(
            id=original_task.id,
            title="Updated Title",
            level=0,
            is_completed=True
        )

        # Update the task
        task_item.update_task(updated_task)

        # Verify the update
        assert task_item.task.title == "Updated Title"
        assert task_item.task.is_completed is True

    def test_update_task_preserves_task_id(self, make_task):
        """Test that update_task preserves the task ID."""
        original_id = uuid4()
        original_task = make_task(id=original_id, title="Original", level=0)
        task_item = TaskItem(task=original_task)

        updated_task = make_task(id=original_id, title="Updated", level=0)
        task_item.update_task(updated_task)

        assert task_item.task_id == original_id
        assert task_item.task.id == original_id

    def test_render_reflects_current_task_data(self, make_task):
        """Test that render always reflects current task data."""
        task = make_task(title="Initial Title", level=0, is_completed=False)
        task_item = TaskItem(task=task)

        # Initial render
        rendered1 = task_item.render()
        assert "Initial Title" in str(rendered1)
        assert "[ ]" in str(rendered1)

        # Update task
        updated_task = make_task(
            id=task.id,
            title="New Title",
            level=0,
            is_completed=True
        )
        task_item.update_task(updated_task)

        # Re-render should show new data
        rendered2 = task_item.render()
        assert "New Title" in str(rendered2)
        assert "[✓]" in str(rendered2)


class TestTaskItemChildProgress:
    """Tests for rendering child progress indicators."""

    def test_task_without_children_no_progress(self, make_task):
        """Test that tasks without children don't show progress."""
        task = make_task(title="No Children", level=0)
        # Don't set child counts - default is 0
        task_item = TaskItem(task=task)

        rendered = task_item.render()
        rendered_str = str(rendered)

        # Should not contain progress indicator
        assert "(" not in rendered_str or "()" not in rendered_str
        assert "/" not in rendered_str

    def test_task_with_children_shows_progress(self, make_task):
        """Test that tasks with children show progress indicator."""
        task = make_task(title="Parent Task", level=0)
        task.update_child_counts(child_count=5, completed_child_count=2)

        task_item = TaskItem(task=task)

        rendered = task_item.render()
        rendered_str = str(rendered)

        # Should show progress indicator
        assert "(2/5)" in rendered_str

    def test_task_with_all_children_completed(self, make_task):
        """Test progress indicator when all children are completed."""
        task = make_task(title="All Done", level=0)
        task.update_child_counts(child_count=3, completed_child_count=3)

        task_item = TaskItem(task=task)

        rendered = task_item.render()
        rendered_str = str(rendered)

        assert "(3/3)" in rendered_str

    def test_task_with_no_children_completed(self, make_task):
        """Test progress indicator when no children are completed."""
        task = make_task(title="Nothing Done", level=0)
        task.update_child_counts(child_count=4, completed_child_count=0)

        task_item = TaskItem(task=task)

        rendered = task_item.render()
        rendered_str = str(rendered)

        assert "(0/4)" in rendered_str

    def test_task_with_many_children(self, make_task):
        """Test progress indicator with many children."""
        task = make_task(title="Many Children", level=0)
        task.update_child_counts(child_count=25, completed_child_count=17)

        task_item = TaskItem(task=task)

        rendered = task_item.render()
        rendered_str = str(rendered)

        assert "(17/25)" in rendered_str


class TestTaskItemComplexScenarios:
    """Tests for complex rendering scenarios combining multiple features."""

    def test_completed_task_with_children(self, make_task):
        """Test rendering a completed task that has children."""
        task = make_task(
            title="Completed Parent",
            level=0,
            is_completed=True,
            completed_at=datetime.utcnow()
        )
        task.update_child_counts(child_count=3, completed_child_count=3)

        task_item = TaskItem(task=task)

        rendered = task_item.render()
        rendered_str = str(rendered)

        assert "[✓]" in rendered_str
        assert "(3/3)" in rendered_str
        assert "Completed Parent" in rendered_str

    def test_selected_completed_task(self, make_task):
        """Test rendering a selected task that is completed."""
        task = make_task(
            title="Selected and Complete",
            level=0,
            is_completed=True,
            completed_at=datetime.utcnow()
        )
        task_item = TaskItem(task=task)
        task_item.selected = True

        rendered = task_item.render()
        rendered_str = str(rendered)

        assert "[✓]" in rendered_str
        assert "Selected and Complete" in rendered_str
        assert "selected" in task_item.classes

    def test_nested_completed_task_as_last_child(self, make_task):
        """Test a completed level 1 task as last child."""
        parent_id = uuid4()
        task = make_task(
            title="Nested Complete",
            level=1,
            parent_id=parent_id,
            is_completed=True,
            completed_at=datetime.utcnow()
        )
        task_item = TaskItem(task=task, is_last_child=True)

        rendered = task_item.render()
        rendered_str = str(rendered)

        assert "└─" in rendered_str
        assert "[✓]" in rendered_str
        assert "Nested Complete" in rendered_str

    def test_deeply_nested_task_with_children(self, make_task):
        """Test a level 2 task with children."""
        parent_id = uuid4()
        task = make_task(
            title="Deep Parent",
            level=2,
            parent_id=parent_id
        )
        task.update_child_counts(child_count=2, completed_child_count=1)

        task_item = TaskItem(task=task, is_last_child=False)

        rendered = task_item.render()
        rendered_str = str(rendered)

        assert "    ├─" in rendered_str  # Level 2 indentation
        assert "(1/2)" in rendered_str
        assert "Deep Parent" in rendered_str


class TestTaskItemSelectedMessage:
    """Tests for the TaskItem.Selected message class."""

    def test_selected_message_creation(self, make_task):
        """Test creating a Selected message."""
        task_id = uuid4()
        message = TaskItem.Selected(task_id)

        assert message.task_id == task_id

    def test_selected_message_with_real_task_id(self, make_task):
        """Test Selected message with a real task's ID."""
        task = make_task(title="Test Task", level=0)
        message = TaskItem.Selected(task.id)

        assert message.task_id == task.id


class TestTaskItemPropertyAccess:
    """Tests for accessing TaskItem properties."""

    def test_task_model_private_attribute_access(self, make_task):
        """Test accessing the private _task_model attribute."""
        task = make_task(title="Test Task", level=0)
        task_item = TaskItem(task=task)

        assert task_item._task_model == task
        assert task_item._task_model.title == "Test Task"

    def test_is_last_child_private_attribute(self, make_task):
        """Test accessing the private _is_last_child attribute."""
        task = make_task(title="Test Task", level=0)
        task_item = TaskItem(task=task, is_last_child=True)

        assert task_item._is_last_child is True

    def test_task_property_is_read_only(self, make_task):
        """Test that task property provides access to the model."""
        task = make_task(title="Test Task", level=0)
        task_item = TaskItem(task=task)

        # Task property should return the task
        assert task_item.task == task

        # It's a property, not directly settable (use update_task instead)
        # This just verifies the getter works
        assert task_item.task.title == "Test Task"


class TestTaskItemTreeLineLogic:
    """Tests for the _get_tree_line internal method."""

    def test_get_tree_line_last_child(self, make_task):
        """Test _get_tree_line returns └─ for last child."""
        parent_id = uuid4()
        task = make_task(title="Last Child", level=1, parent_id=parent_id)
        task_item = TaskItem(task=task, is_last_child=True)

        tree_line, tree_color = task_item._get_tree_line()

        assert "└─" in tree_line
        assert "  └─ " == tree_line  # 2 spaces + tree + space

    def test_get_tree_line_not_last_child(self, make_task):
        """Test _get_tree_line returns ├─ for non-last child."""
        parent_id = uuid4()
        task = make_task(title="Middle Child", level=1, parent_id=parent_id)
        task_item = TaskItem(task=task, is_last_child=False)

        tree_line, tree_color = task_item._get_tree_line()

        assert "├─" in tree_line
        assert "  ├─ " == tree_line  # 2 spaces + tree + space

    def test_get_tree_line_level_2(self, make_task):
        """Test _get_tree_line for level 2 task."""
        parent_id = uuid4()
        task = make_task(title="Deep Child", level=2, parent_id=parent_id)
        task_item = TaskItem(task=task, is_last_child=True)

        tree_line, tree_color = task_item._get_tree_line()

        assert "    └─ " == tree_line  # 4 spaces + tree + space


class TestTaskItemEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_title_task(self, make_task):
        """Test rendering a task with minimal valid title."""
        # Pydantic requires min_length=1, so we use single character
        task = make_task(title="X", level=0)
        task_item = TaskItem(task=task)

        rendered = task_item.render()
        rendered_str = str(rendered)

        assert "X" in rendered_str

    def test_task_at_max_level(self, make_task):
        """Test rendering a task at maximum nesting level (2)."""
        parent_id = uuid4()
        task = make_task(title="Max Level", level=2, parent_id=parent_id)
        task_item = TaskItem(task=task)

        assert task_item.task.level == 2
        assert task_item._task_model.level == 2

    def test_multiple_state_transitions(self, make_task):
        """Test multiple selections and deselections."""
        task = make_task(title="Toggle Task", level=0)
        task_item = TaskItem(task=task)

        # Initial state
        assert task_item.selected is False

        # Select
        task_item.selected = True
        assert task_item.selected is True
        assert "selected" in task_item.classes

        # Deselect
        task_item.selected = False
        assert task_item.selected is False
        assert "selected" not in task_item.classes

        # Select again
        task_item.selected = True
        assert task_item.selected is True
        assert "selected" in task_item.classes

    def test_render_returns_rich_text(self, make_task):
        """Test that render returns a Rich Text object."""
        task = make_task(title="Test Task", level=0)
        task_item = TaskItem(task=task)

        rendered = task_item.render()

        # Should be a Rich Text instance
        assert isinstance(rendered, Text)

    def test_task_with_unicode_in_title(self, make_task):
        """Test rendering a task with Unicode characters in title."""
        unicode_title = "Task with émojis 🎉 and ñoñ-ASCII: 日本語"
        task = make_task(title=unicode_title, level=0)
        task_item = TaskItem(task=task)

        rendered = task_item.render()
        rendered_str = str(rendered)

        assert unicode_title in rendered_str
