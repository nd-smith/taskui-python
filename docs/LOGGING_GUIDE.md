# Logging Developer Guide

Quick reference for using logging in TaskUI following established patterns.

## Setup

### Adding Logging to a New Module

```python
from taskui.logging_config import get_logger

# Initialize logger for this module
logger = get_logger(__name__)
```

**Pattern:** Import `get_logger`, call it with `__name__`, assign to module-level `logger` variable.

## Log Levels

### DEBUG - Execution Flow & State Changes

**When:** Internal state changes, navigation, rendering, method entry/exit

```python
# Navigation
logger.debug(f"ListBar: Navigate next column - from {current_column_id} to {next_column}")

# State changes
logger.debug(f"TaskItem: Selection changed to {selected} for task '{task.title[:30]}' (id={task_id})")

# Rendering operations
logger.debug(f"DetailPanel: Rendering task details - id={task.id}, completed={task.is_completed}")
```

### INFO - User Actions & Important Operations

**When:** User-initiated actions, successful operations, mode changes

```python
# User actions
logger.info(f"ListBar: Setting active list '{list_name}' (id={list_id})")

# Modal operations
logger.info(f"TaskModal: Opened in {self.mode} mode{context_info}")

# Task operations
logger.info(f"Task {self.mode} saved - title='{title[:50]}', has_notes={bool(notes)}")
```

### WARNING - Validation Failures & Fallbacks

**When:** Invalid input, constraint violations, fallback scenarios, non-critical errors

```python
# Validation failures
logger.warning(f"TaskModal: Save validation failed - empty title (mode={self.mode})")

# Constraint violations
logger.warning(f"TaskModal: Nesting limit violation - parent_id={parent_task.id}, parent_level={parent_task.level}")

# Fallback scenarios
logger.warning(f"ListBar: Attempted to set active list with unknown id={list_id}")
logger.warning(f"Keybindings: Unknown column {current_column_id}, defaulting to first column")
```

### ERROR - Operation Failures

**When:** Operations fail, exceptions caught, recovery attempted

```python
# Always use exc_info=True for exceptions
logger.error(f"Failed to load configuration from {path}", exc_info=True)
logger.error(f"Error creating task", exc_info=True)
```

## Message Formatting Patterns

### Include Context

**Always include:** Relevant IDs, truncated titles, state information, counts

```python
# Good - includes context
logger.debug(f"DetailPanel: Setting task '{task.title[:50]}' (id={task.id}, level={task.level})")
logger.debug(f"ArchiveModal: Filtered tasks, query='{search_query}', results={len(filtered)}/{len(total)}")

# Bad - too vague
logger.debug("Setting task")
logger.debug("Filtered tasks")
```

### Truncate Long Strings

**Pattern:** Truncate titles/text to 30-50 characters to prevent log spam

```python
task.title[:30]  # For inline display
task.title[:50]  # For primary log subject
```

### Component Prefixes

**Pattern:** Prefix messages with component name for easy filtering

```python
logger.debug(f"DetailPanel: {message}")
logger.info(f"TaskModal: {message}")
logger.warning(f"ListBar: {message}")
```

### Structured Information

**Pattern:** Use `key=value` format for easy parsing

```python
logger.debug(f"TaskItem: Created for task '{title}' (id={task.id}, level={level}, completed={is_completed})")
logger.info(f"ArchiveModal: Filtered tasks, query='{query}', results={count}/{total}")
```

## Exception Handling

### Logged Exceptions

**Always use `exc_info=True`** to include full traceback:

```python
try:
    risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {operation_name}", exc_info=True)
    # Handle the error
```

### Exception with Fallback

```python
try:
    task_list = self.query_one("#task-list", ListView)
    task_list.focus()
except Exception as e:
    logger.warning(f"Failed to focus task list, falling back to search input", exc_info=True)
    search_input.focus()  # Fallback behavior
```

### Never Silent Exceptions

**Bad:**
```python
except Exception:
    pass  # Silent failure - debugging nightmare!
```

**Good:**
```python
except Exception as e:
    logger.warning(f"Could not perform optional operation: {operation}", exc_info=True)
    # Continue with degraded functionality
```

## Common Patterns by Component Type

### UI Widgets

```python
class MyWidget(Widget):
    def __init__(self, task: Task, **kwargs):
        super().__init__(**kwargs)
        logger.debug(f"MyWidget: Created for task '{task.title[:30]}' (id={task.id})")

    def on_mount(self):
        logger.debug(f"MyWidget: Mounted")

    def on_focus(self):
        logger.debug(f"MyWidget: Focused")

    def on_click(self):
        logger.debug(f"MyWidget: Clicked")
```

