# Cloud Print Relay Setup Guide

This guide explains how to set up cloud-based printing for TaskUI when direct network access to the printer is blocked (e.g., by corporate VPN).

## Architecture Overview

```
Work Machine (VPN) → AWS SQS Queue → Raspberry Pi → Thermal Printer
```

**How it works:**
1. Your work machine sends print jobs to AWS SQS (cloud queue)
2. Raspberry Pi continuously polls the queue
3. When jobs arrive, Pi prints them and removes them from queue
4. Works even when work machine can't reach Pi directly

## Prerequisites

- AWS account (free tier includes 1M SQS requests/month)
- Raspberry Pi with network connection
- Thermal printer connected to Raspberry Pi
- Corporate VPN allows HTTPS access to AWS services

## Step 1: Test AWS Connectivity

On your **work machine**, run the connectivity test:

```bash
cd /home/nick/Projects/taskui-python
python scripts/test_aws_connectivity.py
```

**Expected output:**
```
✅ boto3 library available
✅ Can reach AWS SQS endpoint
✅ CONNECTIVITY TEST PASSED
```

If this fails, AWS is blocked by your VPN and you'll need an alternative solution.

## Step 2: Set Up AWS SQS

### 2.1 Create AWS Account
1. Go to https://aws.amazon.com/free/
2. Sign up for free tier account
3. Verify email and payment method

### 2.2 Create SQS Queue
1. Log into AWS Console: https://console.aws.amazon.com/
2. Navigate to SQS: https://console.aws.amazon.com/sqs/
3. Click **Create queue**
4. Settings:
   - **Name:** `taskui-print-queue`
   - **Type:** Standard Queue
   - **Visibility timeout:** 30 seconds
   - **Message retention:** 4 days
   - **Receive message wait time:** 20 seconds (long polling)
   - Leave other settings as default
5. Click **Create queue**
6. **Save the Queue URL** - you'll need it later
   - Example: `https://sqs.us-east-1.amazonaws.com/123456789012/taskui-print-queue`

### 2.3 Create IAM User for TaskUI
1. Navigate to IAM: https://console.aws.amazon.com/iam/
2. Click **Users** → **Add users**
3. Username: `taskui-printer`
4. Select **Access key - Programmatic access**
5. Click **Next: Permissions**
6. Click **Attach policies directly**
7. Search and select: `AmazonSQSFullAccess`
8. Click **Next** through to **Create user**
9. **Download credentials** or copy:
   - Access Key ID
   - Secret Access Key
   - ⚠️ **Keep these secret!** Don't commit to git!

## Step 3: Configure Work Machine

### 3.1 Install boto3
```bash
pip install boto3
```

### 3.2 Configure AWS Credentials

**Option A: AWS CLI (recommended)**
```bash
pip install awscli
aws configure
# Enter your Access Key ID, Secret Access Key, region (us-east-1)
```

**Option B: Environment variables**
```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_DEFAULT_REGION="us-east-1"
```

**Option C: TaskUI config file**
Edit `~/.taskui/config.ini`:
```ini
[cloud_print]
queue_url = https://sqs.us-east-1.amazonaws.com/123456789012/taskui-print-queue
region = us-east-1
mode = auto
aws_access_key_id = your-access-key-id
aws_secret_access_key = your-secret-access-key
```

⚠️ **Security Note:** Don't commit credentials to git! Use AWS CLI or environment variables for better security.

### 3.3 Test Cloud Queue
```bash
python taskui/services/cloud_print_queue.py
```

## Step 4: Set Up Raspberry Pi

### 4.1 Copy Worker Script to Pi
```bash
scp scripts/pi_print_worker.py pi@your-pi-ip:/home/pi/
```

### 4.2 Install Dependencies on Pi
```bash
ssh pi@your-pi-ip

# Install Python packages
pip install boto3 python-escpos

# Install AWS CLI for easy credential configuration
pip install awscli
```

### 4.3 Configure AWS Credentials on Pi
```bash
# On the Raspberry Pi
aws configure
# Enter the SAME credentials you used on work machine
```

### 4.4 Test Print Worker
```bash
python3 /home/pi/pi_print_worker.py \
  --queue-url "https://sqs.us-east-1.amazonaws.com/123456789012/taskui-print-queue" \
  --printer-host 192.168.1.100 \
  --printer-port 9100
```

You should see:
```
INFO - Print worker initialized for queue: ...
INFO - Connected to SQS queue: ...
INFO - Connected to printer: 192.168.1.100:9100
INFO - Starting print worker polling loop
```

Press `Ctrl+C` to stop when you're ready to set up auto-start.

### 4.5 Set Up Auto-Start with systemd

1. **Edit the service file** with your queue URL:
```bash
nano /home/pi/taskui-printer.service
```

