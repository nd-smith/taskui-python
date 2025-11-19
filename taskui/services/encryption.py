"""
Message encryption/decryption for secure cloud printing.

Implements AES-256-GCM encryption for end-to-end security of print jobs
sent through SQS, protecting data even when SSL/TLS verification is disabled
or compromised.
"""

import os
import json
import base64
from typing import Dict, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class MessageEncryption:
    """Handles encryption and decryption of print job messages."""

    ENCRYPTION_VERSION = "1.0"
    KEY_SIZE = 32  # 256 bits
    NONCE_SIZE = 12  # 96 bits (recommended for GCM)

    def __init__(self, key: Optional[str] = None):
        """
        Initialize encryption handler.

        Args:
            key: Base64-encoded 32-byte encryption key. If None, encryption
                 will be disabled and messages will pass through as-is.
        """
        self.enabled = key is not None and len(key.strip()) > 0

        if self.enabled:
            try:
                # Decode the base64 key
                key_bytes = base64.b64decode(key)

                if len(key_bytes) != self.KEY_SIZE:
                    raise ValueError(
                        f"Encryption key must be {self.KEY_SIZE} bytes, "
                        f"got {len(key_bytes)} bytes"
                    )

                self.aesgcm = AESGCM(key_bytes)
            except Exception as e:
                raise ValueError(f"Invalid encryption key: {e}")
        else:
            self.aesgcm = None

    def encrypt_message(self, plaintext_data: Dict) -> str:
        """
        Encrypt a message dictionary into a JSON string.

        Args:
            plaintext_data: Dictionary containing the message to encrypt

        Returns:
            JSON string containing encrypted data (or plain JSON if disabled)
        """
        if not self.enabled:
            # Encryption disabled - return plain JSON
            return json.dumps(plaintext_data)

        # Convert data to JSON string
        plaintext_json = json.dumps(plaintext_data)
        plaintext_bytes = plaintext_json.encode('utf-8')

        # Generate random nonce (must be unique for each message)
        nonce = os.urandom(self.NONCE_SIZE)

        # Encrypt the data
        # GCM provides both confidentiality and authenticity
        ciphertext = self.aesgcm.encrypt(nonce, plaintext_bytes, None)

        # Create encrypted message envelope
        encrypted_envelope = {
            'encrypted': True,
            'version': self.ENCRYPTION_VERSION,
            'algorithm': 'AES-256-GCM',
            'nonce': base64.b64encode(nonce).decode('utf-8'),
            'ciphertext': base64.b64encode(ciphertext).decode('utf-8')
        }

        return json.dumps(encrypted_envelope)

    def decrypt_message(self, encrypted_json: str) -> Dict:
        """
        Decrypt a message from JSON string to dictionary.

        Args:
            encrypted_json: JSON string containing encrypted or plain data

        Returns:
            Decrypted message dictionary

        Raises:
            ValueError: If decryption fails or message is invalid
        """
        # Parse the JSON envelope
        try:
            envelope = json.loads(encrypted_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON message: {e}")

        # Check if message is encrypted
        if not isinstance(envelope, dict) or not envelope.get('encrypted'):
            # Not encrypted - return as-is (backward compatibility)
            if not self.enabled:
                return envelope
            else:
                # Encryption is enabled but message is not encrypted
                # This could be a legacy message or configuration mismatch
                return envelope

        # Encrypted message - decrypt it
        if not self.enabled:
            raise ValueError(
                "Received encrypted message but encryption is not configured. "
                "Please set encryption_key in config."
            )

        # Validate envelope structure
        required_fields = ['version', 'algorithm', 'nonce', 'ciphertext']
        missing_fields = [f for f in required_fields if f not in envelope]
        if missing_fields:
            raise ValueError(
                f"Invalid encrypted message: missing fields {missing_fields}"
            )

        # Check encryption version
        if envelope['version'] != self.ENCRYPTION_VERSION:
            raise ValueError(
                f"Unsupported encryption version: {envelope['version']}"
            )

        # Check algorithm
        if envelope['algorithm'] != 'AES-256-GCM':
            raise ValueError(
                f"Unsupported encryption algorithm: {envelope['algorithm']}"
            )

        # Decode base64 data
        try:
            nonce = base64.b64decode(envelope['nonce'])
            ciphertext = base64.b64decode(envelope['ciphertext'])
        except Exception as e:
            raise ValueError(f"Invalid base64 encoding: {e}")

        # Decrypt the data
        try:
            plaintext_bytes = self.aesgcm.decrypt(nonce, ciphertext, None)
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")

        # Parse the decrypted JSON
        try:
            plaintext_json = plaintext_bytes.decode('utf-8')
            return json.loads(plaintext_json)
        except Exception as e:
            raise ValueError(f"Invalid decrypted data: {e}")

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new random encryption key.

        Returns:
            Base64-encoded 32-byte key suitable for use with MessageEncryption
        """
        key_bytes = os.urandom(MessageEncryption.KEY_SIZE)
        return base64.b64encode(key_bytes).decode('utf-8')
