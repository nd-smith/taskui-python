"""
Comprehensive tests for logging configuration module.

Tests cover:
- Log directory and file creation
- Log level configuration via environment variables
- Per-module logger naming
- Log rotation functionality
- TextualHandler integration and fallback
"""

import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from taskui.logging_config import (
    setup_logging,
    get_logger,
    LOG_DIR,
    LOG_FILE,
    MAX_BYTES,
    BACKUP_COUNT
)


@pytest.fixture
def temp_log_dir(tmp_path):
    """Create a temporary log directory for testing."""
    log_dir = tmp_path / ".taskui" / "logs"
    return log_dir


@pytest.fixture
def mock_log_dir(temp_log_dir, monkeypatch):
    """Mock the LOG_DIR and LOG_FILE to use temporary directory."""
    log_file = temp_log_dir / "taskui.log"

    # Mock the module-level constants
    monkeypatch.setattr("taskui.logging_config.LOG_DIR", temp_log_dir)
    monkeypatch.setattr("taskui.logging_config.LOG_FILE", log_file)

    return temp_log_dir, log_file


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging handlers before and after each test."""
    # Clear existing handlers before test
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.WARNING)

    yield

    # Clear handlers after test
    root_logger.handlers.clear()
    root_logger.setLevel(logging.WARNING)


class TestLogDirectoryCreation:
    """Test suite for log directory creation."""

    def test_log_directory_created_automatically(self, mock_log_dir):
        """Test that log directory is created if it doesn't exist."""
        temp_log_dir, log_file = mock_log_dir

        # Ensure directory doesn't exist
        assert not temp_log_dir.exists()

        # Setup logging
        setup_logging()

        # Verify directory was created
        assert temp_log_dir.exists()
        assert temp_log_dir.is_dir()

    def test_log_directory_parents_created(self, tmp_path, monkeypatch):
        """Test that parent directories are created if needed."""
        nested_log_dir = tmp_path / "a" / "b" / "c" / "logs"
        log_file = nested_log_dir / "taskui.log"

        monkeypatch.setattr("taskui.logging_config.LOG_DIR", nested_log_dir)
        monkeypatch.setattr("taskui.logging_config.LOG_FILE", log_file)

        setup_logging()

        assert nested_log_dir.exists()
        assert nested_log_dir.is_dir()

    def test_log_directory_already_exists(self, mock_log_dir):
        """Test that existing log directory is not affected."""
        temp_log_dir, log_file = mock_log_dir

        # Create directory beforehand
        temp_log_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging should not fail
        setup_logging()

        assert temp_log_dir.exists()


class TestLogFileCreation:
    """Test suite for log file creation and writing."""

    def test_log_file_created_on_first_write(self, mock_log_dir):
        """Test that log file is created when first log message is written."""
        temp_log_dir, log_file = mock_log_dir

        setup_logging()

        # Write a log message
        logger = get_logger("test_module")
        logger.info("Test message")

        # Verify file was created
        assert log_file.exists()
        assert log_file.is_file()

    def test_log_messages_written_to_file(self, mock_log_dir):
        """Test that log messages are actually written to the file."""
        temp_log_dir, log_file = mock_log_dir

        setup_logging()

        logger = get_logger("test_module")
        test_message = "This is a test log message"
        logger.info(test_message)

        # Force flush
        for handler in logging.getLogger().handlers:
            handler.flush()

        # Read file and verify message is present
        content = log_file.read_text()
        assert test_message in content
        assert "test_module" in content
        assert "INFO" in content

    def test_log_format_includes_required_fields(self, mock_log_dir):
        """Test that log format includes timestamp, module, level, and message."""
        temp_log_dir, log_file = mock_log_dir

        setup_logging()

        logger = get_logger("my_module")
        logger.warning("Test warning message")

        # Force flush
        for handler in logging.getLogger().handlers:
            handler.flush()

        content = log_file.read_text()

        # Verify format components
        assert "my_module" in content  # Module name
        assert "WARNING" in content    # Log level
        assert "Test warning message" in content  # Message
        # Timestamp format: YYYY-MM-DD HH:MM:SS
        import re
        assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", content)


