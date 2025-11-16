# Suggested Commands

## Running the Application
```bash
# Development mode
python -m taskui

# Production (if installed via pip)
taskui
```

## Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=taskui --cov-report=html

# Run specific test markers
pytest -m unit
pytest -m integration
pytest -m "not slow"
```

## Code Quality
```bash
# Format code
black taskui tests

# Lint code
ruff check taskui tests

# Type checking
mypy taskui

# Fix linting issues automatically
ruff check --fix taskui tests
```

## Building
```bash
# Create distribution
python -m build

# Install in development mode
pip install -e ".[dev]"
```

## Database Management
```bash
# Export to JSON
taskui backup export backup.json

# Import from JSON
taskui backup import backup.json
```

## Git Commands
```bash
# Standard git operations
git status
git add .
git commit -m "message"
git push
git pull
```

## System Commands (Linux)
```bash
# File operations
ls -la
find . -name "*.py"
grep -r "pattern" .

# Process management
ps aux | grep taskui
kill <pid>
```
