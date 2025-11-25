"""
Unit tests for PendingOperationsQueue service.

Tests the pending operations queue for local sync storage,
including adding, retrieving, clearing, and removing operations.
"""

import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

from taskui.services.pending_operations import PendingOperationsQueue
from taskui.database import PendingSyncOperationORM


@pytest_asyncio.fixture
async def pending_queue(db_session):
    """
    Create a PendingOperationsQueue instance for testing.

    Args:
        db_session: Database session fixture

    Returns:
        PendingOperationsQueue instance
    """
    return PendingOperationsQueue(db_session)


@pytest_asyncio.fixture
async def pending_queue_with_callback(db_session):
    """
    Create a PendingOperationsQueue with mock callback for testing.

    Args:
        db_session: Database session fixture

    Returns:
        Tuple of (PendingOperationsQueue, MagicMock callback)
    """
    callback = MagicMock()
    queue = PendingOperationsQueue(db_session, on_change_callback=callback)
    return queue, callback


@pytest.mark.asyncio
async def test_add_operation(pending_queue, sample_list_id):
    """Test adding an operation to the queue saves it to the database."""
    list_id = str(sample_list_id)
    operation_data = {"task_id": str(uuid4()), "title": "Test Task"}

    await pending_queue.add("TASK_CREATE", list_id, operation_data)

    # Verify operation was saved
    operations = await pending_queue.get_all()
    assert len(operations) == 1
    assert operations[0]["operation"] == "TASK_CREATE"
    assert operations[0]["list_id"] == list_id
    assert operations[0]["data"]["task_id"] == operation_data["task_id"]
    assert operations[0]["data"]["title"] == operation_data["title"]


@pytest.mark.asyncio
async def test_add_multiple_operations(pending_queue, sample_list_id):
    """Test adding multiple operations maintains correct order."""
    list_id = str(sample_list_id)

    # Add operations with small time gaps
    await pending_queue.add("TASK_CREATE", list_id, {"task_id": "1"})
    await pending_queue.add("TASK_UPDATE", list_id, {"task_id": "2"})
    await pending_queue.add("TASK_DELETE", list_id, {"task_id": "3"})

    # Verify all operations saved in order
    operations = await pending_queue.get_all()
    assert len(operations) == 3
    assert operations[0]["operation"] == "TASK_CREATE"
    assert operations[0]["data"]["task_id"] == "1"
    assert operations[1]["operation"] == "TASK_UPDATE"
    assert operations[1]["data"]["task_id"] == "2"
    assert operations[2]["operation"] == "TASK_DELETE"
    assert operations[2]["data"]["task_id"] == "3"


@pytest.mark.asyncio
async def test_add_operation_calls_callback(pending_queue_with_callback, sample_list_id):
    """Test adding an operation triggers on_change_callback with updated count."""
    queue, callback = pending_queue_with_callback
    list_id = str(sample_list_id)

    await queue.add("TASK_CREATE", list_id, {"task_id": "1"})

    # Verify callback was called with count of 1
    callback.assert_called_once_with(1)

    # Add another operation
    await queue.add("TASK_UPDATE", list_id, {"task_id": "2"})

    # Verify callback called again with count of 2
    assert callback.call_count == 2
    callback.assert_called_with(2)


@pytest.mark.asyncio
async def test_get_all_empty_queue(pending_queue):
    """Test get_all returns empty list when queue is empty."""
    operations = await pending_queue.get_all()
    assert operations == []


@pytest.mark.asyncio
async def test_get_all_ordered_by_created_at(pending_queue, sample_list_id):
    """Test get_all returns operations ordered by created_at (oldest first)."""
    list_id = str(sample_list_id)

    # Add operations
    await pending_queue.add("TASK_CREATE", list_id, {"order": 1})
    await pending_queue.add("TASK_UPDATE", list_id, {"order": 2})
    await pending_queue.add("TASK_DELETE", list_id, {"order": 3})

    operations = await pending_queue.get_all()

    # Verify order matches insertion order (created_at ascending)
    assert len(operations) == 3
    assert operations[0]["data"]["order"] == 1
    assert operations[1]["data"]["order"] == 2
    assert operations[2]["data"]["order"] == 3


@pytest.mark.asyncio
async def test_clear_all_removes_all_operations(pending_queue, sample_list_id):
    """Test clear_all removes all operations from the database."""
    list_id = str(sample_list_id)

    # Add multiple operations
    await pending_queue.add("TASK_CREATE", list_id, {"task_id": "1"})
    await pending_queue.add("TASK_UPDATE", list_id, {"task_id": "2"})
    await pending_queue.add("TASK_DELETE", list_id, {"task_id": "3"})

    # Verify operations exist
    count_before = await pending_queue.count()
    assert count_before == 3

    # Clear all operations
    cleared_count = await pending_queue.clear_all()

    # Verify all removed
    assert cleared_count == 3
    count_after = await pending_queue.count()
    assert count_after == 0
    operations = await pending_queue.get_all()
    assert operations == []


