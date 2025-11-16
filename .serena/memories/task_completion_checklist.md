# Task Completion Checklist

When a task is completed, ensure the following steps are performed:

## 1. Code Quality Checks
```bash
# Format code with black
black taskui tests

# Check linting with ruff
ruff check taskui tests

# Fix auto-fixable issues
ruff check --fix taskui tests
```

## 2. Type Checking
```bash
# Run mypy type checker
mypy taskui
```

## 3. Testing
```bash
# Run all tests
pytest

# Run with coverage to ensure adequate test coverage
pytest --cov=taskui --cov-report=html
```

## 4. Manual Testing
- Run the application: `python -m taskui`
- Test the specific feature/fix implemented
- Verify no regressions in existing functionality
- Test keyboard shortcuts and navigation

## 5. Documentation
- Update README.md if adding new features
- Add/update docstrings for new/modified functions
- Update comments if code behavior changed

## 6. Git Workflow
```bash
# Check status
git status

# Add changes
git add .

# Commit with descriptive message
git commit -m "descriptive message"

# Push to remote
git push
```

## 7. Verify Build
```bash
# Ensure package builds correctly
python -m build
```

## Standards
- All tests must pass
- No type errors
- Code must be formatted with black
- No linting errors
- Manual testing confirms functionality works
