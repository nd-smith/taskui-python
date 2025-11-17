# Testing Guide for TaskUI Developers

A practical guide for writing and running tests in the TaskUI project.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=taskui --cov-report=term-missing

# Run specific test file
pytest tests/test_task_service.py

# Run specific test method
pytest tests/test_task_service.py::TestTaskServiceCreate::test_create_task_basic

# Run tests matching a pattern
pytest -k "test_create"

# Run with verbose output
pytest -v
```

## Test Organization

```
tests/
├── conftest.py                    # Shared fixtures (db_session, make_task, etc.)
├── helpers/                       # Reusable test utilities
│   ├── ui_helpers.py             # UI testing helpers
│   └── README.md                 # Helper documentation
├── test_*.py                     # Unit tests (one file per module)
└── test_integration_*.py         # Integration tests
```

## Writing Tests for New Features

### 1. Choose the Right Test Type

**Unit Test** - Test a single function/method in isolation:
```python
# tests/test_my_service.py
class TestMyServiceCreate:
    """Tests for MyService.create() method."""

    @pytest.mark.asyncio
    async def test_create_with_valid_data(self, db_session):
        """Test creating entity with valid data."""
        service = MyService(db_session)
        result = await service.create(title="Test")

        assert result.title == "Test"
        assert result.id is not None
```

**Integration Test** - Test multiple components working together:
```python
# tests/test_integration_my_feature.py
class TestMyFeatureIntegration:
    """Integration tests for my feature."""

    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        """Test end-to-end workflow."""
        async with TaskUI().run_test() as pilot:
            # Test full user workflow
            ...
```

### 2. Use Available Fixtures

**Database Fixtures** (from `conftest.py`):
```python
async def test_something(db_session, sample_task_list, sample_list_id):
    """db_session: Database session with auto-rollback
    sample_task_list: Pre-created task list in database
    sample_list_id: UUID of the sample task list
    """
    service = TaskService(db_session)
    task = await service.create_task("Test", sample_list_id)
    assert task.list_id == sample_list_id
```

**Factory Fixtures** - Create custom test data:
```python
def test_with_custom_task(make_task, make_task_list):
    """make_task: Factory for creating Task models
    make_task_list: Factory for creating TaskList models
    """
    task = make_task(
        title="Custom Task",
        level=2,
        is_completed=True
    )
    assert task.title == "Custom Task"
```

### 3. Use Test Helpers for UI Tests

**Before (verbose):**
```python
app.action_new_sibling_task()
await pilot.pause()
modal = app.screen
title_input = modal.query_one("#title-input")
title_input.value = "New Task"
modal.action_save()
await pilot.pause()
```

**After (using helpers):**
```python
from tests.helpers import create_sibling_task

task = await create_sibling_task(pilot, "New Task")
```

**Common helpers:**
```python
from tests.helpers import (
    create_sibling_task,       # Create sibling task via modal
    create_child_task,         # Create child task via modal
    select_task_in_column,     # Select task and trigger updates
    navigate_to_column,        # Navigate between columns
    assert_column_has_tasks,   # Assert task count
    assert_task_in_column,     # Assert task exists by title
    get_task_service,          # Get TaskService with session
)

# Example usage
async def test_my_feature(self):
    async with TaskUI().run_test() as pilot:
        # Create parent task
        parent = await create_sibling_task(pilot, "Parent")

        # Select it
        await select_task_in_column(pilot, "column-1", 0)

        # Create child
        child = await create_child_task(pilot, "Child")

        # Assertions
        await assert_column_has_tasks(pilot, "column-1", 2)
        await assert_task_in_column(pilot, "column-2", "Child")
```

See `tests/helpers/README.md` for complete helper documentation.

### 4. Follow Naming Conventions

**Test file naming:**
- `test_<module_name>.py` - Unit tests for a module
- `test_integration_<feature>.py` - Integration tests

**Test class naming:**
```python
class TestServiceNameOperation:
    """Test the operation() method of ServiceName."""
```

**Test method naming:**
```python
async def test_operation_with_specific_scenario(self):
    """Test operation() with specific scenario.

    Verifies:
    - Expected behavior 1
    - Expected behavior 2
    """
```

### 5. Common Test Patterns

**Testing async methods:**
```python
@pytest.mark.asyncio
async def test_async_method(self, db_session):
    service = MyService(db_session)
    result = await service.async_method()
    assert result is not None
```

**Testing exceptions:**
```python
@pytest.mark.asyncio
async def test_raises_error(self, db_session):
    service = TaskService(db_session)

    with pytest.raises(TaskNotFoundError):
        await service.get_task_by_id(uuid4())
```

**Testing UI components:**
```python
@pytest.mark.asyncio
async def test_component_behavior(self):
    async with TaskUI().run_test() as pilot:
        app = pilot.app
        await pilot.pause()

        # Get component
        column = app.query_one("#column-1", TaskColumn)

        # Test behavior
        assert len(column._tasks) == 0
```

**Testing with hierarchical tasks:**
```python
@pytest.mark.asyncio
async def test_with_hierarchy(self, db_session, task_hierarchy):
    """task_hierarchy fixture creates parent + 2 children + 1 grandchild"""
    service = TaskService(db_session)

    parent_id = task_hierarchy["parent_id"]
    children = await service.get_children(parent_id)

    assert len(children) == 2
