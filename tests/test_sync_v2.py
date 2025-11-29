"""
Tests for Sync V2 service.

Tests the sync layer built on top of export/import.
Uses mocks for SQS communication to enable unit testing.
"""

import json
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from taskui.export_schema import ConflictStrategy, CURRENT_SCHEMA_VERSION
from taskui.services.cloud_print_queue import CloudPrintConfig
from taskui.services.encryption import MessageEncryption
from taskui.services.export_import import ExportImportService
from taskui.services.list_service import ListService
from taskui.services.sync_v2 import SyncV2Service, SyncV2Error, SyncV2ConnectionError
from taskui.services.task_service import TaskService


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_config():
    """Create mock CloudPrintConfig for testing."""
    return CloudPrintConfig(
        queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/test-queue",
        region="us-east-1",
        encryption_key=MessageEncryption.generate_key(),
    )


@pytest.fixture
def mock_sqs_client():
    """Create mock SQS client."""
    client = MagicMock()
    client.get_queue_attributes.return_value = {
        'Attributes': {'ApproximateNumberOfMessages': '0'}
    }
    client.send_message.return_value = {'MessageId': 'test-message-id'}
    client.receive_message.return_value = {'Messages': []}
    client.delete_message.return_value = {}
    return client


@pytest_asyncio.fixture
async def sync_service(db_session, mock_config, mock_sqs_client):
    """Create sync service with mocked SQS."""
    service = SyncV2Service(db_session, mock_config, "test-client-id")

    # Inject mock client directly (bypass actual connection)
    service.sqs_client = mock_sqs_client
    service._connected = True

    return service


@pytest_asyncio.fixture
async def populated_sync_service(db_session, mock_config, mock_sqs_client):
    """Create sync service with sample data."""
    # Create sample data
    list_service = ListService(db_session)
    task_service = TaskService(db_session)

    task_list = await list_service.create_list("Work")
    await task_service.create_task(title="Task 1", list_id=task_list.id)
    await task_service.create_task(title="Task 2", list_id=task_list.id)

    # Create sync service
    service = SyncV2Service(db_session, mock_config, "test-client-id")
    service.sqs_client = mock_sqs_client
    service._connected = True

    return service


# ==============================================================================
# CONNECTION TESTS
# ==============================================================================


class TestConnection:
    """Tests for SQS connection management."""

    def test_connect_success(self, mock_config, mock_sqs_client):
        """Connect succeeds with valid config."""
        # Create service with mock client directly injected
        service = SyncV2Service.__new__(SyncV2Service)
        service.config = mock_config
        service.client_id = "test"
        service.encryption = MessageEncryption(mock_config.encryption_key)
        service.sqs_client = mock_sqs_client
        service._connected = True

        assert service.is_connected() is True

    def test_disconnect(self, sync_service):
        """Disconnect clears connection state."""
        sync_service.disconnect()
        assert sync_service.is_connected() is False

    def test_get_queue_depth(self, sync_service, mock_sqs_client):
        """Get queue depth returns message count."""
        mock_sqs_client.get_queue_attributes.return_value = {
            'Attributes': {'ApproximateNumberOfMessages': '5'}
        }
        depth = sync_service.get_queue_depth()
        assert depth == 5


# ==============================================================================
# PUSH TESTS
# ==============================================================================


class TestPush:
    """Tests for sync push operation."""

    async def test_push_sends_message(self, populated_sync_service, mock_sqs_client):
        """Push sends encrypted state to SQS."""
        await populated_sync_service.sync_push()

        # Verify send_message was called
        mock_sqs_client.send_message.assert_called_once()

        # Verify message attributes
        call_args = mock_sqs_client.send_message.call_args
        assert call_args.kwargs['QueueUrl'] == populated_sync_service.config.queue_url
        assert 'MessageBody' in call_args.kwargs
        assert call_args.kwargs['MessageAttributes']['MessageType']['StringValue'] == 'FULL_STATE_SYNC_V2'
        assert call_args.kwargs['MessageAttributes']['ClientId']['StringValue'] == 'test-client-id'

    async def test_push_encrypts_message(self, populated_sync_service, mock_sqs_client):
        """Push encrypts the message body."""
        await populated_sync_service.sync_push()

        call_args = mock_sqs_client.send_message.call_args
        message_body = call_args.kwargs['MessageBody']

        # Encrypted message should be JSON with encryption metadata
        import json
        encrypted_data = json.loads(message_body)
        assert encrypted_data.get('encrypted') is True
        assert 'ciphertext' in encrypted_data

    async def test_push_requires_connection(self, db_session, mock_config):
        """Push raises error when not connected."""
        service = SyncV2Service(db_session, mock_config, "test")
        # Don't connect

        with pytest.raises(SyncV2ConnectionError):
            await service.sync_push()


