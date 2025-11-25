"""
Tests for sync queue service.

Tests the SyncQueue class with mocked AWS SQS client and encryption to avoid
external dependencies.
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from uuid import uuid4
from datetime import datetime

from taskui.services.sync_queue import SyncQueue
from taskui.services.cloud_print_queue import CloudPrintConfig
from taskui.models import Task


@pytest.fixture
def mock_sqs_client():
    """Mock boto3 SQS client."""
    client = MagicMock()
    client.send_message.return_value = {'MessageId': 'test-msg-id'}
    client.get_queue_attributes.return_value = {
        'Attributes': {
            'ApproximateNumberOfMessages': '5'
        }
    }
    return client


@pytest.fixture
def mock_encryption():
    """Mock MessageEncryption."""
    encryption = MagicMock()
    encryption.encrypt_message.return_value = "encrypted-data"
    encryption.enabled = True
    return encryption


@pytest.fixture
def sync_config():
    """Create a test sync config."""
    return CloudPrintConfig(
        queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/test-queue",
        region="us-east-1",
        encryption_key="dGVzdC1lbmNyeXB0aW9uLWtleQ==",  # base64 encoded "test-encryption-key"
        aws_access_key_id="test-access-key",
        aws_secret_access_key="test-secret-key"
    )


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return Task(
        id=uuid4(),
        list_id=uuid4(),
        title="Test Task",
        notes="Test notes",
        parent_id=None,
        level=0,
        position=0,
        is_completed=False,
        created_at=datetime.now()
    )


class TestSyncQueueInitialization:
    """Tests for SyncQueue initialization."""

    def test_init_with_encryption(self, sync_config):
        """Test initialization with encryption enabled."""
        with patch('taskui.services.sync_queue.MessageEncryption') as mock_encryption_class:
            mock_enc = MagicMock()
            mock_enc.enabled = True
            mock_encryption_class.return_value = mock_enc

            client_id = str(uuid4())
            queue = SyncQueue(sync_config, client_id)

            assert queue.config == sync_config
            assert queue.client_id == client_id
            assert queue.sqs_client is None
            assert queue._connected is False
            mock_encryption_class.assert_called_once_with(sync_config.encryption_key)

    def test_init_without_encryption(self, sync_config):
        """Test initialization without encryption."""
        with patch('taskui.services.sync_queue.MessageEncryption') as mock_encryption_class:
            mock_enc = MagicMock()
            mock_enc.enabled = False
            mock_encryption_class.return_value = mock_enc

            client_id = str(uuid4())
            queue = SyncQueue(sync_config, client_id)

            assert queue.encryption.enabled is False


class TestSyncQueueConnection:
    """Tests for SyncQueue connection management."""

    @patch('builtins.__import__')
    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_connect_success(self, mock_encryption_class, mock_import, sync_config):
        """Test successful connection to SQS."""
        mock_encryption_class.return_value.enabled = True

        # Mock boto3 module
        mock_boto3 = MagicMock()
        mock_sqs = MagicMock()
        mock_boto3.client.return_value = mock_sqs

        # Setup import mock to return boto3
        def import_side_effect(name, *args, **kwargs):
            if name == 'boto3':
                return mock_boto3
            elif name == 'botocore.exceptions':
                mock_botocore = MagicMock()
                mock_botocore.NoCredentialsError = Exception
                return mock_botocore
            # For other imports, use real import
            return __import__(name, *args, **kwargs)

        mock_import.side_effect = import_side_effect

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)

        result = queue.connect()

        assert result is True
        assert queue.is_connected() is True
        assert queue.sqs_client is not None
        mock_boto3.client.assert_called_once()
        mock_sqs.get_queue_attributes.assert_called_once_with(
            QueueUrl=sync_config.queue_url,
            AttributeNames=['ApproximateNumberOfMessages']
        )

    @patch('builtins.__import__')
    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_connect_with_credentials(self, mock_encryption_class, mock_import, sync_config):
        """Test connection with AWS credentials."""
        mock_encryption_class.return_value.enabled = True

        # Mock boto3 module
        mock_boto3 = MagicMock()
        mock_sqs = MagicMock()
        mock_boto3.client.return_value = mock_sqs

        # Setup import mock
        def import_side_effect(name, *args, **kwargs):
            if name == 'boto3':
                return mock_boto3
            elif name == 'botocore.exceptions':
                mock_botocore = MagicMock()
                mock_botocore.NoCredentialsError = Exception
                return mock_botocore
            return __import__(name, *args, **kwargs)

        mock_import.side_effect = import_side_effect

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)
        queue.connect()

        # Verify client was created with credentials
        call_kwargs = mock_boto3.client.call_args[1]
        assert call_kwargs['region_name'] == sync_config.region
        assert call_kwargs['aws_access_key_id'] == sync_config.aws_access_key_id
        assert call_kwargs['aws_secret_access_key'] == sync_config.aws_secret_access_key
        assert call_kwargs['verify'] is False  # SSL verification disabled

    @patch('builtins.__import__')
    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_connect_boto3_not_installed(self, mock_encryption_class, mock_import, sync_config):
        """Test connection when boto3 is not installed."""
        mock_encryption_class.return_value.enabled = True

        # Setup import mock to raise ImportError for boto3
        def import_side_effect(name, *args, **kwargs):
            if name == 'boto3':
                raise ImportError("No module named 'boto3'")
            return __import__(name, *args, **kwargs)

        mock_import.side_effect = import_side_effect

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)

        result = queue.connect()

        assert result is False
        assert queue.is_connected() is False

    @patch('builtins.__import__')
    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_connect_no_credentials_error(self, mock_encryption_class, mock_import, sync_config):
        """Test connection with no AWS credentials."""
        mock_encryption_class.return_value.enabled = True

        # Create a proper NoCredentialsError exception class
        class NoCredentialsError(Exception):
            pass

        # Mock boto3 module that raises NoCredentialsError
        mock_boto3 = MagicMock()
        mock_boto3.client.side_effect = NoCredentialsError()

        # Setup import mock
        def import_side_effect(name, *args, **kwargs):
            if name == 'boto3':
                return mock_boto3
            elif name == 'botocore.exceptions':
                mock_botocore = MagicMock()
                mock_botocore.NoCredentialsError = NoCredentialsError
                return mock_botocore
            return __import__(name, *args, **kwargs)

        mock_import.side_effect = import_side_effect

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)

        result = queue.connect()

        assert result is False
        assert queue.is_connected() is False

    @patch('builtins.__import__')
    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_connect_general_exception(self, mock_encryption_class, mock_import, sync_config):
        """Test connection with general exception."""
        mock_encryption_class.return_value.enabled = True

        # Mock boto3 module that raises exception
        mock_boto3 = MagicMock()
        mock_boto3.client.side_effect = Exception("Connection failed")

        # Setup import mock
        def import_side_effect(name, *args, **kwargs):
            if name == 'boto3':
                return mock_boto3
            elif name == 'botocore.exceptions':
                mock_botocore = MagicMock()
                mock_botocore.NoCredentialsError = Exception
                return mock_botocore
            return __import__(name, *args, **kwargs)

        mock_import.side_effect = import_side_effect

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)

        result = queue.connect()

        assert result is False
        assert queue.is_connected() is False

    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_disconnect(self, mock_encryption_class, sync_config):
        """Test disconnection from SQS."""
        mock_encryption_class.return_value.enabled = True

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)
        queue.sqs_client = MagicMock()
        queue._connected = True

        queue.disconnect()

        assert queue.sqs_client is None
        assert queue.is_connected() is False

    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_is_connected_returns_false_initially(self, mock_encryption_class, sync_config):
        """Test is_connected returns False before connecting."""
        mock_encryption_class.return_value.enabled = True

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)

        assert queue.is_connected() is False


class TestSyncQueueOperations:
    """Tests for SyncQueue operation sending."""

    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_send_operation_not_connected(self, mock_encryption_class, sync_config):
        """Test send_operation fails when not connected."""
        mock_encryption_class.return_value.enabled = True

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)

        result = queue.send_operation(
            "TASK_CREATE",
            str(uuid4()),
            {"task": {"id": str(uuid4()), "title": "Test"}}
        )

        assert result is False

    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_send_operation_success(self, mock_encryption_class, sync_config, mock_sqs_client):
        """Test successful operation sending."""
        mock_enc = MagicMock()
        mock_enc.enabled = True
        mock_enc.encrypt_message.return_value = "encrypted-data"
        mock_encryption_class.return_value = mock_enc

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)
        queue.sqs_client = mock_sqs_client
        queue._connected = True

        list_id = str(uuid4())
        data = {"task": {"id": str(uuid4()), "title": "Test"}}

        result = queue.send_operation("TASK_CREATE", list_id, data)

        assert result is True
        mock_enc.encrypt_message.assert_called_once()
        mock_sqs_client.send_message.assert_called_once()

        # Verify message structure passed to encrypt
        call_args = mock_enc.encrypt_message.call_args[0][0]
        assert call_args["version"] == "2.0"
        assert call_args["client_id"] == client_id
        assert call_args["operation"] == "TASK_CREATE"
        assert call_args["list_id"] == list_id
        assert call_args["data"] == data
        assert "timestamp" in call_args

    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_send_operation_encrypts_message(self, mock_encryption_class, sync_config, mock_sqs_client):
        """Test that send_operation encrypts the message."""
        mock_enc = MagicMock()
        mock_enc.enabled = True
        mock_enc.encrypt_message.return_value = "encrypted-data"
        mock_encryption_class.return_value = mock_enc

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)
        queue.sqs_client = mock_sqs_client
        queue._connected = True

        queue.send_operation("TASK_CREATE", str(uuid4()), {})

        # Verify encrypted data was sent to SQS
        call_kwargs = mock_sqs_client.send_message.call_args[1]
        assert call_kwargs['MessageBody'] == "encrypted-data"

    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_send_operation_includes_attributes(self, mock_encryption_class, sync_config, mock_sqs_client):
        """Test that send_operation includes message attributes."""
        mock_enc = MagicMock()
        mock_enc.enabled = True
        mock_enc.encrypt_message.return_value = "encrypted-data"
        mock_encryption_class.return_value = mock_enc

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)
        queue.sqs_client = mock_sqs_client
        queue._connected = True

        queue.send_operation("TASK_UPDATE", str(uuid4()), {})

        # Verify message attributes
        call_kwargs = mock_sqs_client.send_message.call_args[1]
        attrs = call_kwargs['MessageAttributes']
        assert attrs['Operation']['StringValue'] == "TASK_UPDATE"
        assert attrs['Operation']['DataType'] == "String"
        assert attrs['ClientId']['StringValue'] == client_id
        assert attrs['ClientId']['DataType'] == "String"

    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_send_operation_sqs_exception(self, mock_encryption_class, sync_config):
        """Test send_operation handles SQS exceptions."""
        mock_enc = MagicMock()
        mock_enc.enabled = True
        mock_enc.encrypt_message.return_value = "encrypted-data"
        mock_encryption_class.return_value = mock_enc

        mock_sqs = MagicMock()
        mock_sqs.send_message.side_effect = Exception("SQS error")

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)
        queue.sqs_client = mock_sqs
        queue._connected = True

        result = queue.send_operation("TASK_CREATE", str(uuid4()), {})

        assert result is False


class TestTaskOperations:
    """Tests for task-specific operations."""

    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_send_task_create(self, mock_encryption_class, sync_config, mock_sqs_client, sample_task):
        """Test send_task_create formats message correctly."""
        mock_enc = MagicMock()
        mock_enc.enabled = True
        mock_enc.encrypt_message.return_value = "encrypted-data"
        mock_encryption_class.return_value = mock_enc

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)
        queue.sqs_client = mock_sqs_client
        queue._connected = True

        result = queue.send_task_create(sample_task)

        assert result is True

        # Verify message structure
        call_args = mock_enc.encrypt_message.call_args[0][0]
        assert call_args["operation"] == "TASK_CREATE"
        assert call_args["list_id"] == str(sample_task.list_id)

        # Verify task data
        task_data = call_args["data"]["task"]
        assert task_data["id"] == str(sample_task.id)
        assert task_data["title"] == sample_task.title
        assert task_data["notes"] == sample_task.notes
        assert task_data["parent_id"] is None
        assert task_data["level"] == sample_task.level
        assert task_data["position"] == sample_task.position
        assert task_data["is_completed"] == sample_task.is_completed
        assert task_data["created_at"] == sample_task.created_at.isoformat()

    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_send_task_create_with_parent(self, mock_encryption_class, sync_config, mock_sqs_client):
        """Test send_task_create with parent task."""
        mock_enc = MagicMock()
        mock_enc.enabled = True
        mock_enc.encrypt_message.return_value = "encrypted-data"
        mock_encryption_class.return_value = mock_enc

        parent_id = uuid4()
        task = Task(
            id=uuid4(),
            list_id=uuid4(),
            title="Child Task",
            parent_id=parent_id,
            level=1,
            position=0,
            is_completed=False,
            created_at=datetime.now()
        )

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)
        queue.sqs_client = mock_sqs_client
        queue._connected = True

        result = queue.send_task_create(task)

        assert result is True

        call_args = mock_enc.encrypt_message.call_args[0][0]
        task_data = call_args["data"]["task"]
        assert task_data["parent_id"] == str(parent_id)

    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_send_task_update(self, mock_encryption_class, sync_config, mock_sqs_client):
        """Test send_task_update formats message correctly."""
        mock_enc = MagicMock()
        mock_enc.enabled = True
        mock_enc.encrypt_message.return_value = "encrypted-data"
        mock_encryption_class.return_value = mock_enc

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)
        queue.sqs_client = mock_sqs_client
        queue._connected = True

        task_id = str(uuid4())
        list_id = str(uuid4())
        changes = {"title": "Updated Title", "notes": "Updated notes"}

        result = queue.send_task_update(task_id, list_id, changes)

        assert result is True

        # Verify message structure
        call_args = mock_enc.encrypt_message.call_args[0][0]
        assert call_args["operation"] == "TASK_UPDATE"
        assert call_args["list_id"] == list_id

        # Verify update data
        data = call_args["data"]
        assert data["task_id"] == task_id
        assert data["changes"] == changes

    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_send_task_delete(self, mock_encryption_class, sync_config, mock_sqs_client):
        """Test send_task_delete formats message correctly."""
        mock_enc = MagicMock()
        mock_enc.enabled = True
        mock_enc.encrypt_message.return_value = "encrypted-data"
        mock_encryption_class.return_value = mock_enc

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)
        queue.sqs_client = mock_sqs_client
        queue._connected = True

        task_id = str(uuid4())
        list_id = str(uuid4())

        result = queue.send_task_delete(task_id, list_id, cascade=True)

        assert result is True

        # Verify message structure
        call_args = mock_enc.encrypt_message.call_args[0][0]
        assert call_args["operation"] == "TASK_DELETE"
        assert call_args["list_id"] == list_id

        # Verify delete data
        data = call_args["data"]
        assert data["task_id"] == task_id
        assert data["cascade"] is True

    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_send_task_delete_no_cascade(self, mock_encryption_class, sync_config, mock_sqs_client):
        """Test send_task_delete without cascade."""
        mock_enc = MagicMock()
        mock_enc.enabled = True
        mock_enc.encrypt_message.return_value = "encrypted-data"
        mock_encryption_class.return_value = mock_enc

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)
        queue.sqs_client = mock_sqs_client
        queue._connected = True

        result = queue.send_task_delete(str(uuid4()), str(uuid4()), cascade=False)

        call_args = mock_enc.encrypt_message.call_args[0][0]
        assert call_args["data"]["cascade"] is False


class TestQueueUtilities:
    """Tests for queue utility methods."""

    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_get_queue_depth_success(self, mock_encryption_class, sync_config, mock_sqs_client):
        """Test get_queue_depth returns correct count."""
        mock_encryption_class.return_value.enabled = True

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)
        queue.sqs_client = mock_sqs_client
        queue._connected = True

        depth = queue.get_queue_depth()

        assert depth == 5
        mock_sqs_client.get_queue_attributes.assert_called_once_with(
            QueueUrl=sync_config.queue_url,
            AttributeNames=['ApproximateNumberOfMessages']
        )

    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_get_queue_depth_not_connected(self, mock_encryption_class, sync_config):
        """Test get_queue_depth returns None when not connected."""
        mock_encryption_class.return_value.enabled = True

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)

        depth = queue.get_queue_depth()

        assert depth is None

    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_get_queue_depth_sqs_exception(self, mock_encryption_class, sync_config):
        """Test get_queue_depth handles SQS exceptions."""
        mock_encryption_class.return_value.enabled = True

        mock_sqs = MagicMock()
        mock_sqs.get_queue_attributes.side_effect = Exception("SQS error")

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)
        queue.sqs_client = mock_sqs
        queue._connected = True

        depth = queue.get_queue_depth()

        assert depth is None


class TestErrorHandling:
    """Tests for error handling scenarios."""

    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_task_operations_when_not_connected(self, mock_encryption_class, sync_config, sample_task):
        """Test all task operations fail gracefully when not connected."""
        mock_encryption_class.return_value.enabled = True

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)

        # Test task create
        assert queue.send_task_create(sample_task) is False

        # Test task update
        assert queue.send_task_update(str(uuid4()), str(uuid4()), {}) is False

        # Test task delete
        assert queue.send_task_delete(str(uuid4()), str(uuid4())) is False

    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_encryption_failure(self, mock_encryption_class, sync_config, mock_sqs_client):
        """Test handling of encryption failures."""
        mock_enc = MagicMock()
        mock_enc.enabled = True
        mock_enc.encrypt_message.side_effect = Exception("Encryption failed")
        mock_encryption_class.return_value = mock_enc

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)
        queue.sqs_client = mock_sqs_client
        queue._connected = True

        result = queue.send_operation("TASK_CREATE", str(uuid4()), {})

        assert result is False

    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_message_formatting_edge_cases(self, mock_encryption_class, sync_config, mock_sqs_client):
        """Test message formatting with edge cases."""
        mock_enc = MagicMock()
        mock_enc.enabled = True
        mock_enc.encrypt_message.return_value = "encrypted-data"
        mock_encryption_class.return_value = mock_enc

        # Create task with empty notes and URL
        task = Task(
            id=uuid4(),
            list_id=uuid4(),
            title="Test",
            notes="",
            url=None,
            created_at=datetime.now()
        )

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)
        queue.sqs_client = mock_sqs_client
        queue._connected = True

        result = queue.send_task_create(task)

        assert result is True
        call_args = mock_enc.encrypt_message.call_args[0][0]
        assert call_args["data"]["task"]["notes"] == ""
        assert call_args["data"]["task"]["created_at"] is not None


class TestMessageProtocol:
    """Tests for message protocol compliance."""

    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_message_version_is_2_0(self, mock_encryption_class, sync_config, mock_sqs_client):
        """Test that all messages have version 2.0."""
        mock_enc = MagicMock()
        mock_enc.enabled = True
        mock_enc.encrypt_message.return_value = "encrypted-data"
        mock_encryption_class.return_value = mock_enc

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)
        queue.sqs_client = mock_sqs_client
        queue._connected = True

        queue.send_operation("TEST_OP", str(uuid4()), {})

        call_args = mock_enc.encrypt_message.call_args[0][0]
        assert call_args["version"] == "2.0"

    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_message_includes_timestamp(self, mock_encryption_class, sync_config, mock_sqs_client):
        """Test that all messages include ISO format timestamp."""
        mock_enc = MagicMock()
        mock_enc.enabled = True
        mock_enc.encrypt_message.return_value = "encrypted-data"
        mock_encryption_class.return_value = mock_enc

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)
        queue.sqs_client = mock_sqs_client
        queue._connected = True

        queue.send_operation("TEST_OP", str(uuid4()), {})

        call_args = mock_enc.encrypt_message.call_args[0][0]
        assert "timestamp" in call_args
        # Verify it's ISO format by parsing it
        datetime.fromisoformat(call_args["timestamp"])

    @patch('taskui.services.sync_queue.MessageEncryption')
    def test_message_includes_client_id(self, mock_encryption_class, sync_config, mock_sqs_client):
        """Test that all messages include client_id."""
        mock_enc = MagicMock()
        mock_enc.enabled = True
        mock_enc.encrypt_message.return_value = "encrypted-data"
        mock_encryption_class.return_value = mock_enc

        client_id = str(uuid4())
        queue = SyncQueue(sync_config, client_id)
        queue.sqs_client = mock_sqs_client
        queue._connected = True

        queue.send_operation("TEST_OP", str(uuid4()), {})

        call_args = mock_enc.encrypt_message.call_args[0][0]
        assert call_args["client_id"] == client_id
