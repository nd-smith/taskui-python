"""
Cloud print queue service for printing via AWS SQS relay.

This module enables printing in locked-down corporate environments where
direct network access to the printer is blocked by VPN. Print jobs are
sent to an AWS SQS queue, which the Raspberry Pi polls and executes.
"""

import json
import base64
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import logging

from taskui.models import Task
from taskui.logging_config import get_logger

logger = get_logger(__name__)


class CloudPrintMode(Enum):
    """Print delivery modes."""
    DIRECT = "direct"        # Direct network connection to printer
    CLOUD_QUEUE = "cloud"    # Via cloud queue (AWS SQS)
    AUTO = "auto"           # Try direct, fallback to cloud


class CloudPrintConfig:
    """Configuration for cloud print queue."""

    def __init__(
        self,
        queue_url: str,
        region: str = "us-east-1",
        mode: CloudPrintMode = CloudPrintMode.AUTO,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None
    ):
        """
        Initialize cloud print configuration.

        Args:
            queue_url: AWS SQS queue URL
            region: AWS region (default: us-east-1)
            mode: Print delivery mode (direct/cloud/auto)
            aws_access_key_id: AWS access key (or use env/credentials file)
            aws_secret_access_key: AWS secret key (or use env/credentials file)
        """
        self.queue_url = queue_url
        self.region = region
        self.mode = mode
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key

    @classmethod
    def from_config_file(cls, config_path=None) -> "CloudPrintConfig":
        """
        Load cloud print configuration from config.ini.

        Args:
            config_path: Path to config file (default: ~/.taskui/config.ini)

        Returns:
            CloudPrintConfig instance
        """
        from taskui.config import Config

        config = Config(config_path)
        cloud_config = config.get_cloud_print_config()

        mode_str = cloud_config.get('mode', 'auto').lower()
        try:
            mode = CloudPrintMode(mode_str)
        except ValueError:
            logger.warning(f"Invalid cloud print mode '{mode_str}', using AUTO")
            mode = CloudPrintMode.AUTO

        return cls(
            queue_url=cloud_config.get('queue_url', ''),
            region=cloud_config.get('region', 'us-east-1'),
            mode=mode,
            aws_access_key_id=cloud_config.get('aws_access_key_id'),
            aws_secret_access_key=cloud_config.get('aws_secret_access_key')
        )


class CloudPrintQueue:
    """
    Cloud-based print queue using AWS SQS.

    Sends print jobs to AWS SQS queue for pickup by Raspberry Pi.
    """

    def __init__(self, config: CloudPrintConfig):
        """
        Initialize cloud print queue.

        Args:
            config: CloudPrintConfig instance
        """
        self.config = config
        self.sqs_client = None
        self._connected = False

        logger.info(f"CloudPrintQueue initialized, mode={config.mode.value}")

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
            logger.info(f"Connected to AWS SQS queue: {self.config.queue_url}")
            return True

        except ImportError:
            logger.error("boto3 not installed. Install with: pip install boto3")
            return False
        except NoCredentialsError:
            logger.error("AWS credentials not configured")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to AWS SQS: {e}", exc_info=True)
            return False

    def send_print_job(self, task: Task, children: List[Task]) -> bool:
        """
        Send print job to cloud queue.

        Args:
            task: Parent task to print
            children: Child tasks to include

        Returns:
            True if job queued successfully, False otherwise
        """
        if not self._connected:
            logger.error("Not connected to AWS SQS. Call connect() first.")
            return False

        try:
            # Serialize task data
            job_data = self._serialize_print_job(task, children)

            # Send to SQS
            response = self.sqs_client.send_message(
                QueueUrl=self.config.queue_url,
                MessageBody=json.dumps(job_data),
                MessageAttributes={
                    'TaskId': {
                        'StringValue': str(task.id),
                        'DataType': 'String'
                    },
                    'Timestamp': {
                        'StringValue': datetime.now().isoformat(),
                        'DataType': 'String'
                    }
                }
            )

            logger.info(f"Print job queued: {task.title} (MessageId: {response['MessageId']})")
            return True

        except Exception as e:
            logger.error(f"Failed to queue print job: {e}", exc_info=True)
            return False

    def _serialize_print_job(self, task: Task, children: List[Task]) -> Dict[str, Any]:
        """
        Serialize task and children for transmission.

        Args:
            task: Parent task
            children: Child tasks

        Returns:
            Dictionary with serialized job data
        """
        return {
            'version': '1.0',
            'timestamp': datetime.now().isoformat(),
            'task': {
                'id': str(task.id),
                'title': task.title,
                'notes': task.notes,
                'is_completed': task.is_completed,
                'created_at': task.created_at.isoformat() if task.created_at else None
            },
            'children': [
                {
                    'id': str(child.id),
                    'title': child.title,
                    'notes': child.notes,
                    'is_completed': child.is_completed,
                    'created_at': child.created_at.isoformat() if child.created_at else None
                }
                for child in children
            ]
        }

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

    def disconnect(self):
        """Disconnect from AWS SQS."""
        self.sqs_client = None
        self._connected = False
        logger.info("Disconnected from AWS SQS")

    def is_connected(self) -> bool:
        """Check if connected to AWS SQS."""
        return self._connected


