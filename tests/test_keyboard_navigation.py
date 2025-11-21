"""Tests for keyboard navigation functionality.

This module tests:
- Within-column navigation (Up/Down arrows)
- Between-column navigation (Tab/Shift+Tab)
- Focus management and indicators
- Keybinding registration and handling
"""

import pytest
from textual.binding import Binding

from taskui.ui.app import TaskUI
from taskui.ui.keybindings import (
    get_all_bindings,
    get_next_column,
    get_prev_column,
    COLUMN_1_ID,
    COLUMN_2_ID,
    COLUMN_3_ID,
    FOCUSABLE_COLUMNS,
)
from taskui.ui.components.column import TaskColumn
from taskui.models import Task


class TestKeybindings:
    """Test keybinding constants and helper functions."""

    def test_get_all_bindings_returns_list(self):
        """Test that get_all_bindings returns a list of Binding objects."""
        bindings = get_all_bindings()
        assert isinstance(bindings, list)
        assert len(bindings) > 0
        assert all(isinstance(b, Binding) for b in bindings)

    def test_navigation_bindings_present(self):
        """Test that navigation bindings are included."""
        bindings = get_all_bindings()
        binding_keys = [b.key for b in bindings]

        assert "up" in binding_keys
        assert "down" in binding_keys
        assert "tab" in binding_keys
        assert "shift+tab" in binding_keys

    def test_focusable_columns_correct(self):
        """Test that focusable columns list is correct (Column 3 is non-focusable)."""
        assert FOCUSABLE_COLUMNS == [COLUMN_1_ID, COLUMN_2_ID]

    def test_letter_keybindings_case_insensitive(self):
        """Test that letter keybindings work with both uppercase and lowercase (Issue #26)."""
        bindings = get_all_bindings()
        binding_dict = {b.key: b.action for b in bindings}

        # Test task action bindings accept both cases
        assert "n,N" in binding_dict
        assert binding_dict["n,N"] == "new_sibling_task"

        assert "c,C" in binding_dict
        assert binding_dict["c,C"] == "new_child_task"

        assert "e,E" in binding_dict
        assert binding_dict["e,E"] == "edit_task"

        # Test print binding
        assert "p,P" in binding_dict
        assert binding_dict["p,P"] == "print_column"

        # Test quit binding
        assert "q,Q" in binding_dict
        assert binding_dict["q,Q"] == "quit"

    def test_get_next_column_toggles(self):
        """Test that get_next_column toggles between Column 1 and Column 2."""
        assert get_next_column(COLUMN_1_ID) == COLUMN_2_ID
        assert get_next_column(COLUMN_2_ID) == COLUMN_1_ID  # Toggles back

    def test_get_next_column_handles_invalid(self):
        """Test that get_next_column handles invalid input."""
        result = get_next_column("invalid-column")
        assert result == COLUMN_1_ID  # Returns first column as fallback

    def test_get_prev_column_toggles(self):
        """Test that get_prev_column toggles between Column 1 and Column 2."""
        assert get_prev_column(COLUMN_1_ID) == COLUMN_2_ID  # Toggles
        assert get_prev_column(COLUMN_2_ID) == COLUMN_1_ID  # Toggles back

    def test_get_prev_column_handles_invalid(self):
        """Test that get_prev_column handles invalid input."""
        result = get_prev_column("invalid-column")
        assert result == COLUMN_1_ID  # Returns Column 1 (toggles from unknown)


