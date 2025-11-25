"""Tests for sync operation handlers."""

import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from taskui.services.sync_operations import SyncOperationHandler
from taskui.models import Task, TaskList


@pytest.fixture
def mock_task_service():
    """Mock TaskService."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_list_service():
    """Mock ListService."""
    service = AsyncMock()
    return service


@pytest.fixture
def sync_handler(mock_task_service, mock_list_service):
    """Create SyncOperationHandler with mocked services."""
    return SyncOperationHandler(mock_task_service, mock_list_service)


class TestEnsureListExists:
    """Tests for _ensure_list_exists helper method."""

    async def test_does_nothing_if_list_exists(self, sync_handler, mock_list_service):
        """Should return immediately if list already exists."""
        list_id = uuid.uuid4()
        existing_list = TaskList(id=list_id, name="Existing List")
        mock_list_service.get_list.return_value = existing_list

        await sync_handler._ensure_list_exists(list_id)

        # Should check for existing list
        mock_list_service.get_list.assert_called_once_with(list_id)
        # Should not create new list
        mock_list_service.create_list.assert_not_called()

    async def test_creates_placeholder_if_list_missing(self, sync_handler, mock_list_service):
        """Should create placeholder list if list doesn't exist."""
        list_id = uuid.uuid4()
        mock_list_service.get_list.side_effect = Exception("Not found")

        await sync_handler._ensure_list_exists(list_id)

        # Should attempt to create list
        mock_list_service.create_list.assert_called_once_with(
            name="(Syncing...)",
            list_id=list_id
        )

    async def test_handles_race_condition(self, sync_handler, mock_list_service):
        """Should handle case where list is created by another operation."""
        list_id = uuid.uuid4()
        mock_list_service.get_list.side_effect = Exception("Not found")
        mock_list_service.create_list.side_effect = Exception("Already exists")

        # Should not raise exception
        await sync_handler._ensure_list_exists(list_id)

    async def test_uses_custom_placeholder_name(self, sync_handler, mock_list_service):
        """Should use custom placeholder name if provided."""
        list_id = uuid.uuid4()
        custom_name = "Loading..."
        mock_list_service.get_list.side_effect = Exception("Not found")

        await sync_handler._ensure_list_exists(list_id, placeholder_name=custom_name)

        mock_list_service.create_list.assert_called_once_with(
            name=custom_name,
            list_id=list_id
        )


class TestTaskCreateWithMissingList:
    """Tests for TASK_CREATE operation with missing list."""

    async def test_creates_placeholder_list_before_task(self, sync_handler, mock_task_service, mock_list_service):
        """Should create placeholder list before creating task."""
        list_id = uuid.uuid4()
        task_id = uuid.uuid4()

        # Simulate missing list
        mock_list_service.get_list.side_effect = Exception("Not found")
        mock_task_service.get_task.side_effect = Exception("Not found")

        operation_data = {
            'operation': 'TASK_CREATE',
            'list_id': str(list_id),
            'data': {
                'task': {
                    'id': str(task_id),
                    'title': 'Test Task',
                    'description': None,
                    'parent_id': None,
                    'position': 0,
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                }
            }
        }

        await sync_handler._handle_task_create(operation_data)

        # Should create placeholder list first
        mock_list_service.create_list.assert_called_once_with(
            name="(Syncing...)",
            list_id=list_id
        )

        # Should then create task
        mock_task_service.create_task.assert_called_once()


class TestTaskUpdateWithListMove:
    """Tests for TASK_UPDATE operation that moves task to different list."""

    async def test_ensures_target_list_exists(self, sync_handler, mock_task_service, mock_list_service):
        """Should ensure target list exists when task is moved."""
        task_id = uuid.uuid4()
        old_list_id = uuid.uuid4()
        new_list_id = uuid.uuid4()

        # Existing task in old list (with mock updated_at attribute)
        existing_task = MagicMock(spec=Task)
        existing_task.id = task_id
        existing_task.title = "Test Task"
        existing_task.list_id = old_list_id
        existing_task.updated_at = datetime.utcnow()
        mock_task_service.get_task.return_value = existing_task

        # New list doesn't exist yet
        mock_list_service.get_list.side_effect = Exception("Not found")

        operation_data = {
            'operation': 'TASK_UPDATE',
            'timestamp': datetime.utcnow().isoformat(),
            'data': {
                'task_id': str(task_id),
                'changes': {
                    'list_id': str(new_list_id)
                }
            }
        }

        await sync_handler._handle_task_update(operation_data)

        # Should create placeholder for target list
        mock_list_service.create_list.assert_called_once_with(
            name="(Syncing...)",
            list_id=new_list_id
        )

        # Should update task
        mock_task_service.update_task.assert_called_once()
