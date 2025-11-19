# TaskUI

A terminal-based nested task management system with a hierarchical two-column display. TaskUI provides a powerful and intuitive interface for managing complex task hierarchies directly from your terminal.

## Features

- **Two-Column Hierarchical Display**: View tasks and their subtasks side-by-side
- **Configurable Nesting Levels**: Customize maximum nesting depth per column
- **Unlimited Nesting Support**: Extended color palette for deep task hierarchies
- **Visual Hierarchy Indicators**: Tree-style lines and color-coding for clear structure
- **Async SQLite Backend**: Fast and reliable task storage
- **Context-Relative Navigation**: Subtasks display relative to selected parent
- **Keyboard-Driven Interface**: Efficient task management without leaving the keyboard
- **Flexible Configuration**: TOML-based configuration with sensible defaults

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

### Nesting Configuration

TaskUI supports **configurable nesting levels** for each column, allowing you to customize how deep your task hierarchies can go. By default, TaskUI is backward compatible with existing behavior, but you can easily adjust nesting depths to match your workflow.

#### Setting Up Configuration

Create a configuration file at `~/.taskui/nesting.toml`:

```bash
mkdir -p ~/.taskui
cp nesting.toml.example ~/.taskui/nesting.toml
```

Then edit `~/.taskui/nesting.toml` to customize your nesting preferences.

#### Example Configuration

```toml
[nesting]
# Enable/disable nesting features globally
enabled = true

# Number of columns (currently fixed at 2)
num_columns = 2

[nesting.column1]
# Maximum nesting depth for Column 1 (Tasks)
# Level 0 = top-level, so max_depth=1 allows levels 0-1 (2 levels total)
# Default: 1 (matches current behavior)
max_depth = 1

# Display name for this column
display_name = "Tasks"

# Level-specific colors (hex format)
level_colors = [
    "#66D9EF",  # Level 0 - Cyan (top-level tasks)
    "#A6E22E",  # Level 1 - Green (child tasks)
]

[nesting.column2]
# Maximum nesting depth for Column 2 (Subtasks)
# Default: 2 (matches current behavior, allows 3 levels)
max_depth = 2

# Display name for this column
display_name = "Subtasks"

# Level-specific colors (hex format)
level_colors = [
    "#66D9EF",  # Level 0 - Cyan (immediate children)
    "#A6E22E",  # Level 1 - Green (grandchildren)
    "#F92672",  # Level 2 - Pink (great-grandchildren)
]

# Context-relative display: show children of selected task at level 0
context_relative = true

[nesting.validation]
# Prevent creating tasks that exceed max depth
strict_validation = true

# Show warnings when approaching max depth
warn_at_max_depth = true

[nesting.ui]
# Show level indicators in task items
show_level_indicators = true

# Indentation spaces per level
indent_per_level = 2

# Tree line characters for hierarchy
tree_line_enabled = true
tree_line_last_child = "└─"
tree_line_middle_child = "├─"
```

#### Configuration Options Explained

**Nesting Depths:**
- `max_depth = 0`: Flat list (no nesting)
- `max_depth = 1`: Two levels (parent and child)
- `max_depth = 2`: Three levels (parent, child, grandchild)
- And so on... TaskUI supports unlimited nesting levels!

**Column Behavior:**
- **Column 1 (Tasks)**: Shows your main task hierarchy
- **Column 2 (Subtasks)**: Shows children of the selected task from Column 1
- With `context_relative = true`, Column 2 resets level numbering relative to the selected task

**Colors:**
- Define custom colors for each nesting level in hex format
- TaskUI includes an extended color palette for unlimited nesting levels
- If you exceed defined colors, TaskUI cycles through additional colors automatically

#### Backward Compatibility

Without a configuration file, TaskUI uses these defaults:
- Column 1: `max_depth = 1` (2 levels: top-level and children)
- Column 2: `max_depth = 2` (3 levels shown in subtask view)
- Standard color scheme with cyan, green, and pink

This matches the original behavior, so existing users won't see any changes until they create a custom configuration.

#### Use Cases

**Want deeper nesting for complex projects?**
```toml
[nesting.column1]
max_depth = 3  # 4 levels: Project -> Epic -> Feature -> Task

[nesting.column2]
max_depth = 4  # 5 levels in detail view
```

**Prefer a simpler, flatter structure?**
```toml
[nesting.column1]
max_depth = 0  # Only top-level tasks

[nesting.column2]
max_depth = 1  # Only immediate children
```

**Need to track very deep hierarchies?**
TaskUI supports unlimited nesting with automatic color generation. Just set `max_depth` to whatever you need, and TaskUI will handle the rest!

#### Complete Example

For a complete, documented example configuration, see [`nesting.toml.example`](nesting.toml.example) in the repository root.

## Architecture

TaskUI uses a clean, modular architecture:

- **Core**: Task models and business logic using Pydantic
- **Database**: Async SQLite with SQLAlchemy for reliable persistence
- **UI**: Textual framework for a beautiful terminal interface
- **Configuration**: TOML-based settings with validation

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