```

## Test Checklist for New Features

When adding a new feature, ensure you have tests for:

- [ ] **Happy path** - Feature works with valid input
- [ ] **Edge cases** - Empty input, max values, boundaries
- [ ] **Error handling** - Invalid input, missing data
- [ ] **State changes** - Database updates, UI updates
- [ ] **Integration** - Feature works with other components
- [ ] **User workflows** - Complete end-to-end scenarios

Example for a new task operation:
```python
class TestNewTaskOperation:
    """Tests for new_task_operation() method."""

    # Happy path
    async def test_operation_with_valid_input(self): ...

    # Edge cases
    async def test_operation_with_empty_title(self): ...
    async def test_operation_with_max_nesting_level(self): ...

    # Error handling
    async def test_operation_with_invalid_task_id(self): ...
    async def test_operation_with_missing_list(self): ...

    # State changes
    async def test_operation_updates_database(self): ...
    async def test_operation_refreshes_ui(self): ...

    # Integration
    async def test_operation_in_complete_workflow(self): ...
```

## Debugging Tests

**Run with print statements visible:**
```bash
pytest -s
```

**Run with Python debugger:**
```python
@pytest.mark.asyncio
async def test_something(self):
    import pdb; pdb.set_trace()
    # Your test code
```

**Show test output even on success:**
```bash
pytest -v --show-capture=all
```

**Run only failed tests from last run:**
```bash
pytest --lf
```

**Run tests until one fails:**
```bash
pytest -x
```

## Coverage Best Practices

**Check coverage for specific module:**
```bash
pytest --cov=taskui.services.task_service --cov-report=term-missing
```

**Generate HTML coverage report:**
```bash
pytest --cov=taskui --cov-report=html
open htmlcov/index.html
```

**Coverage requirements:**
- Minimum: 75% (enforced by CI)
- Target: 85%+
- Critical modules (services, database): 95%+

**Lines excluded from coverage:**
```python
def __repr__(self):  # Excluded
    return f"Task({self.id})"

if TYPE_CHECKING:  # Excluded
    from typing import List

raise NotImplementedError  # Excluded
```

## CI/CD Integration

**GitHub Actions runs automatically on:**
- Every push to `main`, `master`, `develop`
- Every pull request to these branches

**Tests workflow:**
- Runs on Python 3.10, 3.11, 3.12
- Runs full test suite with coverage
- Fails if coverage < 75%
- Uploads coverage to Codecov

**Lint workflow:**
- Checks Black formatting: `black --check .`
- Runs Ruff linter: `ruff check .`
- Runs MyPy type checker: `mypy taskui/`

**Local pre-commit checks:**
```bash
# Format code
black .

# Lint code
ruff check . --fix

# Type check
mypy taskui/

# Run tests
pytest --cov=taskui --cov-fail-under=75
```

## Common Issues & Solutions

**Issue: Tests fail with database errors**
```python
# Solution: Ensure you're using db_session fixture
async def test_something(self, db_session):  # ✓ Correct
    service = TaskService(db_session)
```

**Issue: UI tests timeout or hang**
```python
# Solution: Always use await pilot.pause() after actions
app.action_new_sibling_task()
await pilot.pause()  # ✓ Required
modal = app.screen
```

**Issue: Async test not running**
```python
# Solution: Add @pytest.mark.asyncio decorator
@pytest.mark.asyncio  # ✓ Required
async def test_async_method(self):
    ...
```

**Issue: Test fails in CI but passes locally**
```python
# Solution: Ensure test doesn't depend on specific timing or order
# Use proper fixtures and database isolation
```

**Issue: Coverage too low**
```bash
# Solution: Identify untested code
pytest --cov=taskui --cov-report=term-missing

# Look for lines with "Missing" in coverage report
# Add tests for those code paths
```

## Quick Reference

**Common pytest options:**
```bash
pytest -v              # Verbose output
pytest -s              # Show print statements
pytest -x              # Stop on first failure
pytest -k "pattern"    # Run tests matching pattern
pytest --lf            # Run last failed
pytest --ff            # Run failed first
pytest -n auto         # Run in parallel (requires pytest-xdist)
```

**Common assertions:**
```python
assert value == expected
assert value is not None
assert value in collection
assert len(collection) == 3
with pytest.raises(ExceptionType):
    code_that_raises()
```

**Async patterns:**
```python
@pytest.mark.asyncio
async def test_name(self, db_session):
    result = await async_function()
    assert result is not None
```

## Resources

- **Pytest documentation**: https://docs.pytest.org/
- **pytest-asyncio**: https://pytest-asyncio.readthedocs.io/
- **Textual testing**: https://textual.textualize.io/guide/testing/
- **Test helpers**: `tests/helpers/README.md`
- **Fixture reference**: `tests/conftest.py`

## Getting Help

**Questions about testing?**
1. Check this guide
2. Look at similar tests in the test suite
3. Review `tests/conftest.py` for available fixtures
4. Check `tests/helpers/README.md` for helper functions
5. Ask in team chat or open a discussion

**Found a bug?**
1. Write a test that reproduces the bug (it should fail)
2. Fix the bug
3. Verify the test now passes
4. Commit both the fix and the test

Remember: **Tests are documentation**. Write tests that clearly show how your code should be used and what behavior is expected.