class HybridPrinterService:
    """
    Hybrid printer service supporting both direct and cloud printing.

    Automatically selects the best available method based on configuration
    and network availability.
    """

    def __init__(self, printer_service, cloud_queue: Optional[CloudPrintQueue] = None):
        """
        Initialize hybrid printer service.

        Args:
            printer_service: PrinterService instance for direct printing
            cloud_queue: Optional CloudPrintQueue for cloud printing
        """
        self.printer_service = printer_service
        self.cloud_queue = cloud_queue

        logger.info("HybridPrinterService initialized")

    def print_task_card(self, task: Task, children: List[Task]) -> bool:
        """
        Print task card using best available method.

        Args:
            task: Parent task to print
            children: Child tasks to include

        Returns:
            True if print successful via any method, False otherwise
        """
        # Try direct printing first
        try:
            if not self.printer_service.is_connected():
                self.printer_service.connect()

            self.printer_service.print_task_card(task, children)
            logger.info(f"Printed via direct connection: {task.title}")
            return True

        except Exception as e:
            logger.warning(f"Direct printing failed: {e}")

            # Fall back to cloud queue
            if self.cloud_queue and self.cloud_queue.is_connected():
                logger.info("Falling back to cloud queue")
                result = self.cloud_queue.send_print_job(task, children)

                if result:
                    logger.info(f"Queued for cloud printing: {task.title}")
                    return True

            logger.error(f"All printing methods failed for task: {task.title}")
            return False


# Example usage
if __name__ == "__main__":
    from taskui.logging_config import setup_logging
    import uuid

    setup_logging()

    # Test cloud queue configuration
    config = CloudPrintConfig(
        queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/taskui-print-queue",
        region="us-east-1",
        mode=CloudPrintMode.CLOUD_QUEUE
    )

    queue = CloudPrintQueue(config)

    # Test connection
    if queue.connect():
        print("✅ Connected to AWS SQS")

        # Create test task
        list_id = uuid.uuid4()
        task = Task(
            id=uuid.uuid4(),
            list_id=list_id,
            title="Test Cloud Print",
            notes="Testing cloud print queue",
            is_completed=False,
            created_at=datetime.now()
        )

        children = [
            Task(id=uuid.uuid4(), list_id=list_id, title="Child 1", is_completed=False, created_at=datetime.now()),
            Task(id=uuid.uuid4(), list_id=list_id, title="Child 2", is_completed=True, created_at=datetime.now()),
        ]

        # Send print job
        if queue.send_print_job(task, children):
            print("✅ Print job queued successfully")
            depth = queue.get_queue_depth()
            print(f"📊 Queue depth: {depth}")
        else:
            print("❌ Failed to queue print job")

        queue.disconnect()
    else:
        print("❌ Failed to connect to AWS SQS")