class TestTaskUIKeyboardNavigation:
    """Test keyboard navigation in the TaskUI app."""

    @pytest.fixture
    async def app(self):
        """Create a TaskUI app instance for testing."""
        app = TaskUI()
        async with app.run_test() as pilot:
            yield pilot

    async def test_app_initializes_with_focus_on_column_1(self, app):
        """Test that app starts with focus on Column 1."""
        taskui = app.app
        assert taskui._focused_column_id == COLUMN_1_ID

    async def test_columns_focusability(self, app):
        """Test that Column 1 and 2 are focusable, Column 3 is not."""
        taskui = app.app
        from taskui.ui.components.detail_panel import DetailPanel

        # Query all columns
        column1 = taskui.query_one(f"#{COLUMN_1_ID}", TaskColumn)
        column2 = taskui.query_one(f"#{COLUMN_2_ID}", TaskColumn)
        column3 = taskui.query_one(f"#{COLUMN_3_ID}", DetailPanel)

        assert column1.can_focus
        assert column2.can_focus
        assert not column3.can_focus  # Column 3 is display-only

    async def test_tab_toggles_between_columns(self, app):
        """Test that Tab action toggles between Column 1 and Column 2."""
        taskui = app.app

        # Start at Column 1
        assert taskui._focused_column_id == COLUMN_1_ID

        # Call navigate_next_column action (Column 1 → Column 2)
        taskui.action_navigate_next_column()
        await app.pause()
        assert taskui._focused_column_id == COLUMN_2_ID

        # Call action again (Column 2 → Column 1)
        taskui.action_navigate_next_column()
        await app.pause()
        assert taskui._focused_column_id == COLUMN_1_ID

        # Call action again (Column 1 → Column 2)
        taskui.action_navigate_next_column()
        await app.pause()
        assert taskui._focused_column_id == COLUMN_2_ID

    async def test_shift_tab_toggles_between_columns(self, app):
        """Test that Shift+Tab action toggles between Column 1 and Column 2."""
        taskui = app.app

        # Start at Column 1
        assert taskui._focused_column_id == COLUMN_1_ID

        # Call navigate_prev_column action (Column 1 → Column 2)
        taskui.action_navigate_prev_column()
        await app.pause()
        assert taskui._focused_column_id == COLUMN_2_ID

        # Call action again (Column 2 → Column 1)
        taskui.action_navigate_prev_column()
        await app.pause()
        assert taskui._focused_column_id == COLUMN_1_ID

        # Call action again (Column 1 → Column 2)
        taskui.action_navigate_prev_column()
        await app.pause()
        assert taskui._focused_column_id == COLUMN_2_ID

    async def test_up_down_navigation_with_no_tasks(self, app):
        """Test that Up/Down navigation works gracefully with no tasks."""
        taskui = app.app

        # Pressing up/down should not crash when there are no tasks
        await app.press("down")
        await app.press("up")

        # App should still be running
        assert taskui.is_running

    async def test_action_handlers_exist(self, app):
        """Test that navigation action handlers exist."""
        taskui = app.app

        assert hasattr(taskui, "action_navigate_up")
        assert hasattr(taskui, "action_navigate_down")
        assert hasattr(taskui, "action_navigate_next_column")
        assert hasattr(taskui, "action_navigate_prev_column")

    async def test_get_focused_column_returns_column(self, app):
        """Test that _get_focused_column returns the correct column."""
        taskui = app.app

        # Should return Column 1 initially
        column = taskui._get_focused_column()
        assert isinstance(column, TaskColumn)
        assert column.column_id == COLUMN_1_ID

        # Navigate to Column 2
        taskui.action_navigate_next_column()
        await app.pause()
        column = taskui._get_focused_column()
        assert isinstance(column, TaskColumn)
        assert column.column_id == COLUMN_2_ID

    async def test_set_column_focus_updates_state(self, app):
        """Test that _set_column_focus updates the focused column."""
        taskui = app.app

        # Set focus to Column 2
        taskui._set_column_focus(COLUMN_2_ID)
        assert taskui._focused_column_id == COLUMN_2_ID

        # Set focus to Column 3
        taskui._set_column_focus(COLUMN_3_ID)
        assert taskui._focused_column_id == COLUMN_3_ID

    async def test_set_column_focus_handles_invalid_id(self, app):
        """Test that _set_column_focus handles invalid column IDs gracefully."""
        taskui = app.app
        original_focus = taskui._focused_column_id

        # Try to set focus to invalid column (should not crash)
        taskui._set_column_focus("invalid-column-id")

        # Focus should remain unchanged
        assert taskui._focused_column_id == original_focus


class TestTaskColumnNavigation:
    """Test navigation within TaskColumn widgets."""

    @pytest.fixture
    def sample_tasks(self):
        """Create sample tasks for testing."""
        return [
            Task(
                id="00000000-0000-0000-0000-000000000001",
                title="Task 1",
                list_id="00000000-0000-0000-0000-000000000100",
                level=0,
                position=0
            ),
            Task(
                id="00000000-0000-0000-0000-000000000002",
                title="Task 2",
                list_id="00000000-0000-0000-0000-000000000100",
                level=0,
                position=1
            ),
            Task(
                id="00000000-0000-0000-0000-000000000003",
                title="Task 3",
                list_id="00000000-0000-0000-0000-000000000100",
                level=0,
                position=2
            ),
        ]

    @pytest.fixture
    async def column_with_tasks(self, sample_tasks):
        """Create a TaskColumn with sample tasks."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield TaskColumn(
                    column_id="test-column",
                    title="Test Column",
                    id="test-column"
                )

        app = TestApp()
        async with app.run_test() as pilot:
            column = app.query_one("#test-column", TaskColumn)
            column.set_tasks(sample_tasks)
            await pilot.pause()
            yield pilot, column

    async def test_navigate_down_moves_selection(self, column_with_tasks):
        """Test that navigate_down moves selection down."""
        pilot, column = column_with_tasks

        # Start at index 0
        assert column._selected_index == 0

        # Navigate down
        column.navigate_down()
        await pilot.pause()
        assert column._selected_index == 1

        # Navigate down again
        column.navigate_down()
        await pilot.pause()
        assert column._selected_index == 2

    async def test_navigate_down_stops_at_end(self, column_with_tasks):
        """Test that navigate_down stops at the last task."""
        pilot, column = column_with_tasks

        # Navigate to the end
        column.navigate_down()
        column.navigate_down()
        await pilot.pause()
        assert column._selected_index == 2

        # Try to navigate down past the end
        column.navigate_down()
        await pilot.pause()
        assert column._selected_index == 2  # Should stay at 2

    async def test_navigate_up_moves_selection(self, column_with_tasks):
        """Test that navigate_up moves selection up."""
        pilot, column = column_with_tasks

        # Start at index 2
        column._update_selection(2)
        await pilot.pause()
        assert column._selected_index == 2

        # Navigate up
        column.navigate_up()
        await pilot.pause()
        assert column._selected_index == 1

        # Navigate up again
        column.navigate_up()
        await pilot.pause()
        assert column._selected_index == 0

    async def test_navigate_up_stops_at_beginning(self, column_with_tasks):
        """Test that navigate_up stops at the first task."""
        pilot, column = column_with_tasks

        # Start at index 0
        assert column._selected_index == 0

        # Try to navigate up past the beginning
        column.navigate_up()
        await pilot.pause()
        assert column._selected_index == 0  # Should stay at 0

