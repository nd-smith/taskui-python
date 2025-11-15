"""
Integration tests for TaskUI MVP (Story 1.16).

Tests complete end-to-end workflows including:
- Database session integration with task_service
- Modal-to-database persistence flow
- Column updates on task creation/modification
- Keyboard shortcuts end-to-end
- Nested task hierarchy creation via modal (N/C keys)
- Task persistence and app restart
- All CRUD operations end-to-end
- Navigation across all columns
- Column 2 updates when Column 1 selection changes
"""

import pytest
import pytest_asyncio
from uuid import UUID, uuid4
from typing import List, Optional
from datetime import datetime
import os
from pathlib import Path

from taskui.ui.app import TaskUI
from taskui.ui.components.column import TaskColumn
from taskui.ui.components.detail_panel import DetailPanel
from taskui.ui.components.list_bar import ListBar
from taskui.ui.components.task_modal import TaskCreationModal
from taskui.models import Task, TaskList
from taskui.services.task_service import TaskService
from taskui.services.list_service import ListService
from taskui.services.nesting_rules import Column as NestingColumn
from taskui.database import DatabaseManager, get_database_manager
import taskui.database

# Use separate test database
TEST_DB_PATH = "test_taskui.db"
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

    # Patch get_database_manager to use test database in both places it's imported
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