@pytest.mark.asyncio
async def test_clear_all_calls_callback_with_zero(pending_queue_with_callback, sample_list_id):
    """Test clear_all triggers on_change_callback with 0."""
    queue, callback = pending_queue_with_callback
    list_id = str(sample_list_id)

    # Add operations
    await queue.add("TASK_CREATE", list_id, {"task_id": "1"})
    await queue.add("TASK_UPDATE", list_id, {"task_id": "2"})

    # Reset callback to focus on clear_all call
    callback.reset_mock()

    # Clear all
    await queue.clear_all()

    # Verify callback called with 0
    callback.assert_called_once_with(0)


@pytest.mark.asyncio
async def test_clear_all_empty_queue_returns_zero(pending_queue):
    """Test clear_all on empty queue returns 0."""
    cleared_count = await pending_queue.clear_all()
    assert cleared_count == 0


@pytest.mark.asyncio
async def test_count_empty_queue(pending_queue):
    """Test count returns 0 for empty queue."""
    count = await pending_queue.count()
    assert count == 0


@pytest.mark.asyncio
async def test_count_with_operations(pending_queue, sample_list_id):
    """Test count returns correct number of operations."""
    list_id = str(sample_list_id)

    # Initially 0
    assert await pending_queue.count() == 0

    # Add operations one by one and verify count
    await pending_queue.add("TASK_CREATE", list_id, {"task_id": "1"})
    assert await pending_queue.count() == 1

    await pending_queue.add("TASK_UPDATE", list_id, {"task_id": "2"})
    assert await pending_queue.count() == 2

    await pending_queue.add("TASK_DELETE", list_id, {"task_id": "3"})
    assert await pending_queue.count() == 3


@pytest.mark.asyncio
async def test_has_pending_empty_queue(pending_queue):
    """Test has_pending returns False for empty queue."""
    has_pending = await pending_queue.has_pending()
    assert has_pending is False


@pytest.mark.asyncio
async def test_has_pending_with_operations(pending_queue, sample_list_id):
    """Test has_pending returns True when operations exist."""
    list_id = str(sample_list_id)

    # Add an operation
    await pending_queue.add("TASK_CREATE", list_id, {"task_id": "1"})

    # Verify has_pending is True
    has_pending = await pending_queue.has_pending()
    assert has_pending is True


@pytest.mark.asyncio
async def test_has_pending_after_clear(pending_queue, sample_list_id):
    """Test has_pending returns False after clearing queue."""
    list_id = str(sample_list_id)

    # Add and verify
    await pending_queue.add("TASK_CREATE", list_id, {"task_id": "1"})
    assert await pending_queue.has_pending() is True

    # Clear and verify
    await pending_queue.clear_all()
    assert await pending_queue.has_pending() is False


@pytest.mark.asyncio
async def test_remove_by_ids_removes_specific_operations(pending_queue, sample_list_id):
    """Test remove_by_ids removes only specified operations."""
    list_id = str(sample_list_id)

    # Add operations
    await pending_queue.add("TASK_CREATE", list_id, {"task_id": "1"})
    await pending_queue.add("TASK_UPDATE", list_id, {"task_id": "2"})
    await pending_queue.add("TASK_DELETE", list_id, {"task_id": "3"})

    # Get operation IDs
    operations = await pending_queue.get_all()
    assert len(operations) == 3

    # Remove first and third operations
    ids_to_remove = [operations[0]["id"], operations[2]["id"]]
    removed_count = await pending_queue.remove_by_ids(ids_to_remove)

    # Verify removal
    assert removed_count == 2
    remaining = await pending_queue.get_all()
    assert len(remaining) == 1
    assert remaining[0]["data"]["task_id"] == "2"
    assert remaining[0]["operation"] == "TASK_UPDATE"


@pytest.mark.asyncio
async def test_remove_by_ids_empty_list_returns_zero(pending_queue):
    """Test remove_by_ids with empty list returns 0."""
    removed_count = await pending_queue.remove_by_ids([])
    assert removed_count == 0


@pytest.mark.asyncio
async def test_remove_by_ids_nonexistent_ids_returns_zero(pending_queue, sample_list_id):
    """Test remove_by_ids with nonexistent IDs returns 0."""
    list_id = str(sample_list_id)

    # Add an operation
    await pending_queue.add("TASK_CREATE", list_id, {"task_id": "1"})

    # Try to remove with nonexistent IDs
    removed_count = await pending_queue.remove_by_ids([9999, 8888])
    assert removed_count == 0

    # Verify original operation still exists
    assert await pending_queue.count() == 1


