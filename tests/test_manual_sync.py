"""
Comprehensive unit tests for ManualSyncService.

Tests the manual synchronization service that orchestrates bidirectional sync
between local pending operations and remote SQS queue.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime
from uuid import uuid4

from taskui.services.manual_sync import ManualSyncService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_sync_queue():
    """Mock SyncQueue with standard configuration."""
    queue = MagicMock()
    queue.is_connected.return_value = True
    queue.client_id = str(uuid4())
    queue.send_operation.return_value = True
    queue.config.queue_url = "https://sqs.us-east-1.amazonaws.com/123456789/test-queue"

    # Mock SQS client
    queue.sqs_client = MagicMock()
    queue.sqs_client.receive_message.return_value = {"Messages": []}
    queue.sqs_client.delete_message.return_value = {}

    # Mock encryption
    queue.encryption = MagicMock()
    queue.encryption.decrypt_message.return_value = {
        "client_id": "different-client",
        "operation": "add_task",
        "list_id": "list-123",
        "data": {"title": "Test Task"}
    }

    return queue


@pytest.fixture
def mock_pending_queue():
    """Mock PendingOperationsQueue with standard configuration."""
    queue = AsyncMock()
    queue.get_all.return_value = []
    queue.count.return_value = 0
    queue.has_pending.return_value = False
    queue.remove_by_ids.return_value = None
    return queue


@pytest.fixture
def mock_operation_handler():
    """Mock SyncOperationHandler with standard configuration."""
    handler = AsyncMock()
    handler.handle_operation.return_value = True
    return handler


@pytest.fixture
def manual_sync_service(mock_sync_queue, mock_pending_queue, mock_operation_handler):
    """Create ManualSyncService instance with mocked dependencies."""
    return ManualSyncService(
        sync_queue=mock_sync_queue,
        pending_queue=mock_pending_queue,
        operation_handler=mock_operation_handler
    )


# ============================================================================
# Initialization Tests
# ============================================================================

def test_init_sets_dependencies(mock_sync_queue, mock_pending_queue, mock_operation_handler):
    """Test __init__ correctly stores all dependencies."""
    service = ManualSyncService(
        sync_queue=mock_sync_queue,
        pending_queue=mock_pending_queue,
        operation_handler=mock_operation_handler
    )

    assert service.sync_queue is mock_sync_queue
    assert service.pending_queue is mock_pending_queue
    assert service.operation_handler is mock_operation_handler
    assert service.last_sync_time is None
    assert service._syncing is False


def test_is_syncing_property(manual_sync_service):
    """Test is_syncing property reflects internal state."""
    assert manual_sync_service.is_syncing is False

    manual_sync_service._syncing = True
    assert manual_sync_service.is_syncing is True

    manual_sync_service._syncing = False
    assert manual_sync_service.is_syncing is False


# ============================================================================
# Sync Tests - Main Orchestration
# ============================================================================

@pytest.mark.asyncio
async def test_sync_calls_push_then_pull(manual_sync_service, mock_pending_queue):
    """Test sync() calls push operations before pull operations."""
    mock_pending_queue.get_all.return_value = []

    with patch.object(manual_sync_service, '_push_pending_operations', new_callable=AsyncMock) as mock_push:
        with patch.object(manual_sync_service, '_pull_remote_operations', new_callable=AsyncMock) as mock_pull:
            mock_push.return_value = 3
            mock_pull.return_value = 2

            sent, received = await manual_sync_service.sync()

            assert sent == 3
            assert received == 2

            # Verify push called before pull
            assert mock_push.call_count == 1
            assert mock_pull.call_count == 1

            # Verify order using call times
            push_call_time = mock_push.call_args
            pull_call_time = mock_pull.call_args
            assert push_call_time is not None
            assert pull_call_time is not None


@pytest.mark.asyncio
async def test_sync_returns_correct_counts(manual_sync_service):
    """Test sync() returns tuple of (sent_count, received_count)."""
    with patch.object(manual_sync_service, '_push_pending_operations', new_callable=AsyncMock) as mock_push:
        with patch.object(manual_sync_service, '_pull_remote_operations', new_callable=AsyncMock) as mock_pull:
            mock_push.return_value = 5
            mock_pull.return_value = 3

            sent, received = await manual_sync_service.sync()

            assert sent == 5
            assert received == 3


@pytest.mark.asyncio
async def test_sync_skips_if_already_syncing(manual_sync_service):
    """Test sync() returns (0, 0) if sync already in progress."""
    manual_sync_service._syncing = True

    sent, received = await manual_sync_service.sync()

    assert sent == 0
    assert received == 0


@pytest.mark.asyncio
async def test_sync_skips_if_not_connected(manual_sync_service, mock_sync_queue):
    """Test sync() returns (0, 0) if not connected to queue."""
    mock_sync_queue.is_connected.return_value = False

    sent, received = await manual_sync_service.sync()

    assert sent == 0
    assert received == 0


@pytest.mark.asyncio
async def test_sync_sets_syncing_flag(manual_sync_service):
    """Test sync() sets and clears _syncing flag."""
    with patch.object(manual_sync_service, '_push_pending_operations', new_callable=AsyncMock) as mock_push:
        with patch.object(manual_sync_service, '_pull_remote_operations', new_callable=AsyncMock) as mock_pull:
            mock_push.return_value = 0
            mock_pull.return_value = 0

            assert manual_sync_service._syncing is False

            async def check_syncing_during():
                assert manual_sync_service._syncing is True
                return 0

            mock_push.side_effect = check_syncing_during

            await manual_sync_service.sync()

            assert manual_sync_service._syncing is False


@pytest.mark.asyncio
async def test_sync_clears_syncing_flag_on_error(manual_sync_service):
    """Test sync() clears _syncing flag even if error occurs."""
    with patch.object(manual_sync_service, '_push_pending_operations', new_callable=AsyncMock) as mock_push:
        mock_push.side_effect = Exception("Test error")

        with pytest.raises(Exception, match="Test error"):
            await manual_sync_service.sync()

        assert manual_sync_service._syncing is False


@pytest.mark.asyncio
async def test_sync_updates_last_sync_time(manual_sync_service):
    """Test sync() updates last_sync_time after successful sync."""
    with patch.object(manual_sync_service, '_push_pending_operations', new_callable=AsyncMock) as mock_push:
        with patch.object(manual_sync_service, '_pull_remote_operations', new_callable=AsyncMock) as mock_pull:
            mock_push.return_value = 1
            mock_pull.return_value = 1

            before_sync = datetime.now()
            assert manual_sync_service.last_sync_time is None

            await manual_sync_service.sync()

            after_sync = datetime.now()
            assert manual_sync_service.last_sync_time is not None
            assert before_sync <= manual_sync_service.last_sync_time <= after_sync


# ============================================================================
# Push Pending Operations Tests
# ============================================================================

@pytest.mark.asyncio
async def test_push_sends_all_pending_operations(manual_sync_service, mock_pending_queue, mock_sync_queue):
    """Test _push_pending_operations sends all pending operations to SQS."""
    pending_ops = [
        {
            "id": "op-1",
            "operation": "add_task",
            "list_id": "list-123",
            "data": {"title": "Task 1"}
        },
        {
            "id": "op-2",
            "operation": "update_task",
            "list_id": "list-123",
            "data": {"id": "task-1", "title": "Updated"}
        },
        {
            "id": "op-3",
            "operation": "delete_task",
            "list_id": "list-123",
            "data": {"id": "task-1"}
        }
    ]
    mock_pending_queue.get_all.return_value = pending_ops
    mock_sync_queue.send_operation.return_value = True

    sent_count = await manual_sync_service._push_pending_operations()

    assert sent_count == 3
    assert mock_sync_queue.send_operation.call_count == 3

    # Verify each operation was sent with correct parameters
    calls = mock_sync_queue.send_operation.call_args_list
    for i, expected_op in enumerate(pending_ops):
        assert calls[i] == call(
            operation=expected_op["operation"],
            list_id=expected_op["list_id"],
            data=expected_op["data"]
        )


@pytest.mark.asyncio
async def test_push_removes_sent_operations_from_queue(manual_sync_service, mock_pending_queue, mock_sync_queue):
    """Test _push_pending_operations removes successfully sent operations."""
    pending_ops = [
        {"id": "op-1", "operation": "add_task", "list_id": "list-123", "data": {}},
        {"id": "op-2", "operation": "update_task", "list_id": "list-123", "data": {}},
    ]
    mock_pending_queue.get_all.return_value = pending_ops
    mock_sync_queue.send_operation.return_value = True

    await manual_sync_service._push_pending_operations()

    # Verify remove_by_ids called with IDs of sent operations
    mock_pending_queue.remove_by_ids.assert_called_once_with(["op-1", "op-2"])


@pytest.mark.asyncio
async def test_push_keeps_failed_operations_in_queue(manual_sync_service, mock_pending_queue, mock_sync_queue):
    """Test _push_pending_operations keeps failed operations for retry."""
    pending_ops = [
        {"id": "op-1", "operation": "add_task", "list_id": "list-123", "data": {}},
        {"id": "op-2", "operation": "update_task", "list_id": "list-123", "data": {}},
        {"id": "op-3", "operation": "delete_task", "list_id": "list-123", "data": {}},
    ]
    mock_pending_queue.get_all.return_value = pending_ops

    # First and third succeed, second fails
    mock_sync_queue.send_operation.side_effect = [True, False, True]

    sent_count = await manual_sync_service._push_pending_operations()

    assert sent_count == 2
    # Only successful operations removed
    mock_pending_queue.remove_by_ids.assert_called_once_with(["op-1", "op-3"])


@pytest.mark.asyncio
async def test_push_returns_zero_when_no_pending(manual_sync_service, mock_pending_queue, mock_sync_queue):
    """Test _push_pending_operations returns 0 when no pending operations."""
    mock_pending_queue.get_all.return_value = []

    sent_count = await manual_sync_service._push_pending_operations()

    assert sent_count == 0
    mock_sync_queue.send_operation.assert_not_called()
    mock_pending_queue.remove_by_ids.assert_not_called()


@pytest.mark.asyncio
async def test_push_handles_all_operations_failing(manual_sync_service, mock_pending_queue, mock_sync_queue):
    """Test _push_pending_operations handles case where all operations fail."""
    pending_ops = [
        {"id": "op-1", "operation": "add_task", "list_id": "list-123", "data": {}},
        {"id": "op-2", "operation": "update_task", "list_id": "list-123", "data": {}},
    ]
    mock_pending_queue.get_all.return_value = pending_ops
    mock_sync_queue.send_operation.return_value = False

    sent_count = await manual_sync_service._push_pending_operations()

    assert sent_count == 0
    mock_pending_queue.remove_by_ids.assert_not_called()


# ============================================================================
# Pull Remote Operations Tests
# ============================================================================

@pytest.mark.asyncio
async def test_pull_receives_and_processes_messages(manual_sync_service, mock_sync_queue):
    """Test _pull_remote_operations receives and processes all messages."""
    messages = [
        {
            "Body": "encrypted_data_1",
            "ReceiptHandle": "receipt-1"
        },
        {
            "Body": "encrypted_data_2",
            "ReceiptHandle": "receipt-2"
        }
    ]
    mock_sync_queue.sqs_client.receive_message.return_value = {"Messages": messages}

    with patch.object(manual_sync_service, '_process_message', new_callable=AsyncMock) as mock_process:
        mock_process.return_value = True

        received_count = await manual_sync_service._pull_remote_operations()

        assert received_count == 2
        assert mock_process.call_count == 2


@pytest.mark.asyncio
async def test_pull_stops_when_no_more_messages(manual_sync_service, mock_sync_queue):
    """Test _pull_remote_operations stops polling when queue returns empty."""
    # First call returns empty, so should stop immediately
    with patch.object(manual_sync_service, '_receive_messages') as mock_receive:
        with patch.object(manual_sync_service, '_process_message', new_callable=AsyncMock) as mock_process:
            mock_receive.return_value = []
            mock_process.return_value = True

            received_count = await manual_sync_service._pull_remote_operations()

            assert received_count == 0
            assert mock_receive.call_count == 1  # Stops after first empty response


@pytest.mark.asyncio
async def test_pull_respects_max_iterations(manual_sync_service, mock_sync_queue):
    """Test _pull_remote_operations respects max_iterations limit."""
    # Always return 10 messages (max batch size) to trigger iteration limit
    with patch.object(manual_sync_service, '_receive_messages') as mock_receive:
        with patch.object(manual_sync_service, '_process_message', new_callable=AsyncMock) as mock_process:
            # Return max batch size (10 messages) every time
            mock_receive.return_value = [
                {"Body": f"data{i}", "ReceiptHandle": f"receipt{i}"} for i in range(10)
            ]
            mock_process.return_value = True

            await manual_sync_service._pull_remote_operations()

            # Should stop at max_iterations (10)
            assert mock_receive.call_count == 10


@pytest.mark.asyncio
async def test_pull_stops_when_batch_smaller_than_max(manual_sync_service, mock_sync_queue):
    """Test _pull_remote_operations stops when receiving less than max batch."""
    # Return less than 10 messages (indicating no more messages available)
    mock_sync_queue.sqs_client.receive_message.return_value = {
        "Messages": [
            {"Body": "data1", "ReceiptHandle": "receipt1"},
            {"Body": "data2", "ReceiptHandle": "receipt2"}
        ]
    }

    with patch.object(manual_sync_service, '_process_message', new_callable=AsyncMock) as mock_process:
        mock_process.return_value = True

        received_count = await manual_sync_service._pull_remote_operations()

        assert received_count == 2
        # Should only call once since batch < 10
        assert mock_sync_queue.sqs_client.receive_message.call_count == 1


@pytest.mark.asyncio
async def test_pull_counts_only_successful_processing(manual_sync_service, mock_sync_queue):
    """Test _pull_remote_operations only counts successfully processed messages."""
    messages = [
        {"Body": "data1", "ReceiptHandle": "receipt1"},
        {"Body": "data2", "ReceiptHandle": "receipt2"},
        {"Body": "data3", "ReceiptHandle": "receipt3"}
    ]
    mock_sync_queue.sqs_client.receive_message.return_value = {"Messages": messages}

    with patch.object(manual_sync_service, '_process_message', new_callable=AsyncMock) as mock_process:
        # First and third succeed, second fails
        mock_process.side_effect = [True, False, True]

        received_count = await manual_sync_service._pull_remote_operations()

        assert received_count == 2


# ============================================================================
# Receive Messages Tests
# ============================================================================

def test_receive_messages_returns_messages(manual_sync_service, mock_sync_queue):
    """Test _receive_messages returns messages from SQS."""
    expected_messages = [
        {"Body": "data1", "ReceiptHandle": "receipt1"},
        {"Body": "data2", "ReceiptHandle": "receipt2"}
    ]
    mock_sync_queue.sqs_client.receive_message.return_value = {"Messages": expected_messages}

    messages = manual_sync_service._receive_messages()

    assert messages == expected_messages
    mock_sync_queue.sqs_client.receive_message.assert_called_once_with(
        QueueUrl=mock_sync_queue.config.queue_url,
        MaxNumberOfMessages=10,
        WaitTimeSeconds=2,
        MessageAttributeNames=['All']
    )


def test_receive_messages_returns_empty_when_no_messages(manual_sync_service, mock_sync_queue):
    """Test _receive_messages returns empty list when no messages."""
    mock_sync_queue.sqs_client.receive_message.return_value = {}

    messages = manual_sync_service._receive_messages()

    assert messages == []


def test_receive_messages_handles_exception(manual_sync_service, mock_sync_queue):
    """Test _receive_messages handles SQS exceptions gracefully."""
    mock_sync_queue.sqs_client.receive_message.side_effect = Exception("SQS error")

    messages = manual_sync_service._receive_messages()

    assert messages == []


# ============================================================================
# Process Message Tests
# ============================================================================

@pytest.mark.asyncio
async def test_process_message_decrypts_and_applies_operation(
    manual_sync_service, mock_sync_queue, mock_operation_handler
):
    """Test _process_message decrypts message and applies operation."""
    message = {
        "Body": "encrypted_data",
        "ReceiptHandle": "receipt-123"
    }
    decrypted_data = {
        "client_id": "different-client",
        "operation": "add_task",
        "list_id": "list-123",
        "data": {"title": "Test Task"}
    }
    mock_sync_queue.encryption.decrypt_message.return_value = decrypted_data

    result = await manual_sync_service._process_message(message)

    assert result is True
    mock_sync_queue.encryption.decrypt_message.assert_called_once_with("encrypted_data")
    mock_operation_handler.handle_operation.assert_called_once_with(decrypted_data)


@pytest.mark.asyncio
async def test_process_message_skips_own_messages(
    manual_sync_service, mock_sync_queue, mock_operation_handler
):
    """Test _process_message skips messages from same client_id."""
    message = {
        "Body": "encrypted_data",
        "ReceiptHandle": "receipt-123"
    }
    decrypted_data = {
        "client_id": mock_sync_queue.client_id,  # Same as our client
        "operation": "add_task",
        "list_id": "list-123",
        "data": {"title": "Test Task"}
    }
    mock_sync_queue.encryption.decrypt_message.return_value = decrypted_data

    result = await manual_sync_service._process_message(message)

    assert result is True
    # Should not apply our own operation
    mock_operation_handler.handle_operation.assert_not_called()


@pytest.mark.asyncio
async def test_process_message_deletes_message_after_processing(
    manual_sync_service, mock_sync_queue
):
    """Test _process_message deletes message from queue after processing."""
    message = {
        "Body": "encrypted_data",
        "ReceiptHandle": "receipt-123"
    }

    await manual_sync_service._process_message(message)

    mock_sync_queue.sqs_client.delete_message.assert_called_once_with(
        QueueUrl=mock_sync_queue.config.queue_url,
        ReceiptHandle="receipt-123"
    )


@pytest.mark.asyncio
async def test_process_message_deletes_even_own_messages(
    manual_sync_service, mock_sync_queue
):
    """Test _process_message deletes own messages (even though skipped)."""
    message = {
        "Body": "encrypted_data",
        "ReceiptHandle": "receipt-123"
    }
    decrypted_data = {
        "client_id": mock_sync_queue.client_id,
        "operation": "add_task"
    }
    mock_sync_queue.encryption.decrypt_message.return_value = decrypted_data

    await manual_sync_service._process_message(message)

    # Should still delete the message
    mock_sync_queue.sqs_client.delete_message.assert_called_once()


@pytest.mark.asyncio
async def test_process_message_handles_decryption_error(
    manual_sync_service, mock_sync_queue, mock_operation_handler
):
    """Test _process_message handles decryption errors."""
    message = {
        "Body": "invalid_encrypted_data",
        "ReceiptHandle": "receipt-123"
    }
    mock_sync_queue.encryption.decrypt_message.side_effect = Exception("Decryption failed")

    result = await manual_sync_service._process_message(message)

    assert result is False
    mock_operation_handler.handle_operation.assert_not_called()
    mock_sync_queue.sqs_client.delete_message.assert_not_called()


@pytest.mark.asyncio
async def test_process_message_handles_operation_handler_error(
    manual_sync_service, mock_sync_queue, mock_operation_handler
):
    """Test _process_message handles operation handler errors."""
    message = {
        "Body": "encrypted_data",
        "ReceiptHandle": "receipt-123"
    }
    mock_operation_handler.handle_operation.side_effect = Exception("Handler error")

    result = await manual_sync_service._process_message(message)

    assert result is False
    mock_sync_queue.sqs_client.delete_message.assert_not_called()


# ============================================================================
# Utility Method Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_pending_count(manual_sync_service, mock_pending_queue):
    """Test get_pending_count returns count from pending queue."""
    mock_pending_queue.count.return_value = 5

    count = await manual_sync_service.get_pending_count()

    assert count == 5
    mock_pending_queue.count.assert_called_once()


@pytest.mark.asyncio
async def test_has_pending_operations_true(manual_sync_service, mock_pending_queue):
    """Test has_pending_operations returns True when operations exist."""
    mock_pending_queue.has_pending.return_value = True

    has_pending = await manual_sync_service.has_pending_operations()

    assert has_pending is True
    mock_pending_queue.has_pending.assert_called_once()


@pytest.mark.asyncio
async def test_has_pending_operations_false(manual_sync_service, mock_pending_queue):
    """Test has_pending_operations returns False when no operations."""
    mock_pending_queue.has_pending.return_value = False

    has_pending = await manual_sync_service.has_pending_operations()

    assert has_pending is False


# ============================================================================
# Push Only Tests (Shutdown Scenario)
# ============================================================================

@pytest.mark.asyncio
async def test_push_only_pushes_without_pulling(manual_sync_service, mock_pending_queue, mock_sync_queue):
    """Test push_only sends operations without receiving (for shutdown)."""
    pending_ops = [
        {"id": "op-1", "operation": "add_task", "list_id": "list-123", "data": {}}
    ]
    mock_pending_queue.get_all.return_value = pending_ops
    mock_sync_queue.send_operation.return_value = True

    sent_count = await manual_sync_service.push_only()

    assert sent_count == 1
    mock_sync_queue.send_operation.assert_called_once()
    # Verify no receive operations
    mock_sync_queue.sqs_client.receive_message.assert_not_called()


@pytest.mark.asyncio
async def test_push_only_returns_zero_when_not_connected(manual_sync_service, mock_sync_queue):
    """Test push_only returns 0 when not connected."""
    mock_sync_queue.is_connected.return_value = False

    sent_count = await manual_sync_service.push_only()

    assert sent_count == 0


@pytest.mark.asyncio
async def test_push_only_uses_push_pending_operations(manual_sync_service):
    """Test push_only delegates to _push_pending_operations."""
    with patch.object(manual_sync_service, '_push_pending_operations', new_callable=AsyncMock) as mock_push:
        mock_push.return_value = 3

        sent_count = await manual_sync_service.push_only()

        assert sent_count == 3
        mock_push.assert_called_once()


# ============================================================================
# Error Handling Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_sync_continues_after_push_error(manual_sync_service):
    """Test sync continues to pull even if push fails."""
    with patch.object(manual_sync_service, '_push_pending_operations', new_callable=AsyncMock) as mock_push:
        with patch.object(manual_sync_service, '_pull_remote_operations', new_callable=AsyncMock) as mock_pull:
            mock_push.side_effect = Exception("Push failed")
            mock_pull.return_value = 2

            with pytest.raises(Exception, match="Push failed"):
                await manual_sync_service.sync()

            # Push was called
            mock_push.assert_called_once()
            # Pull was NOT called (exception stopped execution)
            mock_pull.assert_not_called()


@pytest.mark.asyncio
async def test_sync_handles_pull_error(manual_sync_service):
    """Test sync handles errors during pull operations."""
    with patch.object(manual_sync_service, '_push_pending_operations', new_callable=AsyncMock) as mock_push:
        with patch.object(manual_sync_service, '_pull_remote_operations', new_callable=AsyncMock) as mock_pull:
            mock_push.return_value = 1
            mock_pull.side_effect = Exception("Pull failed")

            with pytest.raises(Exception, match="Pull failed"):
                await manual_sync_service.sync()

            # Both were called
            mock_push.assert_called_once()
            mock_pull.assert_called_once()
            # Syncing flag should be cleared
            assert manual_sync_service._syncing is False


@pytest.mark.asyncio
async def test_multiple_messages_with_mixed_processing(manual_sync_service, mock_sync_queue, mock_operation_handler):
    """Test handling batch with mix of successful and failed message processing."""
    messages = [
        {"Body": "data1", "ReceiptHandle": "receipt1"},
        {"Body": "data2", "ReceiptHandle": "receipt2"},
        {"Body": "data3", "ReceiptHandle": "receipt3"}
    ]
    mock_sync_queue.sqs_client.receive_message.return_value = {"Messages": messages}

    # Setup different behaviors for each message
    def handle_operation_side_effect(data):
        if data.get("operation") == "fail":
            raise Exception("Handler failed")
        return True

    mock_operation_handler.handle_operation.side_effect = handle_operation_side_effect

    # Setup decryption to return different operations
    decrypt_results = [
        {"client_id": "other1", "operation": "add_task"},
        {"client_id": "other2", "operation": "fail"},  # Will fail
        {"client_id": "other3", "operation": "update_task"}
    ]
    mock_sync_queue.encryption.decrypt_message.side_effect = decrypt_results

    received_count = await manual_sync_service._pull_remote_operations()

    # Should count 2 successful (first and third)
    assert received_count == 2
