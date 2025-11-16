#!/usr/bin/env python3
"""
Task card with notes (no subtasks).
"""

from escpos.printer import Network

PRINTER_IP = "192.168.50.99"
PRINTER_PORT = 9100


def print_task_with_notes():
    """Print task with notes in body."""
    try:
        printer = Network(PRINTER_IP, port=PRINTER_PORT, timeout=10)

        # TITLE - BIG and BOLD (Font A, double size)
        printer.set(font='a', bold=True, double_height=True, double_width=True)
        printer.text("\nFix authentication bug\n\n")

        # NOTES - Small font (Font B is smaller than Font A)
        printer.set(font='b', bold=False, double_height=False, double_width=False)
        # Let the printer wrap text automatically - don't manually break lines
        printer.text("Users getting timeout errors on login. Check session management and token expiration.\n")

        printer.text("\n\n\n")
        printer.cut(mode="FULL")
        printer.close()

        print("✓ Task with notes printed")
        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Task with Notes (No Subtasks)")
    print("=" * 50)
    print_task_with_notes()
