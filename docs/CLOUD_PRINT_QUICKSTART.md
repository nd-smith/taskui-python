# Cloud Print Quick Start

**Problem:** Corporate VPN blocks access to your Raspberry Pi printer
**Solution:** Cloud print relay via AWS SQS

## 5-Minute Setup

### 1. Test Connectivity (Work Machine)
```bash
python scripts/test_aws_connectivity.py
```
✅ Must see "CONNECTIVITY TEST PASSED"

### 2. Create AWS Queue
1. https://console.aws.amazon.com/sqs/
2. Create queue: `taskui-print-queue`
3. Copy the Queue URL

### 3. Get AWS Credentials
1. https://console.aws.amazon.com/iam/
2. Create user: `taskui-printer`
3. Attach policy: `AmazonSQSFullAccess`
4. Copy Access Key ID and Secret Access Key 

### 4. Configure Work Machine
```bash
pip install boto3
aws configure
# Enter your credentials
```

Set queue URL:
```bash
export TASKUI_CLOUD_QUEUE_URL="https://sqs.us-east-1.amazonaws.com/856992658652/taskui-print-queue"
export TASKUI_CLOUD_MODE="cloud"
```

### 5. Configure Raspberry Pi
```bash
# Copy script to Pi
scp scripts/pi_print_worker.py nick@192.168.50.99:/home/pi/

# SSH to Pi
ssh pi@your-pi-ip

# Install dependencies
pip install boto3 python-escpos

# Configure AWS
aws configure
# Use SAME credentials as work machine

# Test worker
python3 /home/pi/pi_print_worker.py \
  --queue-url "your-queue-url" \
  --printer-host 192.168.50.99
```

### 6. Set Up Auto-Start (Pi)
```bash
# Edit service file with your queue URL
nano /home/pi/taskui-printer.service

# Install service
sudo cp /home/pi/taskui-printer.service /etc/systemd/system/
sudo systemctl enable taskui-printer
sudo systemctl start taskui-printer
```

### 7. Test End-to-End
From work machine, send a test print job using TaskUI.
Check Pi is receiving and printing.

---

## Your Next Steps

### Step 1: Configure Work Machine (Right Now)

```bash
# Install boto3 if not already installed
pip install boto3

# Configure AWS credentials
aws configure
# AWS Access Key ID: [paste your access key]
# AWS Secret Access Key: [paste your secret key]
# Default region name: us-east-1
# Default output format: json

# Set environment variables for this session
export TASKUI_CLOUD_QUEUE_URL="https://sqs.us-east-1.amazonaws.com/856992658652/taskui-print-queue"
export TASKUI_CLOUD_MODE="cloud"

# Or add to your shell profile for persistence (~/.bashrc or ~/.zshrc):
echo 'export TASKUI_CLOUD_QUEUE_URL="https://sqs.us-east-1.amazonaws.com/856992658652/taskui-print-queue"' >> ~/.bashrc
echo 'export TASKUI_CLOUD_MODE="cloud"' >> ~/.bashrc
```

**Test your work machine setup:**
```bash
# Test AWS connectivity
python scripts/test_aws_connectivity.py

# Expected output: ✅ CONNECTIVITY TEST PASSED
```

### Step 2: Configure Raspberry Pi

```bash
# Copy the worker script to your Pi (replace YOUR-PI-IP with actual IP)
scp scripts/pi_print_worker.py pi@YOUR-PI-IP:/home/pi/
scp scripts/taskui-printer.service pi@YOUR-PI-IP:/home/pi/

# SSH to your Pi
ssh pi@YOUR-PI-IP
```

**On the Raspberry Pi, run:**
```bash
# Install dependencies
pip install boto3 python-escpos

# Configure AWS (use SAME credentials as work machine)
aws configure
# AWS Access Key ID: [paste your access key]
# AWS Secret Access Key: [paste your secret key]
# Default region name: us-east-1
# Default output format: json

# Test the worker manually first
python3 /home/pi/pi_print_worker.py \
  --queue-url "https://sqs.us-east-1.amazonaws.com/856992658652/taskui-print-queue" \
  --printer-host 192.168.50.99 \
  --printer-port 9100

# You should see:
# INFO - Connected to SQS queue: ...
# INFO - Connected to printer: 192.168.50.99:9100
# INFO - Starting print worker polling loop
```

**If manual test works, set up auto-start:**
```bash
# Edit the service file to add your queue URL
nano /home/pi/taskui-printer.service

# Update the ExecStart line to:
# ExecStart=/usr/bin/python3 /home/pi/pi_print_worker.py \
#     --queue-url https://sqs.us-east-1.amazonaws.com/856992658652/taskui-print-queue \
#     --printer-host 192.168.50.99 \
#     --printer-port 9100 \
#     --region us-east-1

# Install and start the service
sudo cp /home/pi/taskui-printer.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable taskui-printer
sudo systemctl start taskui-printer

# Check it's running
sudo systemctl status taskui-printer
```

### Step 3: Test End-to-End

**From your work machine (on VPN):**
```bash
# Send a test print job through the cloud queue
python taskui/services/cloud_print_queue.py

# Or use your normal TaskUI print command
# The job will route through AWS SQS to your Pi
```

**Monitor on the Pi:**
```bash
# Watch the logs in real-time
sudo journalctl -u taskui-printer -f

# You should see:
# INFO - Processing job: [your task title]
# INFO - Printed: [your task title] with X children
```

### Step 4: Verify Queue Status

```bash
# Check how many messages are in the queue
aws sqs get-queue-attributes \
  --queue-url "https://sqs.us-east-1.amazonaws.com/856992658652/taskui-print-queue" \
  --attribute-names ApproximateNumberOfMessages
```

---

## Verification

**Work Machine:**
```bash
# Check AWS connection
python -c "import boto3; print('✅ boto3 works')"

# Check queue configured
echo $TASKUI_CLOUD_QUEUE_URL
```

**Raspberry Pi:**
```bash
# Check service running
sudo systemctl status taskui-printer

# Check logs
sudo journalctl -u taskui-printer -f
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| boto3 not found | `pip install boto3` |
| AWS credentials error | Run `aws configure` |
| Can't reach AWS | VPN is blocking - see alternatives in setup guide |
| Pi not printing | Check `sudo journalctl -u taskui-printer -f` |
| Queue not working | Verify queue URL matches in both places |

## Full Documentation

See `docs/cloud_printing_setup.md` for complete setup guide.

## Cost

- **Free tier:** 1 million requests/month
- **Typical usage:** 300 requests/month (10 prints/day)
- **Cost:** $0 on free tier
