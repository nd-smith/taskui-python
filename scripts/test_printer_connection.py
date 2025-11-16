#!/usr/bin/env python3
"""
Standalone printer connectivity test.
Tests basic connection and printing without app integration.

Usage:
    python scripts/test_printer_connection.py
"""

from escpos.printer import Network
import sys


def test_connection():
    """Test basic connection to printer."""
    try:
        printer = Network("192.168.50.99", port=9100, timeout=10)
        print("✓ Connected to printer")
        return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


def test_print_hello():
    """Print simple hello world test."""
    try:
        printer = Network("192.168.50.99", port=9100, timeout=10)

        # Test text printing
        printer.text("Hello World from TaskUI\n")
        printer.text("Test print successful!\n")
        printer.text("\n\n\n")

        # Test auto-cut with full cut mode
        printer.cut(mode='FULL')

        # Close connection to ensure cut command is sent
        printer.close()

        print("✓ Test print successful")
        return True
    except Exception as e:
        print(f"✗ Print failed: {e}")
        return False


def test_formatted_text():
    """Test text formatting capabilities."""
    try:
        printer = Network("192.168.50.99", port=9100, timeout=10)

        # Test formatting
        printer.set(align='center', bold=True, double_height=True)
        printer.text("TASKUI\n")

        printer.set(align='left', bold=False, double_height=False)
        printer.text("Normal text\n")

        printer.set(bold=True)
        printer.text("Bold text\n")

        printer.set(underline=True, bold=False)
        printer.text("Underlined text\n")

        printer.text("\n\n\n")
        printer.cut(mode='FULL')

        # Close connection to ensure cut command is sent
        printer.close()

        print("✓ Formatting test successful")
        return True
    except Exception as e:
        print(f"✗ Formatting test failed: {e}")
        return False


if __name__ == "__main__":
    print("TaskUI Printer Connectivity Test")
    print("=" * 40)

    tests = [
        ("Connection", test_connection),
        ("Hello World", test_print_hello),
        ("Text Formatting", test_formatted_text),
    ]

    results = []
    for name, test_func in tests:
        print(f"\nRunning: {name}")
        result = test_func()
        results.append((name, result))

    print("\n" + "=" * 40)
    print("Test Results:")
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status} - {name}")

    all_passed = all(result for _, result in results)
    sys.exit(0 if all_passed else 1)
