"""Entry point for TaskUI application.

This module allows running TaskUI as a module:
    python -m taskui

Or as an installed command:
    taskui
"""

import sys
from typing import Optional

from taskui.logging_config import setup_logging, get_logger

# Initialize logger for this module
logger = get_logger(__name__)


def main(args: Optional[list[str]] = None) -> int:
    """Main entry point for TaskUI.

    Args:
        args: Command-line arguments (defaults to sys.argv)

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    if args is None:
        args = sys.argv[1:]

    # Initialize logging before any other operations
    setup_logging()

    # Import here to avoid circular imports and improve startup time
    from taskui.ui.app import TaskUI

    try:
        app = TaskUI()
        app.run()
        logger.info("TaskUI application exited normally")
        return 0
    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C
        logger.info("TaskUI closed by user (Ctrl+C)")
        return 0
    except Exception as e:
        logger.error("Error running TaskUI", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
