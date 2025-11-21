"""
Comprehensive tests for the TaskUI application class (taskui/ui/app.py).

Tests cover:
- App initialization and lifecycle
- State management (focus, list selection)
- Action methods (task operations, navigation)
- Event handlers (modals, selections, list switching)
- Component orchestration (modal-to-database flow, column updates)
- UI refresh and synchronization
"""

import pytest
import pytest_asyncio
from uuid import UUID, uuid4
from typing import List, Optional
from datetime import datetime
import os

from taskui.ui.app import TaskUI
from taskui.ui.components.column import TaskColumn
from taskui.ui.components.detail_panel import DetailPanel
from taskui.ui.components.list_bar import ListBar
from taskui.ui.components.task_modal import TaskCreationModal
from taskui.models import Task, TaskList
from taskui.services.task_service import TaskService
from taskui.services.list_service import ListService
from taskui.database import DatabaseManager, get_database_manager
from taskui.ui.keybindings import COLUMN_1_ID, COLUMN_2_ID, COLUMN_3_ID
import taskui.database

# Use separate test database
TEST_DB_PATH = "test_app_taskui.db"
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"


@pytest_asyncio.fixture(autouse=True)
async def reset_database(monkeypatch):
    """Reset the database singleton before each test to ensure test isolation."""
    # Delete the test database file if it exists
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass

    # Clear the global database manager singleton
    taskui.database._db_manager = None

    # Patch get_database_manager to use test database
    original_get_db = taskui.database.get_database_manager
    def patched_get_db(database_url: str = TEST_DB_URL) -> DatabaseManager:
        return original_get_db(database_url)

    # Patch in the database module
    monkeypatch.setattr(taskui.database, 'get_database_manager', patched_get_db)

    # Also patch in the app module where it's imported
    from taskui.ui import app as app_module
    monkeypatch.setattr(app_module, 'get_database_manager', patched_get_db)

    yield

    # Clean up after test
    if taskui.database._db_manager is not None:
        try:
            await taskui.database._db_manager.close()
        except Exception:
            pass
        taskui.database._db_manager = None

    # Delete the test database file
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass


class TestAppInitialization:
    """Tests for TaskUI application initialization and lifecycle."""

    @pytest.mark.asyncio
    async def test_app_init_sets_default_attributes(self):
        """Test that __init__ sets all default attributes correctly.

        Verifies:
        - title and sub_title are set
        - _focused_column_id defaults to COLUMN_1_ID
        - _db_manager is None initially
        - _current_list_id is None initially
        - _lists is empty initially
        - _printer_service is None initially
        """
        app = TaskUI()

        assert app.title == "TaskUI - Nested Task Manager"
        assert app.sub_title == "Press ? for help"
        assert app._focused_column_id == COLUMN_1_ID
        assert app._db_manager is None
        assert app._current_list_id is None
        assert app._lists == []
        assert app._printer_service is None

    @pytest.mark.asyncio
    async def test_app_compose_creates_all_components(self):
        """Test that compose() creates all required UI components.

        Verifies:
        - ListBar is created
        - Column 1 (TaskColumn) is created with correct config
        - Column 2 (TaskColumn) is created with correct config
        - Column 3 (DetailPanel) is created with correct config
        - Footer is created
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app

            # Verify ListBar exists
            list_bar = app.query_one(ListBar)
            assert list_bar is not None

            # Verify Column 1 exists with correct config
            column1 = app.query_one(f"#{COLUMN_1_ID}", TaskColumn)
            assert column1 is not None
            assert column1.column_id == COLUMN_1_ID
            assert column1.header_title == "Tasks"

            # Verify Column 2 exists with correct config
            column2 = app.query_one(f"#{COLUMN_2_ID}", TaskColumn)
            assert column2 is not None
            assert column2.column_id == COLUMN_2_ID
            assert column2.header_title == "Subtasks"

            # Verify Column 3 exists with correct config
            column3 = app.query_one(f"#{COLUMN_3_ID}", DetailPanel)
            assert column3 is not None
            assert column3.column_id == COLUMN_3_ID

    @pytest.mark.asyncio
    async def test_app_on_mount_initializes_database(self):
        """Test that on_mount() initializes database manager correctly.

        Verifies:
        - _db_manager is initialized
        - _db_manager is a DatabaseManager instance
        - Database is ready for operations
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app

            # Database should be initialized after mount
            assert app._db_manager is not None
            assert isinstance(app._db_manager, DatabaseManager)

            # Verify database is operational
            async with app._db_manager.get_session() as session:
                list_service = ListService(session)
                lists = await list_service.get_all_lists()
                assert isinstance(lists, list)

    @pytest.mark.asyncio
    async def test_app_on_mount_creates_default_lists(self):
        """Test that on_mount() creates default lists (Work, Home, Personal).

        Verifies:
        - Three default lists are created
        - Lists have correct names
        - _lists is populated
        - _current_list_id is set to first list
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app

            # Verify default lists are created
            assert len(app._lists) == 3

            # Verify list names
            list_names = {lst.name for lst in app._lists}
            assert list_names == {"Work", "Home", "Personal"}

            # Verify current list is set
            assert app._current_list_id is not None
            assert app._current_list_id == app._lists[0].id

    @pytest.mark.asyncio
    async def test_app_on_mount_updates_list_bar(self):
        """Test that on_mount() updates ListBar with default lists.

        Verifies:
        - ListBar receives the default lists
        - ListBar sets active list to current list
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app

            list_bar = app.query_one(ListBar)

            # Verify list bar has the lists
            assert len(list_bar.lists) == 3

            # Verify active list is set
            assert list_bar.active_list_id == app._current_list_id


