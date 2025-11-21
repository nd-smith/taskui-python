# TaskUI Configuration Directory

This directory contains all TaskUI configuration files, database, and logs.

## Directory Structure

```
config/
├── settings.ini.example  # Application settings template (optional)
├── taskui.db             # SQLite database (gitignored)
├── logs/                 # Application logs (gitignored)
│   └── taskui.log
├── .gitignore            # Ignore database and logs
└── README.md             # This file
```

## Configuration Files

### settings.ini (Optional)

Application settings for printer services and cloud print functionality.

**Example:** See `settings.ini.example` for available options.

**⚠️ SECURITY WARNING:**
- `settings.ini` is gitignored to prevent committing AWS credentials
- Use environment variables for credentials (recommended)
- Or copy example: `cp settings.ini.example settings.ini` and edit
- NEVER commit `settings.ini` with real credentials to git

If this file doesn't exist, printer features are disabled.

## Environment Variables

Environment variables override configuration file values:

### Logging
- `TASKUI_LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)

### Printer
- `TASKUI_PRINTER_HOST`: Printer IP address
- `TASKUI_PRINTER_PORT`: Printer TCP port
- `TASKUI_PRINTER_TIMEOUT`: Connection timeout (seconds)
- `TASKUI_PRINTER_DETAIL_LEVEL`: Print detail level

### Cloud Print
- `TASKUI_CLOUD_QUEUE_URL`: AWS SQS queue URL
- `TASKUI_CLOUD_REGION`: AWS region
- `TASKUI_CLOUD_MODE`: Connection mode (direct, cloud, auto)
- `TASKUI_ENCRYPTION_KEY`: Base64 encryption key
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key

## Database

**Location:** `config/taskui.db`

The SQLite database is created automatically on first run. It stores:
- Task lists
- Tasks and their hierarchy
- Timestamps and status flags

**Backup:** To backup your tasks, simply copy `taskui.db` to a safe location.

## Logs

**Location:** `config/logs/taskui.log`

Application logs with automatic rotation:
- Max size: 10MB per file
- Backup count: 5 files
- Format: timestamp - logger - level - message

## Version Control

The `.gitignore` file ensures that:
- ✅ Configuration files are committed (settings.ini.example)
- ❌ Database is not committed (taskui.db)
- ❌ Logs are not committed (logs/)
- ❌ Local overrides are not committed (*.local.ini)

## Getting Started

1. **For printer features (optional):**

   **Recommended:** Use environment variables (most secure):
   ```bash
   export TASKUI_CLOUD_QUEUE_URL="your-sqs-url"
   export AWS_ACCESS_KEY_ID="your-key"
   export AWS_SECRET_ACCESS_KEY="your-secret"
   export TASKUI_ENCRYPTION_KEY="your-base64-key"
   ```

   **Alternative:** Create settings.ini (gitignored):
   ```bash
   cp settings.ini.example settings.ini
   nano settings.ini  # Add credentials (will NOT be committed)
   ```

2. **Run TaskUI:**
   ```bash
   taskui
   ```

## Troubleshooting

**Database errors?**
- Check that `config/` directory is writable
- Verify database file isn't corrupted
- Check `config/logs/taskui.log` for error messages

**Can't find logs?**
- Logs are in `config/logs/taskui.log`
- Set `TASKUI_LOG_LEVEL=DEBUG` for more verbose output
