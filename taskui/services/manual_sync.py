"""
Manual sync service for bidirectional synchronization.

User-controlled sync - no background polling. Sync only happens when
explicitly triggered via keyboard shortcut or app lifecycle events.
"""

from typing import Tuple, List, Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime
import asyncio

from taskui.logging_config import get_logger

if TYPE_CHECKING:
    from taskui.services.sync_queue import SyncQueue
    from taskui.services.pending_operations import PendingOperationsQueue
    from taskui.services.sync_operations import SyncOperationHandler

logger = get_logger(__name__)


class ManualSyncService:
    """
    Manual sync service - no background polling.
    Sync only happens when explicitly triggered.
    """

    def __init__(
        self,
        sync_queue: "SyncQueue",
        pending_queue: "PendingOperationsQueue",
        operation_handler: "SyncOperationHandler"
    ):
        """
        Initialize manual sync service.

        Args:
            sync_queue: SyncQueue for sending/receiving SQS messages
            pending_queue: PendingOperationsQueue for local operation storage
            operation_handler: SyncOperationHandler for applying remote operations
        """
        self.sync_queue = sync_queue
        self.pending_queue = pending_queue
        self.operation_handler = operation_handler
        self.last_sync_time: Optional[datetime] = None
        self._syncing = False

    @property
    def is_syncing(self) -> bool:
        """Check if sync is currently in progress."""
        return self._syncing

    async def sync(self) -> Tuple[int, int]:
        """
        Perform bidirectional sync.

        1. Push all pending local operations to SQS
        2. Pull all remote operations from SQS
        3. Apply remote operations to local database

        Returns:
            Tuple of (operations_sent, operations_received)
        """
        if self._syncing:
            logger.warning("Sync already in progress, skipping")
            return (0, 0)

        if not self.sync_queue.is_connected():
            logger.error("Not connected to sync queue")
            return (0, 0)

        self._syncing = True
        try:
            # Push first (send local changes before pulling remote)
            sent_count = await self._push_pending_operations()

            # Then pull and apply remote changes
            received_count = await self._pull_remote_operations()

            self.last_sync_time = datetime.now()
            logger.info(f"Sync complete: {sent_count} sent, {received_count} received")
            return (sent_count, received_count)
        finally:
            self._syncing = False

    async def _push_pending_operations(self) -> int:
        """
        Send all pending operations to SQS.

        Returns:
            Number of operations sent
        """
        pending = await self.pending_queue.get_all()

        if not pending:
            logger.debug("No pending operations to send")
            return 0

        sent_count = 0
        sent_ids = []
        failed_operations = []

        for op in pending:
            success = self.sync_queue.send_operation(
                operation=op['operation'],
                list_id=op['list_id'],
                data=op['data']
            )

            if success:
                sent_count += 1
                sent_ids.append(op['id'])
            else:
                failed_operations.append(op['id'])
                logger.error(f"Failed to send operation: {op['operation']}")

        # Clear only successfully sent operations
        if sent_ids:
            await self.pending_queue.remove_by_ids(sent_ids)
            logger.info(f"Sent {sent_count} operations to sync queue")

        if failed_operations:
            logger.warning(f"{len(failed_operations)} operations failed, will retry later")

        return sent_count

    async def _pull_remote_operations(self) -> int:
        """
        Pull all waiting messages from SQS and apply them.

        Returns:
            Number of operations received and applied
        """
        received_count = 0
        max_iterations = 10  # Prevent infinite loop

        for _ in range(max_iterations):
            messages = self._receive_messages()

            if not messages:
                break  # No more messages

            for message in messages:
                if await self._process_message(message):
                    received_count += 1

            # Continue pulling if we got max batch (might be more)
            if len(messages) < 10:
                break  # Got fewer than max, no more messages

        return received_count

    def _receive_messages(self) -> List[Dict]:
        """
        Receive batch of messages from SQS.

        Returns:
            List of messages
        """
        try:
            response = self.sync_queue.sqs_client.receive_message(
                QueueUrl=self.sync_queue.config.queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=2,  # Short wait
                MessageAttributeNames=['All']
            )
            return response.get('Messages', [])
        except Exception as e:
            logger.error(f"Failed to receive messages: {e}")
            return []

    async def _process_message(self, message: Dict) -> bool:
        """
        Process and apply a single message.

        Returns:
            True if successfully processed
        """
        try:
            # Decrypt message
            encrypted_body = message['Body']
            decrypted_data = self.sync_queue.encryption.decrypt_message(encrypted_body)

            # Check if it's our own message (skip to avoid circular updates)
            if decrypted_data.get('client_id') == self.sync_queue.client_id:
                logger.debug(f"Skipping own message: {decrypted_data.get('operation')}")
            else:
                # Apply operation
                await self.operation_handler.handle_operation(decrypted_data)

            # Delete message from queue (mark as processed)
            self.sync_queue.sqs_client.delete_message(
                QueueUrl=self.sync_queue.config.queue_url,
                ReceiptHandle=message['ReceiptHandle']
            )

            return True
        except Exception as e:
            logger.error(f"Failed to process message: {e}", exc_info=True)
            return False

    async def get_pending_count(self) -> int:
        """Get number of operations waiting to be synced."""
        return await self.pending_queue.count()

    async def has_pending_operations(self) -> bool:
        """Check if there are pending operations."""
        return await self.pending_queue.has_pending()

    async def push_only(self) -> int:
        """
        Push pending operations without pulling.
        Useful for app shutdown.

        Returns:
            Number of operations sent
        """
        if not self.sync_queue.is_connected():
            logger.error("Not connected to sync queue")
            return 0

        return await self._push_pending_operations()
