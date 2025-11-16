"""Keyboard navigation and keybindings for TaskUI.

This module defines all keyboard shortcuts and navigation handlers for the
TaskUI application, including:
- Within-column navigation (Up/Down arrows)
- Between-column navigation (Tab/Shift+Tab)
- Task actions (N, C, E, Space, A, P, Delete)
- Application controls (Q, ?)
"""

from typing import Optional
from textual.app import ComposeResult
from textual.binding import Binding


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
    Binding("space", "toggle_completion", "Toggle Complete", show=True),
    Binding("a,A", "archive_task", "Archive Task", show=True),
    Binding("v,V", "view_archives", "View Archives", show=True),
    Binding("delete,backspace", "delete_task", "Delete Task", show=True),
]

# List management keybindings
LIST_BINDINGS = [
    Binding("1", "switch_list_1", "List 1", show=True),
    Binding("2", "switch_list_2", "List 2", show=True),
    Binding("3", "switch_list_3", "List 3", show=True),
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

# Column navigation order
COLUMN_ORDER = [COLUMN_1_ID, COLUMN_2_ID, COLUMN_3_ID]


def get_next_column(current_column_id: str) -> Optional[str]:
    """Get the next column in the navigation order.

    Args:
        current_column_id: ID of the current column

    Returns:
        ID of the next column, or None if at the end
    """
    try:
        current_index = COLUMN_ORDER.index(current_column_id)
        next_index = (current_index + 1) % len(COLUMN_ORDER)
        return COLUMN_ORDER[next_index]
    except ValueError:
        # If current column not found, return first column
        return COLUMN_ORDER[0]


def get_prev_column(current_column_id: str) -> Optional[str]:
    """Get the previous column in the navigation order.

    Args:
        current_column_id: ID of the current column

    Returns:
        ID of the previous column, or None if at the beginning
    """
    try:
        current_index = COLUMN_ORDER.index(current_column_id)
        prev_index = (current_index - 1) % len(COLUMN_ORDER)
        return COLUMN_ORDER[prev_index]
    except ValueError:
        # If current column not found, return last column
        return COLUMN_ORDER[-1]


def get_all_bindings() -> list[Binding]:
    """Get all application keybindings.

    Returns:
        List of all Binding objects
    """
    return (
        NAVIGATION_BINDINGS +
        TASK_ACTION_BINDINGS +
        LIST_BINDINGS +
        PRINT_BINDINGS +
        APP_CONTROL_BINDINGS
    )