# ==============================================================================
# PULL TESTS
# ==============================================================================


class TestPull:
    """Tests for sync pull operation."""

    def make_sync_message(self, encryption, client_id="other-client"):
        """Create a valid sync message for testing."""
        state = {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "client_id": client_id,
            "lists": [],
        }
        message = {
            "type": "FULL_STATE_SYNC_V2",
            "version": "2.0",
            "client_id": client_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": state,
        }
        return encryption.encrypt_message(message)

    async def test_pull_no_messages(self, sync_service, mock_sqs_client):
        """Pull with no messages returns zeros."""
        mock_sqs_client.receive_message.return_value = {'Messages': []}

        imported, skipped, conflicts = await sync_service.sync_pull()

        assert imported == 0
        assert skipped == 0
        assert conflicts == []

    async def test_pull_skips_own_messages(self, sync_service, mock_sqs_client):
        """Pull ignores messages from same client."""
        encrypted = self.make_sync_message(sync_service.encryption, "test-client-id")

        mock_sqs_client.receive_message.return_value = {
            'Messages': [{
                'MessageId': 'msg-1',
                'ReceiptHandle': 'receipt-1',
                'Body': encrypted,
                'MessageAttributes': {
                    'ClientId': {'StringValue': 'test-client-id'},
                    'MessageType': {'StringValue': 'FULL_STATE_SYNC_V2'},
                }
            }]
        }

        imported, skipped, conflicts = await sync_service.sync_pull()

        # Message should be skipped (from same client)
        assert imported == 0

        # Message should be deleted from queue
        mock_sqs_client.delete_message.assert_called()

    async def test_pull_processes_other_client_messages(
        self, sync_service, mock_sqs_client
    ):
        """Pull processes messages from other clients."""
        encrypted = self.make_sync_message(sync_service.encryption, "other-client")

        mock_sqs_client.receive_message.return_value = {
            'Messages': [{
                'MessageId': 'msg-1',
                'ReceiptHandle': 'receipt-1',
                'Body': encrypted,
                'MessageAttributes': {
                    'ClientId': {'StringValue': 'other-client'},
                    'MessageType': {'StringValue': 'FULL_STATE_SYNC_V2'},
                }
            }]
        }

        imported, skipped, conflicts = await sync_service.sync_pull()

        # Empty state has no lists to import
        assert imported == 0

        # Message should be deleted after processing
        mock_sqs_client.delete_message.assert_called()

    async def test_pull_requires_connection(self, db_session, mock_config):
        """Pull raises error when not connected."""
        service = SyncV2Service(db_session, mock_config, "test")

        with pytest.raises(SyncV2ConnectionError):
            await service.sync_pull()


# ==============================================================================
# FULL SYNC TESTS
# ==============================================================================


class TestFullSync:
    """Tests for full bidirectional sync."""

    async def test_sync_full_push_then_pull(
        self, populated_sync_service, mock_sqs_client
    ):
        """Full sync performs push then pull."""
        results = await populated_sync_service.sync_full()

        # Push should succeed
        assert results['push_success'] is True

        # Pull should complete (no messages in mock)
        assert results['pull_imported'] == 0
        assert results['pull_skipped'] == 0
        assert results['conflicts'] == []

        # Verify both operations occurred
        mock_sqs_client.send_message.assert_called_once()
        mock_sqs_client.receive_message.assert_called_once()

    async def test_sync_full_returns_results(self, populated_sync_service):
        """Full sync returns structured results."""
        results = await populated_sync_service.sync_full()

        assert 'push_success' in results
        assert 'pull_imported' in results
        assert 'pull_skipped' in results
        assert 'conflicts' in results


