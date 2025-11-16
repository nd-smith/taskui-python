"""
Thermal printer service for printing task cards to physical kanban board.

This module handles printing individual task cards via ESC/POS thermal printer.
Each task + children is printed as a separate card with auto-cut for easy
separation and use on a physical kanban board.
"""

from typing import Optional, List
from datetime import datetime
import logging
from pathlib import Path
from enum import Enum

# NOTE: python-escpos will be added as dependency in future session
# from escpos.printer import Network

from taskui.models import Task
from taskui.logging_config import get_logger

logger = get_logger(__name__)


class DetailLevel(Enum):
    """Print detail levels for task cards."""
    MINIMAL = "minimal"      # Title, checkbox, basic progress
    STANDARD = "standard"    # + dates, list name, completion %
    FULL = "full"           # + notes for task and children


class PrinterConfig:
    """Configuration for thermal printer connection."""

    def __init__(
        self,
        host: str = "192.168.50.99",
        port: int = 9100,
        timeout: int = 60,
        detail_level: DetailLevel = DetailLevel.MINIMAL
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.detail_level = detail_level

    @classmethod
    def from_config_file(cls, config_path: Optional[Path] = None) -> "PrinterConfig":
        """
        Load printer configuration from config.ini file.

        Args:
            config_path: Path to config file, defaults to ~/.taskui/config.ini

        Returns:
            PrinterConfig instance with loaded settings

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config format is invalid
        """
        if config_path is None:
            config_path = Path.home() / ".taskui" / "config.ini"

        # TODO: Implement config file parsing in future session
        # For now, return defaults
        logger.debug(f"Loading printer config from {config_path}")
        return cls()


class PrinterService:
    """
    Service for printing task cards to thermal receipt printer.

    Creates physical kanban cards by printing selected task + children
    to an Epson TM-T20III thermal printer via ESC/POS commands.
    """

    def __init__(self, config: PrinterConfig):
        """
        Initialize printer service.

        Args:
            config: PrinterConfig instance with connection details
        """
        self.config = config
        self.printer = None  # Will be Network printer instance
        self._connected = False

        logger.info(
            f"PrinterService initialized for {config.host}:{config.port}, "
            f"detail_level={config.detail_level.value}"
        )

    def connect(self) -> bool:
        """
        Connect to thermal printer.

        Returns:
            True if connection successful, False otherwise

        Raises:
            ConnectionError: If unable to connect to printer
        """
        logger.debug(f"Attempting to connect to printer at {self.config.host}:{self.config.port}")

        try:
            # TODO: Implement actual connection in future session
            # self.printer = Network(self.config.host, port=self.config.port, timeout=self.config.timeout)

            self._connected = True
            logger.info(f"Successfully connected to printer at {self.config.host}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to printer: {e}", exc_info=True)
            self._connected = False
            raise ConnectionError(f"Cannot connect to printer at {self.config.host}:{self.config.port}") from e

    def disconnect(self):
        """Disconnect from thermal printer."""
        if self.printer:
            # TODO: Implement actual disconnection
            self._connected = False
            logger.info("Disconnected from printer")

    def is_connected(self) -> bool:
        """Check if printer is currently connected."""
        return self._connected

    def print_task_card(self, task: Task, children: List[Task]) -> bool:
        """
        Print a single task card with children.

        Creates a physical kanban card by printing the task and all its
        children, then auto-cutting for easy separation.

        Args:
            task: The parent task to print
            children: List of child tasks to include on card

        Returns:
            True if print successful, False otherwise

        Raises:
            ConnectionError: If printer is not connected
            PrintError: If print operation fails
        """
        if not self._connected:
            raise ConnectionError("Printer not connected. Call connect() first.")

        logger.info(f"Printing task card: {task.title} with {len(children)} children")
        logger.debug(f"Detail level: {self.config.detail_level.value}")

        try:
            # Generate card content based on detail level
            card_content = self._format_task_card(task, children)

            # TODO: Implement actual printing in future session
            # self.printer.text(card_content)
            # self.printer.cut()

            logger.info(f"Successfully printed task card for task {task.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to print task card: {e}", exc_info=True)
            raise PrintError(f"Print operation failed: {e}") from e

    def _format_task_card(self, task: Task, children: List[Task]) -> str:
        """
        Format task and children into a kanban card layout.

        Args:
            task: Parent task
            children: Child tasks

        Returns:
            Formatted card content as string
        """
        # Dispatch to appropriate formatter based on detail level
        if self.config.detail_level == DetailLevel.MINIMAL:
            return self._format_minimal(task, children)
        elif self.config.detail_level == DetailLevel.STANDARD:
            return self._format_standard(task, children)
        else:
            return self._format_full(task, children)

    def _format_minimal(self, task: Task, children: List[Task]) -> str:
        """
        Format task card with minimal detail.

        Includes:
        - Title with checkbox
        - Progress indicator
        - Child tasks with checkboxes
        - Created date
        """
        # Card width for 80mm thermal printer (70 chars standard font)
        WIDTH = 70

        lines = []

        # Top border
        lines.append("┌" + "─" * (WIDTH - 2) + "┐")
        lines.append("│" + " " * (WIDTH - 2) + "│")

        # Task title with checkbox
        checkbox = "[X]" if task.is_completed else "[ ]"
        title_line = f"  {checkbox} {task.title}"
        lines.append("│" + title_line.ljust(WIDTH - 2) + "│")
        lines.append("│" + " " * (WIDTH - 2) + "│")

        # Progress indicator if has children
        if children:
            completed_count = sum(1 for child in children if child.is_completed)
            progress_line = f"      Progress: {completed_count}/{len(children)} subtasks"
            lines.append("│" + progress_line.ljust(WIDTH - 2) + "│")
            lines.append("│" + " " * (WIDTH - 2) + "│")

            # Child tasks
            for child in children:
                child_checkbox = "[X]" if child.is_completed else "[ ]"
                child_line = f"      {child_checkbox} {child.title}"
                # Truncate if too long
                if len(child_line) > WIDTH - 4:
                    child_line = child_line[:WIDTH - 7] + "..."
                lines.append("│" + child_line.ljust(WIDTH - 2) + "│")

            lines.append("│" + " " * (WIDTH - 2) + "│")

        # Created date
        created_date = task.created_at.strftime("%Y-%m-%d")
        date_line = f"      Created: {created_date}"
        lines.append("│" + date_line.ljust(WIDTH - 2) + "│")
        lines.append("│" + " " * (WIDTH - 2) + "│")

        # Bottom border
        lines.append("└" + "─" * (WIDTH - 2) + "┘")

        return "\n".join(lines)

    def _format_standard(self, task: Task, children: List[Task]) -> str:
        """
        Format task card with standard detail level.

        Adds to minimal:
        - List name
        - Completion percentage
        - Child task dates
        - Modified timestamp
        """
        # TODO: Implement in future session
        return self._format_minimal(task, children)

    def _format_full(self, task: Task, children: List[Task]) -> str:
        """
        Format task card with full detail level.

        Adds to standard:
        - Task notes
        - Child task notes
        - Column/level information
        - Print timestamp
        """
        # TODO: Implement in future session
        return self._format_minimal(task, children)

    def test_connection(self) -> bool:
        """
        Test printer connection without printing.

        Returns:
            True if printer responds, False otherwise
        """
        logger.debug("Testing printer connection")

        try:
            # TODO: Implement actual test in future session
            # Could send a simple command and check response
            return self._connected
        except Exception as e:
            logger.error(f"Connection test failed: {e}", exc_info=True)
            return False


class MockPrinter:
    """
    Mock printer for testing without hardware.

    Outputs formatted cards to console or file instead of printer.
    """

    def __init__(self, output_path: Optional[Path] = None):
        """
        Initialize mock printer.

        Args:
            output_path: If provided, write to file instead of console
        """
        self.output_path = output_path
        logger.info(f"MockPrinter initialized, output_path={output_path}")

    def print_card(self, card_content: str):
        """
        'Print' card by writing to console or file.

        Args:
            card_content: Formatted card content
        """
        separator = "\n" + "=" * 50 + " [CUT] " + "=" * 50 + "\n"

        if self.output_path:
            with open(self.output_path, "a") as f:
                f.write(card_content)
                f.write(separator)
            logger.debug(f"Mock printed to file: {self.output_path}")
        else:
            print(card_content)
            print(separator)
            logger.debug("Mock printed to console")


class PrintError(Exception):
    """Raised when print operation fails."""
    pass


# Example usage and testing
if __name__ == "__main__":
    from taskui.logging_config import setup_logging

    setup_logging()

    # Example configuration
    config = PrinterConfig(
        host="192.168.50.99",
        port=9100,
        detail_level=DetailLevel.MINIMAL
    )

    # Create mock task for testing
    from taskui.models import Task
    import uuid

    # Generate UUIDs for testing
    list_id = uuid.uuid4()
    task_id = uuid.uuid4()

    parent_task = Task(
        id=task_id,
        list_id=list_id,
        title="Design new feature",
        notes="This is a critical feature",
        is_completed=False,
        created_at=datetime.now()
    )

    children = [
        Task(id=uuid.uuid4(), list_id=list_id, title="Write specs", is_completed=False, created_at=datetime.now()),
        Task(id=uuid.uuid4(), list_id=list_id, title="Create mockups", is_completed=True, created_at=datetime.now()),
        Task(id=uuid.uuid4(), list_id=list_id, title="Review with team", is_completed=False, created_at=datetime.now()),
    ]

    # Test formatting without actual printer
    service = PrinterService(config)
    card_content = service._format_minimal(parent_task, children)

    # Use mock printer to visualize
    mock_printer = MockPrinter()
    mock_printer.print_card(card_content)
