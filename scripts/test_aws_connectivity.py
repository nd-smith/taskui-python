#!/usr/bin/env python3
"""
Test script to verify AWS SQS connectivity and queue access.
Run this on your work machine to verify cloud relay will work.
"""

import sys
import os

def test_queue_connectivity():
    """Test connectivity to specific TaskUI print queue"""

    # Get queue URL from environment or use default
    queue_url = os.getenv(
        'TASKUI_CLOUD_QUEUE_URL',
        'https://sqs.us-east-1.amazonaws.com/856992658652/taskui-print-queue'
    )

    print("=" * 60)
    print("AWS SQS Queue Connectivity Test")
    print("=" * 60)
    print(f"\nQueue URL: {queue_url}")
    print()

    try:
        import boto3
        from botocore.exceptions import NoCredentialsError, ClientError
        print("✅ boto3 library available")
    except ImportError:
        print("❌ boto3 not installed")
        print("   Install with: pip install boto3")
        return False

    # Test AWS credentials
    print("\nTesting AWS credentials...")
    try:
        sqs = boto3.client('sqs', region_name='us-east-1')

        # Test basic auth by listing queues
        response = sqs.list_queues()
        print("✅ AWS credentials configured and working")

        if 'QueueUrls' in response and response['QueueUrls']:
            print(f"✅ Found {len(response['QueueUrls'])} queue(s) in your account")

    except NoCredentialsError:
        print("❌ AWS credentials not configured")
        print("\n   Fix by running:")
        print("   aws configure")
        print("   OR")
        print("   Create ~/.aws/credentials with your access key")
        return False
    except Exception as e:
        print(f"❌ Error connecting to AWS: {e}")
        return False

    # Test specific queue
    print(f"\nTesting specific queue access...")
    try:
        response = sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['ApproximateNumberOfMessages', 'QueueArn']
        )

        print("✅ Successfully connected to your queue!")
        print(f"✅ Messages in queue: {response['Attributes']['ApproximateNumberOfMessages']}")
        print(f"✅ Queue ARN: {response['Attributes']['QueueArn']}")

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nYour work machine can successfully:")
        print("  - Reach AWS SQS")
        print("  - Authenticate with your credentials")
        print("  - Access your print queue")
        print("\nYou're ready to send print jobs through the cloud!")

        return True

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']

        print(f"❌ Error: {error_code}")
        print(f"   {error_msg}")

        if error_code == 'AWS.SimpleQueueService.NonExistentQueue':
            print("\n⚠️  Queue does not exist or URL is wrong")
            print("\n   To find your queue URL:")
            print("   1. Go to: https://console.aws.amazon.com/sqs/")
            print("   2. Click on 'taskui-print-queue'")
            print("   3. Copy the URL shown")
            print("\n   Or run: aws sqs list-queues --region us-east-1")

        elif error_code == 'AccessDenied':
            print("\n⚠️  Access denied - check your credentials")
            print("   Your credentials may be wrong or lack permissions")
            print("\n   Fix by running: aws configure")

        elif error_code == 'InvalidAddress':
            print("\n⚠️  Invalid queue URL format")
            print("   Make sure you're using the full queue URL")
            print("   Format: https://sqs.REGION.amazonaws.com/ACCOUNT_ID/QUEUE_NAME")

        return False

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = test_queue_connectivity()
    sys.exit(0 if success else 1)