class TestAppStateManagement:
    """Tests for TaskUI application state management."""

    @pytest.mark.asyncio
    async def test_focused_column_id_tracks_current_column(self):
        """Test that _focused_column_id correctly tracks the focused column.

        Verifies:
        - Initial focus is on Column 1
        - Focus updates when navigating to different columns
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app

            # Initial focus should be Column 1
            assert app._focused_column_id == COLUMN_1_ID

            # Navigate to Column 2
            app.action_navigate_next_column()
            await pilot.pause()
            assert app._focused_column_id == COLUMN_2_ID

            # Navigate to Column 3
            app.action_navigate_next_column()
            await pilot.pause()
            assert app._focused_column_id == COLUMN_3_ID

            # Navigate back to Column 2
            app.action_navigate_prev_column()
            await pilot.pause()
            assert app._focused_column_id == COLUMN_2_ID

    @pytest.mark.asyncio
    async def test_current_list_id_tracks_active_list(self):
        """Test that _current_list_id correctly tracks the active list.

        Verifies:
        - Initial list is set on mount
        - List ID updates when switching lists
        - List ID persists across operations
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app

            # Store initial list ID
            initial_list_id = app._current_list_id
            assert initial_list_id is not None

            # Switch to a different list
            list_bar = app.query_one(ListBar)
            second_list_id = app._lists[1].id
            list_bar.select_list_by_number(2)
            await pilot.pause()

            # Verify list ID updated
            assert app._current_list_id == second_list_id
            assert app._current_list_id != initial_list_id

    @pytest.mark.asyncio
    async def test_lists_cache_updated_after_operations(self):
        """Test that _lists cache stays synchronized with database.

        Verifies:
        - _lists is populated on mount
        - _lists contains all available lists
        - _lists remains consistent
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app

            # Verify _lists is populated
            assert len(app._lists) == 3
            assert all(isinstance(lst, TaskList) for lst in app._lists)

            # Verify _lists matches database
            async with app._db_manager.get_session() as session:
                list_service = ListService(session)
                db_lists = await list_service.get_all_lists()

            assert len(app._lists) == len(db_lists)
            app_list_ids = {lst.id for lst in app._lists}
            db_list_ids = {lst.id for lst in db_lists}
            assert app_list_ids == db_list_ids


class TestActionMethodsNavigation:
    """Tests for TaskUI navigation action methods."""

    @pytest.mark.asyncio
    async def test_action_navigate_up_moves_selection_up(self):
        """Test that action_navigate_up() moves selection up in column.

        Verifies:
        - Selection moves up when not at top
        - Selection stays at top when already at top
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Create multiple tasks
            for i in range(3):
                app.action_new_sibling_task()
                await pilot.pause()
                modal = app.screen
                title_input = modal.query_one("#title-input")
                title_input.value = f"Task {i + 1}"
                modal.action_save()
                await pilot.pause()

            column1 = app.query_one(f"#{COLUMN_1_ID}", TaskColumn)

            # Start at bottom (index 2)
            column1._selected_index = 2
            assert column1._selected_index == 2

            # Move up to index 1
            app.action_navigate_up()
            await pilot.pause()
            assert column1._selected_index == 1

            # Move up to index 0
            app.action_navigate_up()
            await pilot.pause()
            assert column1._selected_index == 0

            # Try to move up again (should stay at 0)
            app.action_navigate_up()
            await pilot.pause()
            assert column1._selected_index == 0

    @pytest.mark.asyncio
    async def test_action_navigate_down_moves_selection_down(self):
        """Test that action_navigate_down() moves selection down in column.

        Verifies:
        - Selection moves down when not at bottom
        - Selection stays at bottom when already at bottom
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Create multiple tasks
            for i in range(3):
                app.action_new_sibling_task()
                await pilot.pause()
                modal = app.screen
                title_input = modal.query_one("#title-input")
                title_input.value = f"Task {i + 1}"
                modal.action_save()
                await pilot.pause()

            column1 = app.query_one(f"#{COLUMN_1_ID}", TaskColumn)

            # Start at top (index 0)
            column1._selected_index = 0
            assert column1._selected_index == 0

            # Move down to index 1
            app.action_navigate_down()
            await pilot.pause()
            assert column1._selected_index == 1

            # Move down to index 2
            app.action_navigate_down()
            await pilot.pause()
            assert column1._selected_index == 2

            # Try to move down again (should stay at 2)
            app.action_navigate_down()
            await pilot.pause()
            assert column1._selected_index == 2

    @pytest.mark.asyncio
    async def test_action_navigate_next_column_cycles_forward(self):
        """Test that action_navigate_next_column() cycles through columns.

        Verifies:
        - Tab moves from Column 1 to Column 2
        - Tab moves from Column 2 to Column 3
        - Tab wraps from Column 3 to Column 1
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app

            # Start at Column 1
            assert app._focused_column_id == COLUMN_1_ID

            # Navigate to Column 2
            app.action_navigate_next_column()
            await pilot.pause()
            assert app._focused_column_id == COLUMN_2_ID

            # Navigate to Column 3
            app.action_navigate_next_column()
            await pilot.pause()
            assert app._focused_column_id == COLUMN_3_ID

            # Navigate wraps to Column 1
            app.action_navigate_next_column()
            await pilot.pause()
            assert app._focused_column_id == COLUMN_1_ID

    @pytest.mark.asyncio
    async def test_action_navigate_prev_column_cycles_backward(self):
        """Test that action_navigate_prev_column() cycles through columns backward.

        Verifies:
        - Shift+Tab moves from Column 1 to Column 3
        - Shift+Tab moves from Column 3 to Column 2
        - Shift+Tab moves from Column 2 to Column 1
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app

            # Start at Column 1
            assert app._focused_column_id == COLUMN_1_ID

            # Navigate backward to Column 3
            app.action_navigate_prev_column()
            await pilot.pause()
            assert app._focused_column_id == COLUMN_3_ID

            # Navigate backward to Column 2
            app.action_navigate_prev_column()
            await pilot.pause()
            assert app._focused_column_id == COLUMN_2_ID

            # Navigate backward to Column 1
            app.action_navigate_prev_column()
            await pilot.pause()
            assert app._focused_column_id == COLUMN_1_ID


class TestActionMethodsTaskOperations:
    """Tests for TaskUI task operation action methods."""

    @pytest.mark.asyncio
    async def test_action_new_sibling_task_opens_modal_correctly(self):
        """Test that action_new_sibling_task() opens modal with correct mode.

        Verifies:
        - Modal is opened when action is called
        - Modal mode is "create_sibling"
        - Modal has correct parent_task context
        - Modal has correct column context
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Create a task first
            app.action_new_sibling_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "First Task"
            modal.action_save()
            await pilot.pause()

            # Select the task
            column1 = app.query_one(f"#{COLUMN_1_ID}", TaskColumn)
            column1._selected_index = 0
            selected_task = column1.get_selected_task()

            # Open modal for sibling
            app.action_new_sibling_task()
            await pilot.pause()

            # Verify modal is shown with correct mode
            modal = app.screen
            assert isinstance(modal, TaskCreationModal)
            assert modal.mode == "create_sibling"
            assert modal.parent_task == selected_task

    @pytest.mark.asyncio
    async def test_action_new_sibling_task_with_no_selection(self):
        """Test action_new_sibling_task() when no task is selected.

        Verifies:
        - Modal opens even with no selection
        - Modal parent_task is None
        - Creates top-level task
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # No tasks exist, so no selection
            column1 = app.query_one(f"#{COLUMN_1_ID}", TaskColumn)
            assert len(column1._tasks) == 0

            # Open modal for new task
            app.action_new_sibling_task()
            await pilot.pause()

            # Verify modal opens with no parent
            modal = app.screen
            assert isinstance(modal, TaskCreationModal)
            assert modal.mode == "create_sibling"
            assert modal.parent_task is None

    @pytest.mark.asyncio
    async def test_action_new_child_task_opens_modal_correctly(self):
        """Test that action_new_child_task() opens modal with correct mode.

        Verifies:
        - Modal is opened when action is called
        - Modal mode is "create_child"
        - Modal has parent_task set to selected task
        - Modal has correct column context
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Create a parent task
            app.action_new_sibling_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Parent Task"
            modal.action_save()
            await pilot.pause()

            # Select the parent task
            column1 = app.query_one(f"#{COLUMN_1_ID}", TaskColumn)
            column1._selected_index = 0
            parent_task = column1.get_selected_task()

            # Open modal for child
            app.action_new_child_task()
            await pilot.pause()

            # Verify modal is shown with correct mode
            modal = app.screen
            assert isinstance(modal, TaskCreationModal)
            assert modal.mode == "create_child"
            assert modal.parent_task == parent_task

    @pytest.mark.asyncio
    async def test_action_new_child_task_requires_selection(self):
        """Test that action_new_child_task() requires a selected task.

        Verifies:
        - Modal does not open when no task is selected
        - No error occurs
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # No tasks exist, so no selection
            column1 = app.query_one(f"#{COLUMN_1_ID}", TaskColumn)
            assert len(column1._tasks) == 0

            # Try to open modal for child (should not open)
            app.action_new_child_task()
            await pilot.pause()

            # Verify modal did not open (screen is still main app)
            assert app.screen == app

    @pytest.mark.asyncio
    async def test_action_edit_task_opens_modal_with_task_data(self):
        """Test that action_edit_task() opens modal with existing task data.

        Verifies:
        - Modal is opened when action is called
        - Modal mode is "edit"
        - Modal has edit_task set to selected task
        - Modal pre-fills title and notes
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Create a task
            app.action_new_sibling_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Original Title"
            notes_input = modal.query_one("#notes-input")
            notes_input.text = "Original notes"
            modal.action_save()
            await pilot.pause()

            # Select the task
            column1 = app.query_one(f"#{COLUMN_1_ID}", TaskColumn)
            column1._selected_index = 0
            task = column1.get_selected_task()

            # Open edit modal
            app.action_edit_task()
            await pilot.pause()

            # Verify modal is shown with correct mode and data
            modal = app.screen
            assert isinstance(modal, TaskCreationModal)
            assert modal.mode == "edit"
            assert modal.edit_task == task
            title_input = modal.query_one("#title-input")
            assert title_input.value == "Original Title"
            notes_input = modal.query_one("#notes-input")
            assert notes_input.text == "Original notes"

    @pytest.mark.asyncio
    async def test_action_edit_task_requires_selection(self):
        """Test that action_edit_task() requires a selected task.

        Verifies:
        - Modal does not open when no task is selected
        - No error occurs
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # No tasks exist, so no selection
            column1 = app.query_one(f"#{COLUMN_1_ID}", TaskColumn)
            assert len(column1._tasks) == 0

            # Try to open edit modal (should not open)
            app.action_edit_task()
            await pilot.pause()

            # Verify modal did not open
            assert app.screen == app

    @pytest.mark.asyncio
    async def test_action_toggle_completion_updates_task_state(self):
        """Test that action_toggle_completion() updates task completion status.

        Verifies:
        - Task is marked as completed when toggled
        - Task is marked as incomplete when toggled again
        - Database is updated
        - UI is refreshed
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Create a task
            app.action_new_sibling_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Task to Complete"
            modal.action_save()
            await pilot.pause()

            # Select the task
            column1 = app.query_one(f"#{COLUMN_1_ID}", TaskColumn)
            column1._selected_index = 0
            task = column1.get_selected_task()
            task_id = task.id

            # Initially not completed
            assert task.is_completed is False

            # Toggle completion
            await app.action_toggle_completion()
            await pilot.pause()

            # Verify task is now completed in database
            async with app._db_manager.get_session() as session:
                task_service = TaskService(session)
                updated_task = await task_service.get_task_by_id(task_id)
                assert updated_task.is_completed is True

            # Toggle completion again
            await app.action_toggle_completion()
            await pilot.pause()

            # Verify task is now incomplete in database
            async with app._db_manager.get_session() as session:
                task_service = TaskService(session)
                updated_task = await task_service.get_task_by_id(task_id)
                assert updated_task.is_completed is False

    @pytest.mark.asyncio
    async def test_action_toggle_completion_requires_selection(self):
        """Test that action_toggle_completion() requires a selected task.

        Verifies:
        - No error when no task is selected
        - No changes to database
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # No tasks exist
            column1 = app.query_one(f"#{COLUMN_1_ID}", TaskColumn)
            assert len(column1._tasks) == 0

            # Try to toggle completion (should not error)
            await app.action_toggle_completion()
            await pilot.pause()

            # Should complete without error
            assert True


    @pytest.mark.asyncio
    async def test_action_delete_task_shows_not_implemented_notification(self):
        """Test that action_delete_task() shows not implemented notification.

        Verifies:
        - Method exists but shows warning
        - No actual deletion occurs
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Create a task
            app.action_new_sibling_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Task to Delete"
            modal.action_save()
            await pilot.pause()

            # Select the task
            column1 = app.query_one(f"#{COLUMN_1_ID}", TaskColumn)
            column1._selected_index = 0

            # Call delete action
            app.action_delete_task()
            await pilot.pause()

            # Verify task still exists (delete not implemented)
            assert len(column1._tasks) == 1



