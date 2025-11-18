#!/usr/bin/env python3
"""
Test script to verify AWS SQS connectivity from corporate VPN
Run this on your work machine to verify cloud relay will work
"""

import sys
import json
from datetime import datetime

def test_aws_connectivity():
    """Test if we can reach AWS SQS"""
    print("Testing AWS SQS connectivity...")
    print("=" * 50)

    try:
        import boto3
        from botocore.exceptions import NoCredentialsError, ClientError
        print("✅ boto3 library available")
    except ImportError:
        print("❌ boto3 not installed")
        print("   Install with: pip install boto3")
        return False

    # Test basic AWS connectivity (doesn't require credentials)
    try:
        import urllib.request
        import ssl

        # Test HTTPS access to AWS
        context = ssl.create_default_context()
        url = "https://sqs.us-east-1.amazonaws.com"

        print(f"\nTesting HTTPS access to {url}...")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

        try:
            response = urllib.request.urlopen(req, timeout=10, context=context)
            print(f"✅ Can reach AWS SQS endpoint (Status: {response.status})")
            connectivity_ok = True
        except urllib.error.HTTPError as e:
            # HTTP errors (401, 403, etc.) actually mean we CAN reach the service
            # We're just not authenticated yet, which is expected
            if e.code in [400, 403]:
                print(f"✅ Can reach AWS SQS endpoint (Got expected auth error: {e.code})")
                connectivity_ok = True
            else:
                print(f"⚠️  Unexpected HTTP error: {e.code}")
                connectivity_ok = False
        except urllib.error.URLError as e:
            print(f"❌ Cannot reach AWS SQS: {e.reason}")
            print("   Your VPN may be blocking AWS services")
            connectivity_ok = False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            connectivity_ok = False

    except Exception as e:
        print(f"❌ Network test failed: {e}")
        return False

    if not connectivity_ok:
        print("\n" + "=" * 50)
        print("❌ CONNECTIVITY TEST FAILED")
        print("AWS SQS is not reachable from your network")
        print("\nAlternatives to try:")
        print("  1. Test Azure Queue Storage (Office365 is accessible)")
        print("  2. Use GitHub API as message queue")
        print("  3. Host simple queue on accessible cloud service")
        return False

    print("\n" + "=" * 50)
    print("✅ CONNECTIVITY TEST PASSED")
    print("AWS SQS is reachable from your network")
    print("\nNext steps:")
    print("  1. Set up AWS account (free tier)")
    print("  2. Create SQS queue")
    print("  3. Configure AWS credentials")
    print("  4. Run the full implementation")

    # Instructions for AWS setup
    print("\n" + "=" * 50)
    print("AWS Setup Instructions:")
    print("  1. Go to https://aws.amazon.com/free/")
    print("  2. Create account (free tier includes 1M SQS requests/month)")
    print("  3. Go to SQS console: https://console.aws.amazon.com/sqs/")
    print("  4. Create new queue named 'taskui-print-queue'")
    print("  5. Create IAM user with SQS permissions")
    print("  6. Save credentials to ~/.aws/credentials")

    return True


def test_aws_with_credentials():
    """Test AWS SQS with actual credentials if configured"""
    print("\n" + "=" * 50)
    print("Testing with AWS credentials...")

    try:
        import boto3
        from botocore.exceptions import NoCredentialsError, ClientError

        # Try to create SQS client
        sqs = boto3.client('sqs', region_name='us-east-1')

        # Try to list queues (doesn't create anything)
        response = sqs.list_queues()

        print("✅ Successfully authenticated with AWS")

        if 'QueueUrls' in response and response['QueueUrls']:
            print(f"✅ Found {len(response['QueueUrls'])} existing queue(s):")
            for queue_url in response['QueueUrls']:
                queue_name = queue_url.split('/')[-1]
                print(f"   - {queue_name}")
        else:
            print("ℹ️  No existing queues found")
            print("   You'll need to create 'taskui-print-queue'")

        return True

    except NoCredentialsError:
        print("ℹ️  No AWS credentials configured yet")
        print("   This is expected if you haven't set up AWS")
        return None
    except ClientError as e:
        print(f"⚠️  AWS API error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    print(f"AWS Connectivity Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Test basic connectivity
    basic_ok = test_aws_connectivity()

    if basic_ok:
        # Test with credentials if available
        creds_ok = test_aws_with_credentials()

        if creds_ok is None:
            print("\n" + "=" * 50)
            print("READY FOR SETUP")
            print("Connectivity is good, now set up AWS credentials")
        elif creds_ok:
            print("\n" + "=" * 50)
            print("✅ FULLY CONFIGURED")
            print("Ready to implement cloud print relay!")
        else:
            print("\n" + "=" * 50)
            print("⚠️  CREDENTIALS ISSUE")
            print("Check your AWS credentials configuration")
    else:
        print("\n" + "=" * 50)
        print("❌ CONNECTIVITY BLOCKED")
        print("Need to try alternative cloud service")

    sys.exit(0 if basic_ok else 1)
