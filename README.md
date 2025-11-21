# TaskUI

A terminal-based nested task management system with a hierarchical two-column display. TaskUI provides a powerful and intuitive interface for managing complex task hierarchies directly from your terminal.

## Features

- **Two-Column Hierarchical Display**: View tasks and their subtasks side-by-side
- **Multi-Level Task Nesting**: Up to 4 levels of task hierarchy (5 levels total: 0-4)
- **Visual Hierarchy Indicators**: Tree-style lines and color-coding for clear structure
- **Async SQLite Backend**: Fast and reliable task storage
- **Keyboard-Driven Interface**: Efficient task management without leaving the keyboard
- **Thermal Printer Support**: Print tasks to physical kanban boards via AWS SQS

## Installation

### From Source

```bash
git clone https://github.com/yourusername/taskui-python.git
cd taskui-python
pip install -e .
```

### Requirements

- Python 3.10 or higher
- See `pyproject.toml` for full dependency list

## Quick Start

Launch TaskUI from your terminal:

```bash
taskui
```

### Basic Commands

- `a` - Add a new task
- `Enter` - Add a child task to selected item
- `d` - Delete selected task
- `e` - Edit selected task
- `↑/↓` - Navigate tasks
- `Tab` - Switch between columns
- `q` - Quit

## Configuration


## Task Hierarchy

TaskUI supports up to 4 levels of task nesting (levels 0-4, for 5 total levels):

**Column 1 (Tasks):**
- Shows high-level tasks (levels 0-1)
- Use for main projects and phases

**Column 2 (Subtasks):**
- Shows all descendants of selected task
- Use for detailed breakdown

**Example:**
```
Build App (Level 0)
├─ Build UI (Level 1)
│  ├─ Design components (Level 2)
│  │  └─ Button styles (Level 3)
│  └─ Implement forms (Level 2)
└─ Build API (Level 1)
   └─ Auth endpoints (Level 2)
       └─ JWT tokens (Level 3)
```

Select "Build UI" in Column 1 → Column 2 shows all its descendants

## Architecture

TaskUI uses a clean, modular architecture:

- **Core**: Task models and business logic using Pydantic
- **Database**: Async SQLite with SQLAlchemy for reliable persistence
- **UI**: Textual framework for a beautiful terminal interface
- **Services**: Task management and validation logic

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/taskui-python.git
cd taskui-python

# Install with development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black taskui

# Lint
ruff check taskui

# Type checking
mypy taskui
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Project Status

TaskUI is in active development. Features and APIs may change between versions.

Current version: 0.1.0
