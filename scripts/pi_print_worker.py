#!/usr/bin/env python3
"""
Raspberry Pi Print Worker - Polls AWS SQS and prints jobs.

This script runs on the Raspberry Pi connected to the thermal printer.
It continuously polls the AWS SQS queue for print jobs and executes them.

Setup on Raspberry Pi:
1. Install dependencies: pip install boto3 python-escpos
2. Configure AWS credentials: aws configure
3. Set queue URL in environment or config
4. Run as systemd service for auto-start

Usage:
    python pi_print_worker.py --queue-url <SQS_URL>
    python pi_print_worker.py --config /path/to/config.ini
"""

import argparse
import json
import logging
import time
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Raspberry Pi specific imports
try:
    from escpos.printer import Network
    import boto3
    from botocore.exceptions import NoCredentialsError, ClientError
    from taskui.services.encryption import MessageEncryption
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Install with: pip install boto3 python-escpos cryptography")
    sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/taskui-printer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('pi_print_worker')


class PrintWorkerConfig:
    """Configuration for print worker."""

    def __init__(
        self,
        queue_url: str,
        printer_host: str = "192.168.50.99",
        printer_port: int = 9100,
        region: str = "us-east-1",
        poll_interval: int = 5,
        visibility_timeout: int = 30,
        wait_time: int = 20,
        encryption_key: Optional[str] = None
    ):
        """
        Initialize print worker configuration.

        Args:
            queue_url: AWS SQS queue URL
            printer_host: Thermal printer IP address
            printer_port: Thermal printer port
            region: AWS region
            poll_interval: Seconds between polls (short polling)
            visibility_timeout: Message visibility timeout (seconds)
            wait_time: Long polling wait time (seconds, 0-20)
            encryption_key: Base64-encoded encryption key for end-to-end encryption
        """
        self.queue_url = queue_url
        self.printer_host = printer_host
        self.printer_port = printer_port
        self.region = region
        self.poll_interval = poll_interval
        self.visibility_timeout = visibility_timeout
        self.wait_time = wait_time
        self.encryption_key = encryption_key

    @classmethod
    def from_args(cls, args) -> "PrintWorkerConfig":
        """Create config from command line arguments."""
        # Get encryption key from args or environment variable
        encryption_key = getattr(args, 'encryption_key', None)
        if not encryption_key:
            encryption_key = os.environ.get('TASKUI_ENCRYPTION_KEY')

        return cls(
            queue_url=args.queue_url,
            printer_host=args.printer_host,
            printer_port=args.printer_port,
            region=args.region,
            poll_interval=args.poll_interval,
            visibility_timeout=args.visibility_timeout,
            wait_time=args.wait_time,
            encryption_key=encryption_key
        )


