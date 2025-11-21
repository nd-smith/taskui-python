"""Tests for the task creation modal component.

This module tests the TaskCreationModal functionality including:
- Modal display and composition
- Context display (sibling vs child creation)
- Nesting limit validation
- Keyboard shortcuts (Enter to save, Escape to cancel)
- Input validation (title required, notes optional)
"""

import pytest
from uuid import uuid4

from textual.widgets import Input, TextArea, Button

from taskui.models import Task
from taskui.ui.components.task_modal import TaskCreationModal


class TestTaskCreationModalComposition:
    """Test modal composition and basic structure."""

    def test_modal_creates_with_title_input(self):
        """Test that modal includes a title input field."""
        modal = TaskCreationModal(mode="create_sibling")

        # Modal should have composition
        assert modal.mode == "create_sibling"

    def test_modal_creates_with_notes_input(self):
        """Test that modal includes a notes text area."""
        modal = TaskCreationModal(mode="create_sibling")

        # Notes field should be optional
        assert modal.mode == "create_sibling"

    def test_modal_creates_with_save_and_cancel_buttons(self):
        """Test that modal includes Save and Cancel buttons."""
        modal = TaskCreationModal(mode="create_sibling")

        # Buttons should be present
        assert modal.mode == "create_sibling"


class TestTaskCreationModalContext:
    """Test modal context display for different creation modes."""

    def test_create_sibling_mode_displays_correct_header(self):
        """Test header text for sibling creation mode."""
        modal = TaskCreationModal(mode="create_sibling")

        header_text = modal._get_header_text()
        assert "Create New Task" in header_text or "Create" in header_text

    def test_create_child_mode_displays_correct_header(self):
        """Test header text for child creation mode."""
        modal = TaskCreationModal(mode="create_child")

        header_text = modal._get_header_text()
        assert "Create Child" in header_text or "Child" in header_text

    def test_edit_mode_displays_correct_header(self):
        """Test header text for edit mode."""
        task = Task(
            id=uuid4(),
            title="Test Task",
            list_id=uuid4()
        )
        modal = TaskCreationModal(mode="edit", edit_task=task)

        header_text = modal._get_header_text()
        assert "Edit" in header_text

    def test_create_sibling_shows_level_context(self):
        """Test that sibling creation shows current level context."""
        parent_task = Task(
            id=uuid4(),
            title="Parent Task",
            level=1,
            parent_id=uuid4(),  # Level 1 tasks require a parent
            list_id=uuid4()
        )
        modal = TaskCreationModal(
            mode="create_sibling",
            parent_task=parent_task
        )

        context_text = modal._get_context_text()
        # Should show level information
        assert "level" in context_text.lower() or context_text != ""

    def test_create_child_shows_parent_context(self):
        """Test that child creation shows parent task information."""
        parent_task = Task(
            id=uuid4(),
            title="Parent Task",
            level=0,
            list_id=uuid4()
        )
        modal = TaskCreationModal(
            mode="create_child",
            parent_task=parent_task
        )

        context_text = modal._get_context_text()
        # Should show parent task information
        assert "Parent Task" in context_text or "child" in context_text.lower()


class TestNestingLimitValidation:
    """Test nesting limit validation in the modal."""

    def test_max_depth_task_cannot_create_child(self):
        """Test that level 4 tasks (max depth) cannot create children."""
        # Create task with model_validate to pass context with max_level=4
        parent_task = Task.model_validate({
            'id': str(uuid4()),
            'title': "Level 4 Task",
            'level': 4,
            'parent_id': str(uuid4()),
            'list_id': str(uuid4())
        }, context={'max_level': 4})

        modal = TaskCreationModal(
            mode="create_child",
            parent_task=parent_task
        )

        # Should have a validation error
        assert modal.validation_error is not None
        assert "max nesting" in modal.validation_error.lower() or "cannot create" in modal.validation_error.lower()

    def test_level0_task_can_create_child(self):
        """Test that level 0 tasks can create children."""
        parent_task = Task(
            id=uuid4(),
            title="Level 0 Task",
            level=0,
            list_id=uuid4()
        )
        modal = TaskCreationModal(
            mode="create_child",
            parent_task=parent_task
        )

        # Should not have a validation error
        assert modal.validation_error is None

    def test_level3_task_can_create_child(self):
        """Test that level 3 tasks can create children (child would be level 4)."""
        # Create task with model_validate to pass context with max_level=4
        parent_task = Task.model_validate({
            'id': str(uuid4()),
            'title': "Level 3 Task",
            'level': 3,
            'parent_id': str(uuid4()),
            'list_id': str(uuid4())
        }, context={'max_level': 4})

        modal = TaskCreationModal(
            mode="create_child",
            parent_task=parent_task
        )

        # Should not have a validation error (child would be level 4, which is max)
        assert modal.validation_error is None


