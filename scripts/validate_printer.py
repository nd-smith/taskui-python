#!/usr/bin/env python3
"""
Hardware validation script for thermal printer.

This script validates that the printer hardware is properly configured
and all printing features work correctly with the actual thermal printer.
"""

import sys
from datetime import datetime
from uuid import uuid4

from taskui.services.printer_service import PrinterService, PrinterConfig
from taskui.models import Task
from taskui.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def print_section_header(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def validate_connection() -> PrinterService:
    """Validate printer connection.

    Returns:
        PrinterService instance if successful

    Raises:
        SystemExit if connection fails
    """
    print_section_header("1. Testing Printer Connection")

    try:
        config = PrinterConfig.from_config_file()
        print(f"✓ Config loaded: {config.host}:{config.port}")

        service = PrinterService(config)
        service.connect()
        print("✓ Successfully connected to printer")

        return service

    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Check printer is powered on")
        print("  2. Verify network connection (ping 192.168.50.99)")
        print("  3. Ensure port 9100 is accessible")
        print("  4. Check ~/.taskui/config.ini settings")
        sys.exit(1)


def validate_test_connection(service: PrinterService):
    """Validate test connection feature."""
    print_section_header("2. Testing Simple Print")

    try:
        result = service.test_connection()
        if result:
            print("✓ Test print successful")
            print("  Check printer for 'TaskUI Printer Test' message")
        else:
            print("✗ Test print failed")
            return False

    except Exception as e:
        print(f"✗ Test print failed: {e}")
        return False

    # Reconnect after test_connection (it closes the printer)
    service.connect()
    return True


def validate_task_with_children(service: PrinterService):
    """Validate printing task with children."""
    print_section_header("3. Testing Task Card with Children")

    try:
        # Create sample task
        list_id = uuid4()
        parent_task = Task(
            id=uuid4(),
            list_id=list_id,
            title="Design Authentication System",
            notes="Critical security feature",
            is_completed=False,
            created_at=datetime.now()
        )

        # Create sample children
        children = [
            Task(
                id=uuid4(),
                list_id=list_id,
                parent_id=parent_task.id,
                title="Research OAuth2 providers",
                level=1,
                is_completed=True,
                created_at=datetime.now()
            ),
            Task(
                id=uuid4(),
                list_id=list_id,
                parent_id=parent_task.id,
                title="Design database schema",
                level=1,
                is_completed=False,
                created_at=datetime.now()
            ),
            Task(
                id=uuid4(),
                list_id=list_id,
                parent_id=parent_task.id,
                title="Implement JWT tokens",
                level=1,
                is_completed=False,
                created_at=datetime.now()
            ),
            Task(
                id=uuid4(),
                list_id=list_id,
                parent_id=parent_task.id,
                title="Write security tests",
                level=1,
                is_completed=False,
                created_at=datetime.now()
            ),
        ]

        service.print_task_card(parent_task, children)
        print("✓ Task card with children printed")
        print(f"  Validate on physical card:")
        print(f"    - Title: '{parent_task.title}' (large, bold)")
        print(f"    - 4 children as checkboxes")
        print(f"    - First child marked as [X] completed")
        print(f"    - Good spacing between children")
        print(f"    - Clean cut at bottom")

    except Exception as e:
        print(f"✗ Failed to print task with children: {e}")
        return False

    # Reconnect
    service.connect()
    return True


def validate_task_with_notes(service: PrinterService):
    """Validate printing task with notes."""
    print_section_header("4. Testing Task Card with Notes")

    try:
        # Create task with long notes
        task = Task(
            id=uuid4(),
            list_id=uuid4(),
            title="Important Meeting Notes",
            notes="Discussed project timeline and deliverables. Key points: "
                  "1) Launch date moved to Q2. 2) Need additional resources for testing. "
                  "3) Budget approved for new features. 4) Team expansion planned.",
            is_completed=False,
            created_at=datetime.now()
        )

        service.print_task_card(task, [])
        print("✓ Task card with notes printed")
        print(f"  Validate on physical card:")
        print(f"    - Title: '{task.title}' (large, bold)")
        print(f"    - Notes text wrapped properly")
        print(f"    - Text is readable")
        print(f"    - Clean cut at bottom")

    except Exception as e:
        print(f"✗ Failed to print task with notes: {e}")
        return False

    # Reconnect
    service.connect()
    return True


def validate_edge_cases(service: PrinterService):
    """Validate edge cases."""
    print_section_header("5. Testing Edge Cases")

    tests_passed = 0
    tests_total = 0

    # Test 1: Very long title
    tests_total += 1
    try:
        task = Task(
            id=uuid4(),
            list_id=uuid4(),
            title="This is a very long task title that should wrap correctly on the thermal printer without breaking the layout or causing any issues",
            is_completed=False,
            created_at=datetime.now()
        )
        service.print_task_card(task, [])
        print("  ✓ Long title printed")
        tests_passed += 1
        service.connect()
    except Exception as e:
        print(f"  ✗ Long title failed: {e}")

    # Test 2: Many children
    tests_total += 1
    try:
        parent = Task(
            id=uuid4(),
            list_id=uuid4(),
            title="Task with many subtasks",
            is_completed=False,
            created_at=datetime.now()
        )
        children = [
            Task(
                id=uuid4(),
                list_id=parent.list_id,
                parent_id=parent.id,
                title=f"Subtask {i+1}",
                level=1,
                is_completed=(i % 2 == 0),
                created_at=datetime.now()
            )
            for i in range(10)
        ]
        service.print_task_card(parent, children)
        print("  ✓ 10 children printed")
        tests_passed += 1
        service.connect()
    except Exception as e:
        print(f"  ✗ Many children failed: {e}")

    # Test 3: Empty task (no notes, no children)
    tests_total += 1
    try:
        task = Task(
            id=uuid4(),
            list_id=uuid4(),
            title="Simple task",
            is_completed=False,
            created_at=datetime.now()
        )
        service.print_task_card(task, [])
        print("  ✓ Empty task printed")
        tests_passed += 1
        service.connect()
    except Exception as e:
        print(f"  ✗ Empty task failed: {e}")

    print(f"\nEdge cases: {tests_passed}/{tests_total} passed")
    return tests_passed == tests_total


def main():
    """Run all validation tests."""
    print("\n" + "=" * 60)
    print("  THERMAL PRINTER HARDWARE VALIDATION")
    print("=" * 60)
    print("\nThis script will print several test cards to validate")
    print("all printing features work correctly.\n")

    input("Press Enter to begin validation (or Ctrl+C to cancel)...")

    # Run validation tests
    service = validate_connection()

    results = {
        "Connection": True,
        "Test Print": validate_test_connection(service),
        "Task with Children": validate_task_with_children(service),
        "Task with Notes": validate_task_with_notes(service),
        "Edge Cases": validate_edge_cases(service),
    }

    # Cleanup
    service.disconnect()

    # Print summary
    print_section_header("VALIDATION SUMMARY")

    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status} - {test_name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)

    if all_passed:
        print("✓ ALL VALIDATIONS PASSED")
        print("\nYour printer is properly configured and working!")
        print("You can now use the 'P' key in TaskUI to print task cards.")
        return 0
    else:
        print("✗ SOME VALIDATIONS FAILED")
        print("\nPlease review the failures above and:")
        print("  1. Check physical cards for issues")
        print("  2. Review PRINTER_TROUBLESHOOTING.md")
        print("  3. Verify printer settings in config.ini")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nValidation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        logger.error("Validation script error", exc_info=True)
        sys.exit(1)
