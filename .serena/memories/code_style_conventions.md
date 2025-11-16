# Code Style and Conventions

## Python Version
- Minimum: Python 3.10
- Target versions: 3.10, 3.11, 3.12

## Formatting (Black)
- Line length: 100 characters
- Target version: py310, py311, py312
- Excludes: .eggs, .git, .hg, .mypy_cache, .tox, .venv, build, dist

## Linting (Ruff)
- Line length: 100 characters
- Target version: py310
- Enabled rules:
  - E (pycodestyle errors)
  - W (pycodestyle warnings)
  - F (pyflakes)
  - I (isort)
  - B (flake8-bugbear)
  - C4 (flake8-comprehensions)
  - UP (pyupgrade)
- Ignored rules:
  - E501 (line too long - handled by black)
  - B008 (function calls in argument defaults)
  - C901 (too complex)

## Type Hints (MyPy)
- Python version: 3.10
- Settings:
  - warn_return_any = true
  - warn_unused_configs = true
  - check_untyped_defs = true
  - no_implicit_optional = true
  - warn_redundant_casts = true
  - warn_unused_ignores = true
  - warn_no_return = true
  - ignore_missing_imports = true

## Testing (Pytest)
- Test path: tests/
- Async mode: auto
- File patterns: test_*.py, *_test.py
- Class patterns: Test*
- Function patterns: test_*
- Markers: slow, integration, unit

## Project Structure
- Main package: taskui/
- Services: taskui/services/
- UI components: taskui/ui/components/
- Tests: tests/
- Documentation: docs/
