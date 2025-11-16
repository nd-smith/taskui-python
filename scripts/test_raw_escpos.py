#!/usr/bin/env python3
"""
Test raw ESC/POS commands to debug formatting and cut issues.
Sends direct byte sequences instead of using python-escpos abstraction.
"""

import socket
import time

PRINTER_IP = "192.168.50.99"
PRINTER_PORT = 9100

# ESC/POS command bytes
ESC = b'\x1b'
GS = b'\x1d'

# Initialize printer
CMD_INIT = ESC + b'@'

# Text formatting
CMD_BOLD_ON = ESC + b'E\x01'
CMD_BOLD_OFF = ESC + b'E\x00'
CMD_UNDERLINE_ON = ESC + b'-\x01'
CMD_UNDERLINE_OFF = ESC + b'-\x00'

# Alignment
CMD_ALIGN_LEFT = ESC + b'a\x00'
CMD_ALIGN_CENTER = ESC + b'a\x01'
CMD_ALIGN_RIGHT = ESC + b'a\x02'

# Size
CMD_DOUBLE_HEIGHT = GS + b'!\x01'
CMD_NORMAL_SIZE = GS + b'!\x00'

# Cut commands - Epson specific
# GS V m n - where m=66 (0x42) is full cut with feed
CMD_CUT_FULL = GS + b'V\x42\x00'     # Full cut (m=66/0x42)
CMD_CUT_PARTIAL = GS + b'V\x01'      # Partial cut
CMD_CUT_FULL_ALT = GS + b'V\x00'    # Alternative full cut

# Line feed
CMD_LF = b'\n'


def send_to_printer(data, clear_buffer=True):
    """Send raw bytes to printer."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((PRINTER_IP, PRINTER_PORT))

        # Clear any buffered data from previous jobs
        if clear_buffer:
            sock.sendall(ESC + b'@')  # Initialize printer
            time.sleep(0.1)

        sock.sendall(data)

        # Wait for data to be sent and processed
        time.sleep(0.5)

        # Shutdown write side to signal end of data
        sock.shutdown(socket.SHUT_WR)

        # Wait a bit more for cut to complete
        time.sleep(0.5)

        sock.close()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_raw_hello():
    """Test 1: Simple hello world with cut."""
    print("\nTest 1: Simple Hello World + Cut")

    data = (
        CMD_INIT +
        b"Hello World from TaskUI\n" +
        b"Test print successful!\n" +
        CMD_LF + CMD_LF + CMD_LF +  # Extra line feeds before cut
        CMD_CUT_FULL
    )

    result = send_to_printer(data)
    print(f"  {'✓' if result else '✗'} Sent {len(data)} bytes")
    time.sleep(2)
    return result


def test_raw_formatting():
    """Test 2: Text with formatting."""
    print("\nTest 2: Formatted Text")

    data = (
        CMD_INIT +
        CMD_ALIGN_CENTER + CMD_DOUBLE_HEIGHT + CMD_BOLD_ON +
        b"TASKUI\n" +
        CMD_BOLD_OFF + CMD_NORMAL_SIZE + CMD_ALIGN_LEFT +
        CMD_LF +
        b"Normal text\n" +
        CMD_BOLD_ON +
        b"Bold text\n" +
        CMD_BOLD_OFF +
        CMD_UNDERLINE_ON +
        b"Underlined text\n" +
        CMD_UNDERLINE_OFF +
        CMD_LF + CMD_LF + CMD_LF +  # Extra line feeds before cut
        CMD_CUT_FULL
    )

    result = send_to_printer(data)
    print(f"  {'✓' if result else '✗'} Sent {len(data)} bytes")
    time.sleep(2)
    return result


def test_raw_box():
    """Test 3: Box drawing characters."""
    print("\nTest 3: Box Drawing")

    data = (
        CMD_INIT +
        b"\n" +
        b"+" + b"-" * 40 + b"+\n" +
        b"|  Test Card                            |\n" +
        b"|                                       |\n" +
        b"|  [ ] Sample task                      |\n" +
        b"|                                       |\n" +
        b"+" + b"-" * 40 + b"+\n" +
        CMD_LF + CMD_LF + CMD_LF +  # Extra line feeds before cut
        CMD_CUT_FULL
    )

    result = send_to_printer(data)
    print(f"  {'✓' if result else '✗'} Sent {len(data)} bytes")
    time.sleep(2)
    return result


if __name__ == "__main__":
    print("=" * 50)
    print("Raw ESC/POS Command Test")
    print("=" * 50)
    print("\nThis will print 3 separate receipts.")
    print("Check each one for:")
    print("  1. Auto-cut between receipts")
    print("  2. Bold and underlined text")
    print("  3. Centered TASKUI header")
    print("  4. Box drawing characters")
    print()

    tests = [
        test_raw_hello,
        test_raw_formatting,
        test_raw_box,
    ]

    for test in tests:
        test()
        print("  Waiting 3 seconds...")
        time.sleep(3)

    print("\n" + "=" * 50)
    print("Done! Check printer for 3 receipts.")
    print("=" * 50)
