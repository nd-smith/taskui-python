"""Test ListService integration with PendingOperationsQueue."""

import pytest
from uuid import uuid4
from datetime import datetime

from taskui.services.list_service import ListService


@pytest.fixture
def mock_pending_queue():
    """Mock PendingOperationsQueue for testing."""
    class MockPendingQueue:
        def __init__(self):
            self.operations = []

        async def add(self, operation: str, entity_id: str, data: dict):
            self.operations.append({
                "operation": operation,
                "entity_id": entity_id,
                "data": data
            })

    return MockPendingQueue()


@pytest.mark.asyncio
async def test_list_service_without_pending_queue(db_session):
    """Test ListService works without pending_queue (backward compatibility)."""
    service = ListService(db_session)

    # Should work without pending_queue
    task_list = await service.create_list("Test List")

    assert task_list.name == "Test List"
    assert task_list.id is not None


@pytest.mark.asyncio
async def test_create_list_queues_sync_operation(db_session, mock_pending_queue):
    """Test create_list queues LIST_CREATE operation."""
    service = ListService(db_session, pending_queue=mock_pending_queue)

    # Create a list
    task_list = await service.create_list("Work")
    await db_session.commit()

    # Verify operation was queued
    assert len(mock_pending_queue.operations) == 1

    operation = mock_pending_queue.operations[0]
    assert operation["operation"] == "LIST_CREATE"
    assert operation["entity_id"] == str(task_list.id)
    assert operation["data"]["list"]["name"] == "Work"
    assert operation["data"]["list"]["id"] == str(task_list.id)
    assert "created_at" in operation["data"]["list"]


@pytest.mark.asyncio
async def test_update_list_queues_sync_operation(db_session, mock_pending_queue):
    """Test update_list queues LIST_UPDATE operation."""
    service = ListService(db_session, pending_queue=mock_pending_queue)

    # Create a list first
    task_list = await service.create_list("Work")
    await db_session.commit()

    # Clear the create operation
    mock_pending_queue.operations.clear()

    # Update the list
    updated_list = await service.update_list(task_list.id, "Work Projects")
    await db_session.commit()

    # Verify update operation was queued
    assert len(mock_pending_queue.operations) == 1

    operation = mock_pending_queue.operations[0]
    assert operation["operation"] == "LIST_UPDATE"
    assert operation["entity_id"] == str(task_list.id)
    assert operation["data"]["list_id"] == str(task_list.id)
    assert operation["data"]["changes"]["name"] == "Work Projects"


@pytest.mark.asyncio
async def test_multiple_operations_queued(db_session, mock_pending_queue):
    """Test multiple list operations are all queued."""
    service = ListService(db_session, pending_queue=mock_pending_queue)

    # Create two lists
    list1 = await service.create_list("List 1")
    list2 = await service.create_list("List 2")

    # Update one list
    await service.update_list(list1.id, "Updated List 1")

    await db_session.commit()

    # Should have 3 operations queued
    assert len(mock_pending_queue.operations) == 3

    # Verify operation types
    ops = [op["operation"] for op in mock_pending_queue.operations]
    assert ops == ["LIST_CREATE", "LIST_CREATE", "LIST_UPDATE"]


@pytest.mark.asyncio
async def test_delete_list_does_not_queue(db_session, mock_pending_queue):
    """Test delete_list doesn't queue operation (as per design)."""
    service = ListService(db_session, pending_queue=mock_pending_queue)

    # Create a list
    task_list = await service.create_list("To Delete")
    await db_session.commit()

    # Clear the create operation
    mock_pending_queue.operations.clear()

    # Delete the list
    await service.delete_list(task_list.id)
    await db_session.commit()

    # Should not have queued any operation
    assert len(mock_pending_queue.operations) == 0