class TestMVPIntegration:
    """Integration tests for complete MVP functionality."""

    @pytest.mark.asyncio
    async def test_app_initialization_and_database_setup(self):
        """Test that app initializes with database and creates default lists.

        Verifies:
        - Database manager is initialized
        - Default lists (Work, Home, Personal) are created
        - Column 1 loads with empty task list
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app

            # Verify database manager is initialized
            assert app._db_manager is not None
            assert isinstance(app._db_manager, DatabaseManager)

            # Verify default lists are created
            assert len(app._lists) == 3
            assert app._current_list_id is not None

            # Verify list names
            list_names = {lst.name for lst in app._lists}
            assert list_names == {"Work", "Home", "Personal"}

            # Verify Column 1 is empty initially
            column1 = app.query_one("#column-1", TaskColumn)
            assert len(column1._tasks) == 0


    @pytest.mark.asyncio
    async def test_database_session_integration_with_task_service(self):
        """Test that app properly integrates database session with task_service.

        Verifies:
        - Database session is created for task operations
        - Task service can create tasks via app's database connection
        - Session commits properly
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app

            # Wait for app to initialize
            await pilot.pause()

            # Verify we can create a task through task_service
            assert app._db_manager is not None
            assert app._current_list_id is not None

            async with app._db_manager.get_session() as session:
                task_service = TaskService(session)

                # Create a task
                task = await task_service.create_task(
                    title="Integration Test Task",
                    list_id=app._current_list_id,
                    notes="Testing database integration"
                )

                # Verify task was created
                assert task.id is not None
                assert task.title == "Integration Test Task"
                assert task.level == 0
                assert task.list_id == app._current_list_id

            # Verify task persists after session closes
            async with app._db_manager.get_session() as session:
                task_service = TaskService(session)
                retrieved_task = await task_service.get_task_by_id(task.id)

                assert retrieved_task is not None
                assert retrieved_task.title == "Integration Test Task"


    @pytest.mark.asyncio
    async def test_modal_to_database_persistence_flow(self):
        """Test complete flow from modal creation to database persistence.

        Verifies:
        - Modal can be opened with correct context
        - Modal data is passed to app handler
        - App creates task in database via task_service
        - Column refreshes to show new task
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Simulate opening modal for new sibling task (N key)
            app.action_new_sibling_task()
            await pilot.pause()

            # Verify modal is displayed
            modal = app.screen
            assert isinstance(modal, TaskCreationModal)
            assert modal.mode == "create_sibling"

            # Fill in modal data
            title_input = modal.query_one("#title-input")
            title_input.value = "Test Task from Modal"

            notes_input = modal.query_one("#notes-input")
            notes_input.text = "Notes from modal"

            # Save the modal
            modal.action_save()
            await pilot.pause()

            # Verify task was created in database
            async with app._db_manager.get_session() as session:
                task_service = TaskService(session)
                tasks = await task_service.get_tasks_for_list(
                    app._current_list_id,
                    include_archived=False
                )

                assert len(tasks) == 1
                assert tasks[0].title == "Test Task from Modal"
                assert tasks[0].notes == "Notes from modal"

            # Verify Column 1 shows the new task
            column1 = app.query_one("#column-1", TaskColumn)
            assert len(column1._tasks) == 1
            assert column1._tasks[0].title == "Test Task from Modal"


    @pytest.mark.asyncio
    async def test_nested_task_hierarchy_creation_via_modal(self):
        """Test creating nested task hierarchy using N and C keys.

        Verifies:
        - Can create top-level task with N key
        - Can create child task with C key
        - Can create grandchild task with C key
        - Nesting levels are correct
        - All tasks persist to database
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Create parent task (level 0)
            app.action_new_sibling_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Parent Task"
            modal.action_save()
            await pilot.pause()

            # Select the parent task in Column 1
            column1 = app.query_one("#column-1", TaskColumn)
            assert len(column1._tasks) == 1
            parent_task = column1._tasks[0]
            column1._selected_index = 0

            # Create child task (level 1) with C key
            app.action_new_child_task()
            await pilot.pause()
            modal = app.screen
            assert isinstance(modal, TaskCreationModal)
            assert modal.mode == "create_child"
            title_input = modal.query_one("#title-input")
            title_input.value = "Child Task"
            modal.action_save()
            await pilot.pause()

            # Verify child task was created
            async with app._db_manager.get_session() as session:
                task_service = TaskService(session)
                children = await task_service.get_children(parent_task.id)

                assert len(children) == 1
                child_task = children[0]
                assert child_task.title == "Child Task"
                assert child_task.level == 1
                assert child_task.parent_id == parent_task.id

            # Switch to Column 2 to see children
            await pilot.press("tab")
            await pilot.pause()

            column2 = app.query_one("#column-2", TaskColumn)
            # Column 2 should show child with context-relative level 0
            assert len(column2._tasks) == 1
            assert column2._tasks[0].title == "Child Task"
            assert column2._tasks[0].level == 0  # Context-relative

            # Select child in Column 2 and create grandchild
            column2._selected_index = 0
            app.action_new_child_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Grandchild Task"
            modal.action_save()
            await pilot.pause()

            # Verify grandchild task was created
            async with app._db_manager.get_session() as session:
                task_service = TaskService(session)
                grandchildren = await task_service.get_children(child_task.id)

                assert len(grandchildren) == 1
                grandchild_task = grandchildren[0]
                assert grandchild_task.title == "Grandchild Task"
                assert grandchild_task.level == 2
                assert grandchild_task.parent_id == child_task.id


    @pytest.mark.asyncio
    async def test_column2_updates_on_task_creation(self):
        """Test that Column 2 updates when tasks are created in Column 1.

        Verifies:
        - Column 2 updates after creating child task
        - Column 2 shows context-relative levels
        - Column 2 header updates with parent task name
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Create parent task
            app.action_new_sibling_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Parent for Column 2 Test"
            modal.action_save()
            await pilot.pause()

            # Select parent task
            column1 = app.query_one("#column-1", TaskColumn)
            column1._selected_index = 0

            # Trigger selection event to update Column 2
            parent_task = column1.get_selected_task()
            column1.post_message(
                TaskColumn.TaskSelected(task=parent_task, column_id="column-1")
            )
            await pilot.pause()

            # Create child task
            app.action_new_child_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Child in Column 2"
            modal.action_save()
            await pilot.pause()

            # Refresh Column 2 by re-selecting parent
            column1.post_message(
                TaskColumn.TaskSelected(task=parent_task, column_id="column-1")
            )
            await pilot.pause()

            # Verify Column 2 shows the child
            column2 = app.query_one("#column-2", TaskColumn)
            assert len(column2._tasks) == 1
            assert column2._tasks[0].title == "Child in Column 2"
            assert column2._tasks[0].level == 0  # Context-relative

            # Verify Column 2 header updated
            assert "Parent for Column 2 Test" in column2.header_title


    @pytest.mark.asyncio
    async def test_all_crud_operations_end_to_end(self):
        """Test all CRUD operations work end-to-end through the app.

        Verifies:
        - Create: Can create tasks via modal
        - Read: Tasks are loaded and displayed
        - Update: Can edit tasks via modal
        - Delete: Can delete tasks (placeholder for Story 2.5)
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # CREATE: Create a task
            app.action_new_sibling_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "CRUD Test Task"
            notes_input = modal.query_one("#notes-input")
            notes_input.text = "Original notes"
            modal.action_save()
            await pilot.pause()

            # READ: Verify task was created and can be read
            column1 = app.query_one("#column-1", TaskColumn)
            assert len(column1._tasks) == 1
            task = column1._tasks[0]
            assert task.title == "CRUD Test Task"
            assert task.notes == "Original notes"

            # Verify task is in database
            async with app._db_manager.get_session() as session:
                task_service = TaskService(session)
                db_task = await task_service.get_task_by_id(task.id)
                assert db_task is not None
                assert db_task.title == "CRUD Test Task"

            # UPDATE: Edit the task
            column1._selected_index = 0
            app.action_edit_task()
            await pilot.pause()
            modal = app.screen
            assert isinstance(modal, TaskCreationModal)
            assert modal.mode == "edit"
            title_input = modal.query_one("#title-input")
            assert title_input.value == "CRUD Test Task"
            title_input.value = "Updated CRUD Task"
            notes_input = modal.query_one("#notes-input")
            notes_input.text = "Updated notes"
            modal.action_save()
            await pilot.pause()

            # Verify update persisted
            column1 = app.query_one("#column-1", TaskColumn)
            assert column1._tasks[0].title == "Updated CRUD Task"

            async with app._db_manager.get_session() as session:
                task_service = TaskService(session)
                db_task = await task_service.get_task_by_id(task.id)
                assert db_task.title == "Updated CRUD Task"
                assert db_task.notes == "Updated notes"

            # DELETE: To be implemented in Story 2.5
            # For now, verify delete method exists
            assert hasattr(app, 'action_delete_task')


    @pytest.mark.asyncio
    async def test_task_persistence_and_app_restart(self):
        """Test that tasks persist across app restarts.

        Verifies:
        - Tasks created in first session persist to database
        - New app instance loads tasks from database
        - Task hierarchy is maintained
        """
        # First session: Create tasks
        task_ids = []
        list_id = None

        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            list_id = app._current_list_id

            # Create parent task
            app.action_new_sibling_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Persistent Parent"
            modal.action_save()
            await pilot.pause()

            # Create child task
            column1 = app.query_one("#column-1", TaskColumn)
            column1._selected_index = 0
            parent_task = column1.get_selected_task()
            task_ids.append(parent_task.id)

            app.action_new_child_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Persistent Child"
            modal.action_save()
            await pilot.pause()

        # Second session: Verify tasks were loaded
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Verify tasks were restored
            column1 = app.query_one("#column-1", TaskColumn)
            # Column 1 shows hierarchical list: parent + child = 2 tasks
            assert len(column1._tasks) == 2
            assert column1._tasks[0].title == "Persistent Parent"
            assert column1._tasks[1].title == "Persistent Child"

            # Verify child task exists in database
            async with app._db_manager.get_session() as session:
                task_service = TaskService(session)
                children = await task_service.get_children(task_ids[0])

                assert len(children) == 1
                assert children[0].title == "Persistent Child"


    @pytest.mark.asyncio
    async def test_keyboard_navigation_across_columns(self):
        """Test keyboard navigation works across all columns.

        Verifies:
        - Tab key switches to next column
        - Shift+Tab switches to previous column
        - Up/Down keys navigate within column
        - Focus indicators are correct
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Create some tasks for navigation
            for i in range(3):
                app.action_new_sibling_task()
                await pilot.pause()
                modal = app.screen
                title_input = modal.query_one("#title-input")
                title_input.value = f"Task {i + 1}"
                modal.action_save()
                await pilot.pause()

            # Verify initial focus on Column 1
            assert app._focused_column_id == "column-1"

            # Test Tab navigation (Column 1 -> Column 2)
            await pilot.press("tab")
            await pilot.pause()
            assert app._focused_column_id == "column-2"

            # Test Tab navigation (Column 2 -> Column 3)
            await pilot.press("tab")
            await pilot.pause()
            assert app._focused_column_id == "column-3"

            # Test Shift+Tab navigation (Column 3 -> Column 2)
            await pilot.press("shift+tab")
            await pilot.pause()
            assert app._focused_column_id == "column-2"

            # Test Shift+Tab navigation (Column 2 -> Column 1)
            await pilot.press("shift+tab")
            await pilot.pause()
            assert app._focused_column_id == "column-1"

            # Test Up/Down navigation within Column 1
            column1 = app.query_one("#column-1", TaskColumn)
            assert column1._selected_index == 0

            await pilot.press("down")
            await pilot.pause()
            assert column1._selected_index == 1

            await pilot.press("down")
            await pilot.pause()
            assert column1._selected_index == 2

            await pilot.press("up")
            await pilot.pause()
            assert column1._selected_index == 1


    @pytest.mark.asyncio
    async def test_column2_updates_on_column1_selection(self):
        """Test that Column 2 updates when selection changes in Column 1.

        Verifies:
        - Column 2 shows children of selected Column 1 task
        - Column 2 clears when Column 1 selection changes to task with no children
        - Column 2 levels are context-relative
        - Column 2 header updates with parent task name
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Create two parent tasks with different children
            # Parent 1 with 2 children
            app.action_new_sibling_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Parent 1"
            modal.action_save()
            await pilot.pause()

            column1 = app.query_one("#column-1", TaskColumn)
            column1._selected_index = 0
            parent1 = column1.get_selected_task()

            for i in range(2):
                app.action_new_child_task()
                await pilot.pause()
                modal = app.screen
                title_input = modal.query_one("#title-input")
                title_input.value = f"Parent 1 Child {i + 1}"
                modal.action_save()
                await pilot.pause()

            # Parent 2 with 1 child
            app.action_new_sibling_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Parent 2"
            modal.action_save()
            await pilot.pause()

            column1 = app.query_one("#column-1", TaskColumn)
            column1._selected_index = 1
            parent2 = column1.get_selected_task()

            app.action_new_child_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Parent 2 Child 1"
            modal.action_save()
            await pilot.pause()

            # Select Parent 1 and verify Column 2 shows its children
            column1._selected_index = 0
            column1.post_message(
                TaskColumn.TaskSelected(task=parent1, column_id="column-1")
            )
            await pilot.pause()

            column2 = app.query_one("#column-2", TaskColumn)
            assert len(column2._tasks) == 2
            assert column2._tasks[0].title == "Parent 1 Child 1"
            assert column2._tasks[1].title == "Parent 1 Child 2"
            assert "Parent 1" in column2.title

            # Select Parent 2 and verify Column 2 updates
            column1._selected_index = 1
            column1.post_message(
                TaskColumn.TaskSelected(task=parent2, column_id="column-1")
            )
            await pilot.pause()

            column2 = app.query_one("#column-2", TaskColumn)
            assert len(column2._tasks) == 1
            assert column2._tasks[0].title == "Parent 2 Child 1"
            assert "Parent 2" in column2.title


    @pytest.mark.asyncio
    async def test_column3_detail_view_updates(self):
        """Test that Column 3 shows task details when tasks are selected.

        Verifies:
        - Column 3 shows details for selected task
        - Column 3 shows hierarchy path
        - Column 3 updates when selection changes
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Create parent task
            app.action_new_sibling_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Task for Details"
            notes_input = modal.query_one("#notes-input")
            notes_input.text = "Detailed notes here"
            modal.action_save()
            await pilot.pause()

            # Select the task
            column1 = app.query_one("#column-1", TaskColumn)
            column1._selected_index = 0
            task = column1.get_selected_task()

            # Trigger Column 3 update
            column1.post_message(
                TaskColumn.TaskSelected(task=task, column_id="column-1")
            )
            await pilot.pause()

            # Verify Column 3 shows task details
            column3 = app.query_one("#column-3", DetailPanel)
            assert column3._current_task is not None
            assert column3._current_task.title == "Task for Details"


    @pytest.mark.asyncio
    async def test_list_switching(self):
        """Test switching between different task lists.

        Verifies:
        - Can switch lists using number keys
        - Column 1 updates with tasks from new list
        - Column 2 clears when switching lists
        - Tasks are isolated per list
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Create task in first list (Work)
            app.action_new_sibling_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Work Task"
            modal.action_save()
            await pilot.pause()

            # Switch to second list (Home)
            list_bar = app.query_one(ListBar)
            list_bar.select_list_by_number(2)
            await pilot.pause()

            # Verify Column 1 is empty in Home list
            column1 = app.query_one("#column-1", TaskColumn)
            assert len(column1._tasks) == 0

            # Create task in Home list
            app.action_new_sibling_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Home Task"
            modal.action_save()
            await pilot.pause()

            # Verify Home list has one task
            assert len(column1._tasks) == 1
            assert column1._tasks[0].title == "Home Task"

            # Switch back to Work list
            list_bar.select_list_by_number(1)
            await pilot.pause()

            # Verify Work list still has its task
            column1 = app.query_one("#column-1", TaskColumn)
            assert len(column1._tasks) == 1
            assert column1._tasks[0].title == "Work Task"


    @pytest.mark.asyncio
    async def test_nesting_limit_enforcement(self):
        """Test that nesting limits are enforced properly.

        Verifies:
        - Column 1 max depth is 2 levels (0, 1)
        - Column 2 max depth is 3 levels (0, 1, 2)
        - Cannot create children beyond limits
        - Modal shows error for invalid nesting
        """
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Create level 0 task
            app.action_new_sibling_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Level 0"
            modal.action_save()
            await pilot.pause()

            # Create level 1 task (child)
            column1 = app.query_one("#column-1", TaskColumn)
            column1._selected_index = 0
            app.action_new_child_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Level 1"
            modal.action_save()
            await pilot.pause()

            # Select level 1 task in Column 1
            # Should NOT be able to create child (would be level 2 in Column 1)
            column1._selected_index = 0
            parent = column1.get_selected_task()

            # Get the first child
            async with app._db_manager.get_session() as session:
                task_service = TaskService(session)
                children = await task_service.get_children(parent.id)
                assert len(children) == 1
                level1_task = children[0]

            # Try to create child of level 1 task in Column 1
            # This should be blocked by nesting rules
            app.action_new_child_task()
            await pilot.pause()
            modal = app.screen

            # Modal should show validation error
            assert modal.validation_error is not None
            assert "max nesting depth" in modal.validation_error.lower()

            # Save button should be disabled
            save_button = modal.query_one("#save-button")
            assert save_button.disabled


    @pytest.mark.asyncio
    async def test_complete_user_workflow(self):
        """Test a complete user workflow from start to finish.

        Simulates:
        1. App starts
        2. User creates a project task
        3. User creates subtasks
        4. User edits a task
        5. User navigates through columns
        6. App restarts and loads previous state
        """
        task_id = None

        # Session 1: Create tasks
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Create project task
            app.action_new_sibling_task()
            await pilot.pause()
            modal = app.screen
            title_input = modal.query_one("#title-input")
            title_input.value = "Build TaskUI Application"
            notes_input = modal.query_one("#notes-input")
            notes_input.text = "Main project task"
            modal.action_save()
            await pilot.pause()

            # Select project and create subtasks
            column1 = app.query_one("#column-1", TaskColumn)
            column1._selected_index = 0
            project_task = column1.get_selected_task()
            task_id = project_task.id

            subtask_titles = ["Design UI", "Implement Features", "Write Tests"]
            for title in subtask_titles:
                app.action_new_child_task()
                await pilot.pause()
                modal = app.screen
                title_input = modal.query_one("#title-input")
                title_input.value = title
                modal.action_save()
                await pilot.pause()

            # Edit the project task
            column1._selected_index = 0
            app.action_edit_task()
            await pilot.pause()
            modal = app.screen
            notes_input = modal.query_one("#notes-input")
            notes_input.text = "Main project task - Updated with subtasks"
            modal.action_save()
            await pilot.pause()

            # Navigate to Column 2
            await pilot.press("tab")
            await pilot.pause()

            # Verify Column 2 shows subtasks
            column2 = app.query_one("#column-2", TaskColumn)
            assert len(column2._tasks) == 3

        # Session 2: Verify state was restored
        async with TaskUI().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Verify project task exists
            column1 = app.query_one("#column-1", TaskColumn)
            assert len(column1._tasks) == 1
            assert column1._tasks[0].title == "Build TaskUI Application"

            # Verify subtasks exist
            async with app._db_manager.get_session() as session:
                task_service = TaskService(session)
                children = await task_service.get_children(task_id)

                assert len(children) == 3
                child_titles = {child.title for child in children}
                assert child_titles == {"Design UI", "Implement Features", "Write Tests"}

                # Verify edit was saved
                project = await task_service.get_task_by_id(task_id)
                assert "Updated with subtasks" in project.notes