Update the `ExecStart` line with your actual queue URL:
```ini
ExecStart=/usr/bin/python3 /home/pi/pi_print_worker.py \
    --queue-url https://sqs.us-east-1.amazonaws.com/YOUR_ACCOUNT_ID/taskui-print-queue \
    --printer-host 192.168.1.100 \
    --printer-port 9100 \
    --region us-east-1
```

2. **Install the service:**
```bash
sudo cp /home/pi/taskui-printer.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable taskui-printer.service
sudo systemctl start taskui-printer.service
```

3. **Check status:**
```bash
sudo systemctl status taskui-printer
```

4. **View logs:**
```bash
sudo journalctl -u taskui-printer -f
```

## Step 5: Update TaskUI to Use Cloud Printing

### 5.1 Set Cloud Print Mode

**Option A: Environment variable** (temporary)
```bash
export TASKUI_CLOUD_MODE="cloud"
export TASKUI_CLOUD_QUEUE_URL="https://sqs.us-east-1.amazonaws.com/123456789012/taskui-print-queue"
```

**Option B: Config file** (persistent)
Edit `~/.taskui/config.ini`:
```ini
[printer]
host = 192.168.1.100
port = 9100
timeout = 60
detail_level = minimal

[cloud_print]
queue_url = https://sqs.us-east-1.amazonaws.com/123456789012/taskui-print-queue
region = us-east-1
mode = cloud
```

**Mode options:**
- `direct` - Only try direct printer connection
- `cloud` - Only use cloud queue
- `auto` - Try direct first, fallback to cloud (recommended)

### 5.2 Test End-to-End

From your work machine (on VPN):
```bash
# Your normal TaskUI print command
# The system will automatically route through cloud queue if direct fails
```

## Step 6: Enable End-to-End Encryption (HIGHLY RECOMMENDED)

End-to-end encryption protects your print job data before it leaves your machine and ensures only your Raspberry Pi can decrypt it. This is **critical** if:
- SSL verification is disabled (corporate proxies)
- You don't trust AWS to see your task data
- Your tasks contain sensitive information

### 6.1 Why Encryption is Important

Without encryption:
- AWS can read your print job messages (task titles, notes, children)
- Man-in-the-middle attacks are possible if SSL is disabled
- Messages are stored in plaintext in SQS

With encryption:
- Only your machine and Raspberry Pi can read messages
- AWS sees only encrypted data
- Protection against network attacks

### 6.2 Generate Encryption Key

On your **work machine**, generate a new encryption key:

```bash
python scripts/generate_encryption_key.py
```

This will output a base64-encoded encryption key like:
```
MjU2LWJpdCBBRVMta2V5IGhlcmU...
```

**IMPORTANT:**
- Keep this key secret (like a password)
- Never commit it to git
- Store a backup in a secure password manager
- You'll need to enter it on both machines

### 6.3 Configure Work Machine Encryption

Edit `~/.taskui/config.ini` and add the encryption key:

```ini
[cloud_print]
queue_url = https://sqs.us-east-1.amazonaws.com/123456789012/taskui-print-queue
region = us-east-1
mode = auto
encryption_key = YOUR_GENERATED_KEY_HERE
```

Or use an environment variable (more secure):
```bash
export TASKUI_ENCRYPTION_KEY="YOUR_GENERATED_KEY_HERE"
```

### 6.4 Configure Raspberry Pi Encryption

**The Pi must use the SAME encryption key.**

**Option A: Environment variable** (recommended)

Edit the systemd service file:
```bash
sudo nano /etc/systemd/system/taskui-printer.service
```

Add the environment variable in the `[Service]` section:
```ini
[Service]
Type=simple
User=pi
Environment="TASKUI_ENCRYPTION_KEY=YOUR_GENERATED_KEY_HERE"
ExecStart=/usr/bin/python3 /home/pi/pi_print_worker.py \
    --queue-url https://sqs.us-east-1.amazonaws.com/YOUR_ACCOUNT_ID/taskui-print-queue \
    --printer-host 192.168.1.100 \
    --printer-port 9100
Restart=always
RestartSec=10
```

Reload the service:
```bash
sudo systemctl daemon-reload
sudo systemctl restart taskui-printer
```

**Option B: Command line argument**

Update the `ExecStart` line in your systemd service:
```ini
ExecStart=/usr/bin/python3 /home/pi/pi_print_worker.py \
    --queue-url https://sqs.us-east-1.amazonaws.com/YOUR_ACCOUNT_ID/taskui-print-queue \
    --printer-host 192.168.1.100 \
    --encryption-key YOUR_GENERATED_KEY_HERE
```

### 6.5 Install Encryption Dependencies

On **both machines** (work machine and Raspberry Pi):

```bash
pip install cryptography
```

### 6.6 Verify Encryption is Working

**On work machine:** Send a test print job. Check the logs for:
```
INFO - End-to-end encryption enabled for cloud print messages
INFO - Print job queued (encrypted): Your Task Title
```

**On Raspberry Pi:** Check the worker logs:
```bash
sudo journalctl -u taskui-printer -f
```

