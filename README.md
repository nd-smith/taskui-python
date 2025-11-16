# TaskUI - Terminal-based Nested Task Manager

A powerful terminal-based task management system with a three-column hierarchical display, built with Python and Textual.

## Features

- **Three-Column Layout**: Tasks → Subtasks → Details
- **Nested Hierarchies**: Up to 2 levels in Column 1, 3 levels in Column 2
- **Keyboard-Driven**: Fast navigation and task management
- **Multiple Lists**: Work, Home, Personal lists with easy switching
- **Persistent Storage**: SQLite database with auto-save
- **4 Beautiful Themes**: One Monokai (default), Dracula, Tokyo Night, and Nord
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

## Thermal Printer

TaskUI supports printing physical kanban cards to ESC/POS thermal printers. Press **'P'** on any task to create a physical card with the task title and all its children as checkboxes.

### Quick Start

1. **Install printer dependencies:**
   ```bash
   pip install python-escpos Pillow
   ```

2. **Configure printer** in `~/.taskui/config.ini`:
   ```ini
   [printer]
   host = 192.168.50.99
   port = 9100
   ```

3. **Test printer:**
   ```bash
   python3 scripts/validate_printer.py
   ```

4. **Print from TaskUI:**
   - Select a task
   - Press **'P'**
   - Get your physical card!

### Supported Printers

- Epson TM-T20III (tested)
- Any ESC/POS compatible 80mm thermal printer

### Card Format

Cards are printed in a clean, minimal format:
- **Title:** Large, bold, easy to read
- **Children:** Checkboxes `[ ]` or `[X]` for completed
- **Auto-cut:** Automatic separation

### Documentation

- **Setup Guide:** `docs/PRINTER_SETUP_GUIDE.md` - Complete installation and configuration
- **Troubleshooting:** `docs/PRINTER_TROUBLESHOOTING.md` - Common issues and solutions
- **Implementation:** `docs/PRINT_TASKS.md` - Technical details

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

## Theming

TaskUI comes with **4 popular VS Code themes** adapted for terminal use. The default is **One Monokai**, but you can easily switch to **Dracula**, **Tokyo Night**, or **Nord**. The entire application's visual styling is centralized in `taskui/ui/theme.py`, making theme switching effortless.

### Theme Architecture

The theme system follows these principles:
- **Single source of truth**: All colors defined in `theme.py`
- **Dynamic CSS**: Components use f-string interpolation to reference theme constants
- **Consistent patterns**: Standardized hover states, focus indicators, and interaction feedback
- **Semantic colors**: Level-based colors (cyan/green/pink) for visual hierarchy

### Customizing Colors

To change the app's color scheme, edit the constants in `taskui/ui/theme.py`:

```python
# Base colors
BACKGROUND = "#272822"  # Main background
FOREGROUND = "#F8F8F2"  # Text color
SELECTION = "#49483E"   # Selection highlight
BORDER = "#3E3D32"      # Borders and dividers
COMMENT = "#75715E"     # Secondary/dimmed text

# Task hierarchy colors
LEVEL_0_COLOR = "#66D9EF"  # Cyan - Top-level tasks
LEVEL_1_COLOR = "#A6E22E"  # Green - Nested tasks
LEVEL_2_COLOR = "#F92672"  # Pink - Deep nested tasks

# Additional colors
YELLOW = "#E6DB74"      # Highlights/warnings
ORANGE = "#FD971F"      # Archive/warnings
PURPLE = "#AE81FF"      # Info/secondary
```

All components automatically update when you change these constants - no need to modify individual component files!

### Available Themes

TaskUI includes 4 professionally crafted themes:

**1. One Monokai (Default)** - Warm, balanced dark theme with cyan/green/pink hierarchy
**2. Dracula** - Bold, vibrant colors optimized for low-light (10M+ VS Code installs)
**3. Tokyo Night** - Cool blue tones inspired by Tokyo's nighttime skyline
**4. Nord** - Arctic, north-bluish palette with calm, focused atmosphere

**To switch themes:**

```bash
# Method 1: Replace theme.py (recommended)
cd taskui/ui
cp themes/dracula.py theme.py        # Dracula theme
cp themes/tokyo_night.py theme.py    # Tokyo Night theme
cp themes/nord.py theme.py           # Nord theme
```

```python
# Method 2: Import in theme.py (for testing)
from taskui.ui.themes.dracula import *
```

**Full theme documentation:** See `taskui/ui/themes/README.md` for detailed color previews, comparisons, and creating your own themes.

### Theme Features

**Visual Hierarchy**
- Each nesting level has a distinct accent color
- Task items show colored left borders based on their level
- Completed tasks appear dimmed with strikethrough text
- Archived tasks use reduced opacity for visual distinction

**Interactive States**
- **Hover**: 20% transparent overlay on all interactive elements
- **Focus**: Thick cyan border indicates keyboard focus
- **Selection**: Highlighted background for selected items
- **Disabled**: 50% opacity for unavailable actions

**Modal Styling**
- Semi-transparent dark overlay (`#27282280`)
- Consistent button variants (success=green, error=pink)
- Focused inputs highlighted with cyan border

### Creating a Custom Theme

Want to create your own theme? Here's how:

1. **Copy the theme constants** from `theme.py`
2. **Choose your color palette** (use a hex color picker)
3. **Update the constants** with your new colors
4. **Test the application** to see your changes live
5. **(Optional)** Share your theme with the community!

Example - Creating a "Nord" theme:
```python
BACKGROUND = "#2E3440"
FOREGROUND = "#ECEFF4"
LEVEL_0_COLOR = "#88C0D0"  # Frost blue
LEVEL_1_COLOR = "#A3BE8C"  # Aurora green
LEVEL_2_COLOR = "#B48EAD"  # Aurora purple
```

### Advanced Theming

**Using Transparency**

The `with_alpha()` helper function adds transparency to any color:

```python
from taskui.ui.theme import with_alpha, SELECTION, HOVER_OPACITY

# Create a semi-transparent selection overlay
hover_bg = with_alpha(SELECTION, HOVER_OPACITY)  # Returns: '#49483E20'
```

**Base Styles**

The `taskui/ui/base_styles.py` module provides reusable CSS patterns for:
- Modal dialogs and overlays
- Button states and variants
- Semantic text classes
- Background states

Components can import these to maintain consistency:
```python
from taskui.ui.base_styles import MODAL_BASE_CSS, BUTTON_BASE_CSS
```

### Color Reference

| Color Constant | Hex Value | Usage |
|----------------|-----------|-------|
| `BACKGROUND` | `#272822` | Main app background |
| `FOREGROUND` | `#F8F8F2` | Primary text |
| `SELECTION` | `#49483E` | Selected items |
| `BORDER` | `#3E3D32` | Borders, dividers |
| `COMMENT` | `#75715E` | Secondary text |
| `LEVEL_0_COLOR` | `#66D9EF` | Top-level (cyan) |
| `LEVEL_1_COLOR` | `#A6E22E` | Level 1 (green) |
| `LEVEL_2_COLOR` | `#F92672` | Level 2 (pink) |
| `YELLOW` | `#E6DB74` | Highlights |
| `ORANGE` | `#FD971F` | Warnings/archive |
| `PURPLE` | `#AE81FF` | Info |
| `COMPLETE_COLOR` | `#75715E` | Completed tasks |
| `ARCHIVE_COLOR` | `#49483E` | Archived tasks |
| `MODAL_OVERLAY_BG` | `#27282280` | Modal backdrop |

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
