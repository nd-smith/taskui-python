"""
Tests for printer service.

Tests the PrinterService class with mock printer to avoid hardware dependency.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path
from datetime import datetime
from uuid import uuid4

from taskui.services.printer_service import (
    PrinterService,
    PrinterConfig,
    DetailLevel,
    PrintError,
    MockPrinter
)
from taskui.models import Task


@pytest.fixture
def mock_network_printer():
    """Create a mock Network printer."""
    mock_printer = Mock()
    mock_printer.text = Mock()
    mock_printer.set = Mock()
    mock_printer.cut = Mock()
    mock_printer.close = Mock()
    return mock_printer


@pytest.fixture
def printer_config():
    """Create a test printer config."""
    return PrinterConfig(
        host="192.168.1.100",
        port=9100,
        timeout=30,
        detail_level=DetailLevel.MINIMAL
    )


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return Task(
        id=uuid4(),
        list_id=uuid4(),
        title="Test Task",
        notes="Test notes",
        is_completed=False,
        created_at=datetime.now()
    )


@pytest.fixture
def sample_children():
    """Create sample child tasks."""
    list_id = uuid4()
    parent_id = uuid4()
    return [
        Task(
            id=uuid4(),
            list_id=list_id,
            parent_id=parent_id,
            title="Child task 1",
            level=1,
            is_completed=False,
            created_at=datetime.now()
        ),
        Task(
            id=uuid4(),
            list_id=list_id,
            parent_id=parent_id,
            title="Child task 2",
            level=1,
            is_completed=True,
            created_at=datetime.now()
        ),
        Task(
            id=uuid4(),
            list_id=list_id,
            parent_id=parent_id,
            title="Child task 3",
            level=1,
            is_completed=False,
            created_at=datetime.now()
        ),
    ]


class TestPrinterConfig:
    """Tests for PrinterConfig class."""

    def test_default_config(self):
        """Test default printer configuration."""
        config = PrinterConfig()
        assert config.host == "192.168.50.99"
        assert config.port == 9100
        assert config.timeout == 60
        assert config.detail_level == DetailLevel.MINIMAL

    def test_custom_config(self):
        """Test custom printer configuration."""
        config = PrinterConfig(
            host="10.0.0.1",
            port=8080,
            timeout=45,
            detail_level=DetailLevel.MINIMAL
        )
        assert config.host == "10.0.0.1"
        assert config.port == 8080
        assert config.timeout == 45
        assert config.detail_level == DetailLevel.MINIMAL

    def test_from_config_file_defaults(self):
        """Test loading from non-existent config file uses defaults."""
        config = PrinterConfig.from_config_file(Path("/tmp/nonexistent.ini"))
        assert config.host == "192.168.50.99"
        assert config.port == 9100
        assert config.detail_level == DetailLevel.MINIMAL


class TestPrinterService:
    """Tests for PrinterService class."""

    def test_initialization(self, printer_config):
        """Test printer service initialization."""
        service = PrinterService(printer_config)
        assert service.config == printer_config
        assert service.printer is None
        assert not service.is_connected()

    @patch('taskui.services.printer_service.Network')
    def test_connect_success(self, mock_network_class, printer_config, mock_network_printer):
        """Test successful printer connection."""
        mock_network_class.return_value = mock_network_printer
        service = PrinterService(printer_config)

        result = service.connect()

        assert result is True
        assert service.is_connected()
        mock_network_class.assert_called_once_with(
            printer_config.host,
            port=printer_config.port,
            timeout=printer_config.timeout
        )

    @patch('taskui.services.printer_service.Network')
    def test_connect_failure(self, mock_network_class, printer_config):
        """Test failed printer connection."""
        mock_network_class.side_effect = Exception("Connection failed")
        service = PrinterService(printer_config)

        with pytest.raises(ConnectionError, match="Cannot connect to printer"):
            service.connect()

        assert not service.is_connected()

    @patch('taskui.services.printer_service.Network')
    def test_disconnect(self, mock_network_class, printer_config, mock_network_printer):
        """Test printer disconnection."""
        mock_network_class.return_value = mock_network_printer
        service = PrinterService(printer_config)
        service.connect()

        service.disconnect()

        assert not service.is_connected()
        assert service.printer is None
        mock_network_printer.close.assert_called_once()

    @patch('taskui.services.printer_service.Network')
    def test_print_task_card_not_connected(self, mock_network_class, printer_config, sample_task):
        """Test printing when not connected raises error."""
        service = PrinterService(printer_config)

        with pytest.raises(ConnectionError, match="Printer not connected"):
            service.print_task_card(sample_task, [])

    @patch('taskui.services.printer_service.Network')
    def test_print_task_card_with_children(
        self,
        mock_network_class,
        printer_config,
        mock_network_printer,
        sample_task,
        sample_children
    ):
        """Test printing task card with children."""
        mock_network_class.return_value = mock_network_printer
        service = PrinterService(printer_config)
        service.connect()

        result = service.print_task_card(sample_task, sample_children)

        assert result is True
        # Verify printer methods were called
        assert mock_network_printer.set.called
        assert mock_network_printer.text.called
        assert mock_network_printer.cut.called
        assert mock_network_printer.close.called

        # Verify task title was printed (with bold, double-height, double-width)
        title_set_call = call(font='a', bold=True, double_height=True, double_width=True)
        assert title_set_call in mock_network_printer.set.call_args_list

        # Verify children were printed
        text_calls = mock_network_printer.text.call_args_list
        text_content = ''.join([call[0][0] for call in text_calls])
        assert sample_task.title in text_content
        assert "[ ] Child task 1" in text_content
        assert "[X] Child task 2" in text_content  # Completed
        assert "[ ] Child task 3" in text_content

    @patch('taskui.services.printer_service.Network')
    def test_print_task_card_with_notes(
        self,
        mock_network_class,
        printer_config,
        mock_network_printer,
        sample_task
    ):
        """Test printing task card with notes (no children)."""
        mock_network_class.return_value = mock_network_printer
        service = PrinterService(printer_config)
        service.connect()

        result = service.print_task_card(sample_task, [])

        assert result is True
        # Verify notes were printed
        text_calls = mock_network_printer.text.call_args_list
        text_content = ''.join([call[0][0] for call in text_calls])
        assert sample_task.notes in text_content

    @patch('taskui.services.printer_service.Network')
    def test_print_task_card_print_failure(
        self,
        mock_network_class,
        printer_config,
        sample_task
    ):
        """Test handling of print operation failure."""
        mock_printer = Mock()
        mock_printer.set = Mock(side_effect=Exception("Printer error"))
        mock_network_class.return_value = mock_printer

        service = PrinterService(printer_config)
        service.connect()

        with pytest.raises(PrintError, match="Print operation failed"):
            service.print_task_card(sample_task, [])

    @patch('taskui.services.printer_service.Network')
    def test_test_connection_success(self, mock_network_class, printer_config, mock_network_printer):
        """Test successful connection test."""
        mock_network_class.return_value = mock_network_printer
        service = PrinterService(printer_config)
        service.connect()

        result = service.test_connection()

        assert result is True
        assert mock_network_printer.text.called
        assert mock_network_printer.cut.called

    @patch('taskui.services.printer_service.Network')
    def test_test_connection_not_connected(self, mock_network_class, printer_config):
        """Test connection test when not connected."""
        service = PrinterService(printer_config)

        result = service.test_connection()

        assert result is False

    @patch('taskui.services.printer_service.Network')
    def test_test_connection_failure(self, mock_network_class, printer_config, mock_network_printer):
        """Test connection test failure."""
        mock_network_printer.text.side_effect = Exception("Printer error")
        mock_network_class.return_value = mock_network_printer
        service = PrinterService(printer_config)
        service.connect()

        result = service.test_connection()

        assert result is False


class TestMockPrinter:
    """Tests for MockPrinter class."""

    def test_mock_printer_console_output(self, capsys):
        """Test mock printer outputs to console."""
        mock_printer = MockPrinter()
        mock_printer.print_card("Test card content")

        captured = capsys.readouterr()
        assert "Test card content" in captured.out
        assert "[CUT]" in captured.out

    def test_mock_printer_file_output(self, tmp_path):
        """Test mock printer outputs to file."""
        output_file = tmp_path / "test_output.txt"
        mock_printer = MockPrinter(output_path=output_file)

        mock_printer.print_card("Card 1")
        mock_printer.print_card("Card 2")

        content = output_file.read_text()
        assert "Card 1" in content
        assert "Card 2" in content
        assert content.count("[CUT]") == 2


class TestDetailLevel:
    """Tests for DetailLevel enum."""

    def test_detail_level_values(self):
        """Test detail level enum values."""
        assert DetailLevel.MINIMAL.value == "minimal"
        assert DetailLevel.STANDARD.value == "standard"
        assert DetailLevel.FULL.value == "full"

    def test_detail_level_from_string(self):
        """Test creating detail level from string."""
        assert DetailLevel("minimal") == DetailLevel.MINIMAL
        assert DetailLevel("standard") == DetailLevel.STANDARD
        assert DetailLevel("full") == DetailLevel.FULL
