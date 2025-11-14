# TaskUI - Terminal-based Nested Task Manager

A powerful terminal-based task management system with a three-column hierarchical display, built with Python and Textual.

## Features

- **Three-Column Layout**: Tasks → Subtasks → Details
- **Nested Hierarchies**: Up to 2 levels in Column 1, 3 levels in Column 2
- **Keyboard-Driven**: Fast navigation and task management
- **Multiple Lists**: Work, Home, Personal lists with easy switching
- **Persistent Storage**: SQLite database with auto-save
- **One Monokai Theme**: Beautiful terminal interface with level-specific colors
- **Archive System**: Keep completed tasks organized
- **Thermal Printer Support**: Print task lists to Epson TM-T20III (optional)

## Requirements

- Python 3.10 or higher
- Terminal with 256 color support

## Installation

### Development Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd taskui-python
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e ".[dev]"
```

### Production Install

```bash
pip install taskui
```

## Usage

### Running the Application

```bash
python -m taskui
```

Or if installed via pip:
```bash
taskui
```

### Keyboard Shortcuts

#### Navigation
- `↑/↓`: Navigate within column
- `Tab`: Move to next column
- `Shift+Tab`: Move to previous column
- `1-3`: Switch between lists (Work, Home, Personal)

#### Task Management
- `N`: Create new sibling task
- `C`: Create new child task
- `E`: Edit selected task
- `Space`: Toggle task completion
- `A`: Archive completed task
- `Delete/Backspace`: Delete task

#### Other
- `P`: Print current column (requires thermal printer)
- `?`: Show help
- `Esc`: Cancel/Close modal
- `Enter`: Confirm action
- `Q`: Quit application

## Project Structure

```
taskui-python/
├── taskui/              # Main application package
│   ├── __init__.py
│   ├── __main__.py      # Application entry point
│   ├── models.py        # Pydantic data models
│   ├── database.py      # SQLAlchemy database layer
│   ├── services/        # Business logic
│   │   ├── __init__.py
│   │   ├── task_service.py
│   │   ├── list_service.py
│   │   └── nesting_rules.py
│   └── ui/              # Textual UI components
│       ├── __init__.py
│       ├── app.py       # Main application
│       ├── theme.py     # One Monokai theme
│       └── components/  # UI widgets
│           ├── __init__.py
│           ├── task_item.py
│           ├── column.py
│           ├── detail_panel.py
│           └── task_modal.py
├── tests/               # Test suite
│   ├── __init__.py
│   ├── conftest.py
│   └── test_*.py
├── docs/                # Documentation
├── pyproject.toml       # Project configuration
├── pytest.ini           # Pytest configuration
├── .gitignore
└── README.md
```

## Development

### Running Tests

```bash
pytest
```

With coverage:
```bash
pytest --cov=taskui --cov-report=html
```

### Code Quality

Format code:
```bash
black taskui tests
```

Lint code:
```bash
ruff check taskui tests
```

Type checking:
```bash
mypy taskui
```

### Building

Create distribution:
```bash
python -m build
```

## Database

TaskUI uses SQLite for data persistence. The database file is created automatically at:
- Linux/Mac: `~/.local/share/taskui/taskui.db`
- Windows: `%APPDATA%\taskui\taskui.db`

### Backup

```bash
# Export to JSON
taskui backup export backup.json

# Import from JSON
taskui backup import backup.json
```

## Configuration

Create a `.env` file in the project root for custom configuration:

```env
TASKUI_DB_PATH=/custom/path/to/database.db
TASKUI_PRINTER_IP=192.168.1.100
TASKUI_PRINTER_PORT=9100
```

## Nesting Rules

### Column 1 - Tasks
- Maximum 2 levels (Level 0 → Level 1)
- Example: "Sprint Planning" → "Review backlog"
- Cannot create children for Level 1 tasks in Column 1

### Column 2 - Subtasks
- Maximum 3 levels visible (Level 0 → Level 1 → Level 2)
- Displays children of selected Column 1 task
- Context-relative levels (always starts at Level 0)
- Dynamic header shows "[Parent Task] Subtasks"

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and feature requests, please use the GitHub issue tracker.

## Roadmap

- [x] Phase 1: MVP Core (Basic functionality)
- [ ] Phase 2: Enhanced Features (Progress indicators, archive)
- [ ] Phase 3: Polish & Optimization (Error handling, performance)
- [ ] Phase 4: Advanced Features (Thermal printer, PyInstaller build)

## Credits

Built with:
- [Textual](https://github.com/Textualize/textual) - Terminal UI framework
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM
- [aiosqlite](https://github.com/omnilib/aiosqlite) - Async SQLite
