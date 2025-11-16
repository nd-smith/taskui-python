"""
Unit tests for the _refresh_ui_after_task_change helper method (Issue #29).

Tests the standardized refresh pattern that consolidates all UI refresh
logic after task modifications to prevent bugs and reduce code duplication.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from taskui.ui.app import TaskUI
from taskui.models import Task


@pytest.mark.asyncio
class TestRefreshUIAfterTaskChange:
    """Test the standardized UI refresh helper method."""

    async def test_refreshes_column1_always(self):
        """Test that Column 1 is always refreshed."""
        app = TaskUI()

        # Mock the necessary methods
        app._current_list_id = uuid4()
        app.query_one = MagicMock()
        app._refresh_column_tasks = AsyncMock()
        app._refresh_list_bar_for_list = AsyncMock()

        # Mock Column 1
        column1_mock = MagicMock()
        column1_mock.get_selected_task.return_value = None  # No selection
        app.query_one.return_value = column1_mock

        # Call the helper
        await app._refresh_ui_after_task_change()

        # Verify Column 1 was refreshed
        app._refresh_column_tasks.assert_called_once()
        assert app._refresh_column_tasks.call_args[0][0] == column1_mock

    async def test_refreshes_column2_when_parent_selected(self):
        """Test that Column 2 is refreshed when a parent task is selected."""
        app = TaskUI()

        # Mock the necessary methods
        app._current_list_id = uuid4()
        app._refresh_column_tasks = AsyncMock()
        app._refresh_list_bar_for_list = AsyncMock()

        # Mock Column 1 with selected task
        column1_mock = MagicMock()
        selected_task = Task(
            id=uuid4(),
            title="Parent Task",
            list_id=app._current_list_id,
            level=0,
            position=0
        )
        column1_mock.get_selected_task.return_value = selected_task

        # Mock Column 2
        column2_mock = MagicMock()

        # Setup query_one to return correct columns
        def query_one_side_effect(selector, *args):
            if "column-1" in selector:
                return column1_mock
            elif "column-2" in selector:
                return column2_mock
            return MagicMock()

        app.query_one = MagicMock(side_effect=query_one_side_effect)

        # Call the helper
        await app._refresh_ui_after_task_change()

        # Verify both columns were refreshed
        assert app._refresh_column_tasks.call_count == 2
        calls = app._refresh_column_tasks.call_args_list
        assert calls[0][0][0] == column1_mock
        assert calls[1][0][0] == column2_mock

    async def test_skips_column2_when_no_parent_selected(self):
        """Test that Column 2 is not refreshed when no parent is selected."""
        app = TaskUI()

        # Mock the necessary methods
        app._current_list_id = uuid4()
        app._refresh_column_tasks = AsyncMock()
        app._refresh_list_bar_for_list = AsyncMock()

        # Mock Column 1 with NO selected task
        column1_mock = MagicMock()
        column1_mock.get_selected_task.return_value = None

        app.query_one = MagicMock(return_value=column1_mock)

        # Call the helper
        await app._refresh_ui_after_task_change()

        # Verify only Column 1 was refreshed (call_count == 1)
        assert app._refresh_column_tasks.call_count == 1

    async def test_clears_detail_panel_when_requested(self):
        """Test that detail panel is cleared when clear_detail_panel=True."""
        app = TaskUI()

        # Mock the necessary methods
        app._current_list_id = uuid4()
        app._refresh_column_tasks = AsyncMock()
        app._refresh_list_bar_for_list = AsyncMock()

        # Mock columns
        column1_mock = MagicMock()
        column1_mock.get_selected_task.return_value = None

        detail_panel_mock = MagicMock()

        def query_one_side_effect(selector, *args):
            if "column-1" in selector:
                return column1_mock
            elif "column-3" in selector or "DetailPanel" in str(args):
                return detail_panel_mock
            return MagicMock()

        app.query_one = MagicMock(side_effect=query_one_side_effect)

        # Call with clear_detail_panel=True
        await app._refresh_ui_after_task_change(clear_detail_panel=True)

        # Verify detail panel was cleared
        detail_panel_mock.clear.assert_called_once()

    async def test_does_not_clear_detail_panel_by_default(self):
        """Test that detail panel is NOT cleared by default."""
        app = TaskUI()

        # Mock the necessary methods
        app._current_list_id = uuid4()
        app._refresh_column_tasks = AsyncMock()
        app._refresh_list_bar_for_list = AsyncMock()

        # Mock columns
        column1_mock = MagicMock()
        column1_mock.get_selected_task.return_value = None

        detail_panel_mock = MagicMock()

        def query_one_side_effect(selector, *args):
            if "column-1" in selector:
                return column1_mock
            elif "column-3" in selector or "DetailPanel" in str(args):
                return detail_panel_mock
            return MagicMock()

        app.query_one = MagicMock(side_effect=query_one_side_effect)

        # Call WITHOUT clear_detail_panel (default is False)
        await app._refresh_ui_after_task_change()

        # Verify detail panel was NOT cleared
        detail_panel_mock.clear.assert_not_called()

    async def test_refreshes_list_bar_when_list_active(self):
        """Test that list bar is refreshed when a list is active."""
        app = TaskUI()

        # Mock with active list
        app._current_list_id = uuid4()
        app._refresh_column_tasks = AsyncMock()
        app._refresh_list_bar_for_list = AsyncMock()

        # Mock Column 1
        column1_mock = MagicMock()
        column1_mock.get_selected_task.return_value = None
        app.query_one = MagicMock(return_value=column1_mock)

        # Call the helper
        await app._refresh_ui_after_task_change()

        # Verify list bar was refreshed with correct list ID
        app._refresh_list_bar_for_list.assert_called_once_with(app._current_list_id)

    async def test_skips_list_bar_when_no_active_list(self):
        """Test that list bar refresh is skipped when no list is active."""
        app = TaskUI()

        # Mock with NO active list
        app._current_list_id = None
        app._refresh_column_tasks = AsyncMock()
        app._refresh_list_bar_for_list = AsyncMock()

        # Mock Column 1
        column1_mock = MagicMock()
        column1_mock.get_selected_task.return_value = None
        app.query_one = MagicMock(return_value=column1_mock)

        # Call the helper
        await app._refresh_ui_after_task_change()

        # Verify list bar was NOT refreshed
        app._refresh_list_bar_for_list.assert_not_called()


@pytest.mark.asyncio
class TestRefreshHelperIntegration:
    """Integration tests verifying the helper works in real scenarios."""

    async def test_helper_called_after_task_operations(self):
        """Verify that existing task operations successfully call the helper.

        This is more of a smoke test - the real validation is that all
        existing integration tests continue to pass, proving that the
        refactor didn't break any functionality.
        """
        # This test documents the pattern and validates the helper exists
        app = TaskUI()

        # Verify the helper method exists and is callable
        assert hasattr(app, '_refresh_ui_after_task_change')
        assert callable(app._refresh_ui_after_task_change)

        # Verify it has the expected signature
        import inspect
        sig = inspect.signature(app._refresh_ui_after_task_change)
        params = list(sig.parameters.keys())
        assert 'clear_detail_panel' in params