Look for:
```
INFO - End-to-end encryption enabled for received messages
INFO - Processing job ...: Your Task Title
```

**If encryption is NOT working**, you'll see warnings:
```
WARNING - End-to-end encryption NOT enabled - messages will be sent in plaintext
```

### 6.7 Troubleshooting Encryption

**Key mismatch error:**
```
ERROR - Decryption failed: ...
```
- Ensure the SAME key is on both machines
- Check for extra spaces or newlines in the key
- Regenerate key and update both sides

**Missing cryptography package:**
```
ModuleNotFoundError: No module named 'cryptography'
```
```bash
pip install cryptography
```

**Encrypted vs plaintext mismatch:**
- If work machine has encryption enabled but Pi doesn't: Messages will be lost
- If Pi has encryption enabled but work machine doesn't: Messages will be lost
- **Solution:** Both sides must have matching configuration

### 6.8 Key Rotation (Advanced)

For maximum security, rotate your encryption key periodically:

1. Generate a new key: `python scripts/generate_encryption_key.py`
2. Update both machines with the new key
3. Restart the Raspberry Pi worker: `sudo systemctl restart taskui-printer`
4. Delete the old key from all locations

**Note:** Messages encrypted with the old key cannot be decrypted with the new key. Purge the queue when rotating keys:
```bash
aws sqs purge-queue --queue-url "YOUR_QUEUE_URL"
```

## Troubleshooting

### Work Machine Issues

**boto3 not found:**
```bash
pip install boto3
```

**NoCredentialsError:**
- Run `aws configure` and enter your credentials
- Or set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables

**Cannot reach AWS SQS:**
- Your VPN is blocking AWS
- Try accessing https://console.aws.amazon.com/ in browser
- If blocked, consider Azure Queue Storage or alternative cloud service

### Raspberry Pi Issues

**Printer not found:**
```bash
# Test printer connection manually
python3 -c "from escpos.printer import Network; p = Network('192.168.1.100', 9100); p.text('Test\n'); p.cut()"
```

**Worker crashes:**
```bash
# Check logs
sudo journalctl -u taskui-printer -n 50

# Common fixes:
# - Verify printer IP is correct
# - Check printer is powered on and connected
# - Verify AWS credentials are configured
```

**Queue not polling:**
```bash
# Restart service
sudo systemctl restart taskui-printer

# Check network
ping sqs.us-east-1.amazonaws.com
```

### Queue Management

**View queue messages:**
```bash
aws sqs get-queue-attributes \
  --queue-url "https://sqs.us-east-1.amazonaws.com/123456789012/taskui-print-queue" \
  --attribute-names ApproximateNumberOfMessages
```

**Purge queue (clear all messages):**
```bash
aws sqs purge-queue \
  --queue-url "https://sqs.us-east-1.amazonaws.com/123456789012/taskui-print-queue"
```

## Cost Considerations

**AWS Free Tier (first 12 months):**
- 1 million SQS requests per month - FREE
- Standard requests: $0.40 per million after free tier

**Typical usage:**
- ~10 prints/day × 30 days = 300 requests/month
- Well within free tier
- Even at 1000 prints/month, cost is negligible

## Security Best Practices

1. **Enable end-to-end encryption** (Step 6) - CRITICAL for protecting your data
2. **Use IAM user** with minimal permissions (SQS only)
3. **Never commit credentials or encryption keys** to git repositories
4. **Use AWS credentials file** or IAM roles instead of config file
5. **Rotate credentials and encryption keys** periodically
6. **Enable CloudTrail** to audit queue access (optional)
7. **Set queue retention** to minimum needed (4 days default)
8. **Store encryption key** in a password manager for backup

## Alternative Cloud Services

If AWS is blocked, consider these alternatives:

### Azure Queue Storage
- Part of Azure Storage Account
- Similar pricing and functionality
- Requires `azure-storage-queue` Python package

### Google Cloud Pub/Sub
- Google Cloud messaging service
- Requires `google-cloud-pubsub` Python package

### Self-Hosted Options
- Simple REST API on Heroku/Railway/Render
- Redis with pub/sub
- RabbitMQ hosted service

Contact for help implementing alternatives if AWS doesn't work.

## Monitoring and Maintenance

### Daily Checks
```bash
# Check Pi is printing
sudo systemctl status taskui-printer

# Check queue depth
aws sqs get-queue-attributes --queue-url "YOUR_QUEUE_URL" \
  --attribute-names ApproximateNumberOfMessages
```

### Monthly Checks
- Review AWS billing (should be $0 on free tier)
- Check Pi system updates: `sudo apt update && sudo apt upgrade`
- Verify printer supplies (paper, maintenance)

## Support

For issues or questions:
1. Check logs: `sudo journalctl -u taskui-printer -f`
2. Test connectivity: `python scripts/test_aws_connectivity.py`
3. Verify queue: AWS Console → SQS → View messages
4. Review this guide's troubleshooting section
