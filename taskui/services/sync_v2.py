"""
Sync V2: JSON-based full-state sync.

Thin layer on top of export/import for SQS-based sync.
Replaces the complex per-operation V1 sync with atomic state transfer.
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from taskui.logging_config import get_logger
from taskui.export_schema import ConflictStrategy, ExportedState
from taskui.services.cloud_print_queue import CloudPrintConfig
from taskui.services.encryption import MessageEncryption
from taskui.services.export_import import ExportImportService

logger = get_logger(__name__)


class SyncV2Error(Exception):
    """Base exception for sync V2 errors."""
    pass


class SyncV2ConnectionError(SyncV2Error):
    """Failed to connect to sync queue."""
    pass


class SyncV2Service:
    """
    V2 Sync service using full-state JSON transfer.

    Operations:
    - sync_push(): Export local state → encrypt → send to SQS
    - sync_pull(): Receive from SQS → decrypt → import to local
    - sync_full(): Push then pull
    """

    # Message type for V2 sync messages
    MESSAGE_TYPE = "FULL_STATE_SYNC_V2"

    def __init__(
        self,
        session: AsyncSession,
        config: CloudPrintConfig,
        client_id: str,
    ):
        """
        Initialize sync V2 service.

        Args:
            session: SQLAlchemy async session
            config: CloudPrintConfig with SQS and encryption settings
            client_id: Unique identifier for this client/machine
        """
        self.session = session
        self.config = config
        self.client_id = client_id
        self.export_import = ExportImportService(session, client_id)
        self.encryption = MessageEncryption(config.encryption_key)
        self.sqs_client = None
        self._connected = False

    def connect(self) -> bool:
        """
        Connect to AWS SQS.

        Returns:
            True if connection successful
        """
        try:
            import boto3
            from botocore.exceptions import NoCredentialsError

            # Disable SSL warnings for corporate proxies
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            except ImportError:
                pass

            # Build client kwargs
            client_kwargs = {
                'region_name': self.config.region,
                'verify': False  # Disable SSL verification for corporate proxies
            }

            if self.config.aws_access_key_id and self.config.aws_secret_access_key:
                client_kwargs['aws_access_key_id'] = self.config.aws_access_key_id
                client_kwargs['aws_secret_access_key'] = self.config.aws_secret_access_key

            self.sqs_client = boto3.client('sqs', **client_kwargs)

            # Test connection
            self.sqs_client.get_queue_attributes(
                QueueUrl=self.config.queue_url,
                AttributeNames=['ApproximateNumberOfMessages']
            )

            self._connected = True
            logger.info(f"Sync V2 connected to: {self.config.queue_url}")
            return True

        except ImportError:
            logger.error("boto3 not installed")
            return False
        except Exception as e:
            logger.error(f"Failed to connect: {e}", exc_info=True)
            return False

    def disconnect(self) -> None:
        """Disconnect from SQS."""
        self.sqs_client = None
        self._connected = False

    def is_connected(self) -> bool:
        """Check connection status."""
        return self._connected

    # =========================================================================
    # PUSH (Local → Remote)
    # =========================================================================

    async def sync_push(self) -> bool:
        """
        Push local state to remote sync queue.

        Exports all lists, encrypts, and sends to SQS.

        Returns:
            True if push successful
        """
        if not self._connected:
            raise SyncV2ConnectionError("Not connected to sync queue")

        try:
            # Export full state
            state = await self.export_import.export_all_lists()

            # Build message
            message = {
                "type": self.MESSAGE_TYPE,
                "version": "2.0",
                "client_id": self.client_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": state.model_dump(mode="json"),
            }

            # Encrypt
            encrypted = self.encryption.encrypt_message(message)

            # Send to SQS
            response = self.sqs_client.send_message(
                QueueUrl=self.config.queue_url,
                MessageBody=encrypted,
                MessageAttributes={
                    'MessageType': {
                        'StringValue': self.MESSAGE_TYPE,
                        'DataType': 'String'
                    },
                    'ClientId': {
                        'StringValue': self.client_id,
                        'DataType': 'String'
                    }
                }
            )

            logger.info(
                f"[SYNC] Push complete: {len(state.lists)} lists "
                f"(MessageId: {response['MessageId']})"
            )
            return True

        except Exception as e:
            logger.error(f"Sync push failed: {e}", exc_info=True)
            raise SyncV2Error(f"Push failed: {e}") from e

    # =========================================================================
    # PULL (Remote → Local)
    # =========================================================================

    async def sync_pull(
        self,
        strategy: ConflictStrategy = ConflictStrategy.NEWER_WINS,
        conflict_callback: Optional[Callable[[str], bool]] = None,
        max_messages: int = 10,
    ) -> Tuple[int, int, List[str]]:
        """
        Pull remote state from sync queue.

        Receives messages from SQS, decrypts, and imports.
        Only processes messages from other clients (ignores own messages).

        Args:
            strategy: Conflict resolution strategy
            conflict_callback: Optional callback for PROMPT strategy.
                              Takes conflict message, returns True to import.
            max_messages: Maximum messages to process per pull

        Returns:
            Tuple of (lists_imported, lists_skipped, conflict_messages)
        """
        if not self._connected:
            raise SyncV2ConnectionError("Not connected to sync queue")

        total_imported = 0
        total_skipped = 0
        all_conflicts: List[str] = []

        try:
            # Receive messages
            response = self.sqs_client.receive_message(
                QueueUrl=self.config.queue_url,
                MaxNumberOfMessages=min(max_messages, 10),  # SQS limit is 10
                MessageAttributeNames=['All'],
                WaitTimeSeconds=1,  # Short poll for responsiveness
            )

            messages = response.get('Messages', [])

            if not messages:
                logger.debug("No sync messages available")
                return 0, 0, []

            logger.info(f"Processing {len(messages)} sync messages")

            for msg in messages:
                try:
                    # Check if from another client
                    attrs = msg.get('MessageAttributes', {})
                    sender_id = attrs.get('ClientId', {}).get('StringValue', '')
                    msg_type = attrs.get('MessageType', {}).get('StringValue', '')

                    # Skip own messages
                    if sender_id == self.client_id:
                        logger.debug(f"Skipping own message: {msg['MessageId']}")
                        self._delete_message(msg['ReceiptHandle'])
                        continue

                    # Only process V2 sync messages
                    if msg_type != self.MESSAGE_TYPE:
                        logger.debug(f"Skipping non-V2 message: {msg_type}")
                        continue

                    # Decrypt message
                    decrypted = self.encryption.decrypt_message(msg['Body'])

                    # Import the state
                    imported, skipped, conflicts = await self._process_sync_message(
                        decrypted,
                        strategy,
                        conflict_callback,
                    )

                    total_imported += imported
                    total_skipped += skipped
                    all_conflicts.extend(conflicts)

                    # Delete processed message
                    self._delete_message(msg['ReceiptHandle'])

                except Exception as e:
                    logger.error(f"Failed to process message: {e}", exc_info=True)
                    # Don't delete failed messages - they'll be retried

            logger.info(
                f"[SYNC] Pull complete: {total_imported} imported, "
                f"{total_skipped} skipped, {len(all_conflicts)} conflicts"
            )
            return total_imported, total_skipped, all_conflicts

        except Exception as e:
            logger.error(f"Sync pull failed: {e}", exc_info=True)
            raise SyncV2Error(f"Pull failed: {e}") from e

    def _delete_message(self, receipt_handle: str) -> None:
        """Delete a message from the queue."""
        try:
            self.sqs_client.delete_message(
                QueueUrl=self.config.queue_url,
                ReceiptHandle=receipt_handle,
            )
        except Exception as e:
            logger.warning(f"Failed to delete message: {e}")

    async def _process_sync_message(
        self,
        message: Dict[str, Any],
        strategy: ConflictStrategy,
        conflict_callback: Optional[Callable[[str], bool]],
    ) -> Tuple[int, int, List[str]]:
        """
        Process a single sync message.

        Args:
            message: Decrypted message dict
            strategy: Conflict resolution strategy
            conflict_callback: Optional callback for PROMPT strategy

        Returns:
            Tuple of (imported, skipped, conflicts)
        """
        data = message.get('data', {})

        # Handle PROMPT strategy with callback
        if strategy == ConflictStrategy.PROMPT and conflict_callback:
            # We need to do a pre-check for conflicts
            # For now, use NEWER_WINS and collect conflicts
            imported, skipped, conflicts = await self.export_import.import_all_lists(
                data,
                ConflictStrategy.NEWER_WINS,
            )
        else:
            imported, skipped, conflicts = await self.export_import.import_all_lists(
                data,
                strategy,
            )

        return imported, skipped, conflicts

    # =========================================================================
    # FULL SYNC
    # =========================================================================

    async def sync_full(
        self,
        strategy: ConflictStrategy = ConflictStrategy.NEWER_WINS,
        conflict_callback: Optional[Callable[[str], bool]] = None,
    ) -> Dict[str, Any]:
        """
        Perform full bidirectional sync.

        Push local state, then pull remote state.

        Args:
            strategy: Conflict resolution strategy for pull
            conflict_callback: Optional callback for PROMPT strategy

        Returns:
            Dict with sync results:
            - push_success: bool
            - pull_imported: int
            - pull_skipped: int
            - conflicts: List[str]
        """
        results = {
            'push_success': False,
            'pull_imported': 0,
            'pull_skipped': 0,
            'conflicts': [],
        }

        # Push first
        try:
            results['push_success'] = await self.sync_push()
        except SyncV2Error as e:
            logger.error(f"Push phase failed: {e}")

        # Then pull
        try:
            imported, skipped, conflicts = await self.sync_pull(
                strategy,
                conflict_callback,
            )
            results['pull_imported'] = imported
            results['pull_skipped'] = skipped
            results['conflicts'] = conflicts
        except SyncV2Error as e:
            logger.error(f"Pull phase failed: {e}")

        return results

    # =========================================================================
    # STATUS
    # =========================================================================

    def get_queue_depth(self) -> Optional[int]:
        """
        Get number of messages waiting in queue.

        Returns:
            Number of messages, or None if error
        """
        if not self._connected:
            return None

        try:
            response = self.sqs_client.get_queue_attributes(
                QueueUrl=self.config.queue_url,
                AttributeNames=['ApproximateNumberOfMessages']
            )
            return int(response['Attributes']['ApproximateNumberOfMessages'])
        except Exception as e:
            logger.error(f"Failed to get queue depth: {e}")
            return None
