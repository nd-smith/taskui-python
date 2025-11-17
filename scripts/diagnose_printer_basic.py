#!/usr/bin/env python3
"""
Basic printer diagnostic for locked-down Windows environments.
No special permissions or libraries required.
"""

import platform
import subprocess
import sys
import os

def check_with_powershell():
    """Use PowerShell to list printers - usually works in locked-down environments."""
    print("=== Checking printers with PowerShell ===\n")

    commands = [
        # List all printers with their ports
        ("Printers and Ports", "Get-Printer | Select-Object Name, PortName, DriverName | Format-Table -AutoSize"),
        # List printer ports specifically
        ("Printer Ports", "Get-PrinterPort | Select-Object Name, Description | Format-Table -AutoSize"),
    ]

    for title, cmd in commands:
        print(f"\n{title}:")
        print("-" * 60)
        try:
            result = subprocess.run(
                ["powershell", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                if output:
                    print(output)
                else:
                    print("  (No results)")
            else:
                print(f"  Error: {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            print("  Timeout - command took too long")
        except Exception as e:
            print(f"  Failed: {e}")

def check_port_files():
    """Try to access printer port files directly."""
    print("\n=== Testing direct port access ===\n")

    ports = [
        "LPT1", "LPT2", "LPT3",
        "USB001", "USB002", "USB003", "USB004", "USB005", "USB006",
        "DOT4_001", "DOT4_002", "DOT4_003",  # Sometimes USB printers use DOT4
        "COM1", "COM2", "COM3", "COM4"
    ]

    accessible_ports = []

    for port in ports:
        port_path = f"\\\\.\\{port}"
        try:
            # Try to open for reading (less intrusive than writing)
            with open(port_path, "rb") as f:
                print(f"  ✓ {port} - EXISTS and accessible")
                accessible_ports.append(port)
        except FileNotFoundError:
            # Port doesn't exist - this is normal
            pass
        except PermissionError:
            print(f"  ⚠ {port} - EXISTS but permission denied (may be in use)")
            accessible_ports.append(port)
        except Exception as e:
            if "cannot find" not in str(e).lower():
                print(f"  ? {port} - {type(e).__name__}: {e}")

    if not accessible_ports:
        print("  ✗ No accessible printer ports found")

    return accessible_ports

def check_devices_folder():
    """Check /dev style paths that might exist."""
    print("\n=== Checking device paths ===\n")

    # On Windows in some environments, there might be /dev/usb paths
    paths_to_check = [
        "/dev/usb/lp0",
        "/dev/usb/lp1",
        "/dev/ttyUSB0",
        "/dev/ttyUSB1",
    ]

    found = False
    for path in paths_to_check:
        if os.path.exists(path):
            print(f"  ✓ {path} exists")
            found = True

    if not found:
        print("  (No /dev paths found - this is normal on Windows)")

def manual_instructions():
    """Provide manual checking instructions."""
    print("\n" + "=" * 60)
    print("MANUAL STEPS TO FIND YOUR PRINTER PORT")
    print("=" * 60)
    print("""
1. Open Windows Device Manager:
   - Press Win+X, select "Device Manager"
   - OR search for "Device Manager" in Start menu

2. Look for your printer under:
   - "Print queues" or "Printers"
   - "Universal Serial Bus controllers"
   - "Ports (COM & LPT)"

3. Right-click the printer and select "Properties"

4. Go to the "Ports" or "Details" tab

5. Look for the port assignment, it might be:
   - USB001, USB002, USB003, etc.
   - DOT4_001, DOT4_002, etc. (for some USB printers)
   - A COM port (COM1, COM2, etc.)
   - A network path (if network printer)

6. Alternatively, check Windows Settings:
   - Settings → Devices → Printers & scanners
   - Click on your printer
   - Click "Manage"
   - Look at "Printer properties" → "Ports" tab
""")

def main():
    print("TaskUI Printer Diagnostic (Basic - No Admin Required)")
    print("=" * 60)
    print()

    if platform.system() != "Windows":
        print(f"ERROR: This diagnostic is for Windows only. Detected: {platform.system()}")
        sys.exit(1)

    # Try PowerShell first (most reliable in locked-down environments)
    check_with_powershell()

    # Try direct port access
    accessible_ports = check_port_files()

    # Check for /dev paths (unlikely on Windows but worth checking)
    check_devices_folder()

    # Provide manual instructions
    manual_instructions()

    # Summary and recommendations
    print("=" * 60)
    print("RECOMMENDED NEXT STEPS")
    print("=" * 60)
    print()

    if accessible_ports:
        print(f"✓ Found accessible ports: {', '.join(accessible_ports)}")
        print()
        print("Try this configuration in ~/.taskui/config.ini:")
        print()
        print("[printer]")
        print("connection_type = usb")
        print(f"device_path = {accessible_ports[0]}  # Try each port if this doesn't work")
        print("detail_level = minimal")
        print()
    else:
        print("✗ No accessible ports found automatically.")
        print()
        print("Please:")
        print("1. Follow the manual steps above to find your printer port in Device Manager")
        print("2. Once you find the port (e.g., USB001), create ~/.taskui/config.ini:")
        print()
        print("   [printer]")
        print("   connection_type = usb")
        print("   device_path = USB001  # Replace with your actual port")
        print("   detail_level = minimal")
        print()
        print("3. If printer is not showing in Device Manager:")
        print("   - Ensure USB cable is connected")
        print("   - Check if you need to install printer drivers")
        print("   - You may need IT support to install the printer")
        print()

if __name__ == "__main__":
    main()
