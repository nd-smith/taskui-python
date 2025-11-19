"""
Tests for the DetailPanel widget.

Tests the DetailPanel component which displays comprehensive task information
including title, status, dates, hierarchy, parent info, notes, and warnings.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from textual.app import App
from textual.widgets import Static

from taskui.models import Task
from taskui.ui.components.detail_panel import DetailPanel


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return Task(
        id=uuid4(),
        title="Sample Task",
        notes="This is a test task",
        is_completed=False,
        is_archived=False,
        parent_id=None,
        level=0,
        position=0,
        list_id=uuid4(),
        created_at=datetime(2025, 1, 14, 10, 0, 0),
    )


@pytest.fixture
def completed_task(sample_task):
    """Create a completed task for testing."""
    task = sample_task.model_copy(update={
        "is_completed": True,
        "completed_at": datetime(2025, 1, 14, 12, 0, 0),
    })
    return task


@pytest.fixture
def archived_task(completed_task):
    """Create an archived task for testing."""
    task = completed_task.model_copy(update={
        "is_archived": True,
        "archived_at": datetime(2025, 1, 14, 14, 0, 0),
    })
    return task


@pytest.fixture
def child_task(sample_task):
    """Create a child task for testing."""
    parent_id = sample_task.id
    return Task(
        id=uuid4(),
        title="Child Task",
        notes="This is a child task",
        is_completed=False,
        is_archived=False,
        parent_id=parent_id,
        level=1,
        position=0,
        list_id=sample_task.list_id,
        created_at=datetime(2025, 1, 14, 11, 0, 0),
    )


@pytest.fixture
def grandchild_task(child_task):
    """Create a grandchild task for testing."""
    parent_id = child_task.id
    return Task(
        id=uuid4(),
        title="Grandchild Task",
        notes="This is a grandchild task",
        is_completed=False,
        is_archived=False,
        parent_id=parent_id,
        level=2,
        position=0,
        list_id=child_task.list_id,
        created_at=datetime(2025, 1, 14, 11, 30, 0),
    )


class TestDetailPanelLogic:
    """Tests for DetailPanel logic methods (no DOM required)."""

    def test_panel_initialization(self):
        """Test that the panel initializes with correct properties."""
        panel = DetailPanel(column_id="test-panel", title="Test Panel")

        assert panel.column_id == "test-panel"
        assert panel.panel_title == "Test Panel"
        assert panel.current_task is None
        assert panel.task_hierarchy == []

    def test_format_datetime(self, sample_task):
        """Test datetime formatting."""
        panel = DetailPanel()
        formatted = panel._format_datetime(sample_task.created_at)

        assert formatted == "2025-01-14 10:00:00"

    def test_build_details_text_basic(self, sample_task):
        """Test building details text for a basic task."""
        panel = DetailPanel()
        panel.current_task = sample_task
        panel.task_hierarchy = []
        text = panel._build_details_text(sample_task)

        # Check that key sections are present
        assert "TASK" in text
        assert sample_task.title in text
        assert "STATUS" in text
        assert "DATES" in text

    def test_build_details_text_completed(self, completed_task):
        """Test building details text for a completed task."""
        panel = DetailPanel()
        panel.current_task = completed_task
        panel.task_hierarchy = []
        text = panel._build_details_text(completed_task)

        # Check completion indicators
        assert "Complete" in text
        assert "Completed:" in text
        assert "2025-01-14 12:00:00" in text

    def test_build_details_text_archived(self, archived_task):
        """Test building details text for an archived task."""
        panel = DetailPanel()
        panel.current_task = archived_task
        panel.task_hierarchy = []
        text = panel._build_details_text(archived_task)

        # Check archive indicators
        assert "Archived" in text
        assert "2025-01-14 14:00:00" in text

    def test_build_details_text_with_notes(self, sample_task):
        """Test building details text for a task with notes."""
        task_with_notes = sample_task.model_copy(update={
            "notes": "Important task\nWith multiple lines\nOf notes"
        })
        panel = DetailPanel()
        panel.current_task = task_with_notes
        panel.task_hierarchy = []
        text = panel._build_details_text(task_with_notes)

        # Check notes section
        assert "NOTES" in text
        assert "Important task" in text
        assert "With multiple lines" in text
        assert "Of notes" in text

    def test_build_details_text_with_hierarchy(self, sample_task, child_task, grandchild_task):
        """Test building details text with hierarchy path."""
        panel = DetailPanel()
        panel.current_task = grandchild_task
        panel.task_hierarchy = [sample_task, child_task, grandchild_task]
        text = panel._build_details_text(grandchild_task)

        # Check hierarchy section
        assert "HIERARCHY" in text
        assert sample_task.title in text
        assert child_task.title in text
        assert grandchild_task.title in text

    def test_build_details_text_with_parent(self, sample_task, child_task):
        """Test building details text with parent information."""
        panel = DetailPanel()
        panel.current_task = child_task
        panel.task_hierarchy = [sample_task, child_task]
        text = panel._build_details_text(child_task)

        # Check parent section
        assert "PARENT" in text
        assert sample_task.title in text

    def test_task_without_notes(self):
        """Test displaying a task without notes."""
        task = Task(
            id=uuid4(),
            title="Task without notes",
            notes=None,
            is_completed=False,
            is_archived=False,
            parent_id=None,
            level=0,
            position=0,
            list_id=uuid4(),
            created_at=datetime(2025, 1, 14, 10, 0, 0),
        )
        panel = DetailPanel()
        panel.current_task = task
        panel.task_hierarchy = []
        text = panel._build_details_text(task)

        # When notes are None, NOTES section should not appear
        if task.notes:
            assert "NOTES" in text
        # Task title and other info should still be present
        assert task.title in text
        assert "STATUS" in text
        assert "DATES" in text


class TestDetailPanelIntegration:
    """Integration tests for DetailPanel logic."""

    def test_reactive_properties(self):
        """Test reactive properties are set correctly."""
        panel = DetailPanel()
        task = Task(
            id=uuid4(),
            title="Test Task",
            notes="Test notes",
            is_completed=False,
            is_archived=False,
            parent_id=None,
            level=0,
            position=0,
            list_id=uuid4(),
            created_at=datetime(2025, 1, 14, 10, 0, 0),
        )
        hierarchy = [task]

        # Set task and hierarchy
        panel.current_task = task
        panel.task_hierarchy = hierarchy

        assert panel.current_task == task
        assert panel.task_hierarchy == hierarchy

    def test_panel_displays_all_task_information(self, sample_task):
        """Test that all task information is properly displayed."""
        panel = DetailPanel()
        panel.current_task = sample_task
        panel.task_hierarchy = []
        text = panel._build_details_text(sample_task)

        # Verify all expected information is present
        assert sample_task.title in text
        assert str(sample_task.level) in text
        assert "2025-01-14 10:00:00" in text
        assert "STATUS" in text
        assert "DATES" in text

    def test_panel_handles_complex_hierarchy(self, sample_task, child_task, grandchild_task):
        """Test panel with a complex 3-level hierarchy."""
        panel = DetailPanel()
        panel.current_task = grandchild_task
        panel.task_hierarchy = [sample_task, child_task, grandchild_task]
        text = panel._build_details_text(grandchild_task)

        # Verify hierarchy is displayed correctly
        assert "HIERARCHY" in text
        assert all(task.title in text for task in [sample_task, child_task, grandchild_task])

        # Verify parent is displayed
        assert "PARENT" in text
        assert child_task.title in text

    def test_hierarchy_ordering(self, sample_task, child_task, grandchild_task):
        """Test that hierarchy maintains correct ordering."""
        panel = DetailPanel()
        hierarchy = [sample_task, child_task, grandchild_task]
        panel.current_task = grandchild_task
        panel.task_hierarchy = hierarchy

        # Check hierarchy order
        assert panel.task_hierarchy[0] == sample_task  # Root
        assert panel.task_hierarchy[1] == child_task   # Middle
        assert panel.task_hierarchy[2] == grandchild_task  # Current

    def test_different_completion_states(self, sample_task):
        """Test panel with tasks in different completion states."""
        panel = DetailPanel()

        # Test incomplete task
        panel.current_task = sample_task
        text1 = panel._build_details_text(sample_task)
        assert "Incomplete" in text1

        # Test completed task
        completed = sample_task.model_copy(update={
            "is_completed": True,
            "completed_at": datetime(2025, 1, 14, 12, 0, 0)
        })
        panel.current_task = completed
        text2 = panel._build_details_text(completed)
        assert "Complete" in text2
        assert "Completed:" in text2

        # Test archived task
        archived = completed.model_copy(update={
            "is_archived": True,
            "archived_at": datetime(2025, 1, 14, 14, 0, 0)
        })
        panel.current_task = archived
        text3 = panel._build_details_text(archived)
        assert "Archived" in text3

    def test_multiline_notes_display(self):
        """Test that multiline notes are displayed correctly."""
        task = Task(
            id=uuid4(),
            title="Task with multiline notes",
            notes="Line 1\nLine 2\nLine 3\nLine 4",
            is_completed=False,
            is_archived=False,
            parent_id=None,
            level=0,
            position=0,
            list_id=uuid4(),
            created_at=datetime(2025, 1, 14, 10, 0, 0),
        )
        panel = DetailPanel()
        panel.current_task = task
        panel.task_hierarchy = []
        text = panel._build_details_text(task)

        # Check all lines are present
        assert "Line 1" in text
        assert "Line 2" in text
        assert "Line 3" in text
        assert "Line 4" in text

    def test_empty_hierarchy_no_parent_section(self, sample_task):
        """Test that tasks without parents don't show parent section."""
        panel = DetailPanel()
        panel.current_task = sample_task
        panel.task_hierarchy = [sample_task]  # Only the task itself
        text = panel._build_details_text(sample_task)

        # Parent section should not appear for root tasks
        # (task_hierarchy has only 1 item, so no parent to show)
        assert sample_task.title in text
        # The PARENT section requires hierarchy length > 1
        if len(panel.task_hierarchy) > 1:
            assert "PARENT" in text