### Modal Dialogs

```python
class MyModal(ModalScreen):
    def on_mount(self):
        logger.info(f"MyModal: Opened with context={self.context}")

    def action_save(self):
        if not self.validate():
            logger.warning(f"MyModal: Validation failed - {reason}")
            return

        logger.info(f"MyModal: Saved - {summary}")
        self.dismiss()

    def action_cancel(self):
        logger.info(f"MyModal: Cancelled")
        self.dismiss()
```

### Service Methods

```python
async def create_task(self, title: str, parent_id: Optional[UUID]) -> Task:
    logger.debug(f"Creating task: title='{title[:50]}', parent_id={parent_id}")

    try:
        task = await self._create_task_internal(title, parent_id)
        logger.info(f"Task created: '{task.title[:50]}' (id={task.id})")
        return task
    except Exception as e:
        logger.error(f"Failed to create task: title='{title[:50]}'", exc_info=True)
        raise
```

### Navigation & State Changes

```python
def set_active_item(self, item_id: UUID):
    item = self._find_item(item_id)
    if not item:
        logger.warning(f"Attempted to set active item with unknown id={item_id}")
        return

    logger.debug(f"Setting active item: '{item.name}' (id={item_id})")
    self.active_item = item
```

## Viewing Logs

### Development

```bash
# Enable debug logging
TASKUI_LOG_LEVEL=DEBUG taskui

# Tail logs in real-time
tail -f ~/.taskui/logs/taskui.log

# Filter by component
grep "DetailPanel:" ~/.taskui/logs/taskui.log
grep "ERROR" ~/.taskui/logs/taskui.log
```

### Search for Specific Operations

```bash
# Find all task creations
grep "Task created:" ~/.taskui/logs/taskui.log

# Find all errors
grep "ERROR" ~/.taskui/logs/taskui.log

# Find operations on specific task
grep "task_id=<uuid>" ~/.taskui/logs/taskui.log
```

## Anti-Patterns to Avoid

### ❌ Missing Context

```python
logger.debug("Task updated")  # Which task? What changed?
```

### ❌ Unlogged Exceptions

```python
except Exception:
    pass  # Silent failure!
```

### ❌ Logging Full Objects

```python
logger.debug(f"Task: {task}")  # Huge object dump
```

### ❌ Excessive String Formatting

```python
logger.debug(f"Processing: {expensive_object}")  # Stringified even if DEBUG disabled
```

**Instead:**
```python
if logger.isEnabledFor(logging.DEBUG):
    logger.debug(f"Processing: {expensive_object}")
```

### ❌ Sensitive Data

```python
logger.info(f"User logged in: password={password}")  # Never log secrets!
```

## Quick Checklist

When adding logging to a component:

- [ ] Import and initialize logger at module level
- [ ] Log component lifecycle (init, mount, focus/blur)
- [ ] Log user actions (clicks, keyboard shortcuts, form submissions)
- [ ] Log state changes (selection, filtering, navigation)
- [ ] Log validation failures with context
- [ ] Add `exc_info=True` to all exception handlers
- [ ] Use component prefix in all messages
- [ ] Truncate long strings (30-50 chars)
- [ ] Include relevant IDs and state in messages
- [ ] Use appropriate log levels (DEBUG/INFO/WARNING/ERROR)

## Configuration

Log configuration is centralized in `taskui/logging_config.py`:

- **Location:** `~/.taskui/logs/taskui.log`
- **Max Size:** 10MB per file
- **Backups:** 5 files retained (~60MB total)
- **Format:** `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- **Environment:** Set `TASKUI_LOG_LEVEL` to DEBUG/INFO/WARNING/ERROR

## Testing Logging

```python
def test_component_logs_actions(caplog):
    """Test that component logs user actions."""
    component = MyComponent()

    with caplog.at_level(logging.INFO):
        component.perform_action()
        assert "MyComponent: Action performed" in caplog.text
```

## Summary

**Remember:**
- DEBUG = flow & state
- INFO = user actions
- WARNING = validation & fallbacks
- ERROR = failures with `exc_info=True`
- Always include context (IDs, titles, counts)
- Truncate long strings
- Prefix with component name
- Never silent exceptions

**When in doubt:** Look at existing patterns in `detail_panel.py`, `list_bar.py`, `task_modal.py`.
