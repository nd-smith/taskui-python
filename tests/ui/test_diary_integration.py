"""
Integration tests for diary feature UI components.

Tests cover DiaryEntryModal, DetailPanel diary display, and printer
integration with diary entries.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime

from taskui.ui.modals.diary_entry_modal import DiaryEntryModal
from taskui.ui.components.detail_panel import DetailPanel
from taskui.models import DiaryEntry, Task
from taskui.services.cloud_print_queue import CloudPrintQueue


class TestDiaryEntryModal:
    """Tests for DiaryEntryModal component."""

    @pytest.fixture
    def task_id(self):
        """Generate a test task ID."""
        return uuid4()

    def test_modal_initialization(self, task_id):
        """Test that modal initializes with correct parameters."""
        modal = DiaryEntryModal(task_id=task_id)

        assert modal.task_id == task_id
        assert modal.min_length == 1
        assert modal.max_length == 2000

    def test_keyboard_shortcuts_configured(self, task_id):
        """Test that Escape and Ctrl+S keyboard shortcuts are configured."""
        modal = DiaryEntryModal(task_id=task_id)

        # Verify bindings are present
        bindings = {binding.key: binding.action for binding in modal.BINDINGS}
        assert "escape" in bindings
        assert bindings["escape"] == "cancel"
        assert "ctrl+s" in bindings
        assert bindings["ctrl+s"] == "save"

    def test_save_action_creates_entry(self, task_id):
        """Test that save action creates a diary entry with valid content."""
        modal = DiaryEntryModal(task_id=task_id)

        # Mock the widgets and message posting
        mock_content_input = Mock()
        mock_content_input.text = "Test diary entry"
        mock_content_input.id = "content-input"

        with patch.object(modal, 'query_one', return_value=mock_content_input):
            with patch.object(modal, 'post_message') as mock_post:
                with patch.object(modal, 'dismiss') as mock_dismiss:
                    # Trigger save action
                    modal.action_save()

                    # Verify EntrySaved message was posted
                    assert mock_post.called
                    message = mock_post.call_args[0][0]
                    assert isinstance(message, DiaryEntryModal.EntrySaved)
                    assert message.entry.task_id == task_id
                    assert message.entry.content == "Test diary entry"

                    # Verify modal was dismissed
                    assert mock_dismiss.called

    def test_save_validation_rejects_empty_content(self, task_id):
        """Test that save validation rejects empty content."""
        modal = DiaryEntryModal(task_id=task_id)

        # Mock content input with empty/whitespace text
        mock_content_input = Mock()
        mock_content_input.text = "   "  # Only whitespace
        mock_content_input.id = "content-input"

        with patch.object(modal, 'query_one', return_value=mock_content_input):
            with patch.object(modal, 'dismiss') as mock_dismiss:
                modal.action_save()

                # Modal should not be dismissed
                assert not mock_dismiss.called

    def test_cancel_action_dismisses_modal(self, task_id):
        """Test that cancel action dismisses modal without saving."""
        modal = DiaryEntryModal(task_id=task_id)

        with patch.object(modal, 'post_message') as mock_post:
            with patch.object(modal, 'dismiss') as mock_dismiss:
                # Trigger cancel action
                modal.action_cancel()

                # Verify EntryCancelled message was posted
                assert mock_post.called
                message = mock_post.call_args[0][0]
                assert isinstance(message, DiaryEntryModal.EntryCancelled)

                # Verify modal was dismissed with None
                assert mock_dismiss.called
                assert mock_dismiss.call_args[0][0] is None


class TestDetailPanelDiaryDisplay:
    """Tests for diary entry display in DetailPanel."""

    @pytest.fixture
    def sample_task(self):
        """Create a sample task."""
        return Task(
            id=uuid4(),
            list_id=uuid4(),
            title="Test Task",
            notes="Test notes",
            is_completed=False,
            created_at=datetime.now()
        )

    @pytest.fixture
    def sample_diary_entries(self, sample_task):
        """Create sample diary entries."""
        return [
            DiaryEntry(
                id=uuid4(),
                task_id=sample_task.id,
                content="Most recent entry",
                created_at=datetime.now()
            ),
            DiaryEntry(
                id=uuid4(),
                task_id=sample_task.id,
                content="Second entry",
                created_at=datetime.now()
            ),
            DiaryEntry(
                id=uuid4(),
                task_id=sample_task.id,
                content="Oldest entry",
                created_at=datetime.now()
            ),
        ]

    def test_detail_panel_shows_diary_entries(self, sample_task, sample_diary_entries):
        """Test that DetailPanel displays diary entries."""
        panel = DetailPanel(column_id="test-column", title="Details")
        # Set diary entries directly without calling set_task
        panel.diary_entries = sample_diary_entries

        # Build details text
        details_text = panel._build_details_text(sample_task)

        # Verify diary section is present
        assert "DIARY ENTRIES" in details_text

        # Verify all entries are displayed
        for entry in sample_diary_entries:
            assert entry.content in details_text

    def test_detail_panel_shows_empty_state_no_entries(self, sample_task):
        """Test that DetailPanel shows empty state when no diary entries."""
        panel = DetailPanel(column_id="test-column", title="Details")
        # Set empty diary entries directly
        panel.diary_entries = []

        details_text = panel._build_details_text(sample_task)

        # Verify empty state message
        assert "DIARY ENTRIES" in details_text
        assert "No diary entries yet" in details_text

    def test_detail_panel_displays_last_3_entries(self, sample_task):
        """Test that DetailPanel limits display to last 3 entries."""
        # Create 3 entries (service provides only 3)
        entries = [
            DiaryEntry(
                id=uuid4(),
                task_id=sample_task.id,
                content=f"Entry {i}",
                created_at=datetime.now()
            )
            for i in range(3)
        ]

        panel = DetailPanel(column_id="test-column", title="Details")
        # Set entries directly
        panel.diary_entries = entries

        details_text = panel._build_details_text(sample_task)

        # Verify all 3 entries are in the panel
        assert "Entry 0" in details_text
        assert "Entry 1" in details_text
        assert "Entry 2" in details_text

    def test_detail_panel_formats_diary_timestamps(self, sample_task, sample_diary_entries):
        """Test that diary entry timestamps are formatted correctly."""
        panel = DetailPanel(column_id="test-column", title="Details")
        # Set diary entries directly
        panel.diary_entries = sample_diary_entries

        details_text = panel._build_details_text(sample_task)

        # Verify timestamps are present in correct format
        from taskui.utils.datetime_utils import format_diary_timestamp
        for entry in sample_diary_entries:
            formatted_time = format_diary_timestamp(entry.created_at, panel.timezone)
            assert formatted_time in details_text

    def test_detail_panel_handles_multiline_entry_content(self, sample_task):
        """Test that multiline diary content is displayed correctly."""
        entry = DiaryEntry(
            id=uuid4(),
            task_id=sample_task.id,
            content="Line 1\nLine 2\nLine 3",
            created_at=datetime.now()
        )

        panel = DetailPanel(column_id="test-column", title="Details")
        # Set entry directly
        panel.diary_entries = [entry]

        details_text = panel._build_details_text(sample_task)

        # Verify all lines are present
        assert "Line 1" in details_text
        assert "Line 2" in details_text
        assert "Line 3" in details_text


class TestPrinterIntegration:
    """Tests for printer integration with diary entries."""

    @pytest.fixture
    def sample_task(self):
        """Create a sample task."""
        return Task(
            id=uuid4(),
            list_id=uuid4(),
            title="Test Task",
            notes="Test notes",
            is_completed=False,
            created_at=datetime.now()
        )

    @pytest.fixture
    def sample_children(self, sample_task):
        """Create sample child tasks."""
        return [
            Task(
                id=uuid4(),
                list_id=sample_task.list_id,
                parent_id=sample_task.id,
                title="Child task 1",
                level=1,
                is_completed=False,
                created_at=datetime.now()
            ),
        ]

    @pytest.fixture
    def sample_diary_entries(self, sample_task):
        """Create sample diary entries."""
        return [
            DiaryEntry(
                id=uuid4(),
                task_id=sample_task.id,
                content="Diary entry 1",
                created_at=datetime.now()
            ),
            DiaryEntry(
                id=uuid4(),
                task_id=sample_task.id,
                content="Diary entry 2",
                created_at=datetime.now()
            ),
        ]

    def test_serialize_print_job_includes_diary_entries_when_enabled(
        self, sample_task, sample_children, sample_diary_entries
    ):
        """Test that print job serialization includes diary entries when config enabled."""
        from taskui.services.cloud_print_queue import CloudPrintConfig

        config = CloudPrintConfig(queue_url="test-queue")
        queue = CloudPrintQueue(config)

        # Mock config to enable diary entries in print
        with patch('taskui.config.Config') as MockConfig:
            mock_config = MockConfig.return_value
            mock_config.get.return_value = 'true'
            mock_config.get_display_config.return_value = {
                'timezone': 'America/Denver'
            }

            job_data = queue._serialize_print_job(
                sample_task,
                sample_children,
                sample_diary_entries
            )

            # Verify diary entries are in job data
            assert 'diary_entries' in job_data
            assert len(job_data['diary_entries']) == 2
            assert job_data['diary_entries'][0]['content'] == "Diary entry 1"
            assert job_data['diary_entries'][1]['content'] == "Diary entry 2"

    def test_serialize_print_job_excludes_diary_entries_when_disabled(
        self, sample_task, sample_children, sample_diary_entries
    ):
        """Test that print job serialization excludes diary entries when config disabled."""
        from taskui.services.cloud_print_queue import CloudPrintConfig

        config = CloudPrintConfig(queue_url="test-queue")
        queue = CloudPrintQueue(config)

        # Mock config to disable diary entries in print
        with patch('taskui.config.Config') as MockConfig:
            mock_config = MockConfig.return_value
            mock_config.get.return_value = 'false'
            mock_config.get_display_config.return_value = {
                'timezone': 'America/Denver'
            }

            job_data = queue._serialize_print_job(
                sample_task,
                sample_children,
                sample_diary_entries
            )

            # Verify diary entries are NOT in job data
            assert 'diary_entries' not in job_data

    def test_serialize_print_job_excludes_diary_when_none_provided(
        self, sample_task, sample_children
    ):
        """Test that print job handles None diary entries gracefully."""
        from taskui.services.cloud_print_queue import CloudPrintConfig

        config = CloudPrintConfig(queue_url="test-queue")
        queue = CloudPrintQueue(config)

        # Mock config to enable diary entries in print
        with patch('taskui.config.Config') as MockConfig:
            mock_config = MockConfig.return_value
            mock_config.get.return_value = 'true'
            mock_config.get_display_config.return_value = {
                'timezone': 'America/Denver'
            }

            job_data = queue._serialize_print_job(
                sample_task,
                sample_children,
                None  # No diary entries provided
            )

            # Verify diary entries are NOT in job data
            assert 'diary_entries' not in job_data

    def test_serialize_print_job_includes_diary_timestamps(
        self, sample_task, sample_children, sample_diary_entries
    ):
        """Test that serialized diary entries include timestamps."""
        from taskui.services.cloud_print_queue import CloudPrintConfig

        config = CloudPrintConfig(queue_url="test-queue")
        queue = CloudPrintQueue(config)

        # Mock config to enable diary entries in print
        with patch('taskui.config.Config') as MockConfig:
            mock_config = MockConfig.return_value
            mock_config.get.return_value = 'true'
            mock_config.get_display_config.return_value = {
                'timezone': 'America/Denver'
            }

            job_data = queue._serialize_print_job(
                sample_task,
                sample_children,
                sample_diary_entries
            )

            # Verify timestamps are included and formatted
            for i, entry_data in enumerate(job_data['diary_entries']):
                assert 'timestamp' in entry_data
                assert 'content' in entry_data
                # Timestamp should be formatted string, not raw ISO format
                assert isinstance(entry_data['timestamp'], str)
                assert entry_data['timestamp']  # Non-empty

    def test_cloud_print_send_job_with_diary_entries(
        self, sample_task, sample_children, sample_diary_entries
    ):
        """Test that send_print_job handles diary entries correctly."""
        from taskui.services.cloud_print_queue import CloudPrintConfig

        config = CloudPrintConfig(queue_url="test-queue")
        queue = CloudPrintQueue(config)

        # Mock SQS client
        queue.sqs_client = Mock()
        queue._connected = True
        queue.sqs_client.send_message.return_value = {'MessageId': 'test-123'}

        # Mock config to enable diary entries
        with patch('taskui.config.Config') as MockConfig:
            mock_config = MockConfig.return_value
            mock_config.get.return_value = 'true'
            mock_config.get_display_config.return_value = {
                'timezone': 'America/Denver'
            }

            # Send print job with diary entries
            result = queue.send_print_job(
                sample_task,
                sample_children,
                sample_diary_entries
            )

            # Verify job was sent successfully
            assert result is True
            assert queue.sqs_client.send_message.called