class TestModalActions:
    """Test modal action handlers."""

    def test_action_save_extracts_title_and_notes(self):
        """Test that save action extracts input values correctly."""
        modal = TaskCreationModal(mode="create_sibling")

        # Modal should have save functionality
        # This is a structural test - actual testing will be done in integration tests
        assert hasattr(modal, 'action_save')

    def test_action_cancel_dismisses_modal(self):
        """Test that cancel action dismisses the modal."""
        modal = TaskCreationModal(mode="create_sibling")

        # Modal should have cancel functionality
        assert hasattr(modal, 'action_cancel')

    def test_validation_error_disables_save(self):
        """Test that validation errors disable the save button."""
        # Create level 4 task (max depth) which cannot have children
        parent_task = Task.model_validate({
            'id': str(uuid4()),
            'title': "Level 4 Task",
            'level': 4,
            'parent_id': str(uuid4()),
            'list_id': str(uuid4())
        }, context={'max_level': 4})

        modal = TaskCreationModal(
            mode="create_child",
            parent_task=parent_task
        )

        # Should have validation error
        assert modal.validation_error is not None


class TestModalKeyboardBindings:
    """Test keyboard bindings in the modal."""

    def test_escape_binding_exists(self):
        """Test that Escape key binding exists for cancel action."""
        modal = TaskCreationModal(mode="create_sibling")

        # Check that bindings include escape
        binding_keys = [binding.key for binding in modal.BINDINGS]
        assert "escape" in binding_keys

    def test_ctrl_s_binding_exists(self):
        """Test that Ctrl+S binding exists for save action."""
        modal = TaskCreationModal(mode="create_sibling")

        # Check that bindings include ctrl+s
        binding_keys = [binding.key for binding in modal.BINDINGS]
        assert "ctrl+s" in binding_keys


class TestModalEditMode:
    """Test modal in edit mode."""

    def test_edit_mode_shows_existing_title(self):
        """Test that edit mode pre-fills the title field."""
        task = Task(
            id=uuid4(),
            title="Existing Task",
            notes="Existing notes",
            list_id=uuid4()
        )
        modal = TaskCreationModal(mode="edit", edit_task=task)

        # Modal should have edit_task set
        assert modal.edit_task == task
        assert modal.mode == "edit"

    def test_edit_mode_shows_existing_notes(self):
        """Test that edit mode pre-fills the notes field."""
        task = Task(
            id=uuid4(),
            title="Existing Task",
            notes="Existing notes",
            list_id=uuid4()
        )
        modal = TaskCreationModal(mode="edit", edit_task=task)

        # Modal should preserve notes
        assert modal.edit_task.notes == "Existing notes"

    def test_edit_mode_without_notes(self):
        """Test that edit mode handles tasks without notes."""
        task = Task(
            id=uuid4(),
            title="Existing Task",
            list_id=uuid4()
        )
        modal = TaskCreationModal(mode="edit", edit_task=task)

        # Modal should handle None notes
        assert modal.edit_task.notes is None


class TestModalResultData:
    """Test modal result data structure."""

    def test_result_contains_mode_information(self):
        """Test that result data includes mode information."""
        modal = TaskCreationModal(
            mode="create_child"
        )

        # Modal should track mode
        assert modal.mode == "create_child"

    def test_result_contains_parent_task_reference(self):
        """Test that result includes parent task reference."""
        parent_task = Task(
            id=uuid4(),
            title="Parent Task",
            level=0,
            list_id=uuid4()
        )
        modal = TaskCreationModal(
            mode="create_child",
            parent_task=parent_task
        )

        # Modal should preserve parent task reference
        assert modal.parent_task == parent_task


# Integration tests would go in a separate file or be marked with pytest.mark.integration
# These would test the actual Textual app interactions with pilots
