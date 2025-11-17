#!/usr/bin/env python3
"""
Diagnostic script to identify USB printers on Windows.
Helps find the correct port/name for TaskUI printer configuration.
"""

import platform
import subprocess
import sys

def check_windows_printers():
    """Check for installed printers on Windows using PowerShell."""
    print("=== Checking installed Windows printers ===\n")

    try:
        # Use PowerShell to list printers
        result = subprocess.run(
            ["powershell", "-Command", "Get-Printer | Select-Object Name, PortName, DriverName | Format-List"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"Error querying printers: {result.stderr}")
    except Exception as e:
        print(f"Failed to query printers: {e}")

def check_usb_devices():
    """Check USB devices (requires pyusb)."""
    print("\n=== Checking USB devices ===\n")

    try:
        import usb.core

        # Find all USB devices
        devices = usb.core.find(find_all=True)

        print("USB Devices found:")
        for dev in devices:
            try:
                print(f"  Vendor ID: 0x{dev.idVendor:04x}, Product ID: 0x{dev.idProduct:04x}")
                try:
                    print(f"    Manufacturer: {usb.util.get_string(dev, dev.iManufacturer)}")
                    print(f"    Product: {usb.util.get_string(dev, dev.iProduct)}")
                except:
                    pass
                print()
            except:
                continue

        # Specifically look for Epson TM-T20III (0x04b8:0x0e27)
        epson_printer = usb.core.find(idVendor=0x04b8, idProduct=0x0e27)
        if epson_printer:
            print("✓ Found Epson TM-T20III (0x04b8:0x0e27)")
        else:
            print("✗ Epson TM-T20III (0x04b8:0x0e27) not found via USB")

    except ImportError:
        print("pyusb not installed. Install with: pip install pyusb")
        print("Note: This is optional but helps identify USB printer connections")
    except Exception as e:
        print(f"Error checking USB devices: {e}")

def check_printer_ports():
    """Check available printer ports on Windows."""
    print("\n=== Checking printer ports ===\n")

    ports_to_check = [
        "LPT1", "LPT2", "LPT3",
        "USB001", "USB002", "USB003", "USB004", "USB005",
        "COM1", "COM2", "COM3", "COM4"
    ]

    print("Attempting to check if ports exist (will show access errors for non-existent ports):")
    for port in ports_to_check:
        port_path = f"\\\\.\\{port}"
        try:
            # Try to open port (read mode to avoid printer activation)
            with open(port_path, "rb") as f:
                print(f"  ✓ {port} exists (accessible)")
        except FileNotFoundError:
            print(f"  ✗ {port} does not exist")
        except PermissionError:
            print(f"  ✓ {port} exists (permission denied - printer may be in use)")
        except Exception as e:
            print(f"  ? {port} - {type(e).__name__}: {e}")

def check_pywin32():
    """Check if pywin32 is available."""
    print("\n=== Checking pywin32 availability ===\n")

    try:
        import win32print
        print("✓ pywin32 is installed")

        # List printers using win32print
        printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)
        print(f"\nFound {len(printers)} local printer(s):")
        for printer in printers:
            print(f"  - {printer[2]}")  # printer[2] is the printer name

    except ImportError:
        print("✗ pywin32 is NOT installed")
        print("  Install with: pip install pywin32")
        print("  This is optional but provides better printer detection on Windows")

def main():
    print("TaskUI Printer Diagnostic Tool")
    print("=" * 60)
    print()

    if platform.system() != "Windows":
        print(f"ERROR: This diagnostic is for Windows only. Detected: {platform.system()}")
        print("On Linux/macOS, USB printers are typically at /dev/usb/lp0 or /dev/ttyUSB0")
        sys.exit(1)

    check_windows_printers()
    check_usb_devices()
    check_printer_ports()
    check_pywin32()

    print("\n" + "=" * 60)
    print("RECOMMENDATIONS:")
    print("=" * 60)
    print()
    print("1. If you see your printer listed above with a PortName (like USB001),")
    print("   update your config.ini with that port:")
    print()
    print("   [printer]")
    print("   connection_type = usb")
    print("   device_path = USB001  # Use the actual port from above")
    print()
    print("2. If pywin32 is installed and you see a printer name, you can use:")
    print()
    print("   [printer]")
    print("   connection_type = usb")
    print("   device_path = EPSON TM-T20III  # Use exact printer name")
    print()
    print("3. If the printer isn't showing up:")
    print("   - Ensure the printer is connected via USB")
    print("   - Install printer drivers from manufacturer")
    print("   - Add the printer in Windows Settings > Devices > Printers")
    print()

if __name__ == "__main__":
    main()
