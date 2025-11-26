# TaskUI

Terminal-based task manager with hierarchical two-column display. Built with Python and Textual.

## Features

- **Two-Column Layout** - View tasks and subtasks side-by-side with tree-style hierarchy
- **Deep Nesting** - Up to 5 levels of task hierarchy (levels 0-4)
- **Multiple Lists** - Organize tasks into separate lists, switch with number keys
- **Multi-Computer Sync** - Sync tasks across machines via AWS SQS (optional)
- **Thermal Printer** - Print task lists to ESC/POS printers (optional)
- **Keyboard-Driven** - Full keyboard navigation, no mouse needed

## Installation

```bash
pip install taskui
```

Or from source:

```bash
git clone https://github.com/yourusername/taskui-python.git
cd taskui-python
pip install -e .
```

Requires Python 3.10+

## Usage

```bash
taskui
```

### Keybindings

| Key | Action |
|-----|--------|
| `n` | New sibling task |
| `c` | New child task |
| `e` | Edit task |
| `Space` | Toggle complete |
| `Delete` | Delete task |
| `Tab` | Switch columns |
| `Up/Down` | Navigate |
| `1-9` | Switch lists |
| `Ctrl+N` | New list |
| `p` | Print column |
| `q` | Quit |

## Configuration

Create `~/.config/taskui/config.ini` for optional features:

```ini
[printing]
enabled = true
queue_url = https://sqs.region.amazonaws.com/account/queue

[sync]
enabled = true
queue_url = https://sqs.region.amazonaws.com/account/sync-queue
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
