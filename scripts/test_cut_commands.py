#!/usr/bin/env python3
"""
Test different Epson cut commands to find full cut.
Each test prints a label and tries a different cut command.
"""

import socket
import time

PRINTER_IP = "192.168.50.99"
PRINTER_PORT = 9100

ESC = b'\x1b'
GS = b'\x1d'

def send_cut_test(label, cut_command):
    """Send test with specific cut command."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((PRINTER_IP, PRINTER_PORT))

        # Clear buffer
        sock.sendall(ESC + b'@')
        time.sleep(0.1)

        # Print label
        data = ESC + b'@' + label.encode() + b'\n\n\n' + cut_command
        sock.sendall(data)

        time.sleep(0.5)
        sock.shutdown(socket.SHUT_WR)
        time.sleep(0.5)
        sock.close()

        print(f"✓ Sent: {label}")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Epson Cut Command Test")
    print("=" * 50)
    print("\nTesting different cut commands...")
    print("Check each receipt to see which one is FULLY cut.\n")

    # Different Epson cut commands
    tests = [
        ("CUT 1: GS V 0", GS + b'V\x00'),           # Standard full cut
        ("CUT 2: GS V 1", GS + b'V\x01'),           # Standard partial cut
        ("CUT 3: GS V 48", GS + b'V\x30'),          # Function 48 (full)
        ("CUT 4: GS V 49", GS + b'V\x31'),          # Function 49 (partial)
        ("CUT 5: GS V 65", GS + b'V\x41'),          # Mode 65 (A)
        ("CUT 6: GS V 66 0", GS + b'V\x42\x00'),    # Mode 66 with feed 0
        ("CUT 7: GS V 66 3", GS + b'V\x42\x03'),    # Mode 66 with feed 3
        ("CUT 8: ESC i", ESC + b'i'),                # Alternative cut
        ("CUT 9: ESC m", ESC + b'm'),                # Partial cut alternative
    ]

    for label, cut_cmd in tests:
        send_cut_test(label, cut_cmd)
        time.sleep(3)

    print("\n" + "=" * 50)
    print("Done! Check printer for 9 receipts.")
    print("Find which one is FULLY cut and note the number.")
    print("=" * 50)