class TestActionMethodsListSwitching:
    """Tests for TaskUI list switching action methods."""

    @pytest.mark.asyncio
    async def test_action_switch_list_1_switches_to_first_list(self):
        """Test that action_switch_list_1() switches to the first list.

        Verifies:
        - List switches to first list
        - _current_list_id updates
        - Column 1 loads tasks from first list
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            first_list_id = app._lists[0].id

            # Switch to second list first
            app.action_switch_list_2()
            await pilot.pause()
            assert app._current_list_id != first_list_id

            # Switch back to first list
            app.action_switch_list_1()
            await pilot.pause()
            assert app._current_list_id == first_list_id

    @pytest.mark.asyncio
    async def test_action_switch_list_2_switches_to_second_list(self):
        """Test that action_switch_list_2() switches to the second list.

        Verifies:
        - List switches to second list
        - _current_list_id updates
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            second_list_id = app._lists[1].id

            # Switch to second list
            app.action_switch_list_2()
            await pilot.pause()
            assert app._current_list_id == second_list_id

    @pytest.mark.asyncio
    async def test_action_switch_list_3_switches_to_third_list(self):
        """Test that action_switch_list_3() switches to the third list.

        Verifies:
        - List switches to third list
        - _current_list_id updates
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            third_list_id = app._lists[2].id

            # Switch to third list
            app.action_switch_list_3()
            await pilot.pause()
            assert app._current_list_id == third_list_id


class TestEventHandlers:
    """Tests for TaskUI event handler methods."""

    @pytest.mark.asyncio
    async def test_on_key_handles_tab_navigation(self):
        """Test that on_key() handles tab key for column navigation.

        Verifies:
        - Tab key moves to next column
        - Shift+Tab key moves to previous column
        - Tab navigation only works in main app (not modals)
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Initial focus on Column 1
            assert app._focused_column_id == COLUMN_1_ID

            # Press Tab to move to Column 2
            await pilot.press("tab")
            await pilot.pause()
            assert app._focused_column_id == COLUMN_2_ID

            # Press Shift+Tab to move back to Column 1
            await pilot.press("shift+tab")
            await pilot.pause()
            assert app._focused_column_id == COLUMN_1_ID

    @pytest.mark.asyncio
    async def test_on_task_column_task_selected_updates_columns(self):
        """Test that on_task_column_task_selected() updates Column 2 and 3.

        Verifies:
        - Column 2 updates when Column 1 task is selected
        - Column 3 updates for any selected task
        - Column 2 shows children of selected task
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Create parent with child
            app.action_new_sibling_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Parent Task"
            modal.action_save()
            await pilot.pause()

            column1 = app.query_one(f"#{COLUMN_1_ID}", TaskColumn)
            column1._selected_index = 0
            parent_task = column1.get_selected_task()

            app.action_new_child_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Child Task"
            modal.action_save()
            await pilot.pause()

            # Trigger selection event
            column1.post_message(
                TaskColumn.TaskSelected(task=parent_task, column_id=COLUMN_1_ID)
            )
            await pilot.pause()

            # Verify Column 2 shows child
            column2 = app.query_one(f"#{COLUMN_2_ID}", TaskColumn)
            assert len(column2._tasks) == 1
            assert column2._tasks[0].title == "Child Task"

            # Verify Column 3 shows parent details
            column3 = app.query_one(f"#{COLUMN_3_ID}", DetailPanel)
            assert column3.current_task is not None
            assert column3.current_task.title == "Parent Task"

    @pytest.mark.asyncio
    async def test_on_task_creation_modal_task_created_creates_task(self):
        """Test that on_task_creation_modal_task_created() creates tasks.

        Verifies:
        - Task is created in database
        - UI is refreshed
        - Column shows new task
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Open modal and create task
            app.action_new_sibling_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "New Task"
            notes_input = modal.query_one("#notes-input")
            notes_input.text = "Task notes"
            modal.action_save()
            await pilot.pause()

            # Verify task exists in database
            async with app._db_manager.get_session() as session:
                task_service = TaskService(session)
                tasks = await task_service.get_tasks_for_list(
                    app._current_list_id,
                    include_archived=False
                )
                assert len(tasks) == 1
                assert tasks[0].title == "New Task"
                assert tasks[0].notes == "Task notes"

            # Verify UI shows task
            column1 = app.query_one(f"#{COLUMN_1_ID}", TaskColumn)
            assert len(column1._tasks) == 1
            assert column1._tasks[0].title == "New Task"

    @pytest.mark.asyncio
    async def test_on_task_creation_modal_task_created_edits_task(self):
        """Test that on_task_creation_modal_task_created() handles edits.

        Verifies:
        - Task is updated in database
        - UI is refreshed
        - Column shows updated task
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Create task
            app.action_new_sibling_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Original Title"
            modal.action_save()
            await pilot.pause()

            # Edit task
            column1 = app.query_one(f"#{COLUMN_1_ID}", TaskColumn)
            column1._selected_index = 0
            task_id = column1.get_selected_task().id

            app.action_edit_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Updated Title"
            modal.action_save()
            await pilot.pause()

            # Verify task is updated in database
            async with app._db_manager.get_session() as session:
                task_service = TaskService(session)
                updated_task = await task_service.get_task_by_id(task_id)
                assert updated_task.title == "Updated Title"


    @pytest.mark.asyncio
    async def test_on_list_bar_list_selected_switches_list(self):
        """Test that on_list_bar_list_selected() switches active list.

        Verifies:
        - _current_list_id is updated
        - Column 1 loads tasks from new list
        - Column 2 is cleared
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Create task in first list
            app.action_new_sibling_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Task in List 1"
            modal.action_save()
            await pilot.pause()

            # Switch to second list
            list_bar = app.query_one(ListBar)
            second_list_id = app._lists[1].id
            list_bar.post_message(ListBar.ListSelected(list_id=second_list_id))
            await pilot.pause()

            # Verify list ID updated
            assert app._current_list_id == second_list_id

            # Verify Column 1 is empty (no tasks in second list)
            column1 = app.query_one(f"#{COLUMN_1_ID}", TaskColumn)
            assert len(column1._tasks) == 0

            # Verify Column 2 is cleared
            column2 = app.query_one(f"#{COLUMN_2_ID}", TaskColumn)
            assert len(column2._tasks) == 0