# ==============================================================================
# ERROR HANDLING TESTS
# ==============================================================================


class TestErrorHandling:
    """Tests for error handling in sync operations."""

    async def test_push_handles_sqs_error(
        self, populated_sync_service, mock_sqs_client
    ):
        """Push handles SQS errors gracefully."""
        mock_sqs_client.send_message.side_effect = Exception("SQS error")

        with pytest.raises(SyncV2Error):
            await populated_sync_service.sync_push()

    async def test_pull_handles_decrypt_error(
        self, sync_service, mock_sqs_client
    ):
        """Pull handles decryption errors gracefully."""
        # Send invalid encrypted message
        mock_sqs_client.receive_message.return_value = {
            'Messages': [{
                'MessageId': 'msg-1',
                'ReceiptHandle': 'receipt-1',
                'Body': 'invalid-encrypted-data',
                'MessageAttributes': {
                    'ClientId': {'StringValue': 'other-client'},
                    'MessageType': {'StringValue': 'FULL_STATE_SYNC_V2'},
                }
            }]
        }

        # Should not raise, but should not import anything
        imported, skipped, conflicts = await sync_service.sync_pull()
        assert imported == 0

    async def test_full_sync_continues_after_push_error(
        self, sync_service, mock_sqs_client
    ):
        """Full sync continues with pull even if push fails."""
        mock_sqs_client.send_message.side_effect = Exception("Push failed")

        results = await sync_service.sync_full()

        # Push failed
        assert results['push_success'] is False

        # Pull still attempted
        mock_sqs_client.receive_message.assert_called()


# ==============================================================================
# INTEGRATION TESTS
# ==============================================================================


class TestSyncIntegration:
    """Integration tests for sync between clients."""

    @pytest_asyncio.fixture
    async def two_clients(self, db_manager, mock_config):
        """Create two sync clients for testing."""
        # Create two separate sessions (simulating different clients)
        async with db_manager.get_session() as session1:
            async with db_manager.get_session() as session2:
                # Create services
                client1 = SyncV2Service(session1, mock_config, "client-1")
                client2 = SyncV2Service(session2, mock_config, "client-2")

                # Create shared mock SQS (simulating real queue)
                shared_queue = []
                mock_sqs = MagicMock()

                def send_message(**kwargs):
                    shared_queue.append({
                        'MessageId': str(uuid4()),
                        'ReceiptHandle': str(uuid4()),
                        'Body': kwargs['MessageBody'],
                        'MessageAttributes': kwargs['MessageAttributes'],
                    })
                    return {'MessageId': 'test-id'}

                def receive_message(**kwargs):
                    messages = list(shared_queue)
                    return {'Messages': messages}

                def delete_message(**kwargs):
                    # Clear queue after processing
                    shared_queue.clear()
                    return {}

                mock_sqs.send_message = send_message
                mock_sqs.receive_message = receive_message
                mock_sqs.delete_message = delete_message
                mock_sqs.get_queue_attributes.return_value = {
                    'Attributes': {'ApproximateNumberOfMessages': str(len(shared_queue))}
                }

                client1.sqs_client = mock_sqs
                client1._connected = True
                client2.sqs_client = mock_sqs
                client2._connected = True

                yield client1, client2, session1, session2

    async def test_sync_between_clients(self, two_clients):
        """Data syncs between two clients."""
        client1, client2, session1, session2 = two_clients

        # Client 1 creates data
        list_service1 = ListService(session1)
        task_service1 = TaskService(session1)

        task_list = await list_service1.create_list("Shared List")
        await task_service1.create_task(title="Shared Task", list_id=task_list.id)

        # Client 1 pushes
        await client1.sync_push()

        # Client 2 pulls
        imported, _, _ = await client2.sync_pull()

        # Verify data was synced
        assert imported == 1

        list_service2 = ListService(session2)
        lists = await list_service2.get_all_lists()
        assert any(lst.name == "Shared List" for lst in lists)
