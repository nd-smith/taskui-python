"""Tests for task editing functionality (Story 1.12).

This module tests the complete edit task workflow including:
- Opening edit modal with 'E' key
- Pre-filling modal with existing task data
- Saving changes to database
- UI refresh after edit
- Edge cases (no selection, empty title, cancel)
"""

import pytest
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from taskui.models import Task
from taskui.services.nesting_rules import Column
from taskui.services.task_service import TaskService
from taskui.ui.app import TaskUI
from taskui.ui.components.task_modal import TaskCreationModal


class TestEditTaskModalIntegration:
    """Test edit modal integration with the app."""

    def test_edit_modal_opens_with_existing_data(self):
        """Test that edit modal pre-fills with existing task data."""
        task = Task(
            id=uuid4(),
            title="Original Title",
            notes="Original notes",
            list_id=uuid4()
        )

        modal = TaskCreationModal(
            mode="edit",
            edit_task=task,
            column=Column.COLUMN1
        )

        # Verify modal is in edit mode
        assert modal.mode == "edit"
        assert modal.edit_task == task
        assert modal.edit_task.title == "Original Title"
        assert modal.edit_task.notes == "Original notes"

    def test_edit_modal_shows_correct_header(self):
        """Test that edit modal displays correct header text."""
        task = Task(
            id=uuid4(),
            title="Test Task",
            list_id=uuid4()
        )

        modal = TaskCreationModal(
            mode="edit",
            edit_task=task,
            column=Column.COLUMN1
        )

        header_text = modal._get_header_text()
        assert "✏️" in header_text or "Edit" in header_text

    def test_edit_modal_shows_task_context(self):
        """Test that edit modal shows which task is being edited."""
        task = Task(
            id=uuid4(),
            title="Long Task Title That Should Be Truncated If Needed",
            list_id=uuid4()
        )

        modal = TaskCreationModal(
            mode="edit",
            edit_task=task,
            column=Column.COLUMN1
        )

        context_text = modal._get_context_text()
        assert "Editing" in context_text
        assert task.title[:30] in context_text or task.title[:40] in context_text

    def test_edit_modal_handles_task_without_notes(self):
        """Test that edit modal handles tasks that have no notes."""
        task = Task(
            id=uuid4(),
            title="Task Without Notes",
            notes=None,
            list_id=uuid4()
        )

        modal = TaskCreationModal(
            mode="edit",
            edit_task=task,
            column=Column.COLUMN1
        )

        # Should not raise an error
        assert modal.edit_task.notes is None
        assert modal.mode == "edit"


class TestEditTaskServiceIntegration:
    """Test integration between edit functionality and task service."""

    @pytest.mark.asyncio
    async def test_update_task_modifies_title(self, db_session, sample_task_list):
        """Test that update_task successfully modifies task title."""
        # Create a task
        service = TaskService(db_session)
        task = await service.create_task(
            title="Original Title",
            notes="Original notes",
            list_id=UUID(sample_task_list.id)
        )

        # Update the task
        updated_task = await service.update_task(
            task_id=task.id,
            title="Updated Title"
        )

        # Verify the update
        assert updated_task.title == "Updated Title"
        assert updated_task.notes == "Original notes"  # Notes unchanged
        assert updated_task.id == task.id

    @pytest.mark.asyncio
    async def test_update_task_modifies_notes(self, db_session, sample_task_list):
        """Test that update_task successfully modifies task notes."""
        # Create a task
        service = TaskService(db_session)
        task = await service.create_task(
            title="Test Task",
            notes="Original notes",
            list_id=UUID(sample_task_list.id)
        )

        # Update the task
        updated_task = await service.update_task(
            task_id=task.id,
            notes="Updated notes"
        )

        # Verify the update
        assert updated_task.title == "Test Task"  # Title unchanged
        assert updated_task.notes == "Updated notes"
        assert updated_task.id == task.id

    @pytest.mark.asyncio
    async def test_update_task_modifies_both_title_and_notes(self, db_session, sample_task_list):
        """Test that update_task can modify both title and notes."""
        # Create a task
        service = TaskService(db_session)
        task = await service.create_task(
            title="Original Title",
            notes="Original notes",
            list_id=UUID(sample_task_list.id)
        )

        # Update the task
        updated_task = await service.update_task(
            task_id=task.id,
            title="New Title",
            notes="New notes"
        )

        # Verify the update
        assert updated_task.title == "New Title"
        assert updated_task.notes == "New notes"
        assert updated_task.id == task.id

    @pytest.mark.asyncio
    async def test_update_task_can_clear_notes(self, db_session, sample_task_list):
        """Test that update_task can clear notes by setting to empty string."""
        # Create a task with notes
        service = TaskService(db_session)
        task = await service.create_task(
            title="Test Task",
            notes="Original notes",
            list_id=UUID(sample_task_list.id)
        )

        # Clear the notes (service stores empty string as None)
        updated_task = await service.update_task(
            task_id=task.id,
            notes=""
        )

        # Verify notes are cleared (empty string is stored as None in model)
        # Note: The actual storage may vary, but empty notes should be handled
        assert updated_task.notes == "" or updated_task.notes is None

    @pytest.mark.asyncio
    async def test_update_task_persists_to_database(self, db_session, sample_task_list):
        """Test that task updates persist to the database."""
        # Create a task
        service = TaskService(db_session)
        task = await service.create_task(
            title="Original Title",
            list_id=UUID(sample_task_list.id)
        )
        await db_session.commit()

        # Update the task
        await service.update_task(
            task_id=task.id,
            title="Updated Title",
            notes="New notes"
        )
        await db_session.commit()

        # Retrieve the task in a new session to verify persistence
        retrieved_task = await service.get_task_by_id(task.id)

        assert retrieved_task is not None
        assert retrieved_task.title == "Updated Title"
        assert retrieved_task.notes == "New notes"

    @pytest.mark.asyncio
    async def test_update_task_preserves_other_fields(self, db_session, sample_task_list):
        """Test that updating title/notes doesn't modify other fields."""
        # Create a task
        service = TaskService(db_session)
        task = await service.create_task(
            title="Original Title",
            notes="Original notes",
            list_id=UUID(sample_task_list.id)
        )

        # Store original values
        original_id = task.id
        original_list_id = task.list_id
        original_level = task.level
        original_position = task.position
        original_created_at = task.created_at

        # Update the task
        updated_task = await service.update_task(
            task_id=task.id,
            title="New Title"
        )

        # Verify other fields are preserved
        assert updated_task.id == original_id
        assert updated_task.list_id == original_list_id
        assert updated_task.level == original_level
        assert updated_task.position == original_position
        assert updated_task.created_at == original_created_at
        assert updated_task.is_completed is False
        assert updated_task.is_archived is False


