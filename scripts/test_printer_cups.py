#!/usr/bin/env python3
"""
CUPS-based printer connectivity test.
Alternative test using CUPS instead of raw socket on port 9100.

Usage:
    python scripts/test_printer_cups.py [printer_name]

If no printer name is provided, will list available printers.
"""

from escpos.printer import CupsPrinter
import sys
import subprocess


def list_cups_printers():
    """List available CUPS printers."""
    try:
        result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
        if result.returncode == 0:
            print("Available CUPS printers:")
            print(result.stdout)
            return True
        else:
            print("No CUPS printers found or lpstat not available")
            return False
    except FileNotFoundError:
        print("✗ lpstat command not found (CUPS not installed locally)")
        print("\nTo find printer name:")
        print("1. Access http://192.168.50.99:631 in web browser")
        print("2. Click 'Printers' tab")
        print("3. Note the printer name")
        return False


def test_cups_connection(printer_name):
    """Test CUPS printer connection."""
    try:
        printer = CupsPrinter(printer_name)
        print(f"✓ Connected to CUPS printer: {printer_name}")
        return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


def test_cups_print_hello(printer_name):
    """Print hello world via CUPS."""
    try:
        printer = CupsPrinter(printer_name)

        # Test text printing
        printer.text("Hello World from TaskUI\n")
        printer.text("Test print via CUPS\n")
        printer.text("\n")

        # Test auto-cut
        printer.cut()

        print("✓ Test print successful")
        return True
    except Exception as e:
        print(f"✗ Print failed: {e}")
        return False


def test_cups_formatted_text(printer_name):
    """Test text formatting via CUPS."""
    try:
        printer = CupsPrinter(printer_name)

        # Test formatting
        printer.set(align='center', bold=True, double_height=True)
        printer.text("TASKUI\n")

        printer.set(align='left', bold=False, double_height=False)
        printer.text("Normal text\n")

        printer.set(bold=True)
        printer.text("Bold text\n")

        printer.set(underline=True, bold=False)
        printer.text("Underlined text\n")

        printer.text("\n")
        printer.cut()

        print("✓ Formatting test successful")
        return True
    except Exception as e:
        print(f"✗ Formatting test failed: {e}")
        return False


if __name__ == "__main__":
    print("TaskUI CUPS Printer Connectivity Test")
    print("=" * 40)

    # Get printer name from command line or list printers
    if len(sys.argv) > 1:
        printer_name = sys.argv[1]
    else:
        print("\nNo printer name provided. Listing available printers...\n")
        list_cups_printers()
        print("\nUsage: python scripts/test_printer_cups.py PRINTER_NAME")
        print("\nCommon printer names:")
        print("  - TM-T20III")
        print("  - EPSON_TM_T20III")
        print("  - TaskUI_Printer")
        sys.exit(1)

    print(f"\nTesting CUPS printer: {printer_name}\n")

    tests = [
        ("Connection", lambda: test_cups_connection(printer_name)),
        ("Hello World", lambda: test_cups_print_hello(printer_name)),
        ("Text Formatting", lambda: test_cups_formatted_text(printer_name)),
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

    if not all_passed:
        print("\n" + "=" * 40)
        print("Troubleshooting:")
        print("1. Verify printer name with: lpstat -p")
        print("2. Or access: http://192.168.50.99:631")
        print("3. Check docs/PRINTER_TROUBLESHOOTING.md")

    sys.exit(0 if all_passed else 1)