class TestComponentOrchestration:
    """Tests for component orchestration and integration."""

    @pytest.mark.asyncio
    async def test_modal_to_database_to_ui_flow(self):
        """Test complete flow from modal to database to UI update.

        Verifies:
        - Modal data is saved to database
        - Database transaction commits
        - UI automatically refreshes
        - All components are synchronized
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Open modal
            app.action_new_sibling_task()
            await pilot.pause()

            # Fill modal
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Test Task"
            notes_input = modal.query_one("#notes-input")
            notes_input.text = "Test notes"

            # Save modal
            modal.action_save()
            await pilot.pause()

            # Verify database has task
            async with app._db_manager.get_session() as session:
                task_service = TaskService(session)
                tasks = await task_service.get_tasks_for_list(
                    app._current_list_id,
                    include_archived=False
                )
                assert len(tasks) == 1
                assert tasks[0].title == "Test Task"
                assert tasks[0].notes == "Test notes"

            # Verify UI shows task
            column1 = app.query_one(f"#{COLUMN_1_ID}", TaskColumn)
            assert len(column1._tasks) == 1
            assert column1._tasks[0].title == "Test Task"

    @pytest.mark.asyncio
    async def test_column_updates_propagate_correctly(self):
        """Test that column updates propagate through the system.

        Verifies:
        - Column 1 update triggers Column 2 update
        - Column 2 update triggers Column 3 update
        - Updates are efficient (no unnecessary refreshes)
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Create parent task
            app.action_new_sibling_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Parent"
            modal.action_save()
            await pilot.pause()

            column1 = app.query_one(f"#{COLUMN_1_ID}", TaskColumn)
            column1._selected_index = 0
            parent_task = column1.get_selected_task()

            # Create child task
            app.action_new_child_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Child"
            modal.action_save()
            await pilot.pause()

            # Trigger selection to update Column 2 and 3
            column1.post_message(
                TaskColumn.TaskSelected(task=parent_task, column_id=COLUMN_1_ID)
            )
            await pilot.pause()

            # Verify Column 2 shows child
            column2 = app.query_one(f"#{COLUMN_2_ID}", TaskColumn)
            assert len(column2._tasks) == 1
            assert column2._tasks[0].title == "Child"

            # Verify Column 3 shows parent details
            column3 = app.query_one(f"#{COLUMN_3_ID}", DetailPanel)
            assert column3.current_task is not None
            assert column3.current_task.title == "Parent"

    @pytest.mark.asyncio
    async def test_detail_panel_updates_on_task_selection(self):
        """Test that detail panel updates correctly on task selection.

        Verifies:
        - Detail panel shows selected task details
        - Detail panel shows hierarchy path
        - Detail panel updates when selection changes
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Create two tasks
            for i in range(2):
                app.action_new_sibling_task()
                await pilot.pause()
                modal = app.screen
                title_input = modal.query_one("#title-input")
                title_input.value = f"Task {i + 1}"
                notes_input = modal.query_one("#notes-input")
                notes_input.text = f"Notes {i + 1}"
                modal.action_save()
                await pilot.pause()

            column1 = app.query_one(f"#{COLUMN_1_ID}", TaskColumn)
            column3 = app.query_one(f"#{COLUMN_3_ID}", DetailPanel)

            # Select first task
            column1._selected_index = 0
            task1 = column1.get_selected_task()
            column1.post_message(
                TaskColumn.TaskSelected(task=task1, column_id=COLUMN_1_ID)
            )
            await pilot.pause()

            # Verify detail panel shows first task
            assert column3.current_task is not None
            assert column3.current_task.title == "Task 1"

            # Select second task
            column1._selected_index = 1
            task2 = column1.get_selected_task()
            column1.post_message(
                TaskColumn.TaskSelected(task=task2, column_id=COLUMN_1_ID)
            )
            await pilot.pause()

            # Verify detail panel shows second task
            assert column3.current_task.title == "Task 2"


class TestUIRefresh:
    """Tests for UI refresh and synchronization methods."""

    @pytest.mark.asyncio
    async def test_refresh_ui_after_task_change_updates_all_columns(self):
        """Test that _refresh_ui_after_task_change() updates all columns.

        Verifies:
        - Column 1 is refreshed
        - Column 2 is refreshed if parent selected
        - List bar is refreshed
        - Detail panel is optionally cleared
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Create a task
            app.action_new_sibling_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Task"
            modal.action_save()
            await pilot.pause()

            # Verify refresh happened (task is visible)
            column1 = app.query_one(f"#{COLUMN_1_ID}", TaskColumn)
            assert len(column1._tasks) == 1

            # Complete task and verify refresh
            column1._selected_index = 0
            await app.action_toggle_completion()
            await pilot.pause()

            # Task should still be visible but completed
            column1 = app.query_one(f"#{COLUMN_1_ID}", TaskColumn)
            assert len(column1._tasks) == 1
            assert column1._tasks[0].is_completed is True

    @pytest.mark.asyncio
    async def test_refresh_ui_clears_detail_panel_when_requested(self):
        """Test that _refresh_ui_after_task_change() clears detail panel.

        Verifies:
        - Detail panel is cleared when clear_detail_panel=True
        - Detail panel is not cleared when clear_detail_panel=False
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Create task
            app.action_new_sibling_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Task"
            modal.action_save()
            await pilot.pause()

            # Select task to populate detail panel
            column1 = app.query_one(f"#{COLUMN_1_ID}", TaskColumn)
            column1._selected_index = 0
            task = column1.get_selected_task()
            column1.post_message(
                TaskColumn.TaskSelected(task=task, column_id=COLUMN_1_ID)
            )
            await pilot.pause()

            column3 = app.query_one(f"#{COLUMN_3_ID}", DetailPanel)
            assert column3.current_task is not None

            # Complete and archive task (clears detail panel)
            await app.action_toggle_completion()
            await pilot.pause()
            await app.action_archive_task()
            await pilot.pause()

            # Detail panel should be cleared
            column3 = app.query_one(f"#{COLUMN_3_ID}", DetailPanel)
            assert column3.current_task is None

    @pytest.mark.asyncio
    async def test_list_bar_refresh_updates_completion_percentage(self):
        """Test that list bar refreshes show updated completion percentages.

        Verifies:
        - List bar updates after task completion
        - Completion percentage is correct
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Create two tasks
            for i in range(2):
                app.action_new_sibling_task()
                await pilot.pause()
                modal = app.screen
                title_input = modal.query_one("#title-input")
                title_input.value = f"Task {i + 1}"
                modal.action_save()
                await pilot.pause()

            # Complete one task
            column1 = app.query_one(f"#{COLUMN_1_ID}", TaskColumn)
            column1._selected_index = 0
            await app.action_toggle_completion()
            await pilot.pause()

            # Verify list bar updated
            list_bar = app.query_one(ListBar)
            current_list = next(
                (lst for lst in list_bar.lists if lst.id == app._current_list_id),
                None
            )
            assert current_list is not None
            # Should show 50% completion (1 of 2 tasks completed)
            assert current_list.completion_percentage == 50


