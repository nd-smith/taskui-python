#!/usr/bin/env python3
"""
Test script for encryption/decryption functionality.

This script tests the MessageEncryption class to ensure encryption
and decryption are working correctly for cloud print messages.

Usage:
    python scripts/test_encryption.py
"""

import sys
import os
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import encryption module directly to avoid dependencies
import importlib.util
spec = importlib.util.spec_from_file_location(
    "encryption",
    os.path.join(os.path.dirname(__file__), '..', 'taskui', 'services', 'encryption.py')
)
encryption_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(encryption_module)
MessageEncryption = encryption_module.MessageEncryption


def test_encryption_decryption():
    """Test basic encryption and decryption."""
    print("=" * 70)
    print("Testing Encryption/Decryption")
    print("=" * 70)
    print()

    # Generate a test key
    print("1. Generating encryption key...")
    key = MessageEncryption.generate_key()
    print(f"   Key: {key[:20]}...")
    print()

    # Create encryption handler
    print("2. Initializing encryption...")
    encryption = MessageEncryption(key)
    print(f"   Encryption enabled: {encryption.enabled}")
    print()

    # Create a test message (simulating a print job)
    test_message = {
        'version': '1.0',
        'timestamp': datetime.now().isoformat(),
        'task': {
            'id': '12345678-1234-1234-1234-123456789012',
            'title': 'Test Task with Sensitive Data',
            'notes': 'This contains confidential information',
            'is_completed': False,
            'created_at': datetime.now().isoformat()
        },
        'children': [
            {
                'id': '87654321-4321-4321-4321-210987654321',
                'title': 'Confidential subtask',
                'notes': 'Secret notes',
                'is_completed': False,
                'created_at': datetime.now().isoformat()
            }
        ]
    }

    print("3. Original message:")
    print(f"   Task: {test_message['task']['title']}")
    print(f"   Notes: {test_message['task']['notes']}")
    print(f"   Children: {len(test_message['children'])}")
    print()

    # Encrypt the message
    print("4. Encrypting message...")
    encrypted = encryption.encrypt_message(test_message)
    encrypted_obj = json.loads(encrypted)

    print(f"   Encrypted: {encrypted_obj.get('encrypted', False)}")
    print(f"   Algorithm: {encrypted_obj.get('algorithm', 'N/A')}")
    print(f"   Ciphertext length: {len(encrypted_obj.get('ciphertext', ''))} chars")
    print(f"   Sample: {encrypted_obj.get('ciphertext', '')[:50]}...")
    print()

    # Verify original data is not in encrypted form
    if test_message['task']['title'] in encrypted:
        print("   ⚠️  WARNING: Original data found in encrypted message!")
        return False
    else:
        print("   ✅ Original data NOT visible in encrypted form")
    print()

    # Decrypt the message
    print("5. Decrypting message...")
    decrypted = encryption.decrypt_message(encrypted)

    print(f"   Task: {decrypted['task']['title']}")
    print(f"   Notes: {decrypted['task']['notes']}")
    print(f"   Children: {len(decrypted['children'])}")
    print()

    # Verify decrypted matches original
    print("6. Verifying decrypted data matches original...")

    if decrypted['task']['title'] != test_message['task']['title']:
        print("   ❌ FAILED: Task title mismatch")
        return False

    if decrypted['task']['notes'] != test_message['task']['notes']:
        print("   ❌ FAILED: Task notes mismatch")
        return False

    if len(decrypted['children']) != len(test_message['children']):
        print("   ❌ FAILED: Children count mismatch")
        return False

    if decrypted['children'][0]['title'] != test_message['children'][0]['title']:
        print("   ❌ FAILED: Child title mismatch")
        return False

    print("   ✅ All data matches perfectly")
    print()

    return True


def test_wrong_key():
    """Test that wrong key fails decryption."""
    print("=" * 70)
    print("Testing Wrong Key Rejection")
    print("=" * 70)
    print()

    # Create two different keys
    key1 = MessageEncryption.generate_key()
    key2 = MessageEncryption.generate_key()

    enc1 = MessageEncryption(key1)
    enc2 = MessageEncryption(key2)

    # Encrypt with key1
    test_msg = {'test': 'data', 'value': 123}
    encrypted = enc1.encrypt_message(test_msg)

    print("1. Encrypted with key1")
    print("2. Attempting to decrypt with key2 (wrong key)...")

    # Try to decrypt with key2
    try:
        decrypted = enc2.decrypt_message(encrypted)
        print("   ❌ FAILED: Wrong key should not decrypt!")
        return False
    except ValueError as e:
        print(f"   ✅ Correctly rejected: {str(e)}")
        print()
        return True


def test_disabled_encryption():
    """Test that encryption can be disabled."""
    print("=" * 70)
    print("Testing Disabled Encryption (Backward Compatibility)")
    print("=" * 70)
    print()

    # Create encryption with no key (disabled)
    encryption = MessageEncryption(None)

    print(f"1. Encryption enabled: {encryption.enabled}")

    if encryption.enabled:
        print("   ❌ FAILED: Should be disabled with no key")
        return False

    # Test that messages pass through as JSON
    test_msg = {'task': {'title': 'Test'}, 'children': []}

    print("2. Encrypting message (should pass through as plain JSON)...")
    encrypted = encryption.encrypt_message(test_msg)

    # Should be plain JSON, not encrypted
    try:
        parsed = json.loads(encrypted)
        if parsed.get('encrypted'):
            print("   ❌ FAILED: Should not be encrypted")
            return False
        if parsed != test_msg:
            print("   ❌ FAILED: Message was modified")
            return False
        print("   ✅ Message passed through as plain JSON")
    except:
        print("   ❌ FAILED: Should be valid JSON")
        return False

    print("3. Decrypting message (should parse plain JSON)...")
    decrypted = encryption.decrypt_message(encrypted)

    if decrypted != test_msg:
        print("   ❌ FAILED: Decrypted doesn't match original")
        return False

    print("   ✅ Message decrypted correctly")
    print()

    return True


def main():
    """Run all tests."""
    print()
    print("🔐 TaskUI Cloud Print Encryption Test Suite")
    print()

    tests = [
        ("Encryption/Decryption", test_encryption_decryption),
        ("Wrong Key Rejection", test_wrong_key),
        ("Disabled Encryption", test_disabled_encryption),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   ❌ EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Print summary
    print()
    print("=" * 70)
    print("Test Results Summary")
    print("=" * 70)
    print()

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {status}: {test_name}")

    print()
    print(f"Total: {passed}/{total} tests passed")
    print()

    if passed == total:
        print("🎉 All tests passed! Encryption is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