class PrintWorker:
    """Worker that polls SQS and executes print jobs."""

    def __init__(self, config: PrintWorkerConfig):
        """
        Initialize print worker.

        Args:
            config: PrintWorkerConfig instance
        """
        self.config = config
        self.sqs_client = None
        self.printer = None
        self.running = False
        self.stats = {
            'jobs_processed': 0,
            'jobs_failed': 0,
            'started_at': None
        }

        # Initialize encryption
        self.encryption = MessageEncryption(config.encryption_key)
        if self.encryption.enabled:
            logger.info("End-to-end encryption enabled for received messages")
        else:
            logger.warning("End-to-end encryption NOT enabled - expecting plaintext messages")

        logger.info(f"Print worker initialized for queue: {config.queue_url}")

    def connect_sqs(self) -> bool:
        """
        Connect to AWS SQS.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.sqs_client = boto3.client('sqs', region_name=self.config.region)

            # Verify queue exists
            self.sqs_client.get_queue_attributes(
                QueueUrl=self.config.queue_url,
                AttributeNames=['QueueArn']
            )

            logger.info(f"Connected to SQS queue: {self.config.queue_url}")
            return True

        except NoCredentialsError:
            logger.error("AWS credentials not configured")
            return False
        except ClientError as e:
            logger.error(f"Failed to connect to SQS: {e}")
            return False

    def connect_printer(self) -> bool:
        """
        Connect to thermal printer.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.printer = Network(
                self.config.printer_host,
                port=self.config.printer_port,
                timeout=60
            )

            # Test print
            self.printer.text("TaskUI Print Worker\n")
            self.printer.text(f"Connected: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.printer.text("\n\n")
            self.printer.cut(mode="FULL")
            self.printer.close()

            logger.info(f"Connected to printer: {self.config.printer_host}:{self.config.printer_port}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to printer: {e}")
            return False

    def poll_and_print(self):
        """Main polling loop - continuously check for and process jobs."""
        self.running = True
        self.stats['started_at'] = datetime.now()

        logger.info("Starting print worker polling loop")
        logger.info(f"Poll interval: {self.config.poll_interval}s, Wait time: {self.config.wait_time}s")

        while self.running:
            try:
                # Receive messages from SQS (long polling)
                response = self.sqs_client.receive_message(
                    QueueUrl=self.config.queue_url,
                    MaxNumberOfMessages=1,
                    VisibilityTimeout=self.config.visibility_timeout,
                    WaitTimeSeconds=self.config.wait_time,
                    MessageAttributeNames=['All']
                )

                messages = response.get('Messages', [])

                if not messages:
                    logger.debug("No messages in queue")
                    time.sleep(self.config.poll_interval)
                    continue

                # Process each message
                for message in messages:
                    self._process_message(message)

            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}", exc_info=True)
                time.sleep(self.config.poll_interval)

        logger.info("Print worker stopped")
        self._print_stats()

    def _process_message(self, message: Dict[str, Any]):
        """
        Process a single SQS message (print job).

        Args:
            message: SQS message containing print job
        """
        message_id = message['MessageId']
        receipt_handle = message['ReceiptHandle']

        try:
            # Get encrypted message body
            encrypted_body = message['Body']

            # Decrypt the message (if encryption is enabled)
            job_data = self.encryption.decrypt_message(encrypted_body)

            logger.info(f"Processing job {message_id}: {job_data.get('task', {}).get('title', 'Unknown')}")

            # Execute print job
            self._execute_print_job(job_data)

            # Delete message from queue (success)
            self.sqs_client.delete_message(
                QueueUrl=self.config.queue_url,
                ReceiptHandle=receipt_handle
            )

            self.stats['jobs_processed'] += 1
            logger.info(f"Successfully processed job {message_id}")

        except Exception as e:
            logger.error(f"Failed to process job {message_id}: {e}", exc_info=True)
            self.stats['jobs_failed'] += 1

            # Message will become visible again after visibility timeout
            # Consider implementing dead-letter queue for repeated failures

    def _execute_print_job(self, job_data: Dict[str, Any]):
        """
        Execute actual print job.

        Args:
            job_data: Deserialized print job data
        """
        task = job_data.get('task', {})
        children = job_data.get('children', [])

        # Reconnect to printer for each job (escpos closes after each print)
        self.printer = Network(
            self.config.printer_host,
            port=self.config.printer_port,
            timeout=60
        )

        # TITLE - Big and bold
        self.printer.set(font='a', bold=True, double_height=True, double_width=True)
        self.printer.text(f"\n{task['title']}\n\n\n")

        # BODY - Small font
        self.printer.set(font='b', bold=False, double_height=False, double_width=False)

        if children:
            # Print children as checkboxes
            for i, child in enumerate(children):
                checkbox = "[X]" if child.get('is_completed', False) else "[ ]"
                self.printer.text(f"{checkbox} {child['title']}\n")
                if i < len(children) - 1:
                    self.printer.text("\n")
        elif task.get('notes'):
            # Print notes
            self.printer.text(f"{task['notes']}\n")

        # Spacing and cut
        self.printer.text("\n\n\n")
        self.printer.cut(mode="FULL")
        self.printer.close()

        logger.info(f"Printed: {task['title']} with {len(children)} children")

    def _print_stats(self):
        """Print worker statistics."""
        runtime = datetime.now() - self.stats['started_at']
        logger.info("=" * 50)
        logger.info("Print Worker Statistics")
        logger.info(f"Runtime: {runtime}")
        logger.info(f"Jobs processed: {self.stats['jobs_processed']}")
        logger.info(f"Jobs failed: {self.stats['jobs_failed']}")
        logger.info("=" * 50)

    def shutdown(self):
        """Graceful shutdown."""
        logger.info("Shutting down print worker...")
        self.running = False

        if self.printer:
            try:
                self.printer.close()
            except:
                pass


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Raspberry Pi Print Worker for TaskUI cloud printing'
    )

    parser.add_argument(
        '--queue-url',
        required=True,
        help='AWS SQS queue URL'
    )
    parser.add_argument(
        '--printer-host',
        default='192.168.50.99',
        help='Thermal printer IP address (default: 192.168.50.99)'
    )
    parser.add_argument(
        '--printer-port',
        type=int,
        default=9100,
        help='Thermal printer port (default: 9100)'
    )
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    parser.add_argument(
        '--poll-interval',
        type=int,
        default=5,
        help='Polling interval in seconds (default: 5)'
    )
    parser.add_argument(
        '--visibility-timeout',
        type=int,
        default=30,
        help='Message visibility timeout in seconds (default: 30)'
    )
    parser.add_argument(
        '--wait-time',
        type=int,
        default=20,
        help='Long polling wait time in seconds, 0-20 (default: 20)'
    )
    parser.add_argument(
        '--encryption-key',
        help='Base64-encoded encryption key (or use TASKUI_ENCRYPTION_KEY env var)'
    )

    args = parser.parse_args()

    # Create configuration
    config = PrintWorkerConfig.from_args(args)

    # Create and start worker
    worker = PrintWorker(config)

    # Connect to services
    if not worker.connect_sqs():
        logger.error("Failed to connect to SQS, exiting")
        sys.exit(1)

    if not worker.connect_printer():
        logger.error("Failed to connect to printer, exiting")
        sys.exit(1)

    # Start polling
    try:
        worker.poll_and_print()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        worker.shutdown()


if __name__ == "__main__":
    main()
