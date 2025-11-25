"""
Sync queue service for syncing operations between clients via AWS SQS.

Builds on cloud print queue infrastructure for encrypted message delivery.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import json

from taskui.services.cloud_print_queue import CloudPrintConfig
from taskui.services.encryption import MessageEncryption
from taskui.logging_config import get_logger

logger = get_logger(__name__)


class SyncQueue:
    """
    Queue service for syncing operations between clients.
    Sends encrypted operations to AWS SQS.
    """

    def __init__(self, config: CloudPrintConfig, client_id: str):
        """
        Initialize sync queue.

        Args:
            config: CloudPrintConfig with SQS settings
            client_id: Unique identifier for this client
        """
        self.config = config
        self.client_id = client_id
        self.sqs_client = None
        self._connected = False

        # Initialize encryption
        self.encryption = MessageEncryption(config.encryption_key)
        if self.encryption.enabled:
            logger.info("Sync queue encryption enabled")
        else:
            logger.warning("Sync queue encryption NOT enabled - messages will be sent in plaintext")

        logger.info(f"SyncQueue initialized for client: {client_id}")

    def connect(self) -> bool:
        """
        Connect to AWS SQS.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            import boto3
            from botocore.exceptions import NoCredentialsError

            # Disable SSL warnings for corporate proxies
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            except:
                pass

            # Build client kwargs
            client_kwargs = {
                'region_name': self.config.region,
                'verify': False  # Disable SSL verification for corporate proxies
            }

            if self.config.aws_access_key_id and self.config.aws_secret_access_key:
                client_kwargs['aws_access_key_id'] = self.config.aws_access_key_id
                client_kwargs['aws_secret_access_key'] = self.config.aws_secret_access_key

            # Create SQS client
            self.sqs_client = boto3.client('sqs', **client_kwargs)

            # Test connection by getting queue attributes
            self.sqs_client.get_queue_attributes(
                QueueUrl=self.config.queue_url,
                AttributeNames=['ApproximateNumberOfMessages']
            )

            self._connected = True
            logger.info(f"Connected to sync queue: {self.config.queue_url}")
            return True

        except ImportError:
            logger.error("boto3 not installed. Install with: pip install boto3")
            return False
        except NoCredentialsError:
            logger.error("AWS credentials not configured")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to sync queue: {e}", exc_info=True)
            return False

    def disconnect(self):
        """Disconnect from AWS SQS."""
        self.sqs_client = None
        self._connected = False
        logger.info("Disconnected from sync queue")

    def is_connected(self) -> bool:
        """Check if connected to SQS."""
        return self._connected

    def send_operation(self, operation: str, list_id: str, data: Dict[str, Any]) -> bool:
        """
        Send sync operation to queue.

        Args:
            operation: Operation type (TASK_CREATE, TASK_UPDATE, etc.)
            list_id: UUID of the list
            data: Operation-specific data

        Returns:
            True if sent successfully
        """
        if not self._connected:
            logger.error("Not connected to sync queue")
            return False

        try:
            # Build message with protocol version
            message = {
                "version": "2.0",
                "client_id": self.client_id,
                "operation": operation,
                "timestamp": datetime.utcnow().isoformat(),
                "list_id": str(list_id),
                "data": data
            }

            # Encrypt the message (if encryption is enabled)
            encrypted_message = self.encryption.encrypt_message(message)

            # Send to SQS with attributes
            response = self.sqs_client.send_message(
                QueueUrl=self.config.queue_url,
                MessageBody=encrypted_message,
                MessageAttributes={
                    'Operation': {
                        'StringValue': operation,
                        'DataType': 'String'
                    },
                    'ClientId': {
                        'StringValue': self.client_id,
                        'DataType': 'String'
                    }
                }
            )

            encryption_status = "encrypted" if self.encryption.enabled else "plaintext"
            logger.debug(f"Sent operation ({encryption_status}): {operation} (MessageId: {response['MessageId']})")
            return True

        except Exception as e:
            logger.error(f"Failed to send operation: {e}", exc_info=True)
            return False

    def send_task_create(self, task) -> bool:
        """
        Send task creation operation.

        Args:
            task: Task object to sync

        Returns:
            True if sent successfully
        """
        data = {
            "task": {
                "id": str(task.id),
                "title": task.title,
                "notes": task.notes,
                "parent_id": str(task.parent_id) if task.parent_id else None,
                "level": task.level,
                "position": task.position,
                "is_completed": task.is_completed,
                "created_at": task.created_at.isoformat() if task.created_at else None
            }
        }
        return self.send_operation("TASK_CREATE", str(task.list_id), data)

    def send_task_update(self, task_id: str, list_id: str, changes: Dict[str, Any]) -> bool:
        """
        Send task update operation.

        Args:
            task_id: UUID of task to update
            list_id: UUID of the list
            changes: Dictionary of field changes

        Returns:
            True if sent successfully
        """
        data = {
            "task_id": str(task_id),
            "changes": changes
        }
        return self.send_operation("TASK_UPDATE", list_id, data)

    def send_task_delete(self, task_id: str, list_id: str, cascade: bool = True) -> bool:
        """
        Send task deletion operation.

        Args:
            task_id: UUID of task to delete
            list_id: UUID of the list
            cascade: Whether to delete children

        Returns:
            True if sent successfully
        """
        data = {
            "task_id": str(task_id),
            "cascade": cascade
        }
        return self.send_operation("TASK_DELETE", list_id, data)

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


# Example usage
if __name__ == "__main__":
    from taskui.logging_config import setup_logging
    from taskui.models import Task
    import uuid

    setup_logging()

    # Test sync queue configuration
    config = CloudPrintConfig(
        queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/taskui-sync-queue",
        region="us-east-1",
        encryption_key="your-base64-encryption-key"
    )

    # Generate unique client ID
    client_id = str(uuid.uuid4())

    queue = SyncQueue(config, client_id)

    # Test connection
    if queue.connect():
        print("✅ Connected to sync queue")

        # Create test task
        list_id = uuid.uuid4()
        task = Task(
            id=uuid.uuid4(),
            list_id=list_id,
            title="Test Sync Task",
            notes="Testing sync queue",
            parent_id=None,
            level=0,
            position=0,
            is_completed=False,
            created_at=datetime.now()
        )

        # Send task create operation
        if queue.send_task_create(task):
            print("✅ Task create operation sent successfully")
            depth = queue.get_queue_depth()
            print(f"📊 Queue depth: {depth}")
        else:
            print("❌ Failed to send task create operation")

        # Send task update operation
        if queue.send_task_update(str(task.id), str(list_id), {"title": "Updated Title"}):
            print("✅ Task update operation sent successfully")

        # Send task delete operation
        if queue.send_task_delete(str(task.id), str(list_id), cascade=True):
            print("✅ Task delete operation sent successfully")

        queue.disconnect()
    else:
        print("❌ Failed to connect to sync queue")
