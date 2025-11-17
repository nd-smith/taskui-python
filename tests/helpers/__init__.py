"""Test helper utilities for TaskUI integration tests.

This package provides reusable helper functions to reduce test brittleness
and improve test maintainability.
"""

from tests.helpers.ui_helpers import (
    # Task Creation Helpers
    create_task_via_modal,
    create_sibling_task,
    create_child_task,

    # Selection Helpers
    select_task_in_column,
    get_selected_task_from_column,

    # Navigation Helpers
    navigate_to_column,
    navigate_down,
    navigate_up,

    # Modal Helpers
    fill_task_modal,
    save_modal,
    cancel_modal,

    # Assertion Helpers
    assert_column_has_tasks,
    assert_task_in_column,
    assert_task_exists_in_db,

    # Database Helpers
    get_task_service,
    get_tasks_from_db,
)

__all__ = [
    # Task Creation Helpers
    "create_task_via_modal",
    "create_sibling_task",
    "create_child_task",

    # Selection Helpers
    "select_task_in_column",
    "get_selected_task_from_column",

    # Navigation Helpers
    "navigate_to_column",
    "navigate_down",
    "navigate_up",

    # Modal Helpers
    "fill_task_modal",
    "save_modal",
    "cancel_modal",

    # Assertion Helpers
    "assert_column_has_tasks",
    "assert_task_in_column",
    "assert_task_exists_in_db",

    # Database Helpers
    "get_task_service",
    "get_tasks_from_db",
]