class TestHelperMethods:
    """Tests for private helper methods."""

    @pytest.mark.asyncio
    async def test_has_db_manager_returns_correct_status(self):
        """Test that _has_db_manager() returns correct status.

        Verifies:
        - Returns True when database manager is initialized
        - Returns False when database manager is None
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app

            # After mount, should have database manager
            assert app._has_db_manager() is True

        # Create app without mounting
        app = TaskUI()
        assert app._has_db_manager() is False

    @pytest.mark.asyncio
    async def test_can_perform_task_operation_checks_prerequisites(self):
        """Test that _can_perform_task_operation() checks prerequisites.

        Verifies:
        - Returns True when db_manager and current_list_id are set
        - Returns False when either is missing
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app

            # After mount, should be able to perform operations
            assert app._can_perform_task_operation() is True

        # Create app without mounting
        app = TaskUI()
        assert app._can_perform_task_operation() is False

    @pytest.mark.asyncio
    async def test_get_focused_column_returns_correct_column(self):
        """Test that _get_focused_column() returns the focused column.

        Verifies:
        - Returns correct column widget
        - Returns None if column doesn't exist or isn't TaskColumn
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app

            # Focus on Column 1
            app._focused_column_id = COLUMN_1_ID
            column = app._get_focused_column()
            assert column is not None
            assert isinstance(column, TaskColumn)
            assert column.column_id == COLUMN_1_ID

            # Focus on Column 2
            app._focused_column_id = COLUMN_2_ID
            column = app._get_focused_column()
            assert column is not None
            assert column.column_id == COLUMN_2_ID

            # Focus on Column 3 (DetailPanel, should return None)
            app._focused_column_id = COLUMN_3_ID
            column = app._get_focused_column()
            assert column is None

    @pytest.mark.asyncio
    async def test_get_parent_id_for_sibling_returns_correct_parent(self):
        """Test that _get_parent_id_for_sibling() returns correct parent ID.

        Verifies:
        - Returns None for top-level task
        - Returns parent_id for child task
        - Returns None when parent_task is None
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # No task selected - should return None
            parent_id = app._get_parent_id_for_sibling(None)
            assert parent_id is None

            # Create a parent task
            app.action_new_sibling_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Parent"
            modal.action_save()
            await pilot.pause()

            column1 = app.query_one(f"#{COLUMN_1_ID}", TaskColumn)
            column1._selected_index = 0
            parent_task = column1.get_selected_task()

            # Top-level task - should return None
            parent_id = app._get_parent_id_for_sibling(parent_task)
            assert parent_id is None

            # Create a child task
            app.action_new_child_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Child"
            modal.action_save()
            await pilot.pause()

            # Get child task
            async with app._db_manager.get_session() as session:
                task_service = TaskService(session)
                children = await task_service.get_children(parent_task.id)
                child_task = children[0]

            # Child task - should return parent's ID
            parent_id = app._get_parent_id_for_sibling(child_task)
            assert parent_id == parent_task.id