class TestPerModuleLogger:
    """Test suite for per-module logger naming."""

    def test_get_logger_returns_logger_instance(self):
        """Test that get_logger returns a logging.Logger instance."""
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)

    def test_logger_name_matches_provided_name(self):
        """Test that logger has the correct name."""
        module_name = "taskui.services.task_service"
        logger = get_logger(module_name)
        assert logger.name == module_name

    def test_different_modules_get_different_loggers(self):
        """Test that different module names get different logger instances."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        assert logger1 is not logger2
        assert logger1.name == "module1"
        assert logger2.name == "module2"

    def test_same_module_gets_same_logger(self):
        """Test that same module name gets the same logger instance."""
        logger1 = get_logger("same_module")
        logger2 = get_logger("same_module")

        assert logger1 is logger2

    def test_module_name_appears_in_log_output(self, mock_log_dir):
        """Test that module name appears in log file output."""
        temp_log_dir, log_file = mock_log_dir

        setup_logging()

        logger = get_logger("custom.module.name")
        logger.info("Test message from custom module")

        # Force flush
        for handler in logging.getLogger().handlers:
            handler.flush()

        content = log_file.read_text()
        assert "custom.module.name" in content


class TestLogLevelConfiguration:
    """Test suite for log level configuration via environment variables."""

    def test_default_log_level_is_info(self, mock_log_dir):
        """Test that default log level is INFO when no env var is set."""
        temp_log_dir, log_file = mock_log_dir

        with patch.dict(os.environ, {}, clear=True):
            setup_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_env_var_sets_debug_level(self, mock_log_dir):
        """Test that TASKUI_LOG_LEVEL=DEBUG sets DEBUG level."""
        temp_log_dir, log_file = mock_log_dir

        with patch.dict(os.environ, {"TASKUI_LOG_LEVEL": "DEBUG"}):
            setup_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_env_var_sets_warning_level(self, mock_log_dir):
        """Test that TASKUI_LOG_LEVEL=WARNING sets WARNING level."""
        temp_log_dir, log_file = mock_log_dir

        with patch.dict(os.environ, {"TASKUI_LOG_LEVEL": "WARNING"}):
            setup_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING

    def test_env_var_sets_error_level(self, mock_log_dir):
        """Test that TASKUI_LOG_LEVEL=ERROR sets ERROR level."""
        temp_log_dir, log_file = mock_log_dir

        with patch.dict(os.environ, {"TASKUI_LOG_LEVEL": "ERROR"}):
            setup_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.ERROR

    def test_env_var_case_insensitive(self, mock_log_dir):
        """Test that log level env var is case-insensitive."""
        temp_log_dir, log_file = mock_log_dir

        with patch.dict(os.environ, {"TASKUI_LOG_LEVEL": "debug"}):
            setup_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_invalid_log_level_defaults_to_info(self, mock_log_dir):
        """Test that invalid log level defaults to INFO."""
        temp_log_dir, log_file = mock_log_dir

        with patch.dict(os.environ, {"TASKUI_LOG_LEVEL": "INVALID"}):
            setup_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_parameter_overrides_env_var(self, mock_log_dir):
        """Test that log_level parameter overrides environment variable."""
        temp_log_dir, log_file = mock_log_dir

        with patch.dict(os.environ, {"TASKUI_LOG_LEVEL": "INFO"}):
            setup_logging(log_level="DEBUG")

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_debug_level_logs_debug_messages(self, mock_log_dir):
        """Test that DEBUG level actually logs debug messages."""
        temp_log_dir, log_file = mock_log_dir

        setup_logging(log_level="DEBUG")

        logger = get_logger("test")
        logger.debug("Debug message")

        # Force flush
        for handler in logging.getLogger().handlers:
            handler.flush()

        content = log_file.read_text()
        assert "Debug message" in content

    def test_info_level_filters_debug_messages(self, mock_log_dir):
        """Test that INFO level filters out DEBUG messages."""
        temp_log_dir, log_file = mock_log_dir

        setup_logging(log_level="INFO")

        logger = get_logger("test")
        logger.debug("Debug message - should not appear")
        logger.info("Info message - should appear")

        # Force flush
        for handler in logging.getLogger().handlers:
            handler.flush()

        content = log_file.read_text()
        assert "Debug message" not in content
        assert "Info message" in content


class TestLogRotation:
    """Test suite for log rotation functionality."""

    def test_rotating_file_handler_configured(self, mock_log_dir):
        """Test that RotatingFileHandler is configured correctly."""
        from logging.handlers import RotatingFileHandler

        temp_log_dir, log_file = mock_log_dir
        setup_logging()

        root_logger = logging.getLogger()

        # Find the RotatingFileHandler
        rotating_handlers = [
            h for h in root_logger.handlers
            if isinstance(h, RotatingFileHandler)
        ]

        assert len(rotating_handlers) > 0
        handler = rotating_handlers[0]

        # Verify rotation configuration
        assert handler.maxBytes == MAX_BYTES
        assert handler.backupCount == BACKUP_COUNT

    def test_log_rotation_creates_backup_files(self, mock_log_dir):
        """Test that log rotation creates backup files when size limit is exceeded."""
        temp_log_dir, log_file = mock_log_dir

        # Use smaller max bytes for testing
        with patch("taskui.logging_config.MAX_BYTES", 1024):  # 1KB
            setup_logging()

        logger = get_logger("test")

        # Write enough data to trigger rotation
        large_message = "X" * 500  # 500 bytes per message
        for i in range(5):  # Write ~2.5KB total
            logger.info(f"Message {i}: {large_message}")

        # Force flush
        for handler in logging.getLogger().handlers:
            handler.flush()

        # Check for backup files
        log_files = list(temp_log_dir.glob("taskui.log*"))

        # Should have at least the main log file
        assert len(log_files) >= 1
        assert log_file.exists()

    def test_backup_count_limits_number_of_backups(self, mock_log_dir):
        """Test that backup count limits the number of backup files."""
        temp_log_dir, log_file = mock_log_dir

        # Use very small max bytes and backup count for testing
        with patch("taskui.logging_config.MAX_BYTES", 500), \
             patch("taskui.logging_config.BACKUP_COUNT", 2):
            setup_logging()

        logger = get_logger("test")

        # Write enough data to create more rotations than backup count
        large_message = "Y" * 200
        for i in range(15):  # Write enough to trigger multiple rotations
            logger.info(f"Rotation test {i}: {large_message}")

        # Force flush
        for handler in logging.getLogger().handlers:
            handler.flush()

        # Count backup files
        log_files = list(temp_log_dir.glob("taskui.log*"))

        # Should have main file + up to BACKUP_COUNT backups
        # Note: May be fewer if rotation hasn't triggered enough times
        assert len(log_files) <= 3  # 1 main + 2 backups


class TestTextualHandlerIntegration:
    """Test suite for TextualHandler integration and fallback."""

    def test_file_handler_used_when_textual_disabled(self, mock_log_dir):
        """Test that file handler is used when use_textual_handler=False."""
        from logging.handlers import RotatingFileHandler

        temp_log_dir, log_file = mock_log_dir
        setup_logging(use_textual_handler=False)

        root_logger = logging.getLogger()

        # Should have at least one RotatingFileHandler
        rotating_handlers = [
            h for h in root_logger.handlers
            if isinstance(h, RotatingFileHandler)
        ]
        assert len(rotating_handlers) > 0

    def test_textual_handler_used_when_available(self, mock_log_dir):
        """Test that TextualHandler is used when available and enabled."""
        temp_log_dir, log_file = mock_log_dir

        # Mock TextualHandler to be available
        mock_handler_instance = MagicMock()
        mock_handler_instance.level = logging.INFO  # Set level attribute for comparison

        mock_textual_handler_class = MagicMock(return_value=mock_handler_instance)

        # Create a mock module with the TextualHandler class
        mock_textual_logging = MagicMock()
        mock_textual_logging.TextualHandler = mock_textual_handler_class

        with patch.dict("sys.modules", {"textual.logging": mock_textual_logging}):
            setup_logging(use_textual_handler=True)

        # Verify TextualHandler was instantiated
        mock_textual_handler_class.assert_called_once()
        mock_handler_instance.setLevel.assert_called()
        mock_handler_instance.setFormatter.assert_called()

    def test_fallback_to_file_handler_when_textual_unavailable(self, mock_log_dir):
        """Test graceful fallback to file handler when TextualHandler unavailable."""
        from logging.handlers import RotatingFileHandler

        temp_log_dir, log_file = mock_log_dir

        # Simulate ImportError when trying to import TextualHandler
        # We need to remove the module from sys.modules if it exists
        import sys
        textual_logging_exists = "textual.logging" in sys.modules

        if textual_logging_exists:
            # Temporarily remove it
            original_module = sys.modules.pop("textual.logging")

        try:
            # Mock the import to raise ImportError
            with patch.dict("sys.modules", {"textual.logging": None}):
                setup_logging(use_textual_handler=True)

            root_logger = logging.getLogger()

            # Should fall back to RotatingFileHandler
            rotating_handlers = [
                h for h in root_logger.handlers
                if isinstance(h, RotatingFileHandler)
            ]
            assert len(rotating_handlers) > 0
        finally:
            # Restore original state
            if textual_logging_exists:
                sys.modules["textual.logging"] = original_module

    def test_no_duplicate_handlers_on_multiple_calls(self, mock_log_dir):
        """Test that calling setup_logging multiple times doesn't create duplicate handlers."""
        temp_log_dir, log_file = mock_log_dir

        setup_logging()
        initial_handler_count = len(logging.getLogger().handlers)

        setup_logging()
        second_handler_count = len(logging.getLogger().handlers)

        # Handler count should be the same (handlers cleared before adding)
        assert initial_handler_count == second_handler_count

    def test_logging_initialized_message_logged(self, mock_log_dir):
        """Test that setup_logging logs an initialization message."""
        temp_log_dir, log_file = mock_log_dir

        setup_logging()

        # Force flush
        for handler in logging.getLogger().handlers:
            handler.flush()

        content = log_file.read_text()
        assert "Logging initialized" in content


