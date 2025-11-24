"""Keyboard navigation and keybindings for TaskUI.

This module defines all keyboard shortcuts and navigation handlers for the
TaskUI application, including:
- Within-column navigation (Up/Down arrows)
- Between-column navigation (Tab/Shift+Tab)
- Task actions (N, C, E, D, Space, A, P, Delete)
- Application controls (Q, ?)
"""

from typing import Optional
from textual.app import ComposeResult
from textual.binding import Binding

from taskui.logging_config import get_logger

# Initialize logger for this module
logger = get_logger(__name__)


# Navigation keybindings
NAVIGATION_BINDINGS = [
    Binding("up", "navigate_up", "Navigate Up", show=False),
    Binding("down", "navigate_down", "Navigate Down", show=False),
    Binding("tab", "navigate_next_column", "Next Column", show=False),
    Binding("shift+tab", "navigate_prev_column", "Previous Column", show=False),
]

# Task action keybindings
TASK_ACTION_BINDINGS = [
    Binding("n,N", "new_sibling_task", "New Sibling Task", show=True),
    Binding("c,C", "new_child_task", "New Child Task", show=True),
    Binding("e,E", "edit_task", "Edit Task", show=True),
    Binding("d,D", "create_diary_entry", "Diary Entry", show=True),
    Binding("space", "toggle_completion", "Toggle Complete", show=True),
    Binding("delete,backspace", "delete_task", "Delete Task", show=True),
]

# List management keybindings
LIST_BINDINGS = [
    Binding("1", "switch_list_1", "List 1", show=True),
    Binding("2", "switch_list_2", "List 2", show=True),
    Binding("3", "switch_list_3", "List 3", show=True),
    Binding("4", "switch_list_4", "List 4", show=True)
]

# List CRUD keybindings
LIST_CRUD_BINDINGS = [
    Binding("ctrl+n", "create_list", "New List", show=True),
    Binding("ctrl+e", "edit_list", "Edit List", show=True),
    Binding("ctrl+d", "delete_list", "Delete List", show=True),
]

# Printing keybindings
PRINT_BINDINGS = [
    Binding("p,P", "print_column", "Print Column", show=True),
]

# Application control keybindings
APP_CONTROL_BINDINGS = [
    Binding("q,Q", "quit", "Quit", priority=True, show=True),
    Binding("question_mark", "help", "Help", show=True),
    Binding("escape", "cancel", "Cancel", show=False),
]

# Column identifiers
COLUMN_1_ID = "column-1"
COLUMN_2_ID = "column-2"
COLUMN_3_ID = "column-3"

# Focusable columns for navigation (Column 3 is display-only)
FOCUSABLE_COLUMNS = [COLUMN_1_ID, COLUMN_2_ID]


def get_next_column(current_column_id: str) -> Optional[str]:
    """Get the next column in the navigation order.

    Only cycles between Column 1 and Column 2 (Column 3 is non-focusable).
    Tab key toggles: Column 1 ↔ Column 2

    Args:
        current_column_id: ID of the current column

    Returns:
        ID of the next column (toggles between Column 1 and Column 2)
    """
    # Simple toggle between Column 1 and Column 2
    if current_column_id == COLUMN_1_ID:
        next_column = COLUMN_2_ID
    else:
        # From Column 2 (or any unknown column), go to Column 1
        next_column = COLUMN_1_ID

    logger.debug(f"Keybindings: Navigate next column - from {current_column_id} to {next_column}")
    return next_column


def get_prev_column(current_column_id: str) -> Optional[str]:
    """Get the previous column in the navigation order.

    Only cycles between Column 1 and Column 2 (Column 3 is non-focusable).
    Shift+Tab key toggles: Column 1 ↔ Column 2

    Args:
        current_column_id: ID of the current column

    Returns:
        ID of the previous column (toggles between Column 1 and Column 2)
    """
    # Simple toggle between Column 1 and Column 2 (same as next)
    if current_column_id == COLUMN_1_ID:
        prev_column = COLUMN_2_ID
    else:
        # From Column 2 (or any unknown column), go to Column 1
        prev_column = COLUMN_1_ID

    logger.debug(f"Keybindings: Navigate previous column - from {current_column_id} to {prev_column}")
    return prev_column


def get_all_bindings() -> list[Binding]:
    """Get all application keybindings.

    Returns:
        List of all Binding objects
    """
    return (
        NAVIGATION_BINDINGS +
        TASK_ACTION_BINDINGS +
        LIST_BINDINGS +
        LIST_CRUD_BINDINGS +
        PRINT_BINDINGS +
        APP_CONTROL_BINDINGS
    )
