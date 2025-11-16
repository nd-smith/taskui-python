#!/usr/bin/env python3
"""
Test different python-escpos cut modes and parameters.
"""

from escpos.printer import Network
import time

PRINTER_IP = "192.168.50.99"
PRINTER_PORT = 9100

def test_cut_mode(label, mode=None, feed=False):
    """Test specific cut mode."""
    try:
        printer = Network(PRINTER_IP, port=PRINTER_PORT, timeout=10)

        printer.text(f"{label}\n\n\n")

        if mode and feed:
            printer.cut(mode=mode, feed=feed)
        elif mode:
            printer.cut(mode=mode)
        elif feed:
            printer.cut(feed=feed)
        else:
            printer.cut()

        printer.close()
        print(f"✓ {label}")
        time.sleep(2)
        return True
    except Exception as e:
        print(f"✗ {label}: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Python-ESCPOS Cut Modes Test")
    print("=" * 50)

    tests = [
        ("1. Default cut()", None, False),
        ("2. cut(mode='FULL')", 'FULL', False),
        ("3. cut(mode='PART')", 'PART', False),
        ("4. cut(feed=True)", None, True),
        ("5. cut(mode='FULL', feed=True)", 'FULL', True),
        ("6. cut(mode='FULL', feed=4)", 'FULL', 4),
    ]

    for label, mode, feed in tests:
        test_cut_mode(label, mode, feed)

    print("\n" + "=" * 50)
    print("Check printer - which receipt is FULLY cut?")
    print("=" * 50)
