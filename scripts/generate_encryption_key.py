#!/usr/bin/env python3
"""
Generate a secure encryption key for TaskUI cloud print encryption.

This script generates a cryptographically secure 256-bit encryption key
that can be used for end-to-end encryption of print jobs sent through SQS.

Usage:
    python scripts/generate_encryption_key.py

The generated key should be:
1. Copied to ~/.taskui/config.ini under [cloud_print] section as 'encryption_key'
2. Copied to the Raspberry Pi configuration (same key on both sides)
3. NEVER committed to git or shared insecurely
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from taskui.services.encryption import MessageEncryption


def main():
    """Generate and display a new encryption key."""
    print("=" * 70)
    print("TaskUI Cloud Print - Encryption Key Generator")
    print("=" * 70)
    print()

    # Generate a new key
    encryption_key = MessageEncryption.generate_key()

    print("Your new encryption key has been generated:")
    print()
    print("  " + encryption_key)
    print()
    print("=" * 70)
    print("IMPORTANT: Keep this key secure!")
    print("=" * 70)
    print()
    print("Next steps:")
    print()
    print("1. Copy this key to your TaskUI config file (~/.taskui/config.ini):")
    print("   [cloud_print]")
    print(f"   encryption_key = {encryption_key}")
    print()
    print("2. Copy the SAME key to your Raspberry Pi configuration")
    print("   (either config file or use TASKUI_ENCRYPTION_KEY environment variable)")
    print()
    print("3. NEVER commit this key to git or share it insecurely")
    print()
    print("4. Store a backup copy in a secure password manager")
    print()
    print("Security notes:")
    print("- This key provides end-to-end encryption for your print jobs")
    print("- Both sender (TaskUI app) and receiver (Raspberry Pi) need the same key")
    print("- Without this key, encrypted messages cannot be decrypted")
    print("- If you lose the key, generate a new one and update both sides")
    print("- Rotate keys periodically for best security")
    print()


if __name__ == "__main__":
    main()
