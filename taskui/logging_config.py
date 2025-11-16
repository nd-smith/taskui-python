"""Centralized logging configuration for TaskUI application.

This module provides a standardized logging setup with:
- File-based logging with rotation
- Configurable log levels via environment variable
- Structured log format with timestamps
- Automatic log directory creation
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


# Log file configuration
LOG_DIR = Path.home() / ".taskui" / "logs"
LOG_FILE = LOG_DIR / "taskui.log"

# Log format configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Rotation configuration
MAX_BYTES = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5


def setup_logging(
    log_level: Optional[str] = None,
    use_textual_handler: bool = False
) -> None:
    """Initialize application logging with file rotation.

    Creates log directory if it doesn't exist and configures a rotating
    file handler for all application logs.

    Args:
        log_level: Override log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                  If None, reads from TASKUI_LOG_LEVEL environment variable.
                  Defaults to INFO if not specified.
        use_textual_handler: If True, use Textual's handler for dev mode.
                            Falls back to file handler if unavailable.

    Example:
        >>> setup_logging()  # Uses default INFO level
        >>> setup_logging(log_level="DEBUG")  # Override to DEBUG
        >>> setup_logging(use_textual_handler=True)  # Dev mode
    """
    # Determine log level from parameter, env var, or default
    if log_level is None:
        log_level = os.getenv("TASKUI_LOG_LEVEL", "INFO").upper()

    # Validate log level
    numeric_level = getattr(logging, log_level, None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
        log_level = "INFO"

    # Create log directory if it doesn't exist
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Try to use TextualHandler in dev mode
    handler_added = False
    if use_textual_handler:
        try:
            from textual.logging import TextualHandler

            textual_handler = TextualHandler()
            textual_handler.setLevel(numeric_level)
            formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
            textual_handler.setFormatter(formatter)
            root_logger.addHandler(textual_handler)
            handler_added = True
        except ImportError:
            # TextualHandler not available, fall back to file handler
            pass

    # Add file handler (always, or as fallback)
    if not handler_added or not use_textual_handler:
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8"
        )
        file_handler.setLevel(numeric_level)
        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Log initial setup message
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging initialized: level={log_level}, "
        f"file={LOG_FILE}, "
        f"textual_handler={use_textual_handler and handler_added}"
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the specified module.

    This is a convenience wrapper around logging.getLogger() that ensures
    consistent logger naming across the application.

    Args:
        name: Module name, typically __name__

    Returns:
        Logger instance configured with the module name

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
        >>> logger.debug("Debug information")
        >>> logger.error("Error occurred", exc_info=True)
    """
    return logging.getLogger(name)
