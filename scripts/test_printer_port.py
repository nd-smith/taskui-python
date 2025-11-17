#!/usr/bin/env python3
"""
Test a specific printer port to verify it works.
Usage: python test_printer_port.py USB001
"""

import sys

def test_port(port_name):
    """Test if we can open and write to a printer port."""
    port_path = f"\\\\.\\{port_name}"

    print(f"Testing printer port: {port_name}")
    print(f"Full path: {port_path}")
    print()

    try:
        # Try to open the port
        print("Attempting to open port...")
        with open(port_path, "wb", buffering=0) as f:
            print("✓ Port opened successfully!")

            # Try to write a simple test
            print("Sending test data...")
            f.write(b"TaskUI Test\n")
            f.write(b"\n\n\n")
            f.flush()
            print("✓ Data sent successfully!")

        print()
        print("SUCCESS: Port is accessible and working!")
        print()
        print("Add this to ~/.taskui/config.ini:")
        print()
        print("[printer]")
        print("connection_type = usb")
        print(f"device_path = {port_name}")
        print("detail_level = minimal")

        return True

    except FileNotFoundError:
        print(f"✗ ERROR: Port {port_name} does not exist")
        print()
        print("The port file cannot be found. This usually means:")
        print("  - The printer is not connected")
        print("  - The printer is connected to a different port")
        print("  - The printer is not installed in Windows")
        print()
        print("Run diagnose_printer_basic.py to find available ports")
        return False

    except PermissionError:
        print(f"✗ ERROR: Permission denied for port {port_name}")
        print()
        print("The port exists but cannot be accessed. This could mean:")
        print("  - Another program is using the printer")
        print("  - You need administrator privileges")
        print("  - The printer is in an error state")
        print()
        print("Try:")
        print("  1. Close any printer software")
        print("  2. Restart the printer")
        print("  3. Run this script as administrator")
        return False

    except Exception as e:
        print(f"✗ ERROR: {type(e).__name__}: {e}")
        print()
        print("An unexpected error occurred.")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_printer_port.py <PORT_NAME>")
        print()
        print("Examples:")
        print("  python test_printer_port.py USB001")
        print("  python test_printer_port.py LPT1")
        print("  python test_printer_port.py DOT4_001")
        print()
        print("Run diagnose_printer_basic.py first to find available ports")
        sys.exit(1)

    port_name = sys.argv[1]
    test_port(port_name)

if __name__ == "__main__":
    main()
