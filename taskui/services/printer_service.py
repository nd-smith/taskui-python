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

from escpos.printer import Network, Usb, File

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
        connection_type: str = "network",
        host: str = "192.168.50.99",
        port: int = 9100,
        timeout: int = 60,
        detail_level: DetailLevel = DetailLevel.MINIMAL,
        device_path: str = "auto"
    ):
        self.connection_type = connection_type.lower()
        self.host = host
        self.port = port
        self.timeout = timeout
        self.detail_level = detail_level
        self.device_path = device_path

        # Validate connection type
        if self.connection_type not in ("network", "usb"):
            raise ValueError(f"Invalid connection_type: {connection_type}. Must be 'network' or 'usb'")

    @classmethod
    def from_config_file(cls, config_path: Optional[Path] = None) -> "PrinterConfig":
        """
        Load printer configuration from config.ini file.

        Args:
            config_path: Path to config file, defaults to ~/.taskui/config.ini

        Returns:
            PrinterConfig instance with loaded settings

        Raises:
            ValueError: If config format is invalid
        """
        from taskui.config import Config

        # Load configuration
        config = Config(config_path)
        printer_config = config.get_printer_config()

        # Convert detail_level string to enum
        detail_level_str = printer_config.get('detail_level', 'minimal').lower()
        try:
            detail_level = DetailLevel(detail_level_str)
        except ValueError:
            logger.warning(f"Invalid detail_level '{detail_level_str}', using MINIMAL")
            detail_level = DetailLevel.MINIMAL

        connection_type = printer_config.get('connection_type', 'network')
        logger.debug(f"Loaded printer config: connection_type={connection_type}, "
                    f"host={printer_config['host']}:{printer_config['port']}, "
                    f"device_path={printer_config.get('device_path', 'auto')}")

        return cls(
            connection_type=connection_type,
            host=printer_config['host'],
            port=printer_config['port'],
            timeout=printer_config['timeout'],
            detail_level=detail_level,
            device_path=printer_config.get('device_path', 'auto')
        )


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
        self.printer = None  # Will be Network or USB printer instance
        self._connected = False

        if config.connection_type == "network":
            logger.info(
                f"PrinterService initialized for network printer at {config.host}:{config.port}, "
                f"detail_level={config.detail_level.value}"
            )
        else:
            logger.info(
                f"PrinterService initialized for USB printer at {config.device_path}, "
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
        try:
            if self.config.connection_type == "network":
                logger.debug(f"Attempting to connect to network printer at {self.config.host}:{self.config.port}")
                self.printer = Network(self.config.host, port=self.config.port, timeout=self.config.timeout)
                logger.info(f"Successfully connected to network printer at {self.config.host}")
            else:  # USB
                # Check if auto-detection is requested
                if self.config.device_path.lower() in ("auto", ""):
                    logger.debug("Attempting to auto-detect USB printer")
                    # Auto-detect USB printer using Usb class (finds first available USB printer)
                    # Common ESC/POS printer vendor IDs: Epson (0x04b8), Star (0x0519), others
                    try:
                        # Try Epson TM-T20III first (0x04b8:0x0e27)
                        self.printer = Usb(0x04b8, 0x0e27)
                        logger.info("Successfully connected to Epson TM-T20III USB printer via auto-detection")
                    except:
                        # If Epson fails, try generic auto-detection with no IDs (finds first printer)
                        self.printer = Usb()
                        logger.info("Successfully connected to USB printer via auto-detection")
                else:
                    logger.debug(f"Attempting to connect to USB printer at {self.config.device_path}")
                    # For USB printers with specific device path, use File class
                    self.printer = File(self.config.device_path)
                    logger.info(f"Successfully connected to USB printer at {self.config.device_path}")

            self._connected = True
            return True

        except Exception as e:
            logger.error(f"Failed to connect to printer: {e}", exc_info=True)
            self._connected = False
            if self.config.connection_type == "network":
                raise ConnectionError(f"Cannot connect to network printer at {self.config.host}:{self.config.port}") from e
            else:
                raise ConnectionError(f"Cannot connect to USB printer at {self.config.device_path}") from e

    def disconnect(self):
        """Disconnect from thermal printer."""
        if self.printer:
            self.printer.close()
            self.printer = None
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
            # Print card based on detail level
            self._print_card(task, children)

            logger.info(f"Successfully printed task card for task {task.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to print task card: {e}", exc_info=True)
            raise PrintError(f"Print operation failed: {e}") from e

    def _print_card(self, task: Task, children: List[Task]):
        """
        Print task card directly to printer with validated minimal format.

        Format:
        - Title: Font A, bold, double-height, double-width
        - Body: Font B (smaller), no bold
        - Children: Checkboxes with titles
        - Notes: Plain text with automatic wrapping

        Args:
            task: Parent task
            children: Child tasks
        """
        # TITLE - BIG and BOLD (Font A, double size)
        self.printer.set(font='a', bold=True, double_height=True, double_width=True)
        self.printer.text(f"\n{task.title}\n\n\n")

        # BODY - Small font (Font B is smaller than Font A)
        self.printer.set(font='b', bold=False, double_height=False, double_width=False)

        if children:
            # Print children as checkboxes with spacing between them
            for i, child in enumerate(children):
                checkbox = "[X]" if child.is_completed else "[ ]"
                self.printer.text(f"{checkbox} {child.title}\n")
                # Add extra line between children (but not after the last one)
                if i < len(children) - 1:
                    self.printer.text("\n")
        elif task.notes:
            # Print notes with automatic wrapping
            self.printer.text(f"{task.notes}\n")

        # Spacing and cut
        self.printer.text("\n\n\n")
        self.printer.cut(mode="FULL")
        self.printer.close()

    def test_connection(self) -> bool:
        """
        Test printer connection by printing a simple test message.

        Returns:
            True if printer responds, False otherwise
        """
        logger.debug("Testing printer connection")

        try:
            if not self._connected:
                return False

            # Print simple test message
            self.printer.text("TaskUI Printer Test\n")
            self.printer.text("Connection OK\n\n\n")
            self.printer.cut(mode="FULL")
            self.printer.close()

            logger.info("Printer connection test successful")
            return True
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

    # Example configuration for network printer
    config = PrinterConfig(
        connection_type="network",
        host="192.168.50.99",
        port=9100,
        detail_level=DetailLevel.MINIMAL
    )

    # Example configuration for USB printer (uncomment to test USB)
    # config = PrinterConfig(
    #     connection_type="usb",
    #     device_path="/dev/usb/lp0",
    #     detail_level=DetailLevel.MINIMAL
    # )

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

    # Test with actual printer
    service = PrinterService(config)

    try:
        # Connect to printer
        service.connect()

        # Test connection
        if service.test_connection():
            print("✓ Connection test passed")

        # Reconnect after test (test_connection closes printer)
        service.connect()

        # Print task card
        service.print_task_card(parent_task, children)
        print("✓ Task card printed successfully")

    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        service.disconnect()