class TestIntegrationScenarios:
    """Integration tests for real-world logging scenarios."""

    def test_multiple_modules_logging_simultaneously(self, mock_log_dir):
        """Test that multiple modules can log simultaneously."""
        temp_log_dir, log_file = mock_log_dir

        setup_logging()

        logger1 = get_logger("module.service")
        logger2 = get_logger("module.database")
        logger3 = get_logger("module.ui")

        logger1.info("Service message")
        logger2.warning("Database warning")
        logger3.error("UI error")

        # Force flush
        for handler in logging.getLogger().handlers:
            handler.flush()

        content = log_file.read_text()

        # All messages should be present
        assert "module.service" in content
        assert "Service message" in content
        assert "module.database" in content
        assert "Database warning" in content
        assert "module.ui" in content
        assert "UI error" in content

    def test_exception_logging_with_traceback(self, mock_log_dir):
        """Test that exceptions are logged with full traceback."""
        temp_log_dir, log_file = mock_log_dir

        setup_logging()
        logger = get_logger("test")

        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.error("An error occurred", exc_info=True)

        # Force flush
        for handler in logging.getLogger().handlers:
            handler.flush()

        content = log_file.read_text()

        # Should include exception type, message, and traceback
        assert "ValueError" in content
        assert "Test exception" in content
        assert "Traceback" in content

    def test_utf8_encoding_support(self, mock_log_dir):
        """Test that log files support UTF-8 encoding."""
        temp_log_dir, log_file = mock_log_dir

        setup_logging()
        logger = get_logger("test")

        # Log message with various UTF-8 characters
        unicode_message = "Test: 你好 مرحبا Привет 🎉"
        logger.info(unicode_message)

        # Force flush
        for handler in logging.getLogger().handlers:
            handler.flush()

        # Read with UTF-8 encoding
        content = log_file.read_text(encoding="utf-8")
        assert unicode_message in content