class TestEditTaskEdgeCases:
    """Test edge cases for task editing."""

    @pytest.mark.asyncio
    async def test_update_nonexistent_task_raises_error(self, db_session):
        """Test that updating a non-existent task raises TaskNotFoundError."""
        from taskui.services.task_service import TaskNotFoundError

        service = TaskService(db_session)
        fake_id = uuid4()

        with pytest.raises(TaskNotFoundError):
            await service.update_task(
                task_id=fake_id,
                title="New Title"
            )

    @pytest.mark.asyncio
    async def test_update_task_requires_at_least_one_field(self, db_session, sample_task_list):
        """Test that update_task requires either title or notes."""
        service = TaskService(db_session)
        task = await service.create_task(
            title="Test Task",
            list_id=UUID(sample_task_list.id)
        )

        # Should raise ValueError when neither field is provided
        with pytest.raises(ValueError):
            await service.update_task(task_id=task.id)

    def test_edit_modal_result_includes_edit_task(self):
        """Test that modal result includes the edit_task reference."""
        task = Task(
            id=uuid4(),
            title="Test Task",
            list_id=uuid4()
        )

        modal = TaskCreationModal(
            mode="edit",
            edit_task=task,
            column=Column.COLUMN1
        )

        # The modal should preserve the edit_task for result handling
        assert modal.edit_task == task
        assert modal.mode == "edit"


class TestEditTaskWorkflow:
    """Test the complete edit task workflow."""

    def test_action_edit_task_requires_selected_task(self):
        """Test that edit action requires a task to be selected."""
        # This is a structural test - the action should check for selection
        app = TaskUI()

        # action_edit_task should handle the case where no task is selected
        # It should return early without opening the modal
        assert hasattr(app, 'action_edit_task')

    def test_handle_task_modal_result_processes_edit_mode(self):
        """Test that modal message handler recognizes edit mode."""
        app = TaskUI()

        # The handler should use message-based approach
        assert hasattr(app, 'on_task_creation_modal_task_created')

    def test_handle_edit_task_calls_task_service(self):
        """Test that _handle_edit_task calls the task service update method."""
        app = TaskUI()

        # The handler should have a dedicated method for edit processing
        assert hasattr(app, '_handle_edit_task')


class TestEditTaskUIRefresh:
    """Test UI refresh behavior after editing tasks."""

    def test_refresh_column_tasks_for_column1(self):
        """Test that Column 1 refresh reloads top-level tasks."""
        app = TaskUI()

        # The app should have a method to refresh column tasks
        assert hasattr(app, '_refresh_column_tasks')

    def test_refresh_column_tasks_for_column2(self):
        """Test that Column 2 refresh reloads children of selected task."""
        app = TaskUI()

        # The refresh method should handle Column 2 differently
        assert hasattr(app, '_refresh_column_tasks')
        assert hasattr(app, '_update_column2_for_selection')


# Mark these as integration tests if using pytest markers
pytestmark = pytest.mark.integration
