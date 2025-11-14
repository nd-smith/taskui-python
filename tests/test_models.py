"""
Tests for TaskUI Pydantic models.

Tests cover:
- Model creation and validation
- Field constraints
- Computed properties
- Status transitions
- Nesting rules
"""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from taskui.models import Task, TaskList


class TestTaskList:
    """Tests for TaskList model."""

    def test_tasklist_creation_minimal(self):
        """Test creating a task list with minimal required fields."""
        task_list = TaskList(name="Work")

        assert task_list.name == "Work"
        assert isinstance(task_list.id, UUID)
        assert isinstance(task_list.created_at, datetime)
        assert task_list._task_count == 0
        assert task_list._completed_count == 0

    def test_tasklist_creation_with_id(self):
        """Test creating a task list with explicit ID."""
        list_id = uuid4()
        task_list = TaskList(id=list_id, name="Home")

        assert task_list.id == list_id
        assert task_list.name == "Home"

    def test_tasklist_name_validation_empty(self):
        """Test that empty names are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TaskList(name="")

        assert "String should have at least 1 character" in str(exc_info.value)

    def test_tasklist_name_validation_too_long(self):
        """Test that names over 100 characters are rejected."""
        long_name = "a" * 101
        with pytest.raises(ValidationError) as exc_info:
            TaskList(name=long_name)

        assert "String should have at most 100 characters" in str(exc_info.value)

    def test_tasklist_completion_percentage_no_tasks(self):
        """Test completion percentage with no tasks."""
        task_list = TaskList(name="Personal")

        assert task_list.completion_percentage == 0.0

    def test_tasklist_completion_percentage_all_complete(self):
        """Test completion percentage with all tasks complete."""
        task_list = TaskList(name="Personal")
        task_list.update_counts(task_count=5, completed_count=5)

        assert task_list.completion_percentage == 100.0

    def test_tasklist_completion_percentage_partial(self):
        """Test completion percentage with partial completion."""
        task_list = TaskList(name="Personal")
        task_list.update_counts(task_count=10, completed_count=3)

        assert task_list.completion_percentage == 30.0

    def test_tasklist_update_counts(self):
        """Test updating task counts."""
        task_list = TaskList(name="Work")

        task_list.update_counts(task_count=20, completed_count=15)

        assert task_list._task_count == 20
        assert task_list._completed_count == 15
        assert task_list.completion_percentage == 75.0


class TestTask:
    """Tests for Task model."""

    def test_task_creation_minimal(self):
        """Test creating a task with minimal required fields."""
        list_id = uuid4()
        task = Task(title="Complete documentation", list_id=list_id)

        assert task.title == "Complete documentation"
        assert task.list_id == list_id
        assert isinstance(task.id, UUID)
        assert isinstance(task.created_at, datetime)
        assert task.is_completed is False
        assert task.is_archived is False
        assert task.level == 0
        assert task.position == 0
        assert task.parent_id is None
        assert task.notes is None
        assert task.completed_at is None
        assert task.archived_at is None

    def test_task_creation_full(self):
        """Test creating a task with all fields."""
        task_id = uuid4()
        list_id = uuid4()
        parent_id = uuid4()
        created_time = datetime(2025, 1, 14, 10, 0, 0)

        task = Task(
            id=task_id,
            title="Review code",
            notes="Focus on error handling",
            is_completed=False,
            is_archived=False,
            parent_id=parent_id,
            level=1,
            position=2,
            list_id=list_id,
            created_at=created_time,
        )

        assert task.id == task_id
        assert task.title == "Review code"
        assert task.notes == "Focus on error handling"
        assert task.parent_id == parent_id
        assert task.level == 1
        assert task.position == 2
        assert task.list_id == list_id
        assert task.created_at == created_time

    def test_task_title_validation_empty(self):
        """Test that empty titles are rejected."""
        list_id = uuid4()
        with pytest.raises(ValidationError) as exc_info:
            Task(title="", list_id=list_id)

        assert "String should have at least 1 character" in str(exc_info.value)

    def test_task_title_validation_too_long(self):
        """Test that titles over 500 characters are rejected."""
        list_id = uuid4()
        long_title = "a" * 501
        with pytest.raises(ValidationError) as exc_info:
            Task(title=long_title, list_id=list_id)

        assert "String should have at most 500 characters" in str(exc_info.value)

    def test_task_notes_validation_too_long(self):
        """Test that notes over 5000 characters are rejected."""
        list_id = uuid4()
        long_notes = "a" * 5001
        with pytest.raises(ValidationError) as exc_info:
            Task(title="Test", list_id=list_id, notes=long_notes)

        assert "String should have at most 5000 characters" in str(exc_info.value)

    def test_task_level_validation_negative(self):
        """Test that negative levels are rejected."""
        list_id = uuid4()
        with pytest.raises(ValidationError) as exc_info:
            Task(title="Test", list_id=list_id, level=-1)

        assert "greater than or equal to 0" in str(exc_info.value)

    def test_task_level_validation_too_high(self):
        """Test that levels over 2 are rejected."""
        list_id = uuid4()
        parent_id = uuid4()
        with pytest.raises(ValidationError) as exc_info:
            Task(title="Test", list_id=list_id, level=3, parent_id=parent_id)

        assert "less than or equal to 2" in str(exc_info.value)

    def test_task_level_0_cannot_have_parent(self):
        """Test that level 0 tasks cannot have a parent_id."""
        list_id = uuid4()
        parent_id = uuid4()
        with pytest.raises(ValidationError) as exc_info:
            Task(title="Test", list_id=list_id, level=0, parent_id=parent_id)

        assert "Level 0 tasks cannot have a parent_id" in str(exc_info.value)

    def test_task_level_1_must_have_parent(self):
        """Test that level 1+ tasks must have a parent_id."""
        list_id = uuid4()
        with pytest.raises(ValidationError) as exc_info:
            Task(title="Test", list_id=list_id, level=1, parent_id=None)

        assert "must have a parent_id" in str(exc_info.value)

    def test_task_level_2_must_have_parent(self):
        """Test that level 2 tasks must have a parent_id."""
        list_id = uuid4()
        with pytest.raises(ValidationError) as exc_info:
            Task(title="Test", list_id=list_id, level=2, parent_id=None)

        assert "must have a parent_id" in str(exc_info.value)

    def test_task_progress_string_no_children(self):
        """Test progress string with no children."""
        list_id = uuid4()
        task = Task(title="Test", list_id=list_id)

        assert task.progress_string == ""

    def test_task_progress_string_with_children(self):
        """Test progress string with children."""
        list_id = uuid4()
        task = Task(title="Test", list_id=list_id)
        task.update_child_counts(child_count=5, completed_child_count=2)

        assert task.progress_string == "2/5"

    def test_task_completion_percentage_no_children(self):
        """Test completion percentage with no children."""
        list_id = uuid4()
        task = Task(title="Test", list_id=list_id)

        assert task.completion_percentage == 0.0

    def test_task_completion_percentage_all_complete(self):
        """Test completion percentage with all children complete."""
        list_id = uuid4()
        task = Task(title="Test", list_id=list_id)
        task.update_child_counts(child_count=8, completed_child_count=8)

        assert task.completion_percentage == 100.0

    def test_task_completion_percentage_partial(self):
        """Test completion percentage with partial completion."""
        list_id = uuid4()
        task = Task(title="Test", list_id=list_id)
        task.update_child_counts(child_count=10, completed_child_count=7)

        assert task.completion_percentage == 70.0

    def test_task_has_children_false(self):
        """Test has_children property when task has no children."""
        list_id = uuid4()
        task = Task(title="Test", list_id=list_id)

        assert task.has_children is False

    def test_task_has_children_true(self):
        """Test has_children property when task has children."""
        list_id = uuid4()
        task = Task(title="Test", list_id=list_id)
        task.update_child_counts(child_count=3, completed_child_count=1)

        assert task.has_children is True

    def test_task_can_have_children_in_column1_level_0(self):
        """Test that level 0 tasks can have children in Column 1."""
        list_id = uuid4()
        task = Task(title="Test", list_id=list_id, level=0)

        assert task.can_have_children_in_column1 is True

    def test_task_can_have_children_in_column1_level_1(self):
        """Test that level 1 tasks cannot have children in Column 1."""
        list_id = uuid4()
        parent_id = uuid4()
        task = Task(title="Test", list_id=list_id, level=1, parent_id=parent_id)

        assert task.can_have_children_in_column1 is False

    def test_task_can_have_children_in_column2_level_0(self):
        """Test that level 0 tasks can have children in Column 2."""
        list_id = uuid4()
        task = Task(title="Test", list_id=list_id, level=0)

        assert task.can_have_children_in_column2 is True

    def test_task_can_have_children_in_column2_level_1(self):
        """Test that level 1 tasks can have children in Column 2."""
        list_id = uuid4()
        parent_id = uuid4()
        task = Task(title="Test", list_id=list_id, level=1, parent_id=parent_id)

        assert task.can_have_children_in_column2 is True

    def test_task_can_have_children_in_column2_level_2(self):
        """Test that level 2 tasks cannot have children in Column 2."""
        list_id = uuid4()
        parent_id = uuid4()
        task = Task(title="Test", list_id=list_id, level=2, parent_id=parent_id)

        assert task.can_have_children_in_column2 is False

    def test_task_mark_completed(self):
        """Test marking a task as completed."""
        list_id = uuid4()
        task = Task(title="Test", list_id=list_id)

        assert task.is_completed is False
        assert task.completed_at is None

        task.mark_completed()

        assert task.is_completed is True
        assert isinstance(task.completed_at, datetime)

    def test_task_mark_incomplete(self):
        """Test marking a completed task as incomplete."""
        list_id = uuid4()
        task = Task(title="Test", list_id=list_id)
        task.mark_completed()

        assert task.is_completed is True
        assert task.completed_at is not None

        task.mark_incomplete()

        assert task.is_completed is False
        assert task.completed_at is None

    def test_task_archive_completed(self):
        """Test archiving a completed task."""
        list_id = uuid4()
        task = Task(title="Test", list_id=list_id)
        task.mark_completed()

        assert task.is_archived is False
        assert task.archived_at is None

        task.archive()

        assert task.is_archived is True
        assert isinstance(task.archived_at, datetime)

    def test_task_archive_incomplete_raises_error(self):
        """Test that archiving an incomplete task raises an error."""
        list_id = uuid4()
        task = Task(title="Test", list_id=list_id)

        with pytest.raises(ValueError) as exc_info:
            task.archive()

        assert "Only completed tasks can be archived" in str(exc_info.value)

    def test_task_unarchive(self):
        """Test unarchiving a task."""
        list_id = uuid4()
        task = Task(title="Test", list_id=list_id)
        task.mark_completed()
        task.archive()

        assert task.is_archived is True
        assert task.archived_at is not None

        task.unarchive()

        assert task.is_archived is False
        assert task.archived_at is None

    def test_task_update_child_counts(self):
        """Test updating child counts."""
        list_id = uuid4()
        task = Task(title="Test", list_id=list_id)

        task.update_child_counts(child_count=10, completed_child_count=6)

        assert task._child_count == 10
        assert task._completed_child_count == 6
        assert task.progress_string == "6/10"
        assert task.completion_percentage == 60.0
        assert task.has_children is True


class TestTaskNestingRules:
    """Tests specifically for nesting rules and hierarchy."""

    def test_create_level_0_task(self):
        """Test creating a level 0 (root) task."""
        list_id = uuid4()
        task = Task(title="Root Task", list_id=list_id, level=0)

        assert task.level == 0
        assert task.parent_id is None
        assert task.can_have_children_in_column1 is True
        assert task.can_have_children_in_column2 is True

    def test_create_level_1_task(self):
        """Test creating a level 1 (child) task."""
        list_id = uuid4()
        parent_id = uuid4()
        task = Task(title="Child Task", list_id=list_id, level=1, parent_id=parent_id)

        assert task.level == 1
        assert task.parent_id == parent_id
        assert task.can_have_children_in_column1 is False
        assert task.can_have_children_in_column2 is True

    def test_create_level_2_task(self):
        """Test creating a level 2 (grandchild) task."""
        list_id = uuid4()
        parent_id = uuid4()
        task = Task(title="Grandchild Task", list_id=list_id, level=2, parent_id=parent_id)

        assert task.level == 2
        assert task.parent_id == parent_id
        assert task.can_have_children_in_column1 is False
        assert task.can_have_children_in_column2 is False

    def test_column1_max_nesting_enforced(self):
        """Test that Column 1 enforces max 2 levels (0-1)."""
        list_id = uuid4()

        # Level 0 can have children in Column 1
        level_0 = Task(title="Level 0", list_id=list_id, level=0)
        assert level_0.can_have_children_in_column1 is True

        # Level 1 cannot have children in Column 1
        level_1 = Task(title="Level 1", list_id=list_id, level=1, parent_id=level_0.id)
        assert level_1.can_have_children_in_column1 is False

    def test_column2_max_nesting_enforced(self):
        """Test that Column 2 enforces max 3 levels (0-2)."""
        list_id = uuid4()

        # Level 0 can have children in Column 2
        level_0 = Task(title="Level 0", list_id=list_id, level=0)
        assert level_0.can_have_children_in_column2 is True

        # Level 1 can have children in Column 2
        level_1 = Task(title="Level 1", list_id=list_id, level=1, parent_id=level_0.id)
        assert level_1.can_have_children_in_column2 is True

        # Level 2 cannot have children in Column 2
        level_2 = Task(title="Level 2", list_id=list_id, level=2, parent_id=level_1.id)
        assert level_2.can_have_children_in_column2 is False