@pytest.mark.asyncio
async def test_remove_by_ids_calls_callback(pending_queue_with_callback, sample_list_id):
    """Test remove_by_ids triggers on_change_callback with remaining count."""
    queue, callback = pending_queue_with_callback
    list_id = str(sample_list_id)

    # Add operations
    await queue.add("TASK_CREATE", list_id, {"task_id": "1"})
    await queue.add("TASK_UPDATE", list_id, {"task_id": "2"})
    await queue.add("TASK_DELETE", list_id, {"task_id": "3"})

    # Get IDs and reset callback
    operations = await queue.get_all()
    callback.reset_mock()

    # Remove first operation
    await queue.remove_by_ids([operations[0]["id"]])

    # Verify callback called with remaining count (2)
    callback.assert_called_once_with(2)

    # Remove another operation
    await queue.remove_by_ids([operations[1]["id"]])

    # Verify callback called with remaining count (1)
    assert callback.call_count == 2
    callback.assert_called_with(1)


@pytest.mark.asyncio
async def test_operation_data_serialization(pending_queue, sample_list_id):
    """Test complex data structures are properly serialized and deserialized."""
    list_id = str(sample_list_id)

    # Add operation with complex nested data
    complex_data = {
        "task_id": str(uuid4()),
        "title": "Complex Task",
        "metadata": {
            "tags": ["urgent", "important"],
            "priority": 1,
            "nested": {
                "deep": "value"
            }
        },
        "list_of_items": [1, 2, 3, "four"]
    }

    await pending_queue.add("TASK_CREATE", list_id, complex_data)

    # Retrieve and verify
    operations = await pending_queue.get_all()
    assert len(operations) == 1

    retrieved_data = operations[0]["data"]
    assert retrieved_data["task_id"] == complex_data["task_id"]
    assert retrieved_data["title"] == complex_data["title"]
    assert retrieved_data["metadata"]["tags"] == ["urgent", "important"]
    assert retrieved_data["metadata"]["priority"] == 1
    assert retrieved_data["metadata"]["nested"]["deep"] == "value"
    assert retrieved_data["list_of_items"] == [1, 2, 3, "four"]


@pytest.mark.asyncio
async def test_operations_for_multiple_lists(pending_queue):
    """Test operations can be tracked for multiple different lists."""
    list_id_1 = str(uuid4())
    list_id_2 = str(uuid4())

    # Add operations for different lists
    await pending_queue.add("TASK_CREATE", list_id_1, {"list": "1"})
    await pending_queue.add("TASK_CREATE", list_id_2, {"list": "2"})
    await pending_queue.add("TASK_UPDATE", list_id_1, {"list": "1"})

    # Verify all operations are tracked
    operations = await pending_queue.get_all()
    assert len(operations) == 3

    # Verify list_id preservation
    list_1_ops = [op for op in operations if op["list_id"] == list_id_1]
    list_2_ops = [op for op in operations if op["list_id"] == list_id_2]

    assert len(list_1_ops) == 2
    assert len(list_2_ops) == 1


@pytest.mark.asyncio
async def test_timestamp_field_is_set(pending_queue, sample_list_id):
    """Test timestamp field is properly set when adding operations."""
    list_id = str(sample_list_id)

    await pending_queue.add("TASK_CREATE", list_id, {"task_id": "1"})

    operations = await pending_queue.get_all()
    assert len(operations) == 1

    # Verify timestamp exists and is a valid ISO-8601 string
    timestamp = operations[0]["timestamp"]
    assert timestamp is not None
    assert isinstance(timestamp, str)

    # Should be parseable as datetime
    parsed_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    assert isinstance(parsed_dt, datetime)


@pytest.mark.asyncio
async def test_operation_has_all_required_fields(pending_queue, sample_list_id):
    """Test retrieved operations have all required fields."""
    list_id = str(sample_list_id)

    await pending_queue.add("TASK_CREATE", list_id, {"task_id": "1"})

    operations = await pending_queue.get_all()
    assert len(operations) == 1

    operation = operations[0]

    # Verify all required fields exist
    assert "id" in operation
    assert "operation" in operation
    assert "list_id" in operation
    assert "data" in operation
    assert "timestamp" in operation

    # Verify field types
    assert isinstance(operation["id"], int)
    assert isinstance(operation["operation"], str)
    assert isinstance(operation["list_id"], str)
    assert isinstance(operation["data"], dict)
    assert isinstance(operation["timestamp"], str)


@pytest.mark.asyncio
async def test_queue_without_callback_works(db_session, sample_list_id):
    """Test queue operations work correctly without on_change_callback."""
    # Create queue without callback
    queue = PendingOperationsQueue(db_session)
    list_id = str(sample_list_id)

    # All operations should work without callback
    await queue.add("TASK_CREATE", list_id, {"task_id": "1"})
    assert await queue.count() == 1

    await queue.add("TASK_UPDATE", list_id, {"task_id": "2"})
    assert await queue.count() == 2

    operations = await queue.get_all()
    await queue.remove_by_ids([operations[0]["id"]])
    assert await queue.count() == 1

    await queue.clear_all()
    assert await queue.count() == 0
