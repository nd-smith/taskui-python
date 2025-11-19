#!/usr/bin/env python3
"""
Minimal kanban card - just title and subtasks.
"""

from escpos.printer import Network

PRINTER_IP = "192.168.1.100"
PRINTER_PORT = 9100


def print_minimal_card():
    """Print super simple card."""
    try:
        printer = Network(PRINTER_IP, port=PRINTER_PORT, timeout=10)

        # TITLE - BIG and BOLD (Font A, double size)
        printer.set(font='a', bold=True, double_height=True, double_width=True)
        printer.text("\nDesign new feature\n\n")

        # BODY - Small font (Font B is smaller than Font A)
        printer.set(font='b', bold=False, double_height=False, double_width=False)
        printer.text("[ ] Write specs\n")
        printer.text("[X] Create mockups\n")
        printer.text("[ ] Review with team\n")

        printer.text("\n\n\n")
        printer.cut(mode="FULL")
        printer.close()

        print("✓ Minimal card printed")
        return True

    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Minimal Kanban Card")
    print("=" * 50)
    print("\nJust: Title (big/bold) + Subtasks (normal)\n")
    print_minimal_card()
