"""Main Textual application for TaskUI.

This module contains the main TaskUI application with three-column layout:
- Column 1: Tasks (configurable nesting depth)
- Column 2: Subtasks (configurable nesting depth, context-relative)
- Column 3: Details (task information)

Nesting depth is configured via ~/.taskui/nesting.toml or uses sensible defaults.
"""

from contextlib import asynccontextmanager
from typing import Optional, Any, List
from uuid import UUID

from textual.app import App, ComposeResult
from textual.command import Provider, Hits, Hit, DiscoveryHit
from textual.containers import Container, Horizontal
from textual.widgets import Footer
from textual.events import Key

from taskui.database import DatabaseManager, get_database_manager
from taskui.logging_config import get_logger
from taskui.models import Task, TaskList
from taskui.services.task_service import TaskService
from taskui.services.list_service import ListService
from taskui.config import Config
from taskui.services.diary_service import DiaryService
from taskui.services.printer_service import PrinterService, PrinterConfig
from taskui.services.cloud_print_queue import CloudPrintQueue, CloudPrintConfig
from taskui.services.sync_v2 import SyncV2Service, SyncV2Error
from taskui.export_schema import ConflictStrategy
from taskui.ui.components.task_modal import TaskCreationModal
from taskui.ui.components.detail_panel import DetailPanel
from taskui.ui.components.list_bar import ListBar
from taskui.ui.components.list_management_modal import ListManagementModal
from taskui.ui.components.list_delete_modal import ListDeleteModal
from taskui.ui.modals import DiaryEntryModal
from taskui.ui.theme import (
    BACKGROUND,
    FOREGROUND,
    BORDER,
    SELECTION,
    LEVEL_0_COLOR,
    LEVEL_1_COLOR,
    LEVEL_2_COLOR,
)
from taskui.ui.constants import (
    MAX_TITLE_LENGTH_IN_NOTIFICATION,
    NOTIFICATION_TIMEOUT_SHORT,
    NOTIFICATION_TIMEOUT_MEDIUM,
    NOTIFICATION_TIMEOUT_LONG,
    SCREEN_STACK_SIZE_MAIN_APP,
    THEME_SELECTION_COLOR,
)
from taskui.ui.components.column import TaskColumn
from taskui.ui.keybindings import (
    get_all_bindings,
    get_next_column,
    get_prev_column,
    COLUMN_1_ID,
    COLUMN_2_ID,
    COLUMN_3_ID,
)

# Initialize logger for this module
logger = get_logger(__name__)


class TaskUICommands(Provider):
    """Command provider for TaskUI actions."""

    async def discover(self) -> Hits:
        """Provide commands that are always available for discovery."""
        app = self.app

        # Task operations
        yield DiscoveryHit(
            "New Task",
            "Create a new sibling task (n)",
            app.action_new_sibling_task,
        )
        yield DiscoveryHit(
            "New Child Task",
            "Create a child task under selected task (c)",
            app.action_new_child_task,
        )
        yield DiscoveryHit(
            "Edit Task",
            "Edit the selected task (e)",
            app.action_edit_task,
        )
        yield DiscoveryHit(
            "Toggle Task Completion",
            "Mark task as complete/incomplete (Enter/Space)",
            app.action_toggle_completion,
        )
        yield DiscoveryHit(
            "Delete Task",
            "Delete the selected task (x/Backspace)",
            app.action_delete_task,
        )

        # Diary operations
        yield DiscoveryHit(
            "New Diary Entry",
            "Add a diary entry to selected task (d)",
            app.action_create_diary_entry,
        )

        # List operations
        yield DiscoveryHit(
            "New List",
            "Create a new task list (Ctrl+N)",
            app.action_create_list,
        )
        yield DiscoveryHit(
            "Edit List",
            "Edit the current list name (Ctrl+E)",
            app.action_edit_list,
        )
        yield DiscoveryHit(
            "Delete List",
            "Delete the current list (Ctrl+D)",
            app.action_delete_list,
        )

        # Navigation
        yield DiscoveryHit(
            "Next Column",
            "Move focus to next column (Tab)",
            app.action_navigate_next_column,
        )
        yield DiscoveryHit(
            "Previous Column",
            "Move focus to previous column (Shift+Tab)",
            app.action_navigate_prev_column,
        )

        # Printing
        yield DiscoveryHit(
            "Print Column",
            "Print the current column (p)",
            app.action_print_column,
        )

        # Help
        yield DiscoveryHit(
            "Show Help",
            "Display keyboard shortcuts (?)",
            app.action_help,
        )

    async def search(self, query: str) -> Hits:
        """Search for commands matching the query."""
        matcher = self.matcher(query)
        app = self.app

        # Define all commands with their metadata
        commands = [
            ("New Task", "Create a new sibling task (n)", app.action_new_sibling_task),
            ("New Child Task", "Create a child task under selected task (c)", app.action_new_child_task),
            ("Edit Task", "Edit the selected task (e)", app.action_edit_task),
            ("Toggle Task Completion", "Mark task as complete/incomplete (Enter/Space)", app.action_toggle_completion),
            ("Delete Task", "Delete the selected task (x/Backspace)", app.action_delete_task),
            ("New Diary Entry", "Add a diary entry to selected task (d)", app.action_create_diary_entry),
            ("New List", "Create a new task list (Ctrl+N)", app.action_create_list),
            ("Edit List", "Edit the current list name (Ctrl+E)", app.action_edit_list),
            ("Delete List", "Delete the current list (Ctrl+D)", app.action_delete_list),
            ("Next Column", "Move focus to next column (Tab)", app.action_navigate_next_column),
            ("Previous Column", "Move focus to previous column (Shift+Tab)", app.action_navigate_prev_column),
            ("Print Column", "Print the current column (p)", app.action_print_column),
            ("Show Help", "Display keyboard shortcuts (?)", app.action_help),
            ("Switch to List 1", "Switch to first list (1)", app.action_switch_list_1),
            ("Switch to List 2", "Switch to second list (2)", app.action_switch_list_2),
            ("Switch to List 3", "Switch to third list (3)", app.action_switch_list_3),
            ("Switch to List 4", "Switch to fourth list (4)", app.action_switch_list_4),
            ("Switch to List 5", "Switch to fifth list (5)", app.action_switch_list_5),
            ("Switch to List 6", "Switch to sixth list (6)", app.action_switch_list_6),
            ("Switch to List 7", "Switch to seventh list (7)", app.action_switch_list_7),
            ("Switch to List 8", "Switch to eighth list (8)", app.action_switch_list_8),
            ("Switch to List 9", "Switch to ninth list (9)", app.action_switch_list_9),
        ]

        for title, help_text, callback in commands:
            score = matcher.match(title)
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(title),
                    callback,
                    help=help_text,
                )


class TaskUI(App):
    """Main TaskUI application with three-column layout."""

    CSS = f"""
    Screen {{
        background: {BACKGROUND};
        layout: vertical;
    }}

    #main-container {{
        width: 100%;
        height: 1fr;
        background: {BACKGROUND};
    }}

    #columns-container {{
        width: 100%;
        height: 100%;
        layout: horizontal;
    }}

    #column-1 {{
        width: 1fr;
        height: 100%;
        border: round {BORDER};
    }}

    #column-2 {{
        width: 1fr;
        height: 100%;
        border: double {BORDER};
    }}

    #column-3 {{
        width: 1fr;
        height: 100%;
        border: dashed {BORDER};
    }}

    #column-1:focus {{
        border: round {LEVEL_0_COLOR};
    }}

    #column-2:focus {{
        border: double {LEVEL_1_COLOR};
    }}

    #column-3:focus {{
        border: dashed {LEVEL_2_COLOR};
    }}

    Footer {{
        background: {SELECTION};
    }}
    """

    BINDINGS = get_all_bindings()
    COMMANDS = App.COMMANDS | {TaskUICommands}

    # ==============================================================================
    # LIFECYCLE METHODS
    # ==============================================================================

    def __init__(self, **kwargs) -> None:
        """Initialize the TaskUI application."""
        super().__init__(**kwargs)
        self.title = "TaskUI - Nested Task Manager"
        self.sub_title = "Press ? for help"
        self._focused_column_id: str = COLUMN_1_ID  # Track which column has focus
        self._db_manager: Optional[DatabaseManager] = None
        self._current_list_id: Optional[UUID] = None  # Will be set after database initialization
        self._lists: List[TaskList] = []  # Store available lists
        self._printer_service: Optional[CloudPrintQueue] = None  # Cloud print queue service

    def compose(self) -> ComposeResult:
        """Compose the application layout.

        Yields:
            Widgets that make up the application
        """
        # List bar for switching between task lists
        yield ListBar(lists=self._lists, active_list_id=self._current_list_id)

        with Container(id="main-container"):
            with Horizontal(id="columns-container"):
                # Column 1: Tasks (max 2 levels)
                yield TaskColumn(
                    column_id=COLUMN_1_ID,
                    title="Tasks",
                    empty_message="No tasks yet\nPress N to create a new task",
                    id=COLUMN_1_ID
                )

                # Column 2: Subtasks (max 3 levels, context-relative)
                yield TaskColumn(
                    column_id=COLUMN_2_ID,
                    title="Subtasks",
                    empty_message="Select a task from Column 1",
                    id=COLUMN_2_ID
                )

                # Column 3: Details
                yield DetailPanel(
                    column_id=COLUMN_3_ID,
                    title="Details",
                    id=COLUMN_3_ID
                )

        yield Footer()

    async def on_mount(self) -> None:
        """Called when app is mounted and ready."""
        logger.info("TaskUI application mounted, initializing...")

        # Set up the theme colors
        self.theme_variables.update({
            "background": BACKGROUND,
            "foreground": FOREGROUND,
            "border": BORDER,
            "selection": THEME_SELECTION_COLOR,
            "level-0": LEVEL_0_COLOR,
        })
        logger.debug("Theme colors applied")

        # Initialize database
        self._db_manager = get_database_manager()
        await self._db_manager.initialize()
        logger.info("Database initialized")

        # Ensure default list exists
        # Note: _ensure_default_list() updates the ListBar which triggers
        # on_list_bar_list_selected event, which loads tasks and sets focus
        await self._ensure_default_list()

        # Initialize cloud print queue service (don't fail if unavailable)
        try:
            # Load cloud print configuration from config file (includes encryption key)
            cloud_config = CloudPrintConfig.from_config_file()
            self._printer_service = CloudPrintQueue(cloud_config)
            self._printer_service.connect()
            logger.info("Cloud print queue initialized and connected")
        except Exception as e:
            logger.warning(f"Cloud print queue not available at startup: {e}")
            # Continue without printer - user can still use the app

        logger.info("TaskUI application ready")

    async def on_unmount(self) -> None:
        """Called when app is shutting down."""
        logger.info("TaskUI application shutting down")
        logger.info("TaskUI application shutdown complete")

    # ==============================================================================
    # EVENT HANDLERS
    # ==============================================================================

    def on_key(self, event: Key) -> None:
        """Handle tab navigation in main app vs modals.

        Provides column navigation in main app, form navigation in modals.

        Args:
            event: The key event
        """
        logger.debug(f"Key pressed: {event.key}, screen_stack_size={len(self.screen_stack)}")

        # Only intercept tab/shift+tab when not in a modal (screen stack size is 1)
        if len(self.screen_stack) == SCREEN_STACK_SIZE_MAIN_APP:
            if event.key == "tab":
                # Prevent default focus cycling and handle column navigation
                logger.debug("Tab key: navigating to next column")
                event.prevent_default()
                event.stop()
                self.action_navigate_next_column()
            elif event.key == "shift+tab":
                # Prevent default focus cycling and handle column navigation
                logger.debug("Shift+Tab key: navigating to previous column")
                event.prevent_default()
                event.stop()
                self.action_navigate_prev_column()

    async def on_task_column_task_selected(self, message: TaskColumn.TaskSelected) -> None:
        """Handle task selection to update Column 2 and Column 3.

        Column 2 shows children (if selected in Column 1), Column 3 shows details.

        Args:
            message: TaskSelected message containing the selected task
        """
        # Fetch the fresh task from the database to ensure we have the latest data
        # (the task object in the message might be stale if tasks were recently created/updated)
        if not self._has_db_manager():
            return

        try:
            async with self._with_task_service() as task_service:
                fresh_task = await task_service.get_task_by_id(message.task.id)

            if not fresh_task:
                logger.warning(f"Task {message.task.id} not found in database")
                return

            # Update Column 3 with task details (for any selected task from any column)
            await self._update_column3_for_selection(fresh_task)

            # Update Column 2 only for selections from Column 1
            if message.column_id == COLUMN_1_ID:
                await self._update_column2_for_selection(fresh_task)

        except Exception as e:
            logger.error("Error handling task selection", exc_info=True)

    async def on_task_creation_modal_task_created(self, message: TaskCreationModal.TaskCreated) -> None:
        """Handle TaskCreated message from the task creation modal.

        Args:
            message: TaskCreated message containing task data
        """
        title = message.title
        notes = message.notes
        url = message.url
        mode = message.mode
        parent_task = message.parent_task
        edit_task = message.edit_task

        if not title:
            return

        # Handle edit mode
        if mode == "edit" and edit_task is not None:
            await self._handle_edit_task(edit_task.id, title, notes, url)
            return

        # Handle create modes (create_sibling, create_child)
        if mode == "create_sibling":
            await self._handle_create_sibling_task(title, notes, url, parent_task)
        elif mode == "create_child":
            await self._handle_create_child_task(title, notes, url, parent_task)

        # Refresh UI to show the new task
        await self._refresh_ui_after_task_change()

    async def on_task_creation_modal_task_cancelled(self, message: TaskCreationModal.TaskCancelled) -> None:
        """Handle TaskCancelled message from the task creation modal.

        Args:
            message: TaskCancelled message
        """
        pass


    async def on_list_bar_list_selected(self, message: ListBar.ListSelected) -> None:
        """Handle list selection from the list bar.

        Updates Column 1 with list tasks, clears Column 2.

        Args:
            message: ListSelected message containing the selected list info
        """
        self._current_list_id = message.list_id

        column1 = self.query_one(f"#{COLUMN_1_ID}", TaskColumn)
        column2 = self.query_one(f"#{COLUMN_2_ID}", TaskColumn)

        # Clear Column 2 (no task selected yet)
        column2.set_tasks([])
        column2.update_header("Subtasks")

        # Load tasks for the selected list into Column 1 (with 2 levels of hierarchy)
        if self._db_manager and self._current_list_id:
            try:
                async with self._with_task_service() as task_service:
                    tasks = await self._get_tasks_with_children(
                        task_service,
                        self._current_list_id
                    )
                    column1.set_tasks(tasks)
                    # Note: set_tasks() now handles triggering selection automatically
                    # when the column is focused, so no manual trigger needed

            except Exception as e:
                logger.error("Error loading tasks for list", exc_info=True)

    async def on_list_management_modal_list_saved(self, message: ListManagementModal.ListSaved) -> None:
        """Handle list creation/editing from the list management modal.

        Args:
            message: ListSaved message containing list data
        """
        if not self._has_db_manager():
            return

        try:
            async with self._with_list_service() as list_service:
                if message.mode == "create":
                    # Create new list
                    new_list = await list_service.create_list(message.name)
                    logger.info(f"Created new list: {new_list.name} (id={new_list.id})")
                    self.notify(f"✓ Created list: {message.name}", severity="information", timeout=NOTIFICATION_TIMEOUT_SHORT)

                elif message.mode == "edit" and message.edit_list:
                    # Update existing list
                    updated_list = await list_service.update_list(message.edit_list.id, message.name)
                    if updated_list:
                        logger.info(f"Updated list: {updated_list.name} (id={updated_list.id})")
                        self.notify(f"✓ Updated list: {message.name}", severity="information", timeout=NOTIFICATION_TIMEOUT_SHORT)

            # Refresh the lists
            await self._refresh_lists()

        except ValueError as e:
            # Handle duplicate name errors
            logger.warning(f"List save failed: {e}")
            self.notify(str(e), severity="error", timeout=NOTIFICATION_TIMEOUT_MEDIUM)
        except Exception as e:
            logger.error("Error saving list", exc_info=True)
            self.notify("Failed to save list", severity="error", timeout=NOTIFICATION_TIMEOUT_MEDIUM)

    async def on_list_management_modal_list_cancelled(self, message: ListManagementModal.ListCancelled) -> None:
        """Handle list creation/editing cancellation.

        Args:
            message: ListCancelled message
        """
        pass

    async def on_list_delete_modal_delete_confirmed(self, message: ListDeleteModal.DeleteConfirmed) -> None:
        """Handle list deletion confirmation from the delete modal.

        Args:
            message: DeleteConfirmed message containing deletion options
        """
        if not self._has_db_manager():
            return

        try:
            async with self._with_list_service() as list_service:
                if message.option == "migrate":
                    # Migrate tasks to another list
                    if not message.target_list_id:
                        self.notify("No target list selected", severity="error", timeout=NOTIFICATION_TIMEOUT_MEDIUM)
                        return

                    success = await list_service.migrate_tasks_and_delete_list(
                        message.list_to_delete.id,
                        message.target_list_id
                    )

                    if success:
                        logger.info(f"Migrated tasks and deleted list: {message.list_to_delete.name}")
                        self.notify(
                            f"✓ Migrated tasks and deleted list: {message.list_to_delete.name}",
                            severity="information",
                            timeout=NOTIFICATION_TIMEOUT_MEDIUM
                        )

                elif message.option == "delete_all":
                    # Delete all tasks (cascade)
                    success = await list_service.delete_list(message.list_to_delete.id)

                    if success:
                        logger.info(f"Deleted list and all tasks: {message.list_to_delete.name}")
                        self.notify(
                            f"✓ Deleted list: {message.list_to_delete.name}",
                            severity="information",
                            timeout=NOTIFICATION_TIMEOUT_MEDIUM
                        )

            # Refresh the lists
            await self._refresh_lists()

            # If the deleted list was the current list, switch to the first available list
            if self._current_list_id == message.list_to_delete.id:
                if self._lists:
                    self._current_list_id = self._lists[0].id
                    # Update the list bar (this will trigger on_list_bar_list_selected)
                    list_bar = self.query_one(ListBar)
                    list_bar.set_active_list(self._current_list_id)
                else:
                    self._current_list_id = None

        except ValueError as e:
            # Handle validation errors (e.g., last list)
            logger.warning(f"List deletion failed: {e}")
            self.notify(str(e), severity="error", timeout=NOTIFICATION_TIMEOUT_MEDIUM)
        except Exception as e:
            logger.error("Error deleting list", exc_info=True)
            self.notify("Failed to delete list", severity="error", timeout=NOTIFICATION_TIMEOUT_MEDIUM)

    async def on_list_delete_modal_delete_cancelled(self, message: ListDeleteModal.DeleteCancelled) -> None:
        """Handle list deletion cancellation.

        Args:
            message: DeleteCancelled message
        """
        pass

    async def on_diary_entry_modal_entry_saved(self, message: DiaryEntryModal.EntrySaved) -> None:
        """Handle diary entry creation from the modal.

        Args:
            message: EntrySaved message containing the diary entry
        """
        if not self._has_db_manager():
            return

        try:
            # Save the entry to the database
            async with self._with_diary_service() as diary_service:
                saved_entry = await diary_service.create_entry(
                    task_id=message.entry.task_id,
                    content=message.entry.content
                )

            if saved_entry:
                logger.info(f"Diary entry created: id={saved_entry.id}, task_id={saved_entry.task_id}")
                self.notify(
                    "✓ Diary entry created",
                    severity="information",
                    timeout=NOTIFICATION_TIMEOUT_SHORT
                )

                # Refresh the detail panel to show the new entry
                column = self._get_focused_column()
                if column:
                    selected_task = column.get_selected_task()
                    if selected_task and selected_task.id == message.entry.task_id:
                        await self._update_column3_for_selection(selected_task)

        except Exception as e:
            logger.error("Error creating diary entry", exc_info=True)
            self.notify(
                "Failed to create diary entry",
                severity="error",
                timeout=NOTIFICATION_TIMEOUT_MEDIUM
            )

    async def on_diary_entry_modal_entry_cancelled(self, message: DiaryEntryModal.EntryCancelled) -> None:
        """Handle diary entry creation cancellation.

        Args:
            message: EntryCancelled message
        """
        pass

    # ==============================================================================
    # ACTION HANDLERS - NAVIGATION
    # ==============================================================================

    def action_navigate_up(self) -> None:
        """Navigate up within the current column."""
        column = self._get_focused_column()
        if column:
            column.navigate_up()

    def action_navigate_down(self) -> None:
        """Navigate down within the current column."""
        column = self._get_focused_column()
        if column:
            column.navigate_down()

    def action_navigate_next_column(self) -> None:
        """Navigate to the next column (Tab)."""
        next_column_id = get_next_column(self._focused_column_id)
        if next_column_id:
            self._set_column_focus(next_column_id)

    def action_navigate_prev_column(self) -> None:
        """Navigate to the previous column (Shift+Tab)."""
        prev_column_id = get_prev_column(self._focused_column_id)
        if prev_column_id:
            self._set_column_focus(prev_column_id)

    # ==============================================================================
    # ACTION HANDLERS - TASK OPERATIONS
    # ==============================================================================

    def action_new_sibling_task(self) -> None:
        """Create a new sibling task (N key).

        Opens the task creation modal to create a new task at the same level
        as the currently selected task. If no task is selected, creates a
        top-level task (level 0).
        """
        column = self._get_focused_column()
        if not column:
            return

        selected_task = column.get_selected_task()

        modal = TaskCreationModal(
            mode="create_sibling",
            parent_task=selected_task,
            diary_service_getter=self._with_diary_service
        )
        self.push_screen(modal)

    def action_new_child_task(self) -> None:
        """Create a new child task (C key).

        Opens the task creation modal to create a child task under the currently
        selected task. Respects nesting limits based on column context.

        Hierarchical creation:
        - Column 1 focused: Creates child of Column 1 selection
        - Column 2 focused: Creates child of Column 2 selection (or Column 1 if Column 2 is empty)

        Note: Column 3 is not focusable (display-only), so no handling needed.
        """
        # Use the currently focused column's selected task as the parent
        parent_column = self._get_focused_column()

        if not parent_column:
            return

        selected_task = parent_column.get_selected_task()

        # Fallback: If Column 2 is focused but empty, use Column 1's selection
        if not selected_task and self._focused_column_id == COLUMN_2_ID:
            try:
                column1 = self.query_one(f"#{COLUMN_1_ID}", TaskColumn)
                selected_task = column1.get_selected_task()
            except Exception as e:
                logger.error(f"Could not get Column 1 selection: {e}")
                return

        if not selected_task:
            # Can't create a child without a parent selected
            return

        modal = TaskCreationModal(
            mode="create_child",
            parent_task=selected_task,
            diary_service_getter=self._with_diary_service
        )
        self.push_screen(modal)

    def action_edit_task(self) -> None:
        """Edit the selected task (E key).

        Opens the task creation modal in edit mode with the currently selected
        task's data pre-filled. User can modify title and notes.
        """
        column = self._get_focused_column()
        if not column:
            return

        # Get the currently selected task
        selected_task = column.get_selected_task()
        if not selected_task:
            # Can't edit without a task selected
            return

        # Show the modal in edit mode
        modal = TaskCreationModal(
            mode="edit",
            parent_task=None,  # Not needed for edit mode
            edit_task=selected_task,
            diary_service_getter=self._with_diary_service
        )
        self.push_screen(modal)

    async def action_toggle_completion(self) -> None:
        """Toggle task completion status (Space key).

        Toggles the completion status of the currently selected task.
        When completed, the task will display with a strikethrough.
        """
        logger.debug("Completion toggle key pressed (Space)")

        column = self._get_focused_column()
        if not column:
            logger.debug("No focused column found for completion toggle")
            return

        # Get the currently selected task
        selected_task = column.get_selected_task()
        if not selected_task:
            # No task selected, nothing to toggle
            logger.debug("No task selected for completion toggle")
            return

        if not self._has_db_manager():
            logger.debug("No database manager available for completion toggle")
            return

        try:
            # Single combined session for toggle and fetch
            async with self._with_task_service() as task_service:
                # Toggle the task completion status
                await task_service.toggle_completion(selected_task.id)

                # Get updated task in same session
                updated_task = await task_service.get_task_by_id(selected_task.id)

            # Determine completion status for notification
            completion_status = "completed" if not selected_task.is_completed else "reopened"
            icon = "✓" if not selected_task.is_completed else "○"
            self.notify(f"{icon} Task {completion_status}", severity="information", timeout=NOTIFICATION_TIMEOUT_SHORT)

            # Refresh UI to show the updated task with strikethrough and updated progress
            await self._refresh_ui_after_task_change()

            # Update detail panel with fetched task
            if updated_task:
                await self._update_column3_for_selection(updated_task)

        except Exception as e:
            logger.error("Error toggling task completion", exc_info=True)
            self._notify_task_error("toggle completion")



    async def action_delete_task(self) -> None:
        """Delete the selected task (Delete/Backspace key).

        Permanently deletes the task and all its descendants from the database.
        This operation cannot be undone.
        """
        logger.debug("Delete key pressed")

        if not self._can_perform_task_operation():
            logger.debug("Cannot perform delete operation")
            return

        # Get the focused column
        column = self._get_focused_column()
        if not column:
            logger.debug("No focused column found for delete")
            return

        # Get the currently selected task
        selected_task = column.get_selected_task()
        if not selected_task:
            logger.debug("No task selected for delete")
            return

        if not self._has_db_manager():
            logger.debug("No database manager available for delete")
            return

        try:
            async with self._with_task_service() as task_service:
                # Permanently delete the task
                await task_service.delete_task(selected_task.id)

            # Notify user of successful deletion
            self._notify_task_success("deleted", selected_task.title, icon="🗑️")

            # Refresh UI to remove deleted task and clear detail panel
            await self._refresh_ui_after_task_change(clear_detail_panel=True)

        except Exception as e:
            logger.error("Error deleting task", exc_info=True)
            self._notify_task_error("delete task")

    # ==============================================================================
    # ACTION HANDLERS - UTILITY
    # ==============================================================================

    def action_help(self) -> None:
        """Show help information."""
        # Show notification with basic help info (full help screen not yet implemented)
        self.notify(
            "Keybindings shown in footer. N=New Task, C=Child, E=Edit, Space=Complete, Delete=Permanent Delete",
            severity="information",
            timeout=NOTIFICATION_TIMEOUT_LONG
        )

    async def action_print_column(self) -> None:
        """Print the selected task card to thermal printer (P key).

        Prints the currently selected task with all its children to the
        thermal printer as a physical kanban card.
        """
        logger.debug("Print key pressed ('P')")

        # Check if printer is available
        if not self._printer_service or not self._printer_service.is_connected():
            self.notify("Printer not connected", severity="warning", timeout=NOTIFICATION_TIMEOUT_MEDIUM)
            logger.warning("Print requested but printer not connected")
            return

        # Get the focused column
        column = self._get_focused_column()
        if not column:
            logger.debug("No focused column for print")
            return

        # Get the currently selected task
        selected_task = column.get_selected_task()
        if not selected_task:
            self.notify("No task selected to print", severity="warning", timeout=NOTIFICATION_TIMEOUT_MEDIUM)
            logger.debug("No task selected for printing")
            return

        # Get children of the selected task
        if not self._has_db_manager():
            logger.warning("No database manager available for printing")
            return

        try:
            # Show printing status
            self.notify("Printing task card...", timeout=NOTIFICATION_TIMEOUT_SHORT)
            logger.info(f"Printing task card: {selected_task.title}")

            # Get children from database
            async with self._with_task_service() as task_service:
                children = await task_service.get_children(selected_task.id)

            # Load diary entries for the task
            diary_entries = None
            try:
                async with self._with_diary_service() as diary_service:
                    diary_entries = await diary_service.get_entries_for_task(selected_task.id)
            except Exception as e:
                logger.warning(f"Failed to load diary entries for print: {e}")
                # Continue without diary entries

            # Send print job to cloud queue
            self._printer_service.send_print_job(selected_task, children, diary_entries)

            # Show success message
            self.notify("✓ Print job queued!", severity="information", timeout=NOTIFICATION_TIMEOUT_MEDIUM)
            logger.info(f"Print job queued for: {selected_task.title}")

        except Exception as e:
            # Show error message
            self.notify(f"Print failed: {str(e)}", severity="error", timeout=NOTIFICATION_TIMEOUT_LONG)
            logger.error(f"Failed to print task card: {e}", exc_info=True)

    async def action_sync(self) -> None:
        """Sync with remote (Ctrl+Shift+S).

        Performs full bidirectional sync:
        1. Push local state to SQS
        2. Pull remote state from SQS
        """
        logger.info("Sync triggered (Ctrl+Shift+S)")

        if not self._has_db_manager():
            self.notify("Database not ready", severity="error", timeout=NOTIFICATION_TIMEOUT_MEDIUM)
            return

        try:
            # Load sync configuration using centralized Config
            app_config = Config()
            sync_config = app_config.get_sync_config()

            # Check if sync is enabled
            if not sync_config.get('enabled'):
                self.notify("Sync is disabled in config", severity="warning", timeout=NOTIFICATION_TIMEOUT_MEDIUM)
                logger.info("Sync disabled in configuration")
                return

            # Check for required settings
            if not sync_config.get('queue_url'):
                self.notify("Sync queue URL not configured", severity="warning", timeout=NOTIFICATION_TIMEOUT_LONG)
                logger.warning("Sync queue_url not set in config")
                return

            if not sync_config.get('encryption_key'):
                self.notify("Sync encryption key not configured", severity="warning", timeout=NOTIFICATION_TIMEOUT_LONG)
                logger.warning("Sync encryption_key not set in config")
                return

            # Build CloudPrintConfig from sync settings
            cloud_config = CloudPrintConfig(
                queue_url=sync_config['queue_url'],
                region=sync_config.get('region', 'us-east-1'),
                aws_access_key_id=sync_config.get('aws_access_key_id'),
                aws_secret_access_key=sync_config.get('aws_secret_access_key'),
                encryption_key=sync_config['encryption_key'],
            )

            # Generate client ID (based on machine - simple hash of hostname)
            import platform
            import hashlib
            hostname = platform.node()
            client_id = hashlib.md5(hostname.encode()).hexdigest()[:16]

            # Show syncing status
            self.notify("Syncing...", timeout=NOTIFICATION_TIMEOUT_SHORT)

            # Perform sync
            async with self._db_manager.session() as session:
                sync_service = SyncV2Service(session, cloud_config, client_id)

                if not sync_service.connect():
                    self.notify("Failed to connect to sync queue", severity="error", timeout=NOTIFICATION_TIMEOUT_LONG)
                    return

                try:
                    results = await sync_service.sync_full(
                        strategy=ConflictStrategy.NEWER_WINS
                    )

                    # Report results
                    if results['push_success']:
                        msg = "Sync complete"
                        if results['pull_imported'] > 0:
                            msg += f" - imported {results['pull_imported']} list(s)"
                        if results['conflicts']:
                            msg += f" - {len(results['conflicts'])} conflict(s)"

                        self.notify(msg, severity="information", timeout=NOTIFICATION_TIMEOUT_MEDIUM)
                        logger.info(f"Sync results: {results}")

                        # Refresh UI if anything was imported
                        if results['pull_imported'] > 0:
                            await self._refresh_lists()
                    else:
                        self.notify("Sync push failed", severity="warning", timeout=NOTIFICATION_TIMEOUT_MEDIUM)

                finally:
                    sync_service.disconnect()

        except SyncV2Error as e:
            self.notify(f"Sync failed: {e}", severity="error", timeout=NOTIFICATION_TIMEOUT_LONG)
            logger.error(f"Sync error: {e}", exc_info=True)
        except Exception as e:
            self.notify(f"Sync failed: {e}", severity="error", timeout=NOTIFICATION_TIMEOUT_LONG)
            logger.error(f"Unexpected sync error: {e}", exc_info=True)

    def action_cancel(self) -> None:
        """Cancel current operation (Escape key)."""
        # Note: Textual handles Escape key for modal dismissal automatically.
        # This action is reserved for future custom cancel behaviors if needed.
        pass

    def action_create_diary_entry(self) -> None:
        """Create a diary entry for the selected task (D key).

        Opens the diary entry modal to create a quick journal entry for the
        currently selected task. The modal provides a text area for entry content
        with character counter (1-2000 characters).
        """
        logger.debug("Create diary entry key pressed ('D')")

        # Get the focused column
        column = self._get_focused_column()
        if not column:
            logger.debug("No focused column for diary entry")
            return

        # Get the currently selected task
        selected_task = column.get_selected_task()
        if not selected_task:
            self.notify(
                "No task selected",
                severity="warning",
                timeout=NOTIFICATION_TIMEOUT_MEDIUM
            )
            logger.debug("No task selected for diary entry")
            return

        # Open the diary entry modal
        modal = DiaryEntryModal(task_id=selected_task.id)
        self.push_screen(modal)

    # ==============================================================================
    # ACTION HANDLERS - LIST SWITCHING
    # ==============================================================================

    def action_switch_list_1(self) -> None:
        """Switch to list 1 (1 key)."""
        self._switch_to_list(1)

    def action_switch_list_2(self) -> None:
        """Switch to list 2 (2 key)."""
        self._switch_to_list(2)

    def action_switch_list_3(self) -> None:
        """Switch to list 3 (3 key)."""
        self._switch_to_list(3)

    def action_switch_list_4(self) -> None:
        """Switch to list 4 (4 key)."""
        self._switch_to_list(4)

    def action_switch_list_5(self) -> None:
        """Switch to list 5 (5 key)."""
        self._switch_to_list(5)

    def action_switch_list_6(self) -> None:
        """Switch to list 6 (6 key)."""
        self._switch_to_list(6)

    def action_switch_list_7(self) -> None:
        """Switch to list 7 (7 key)."""
        self._switch_to_list(7)

    def action_switch_list_8(self) -> None:
        """Switch to list 8 (8 key)."""
        self._switch_to_list(8)

    def action_switch_list_9(self) -> None:
        """Switch to list 9 (9 key)."""
        self._switch_to_list(9)

    # ==============================================================================
    # ACTION HANDLERS - LIST MANAGEMENT
    # ==============================================================================

    def action_create_list(self) -> None:
        """Create a new list (Ctrl+N)."""
        logger.debug("Create list action triggered")

        # Open the list management modal in create mode
        modal = ListManagementModal(mode="create")
        self.push_screen(modal)

    def action_edit_list(self) -> None:
        """Edit the current list (Ctrl+E)."""
        logger.debug("Edit list action triggered")

        if not self._current_list_id:
            self.notify("No list selected", severity="warning", timeout=NOTIFICATION_TIMEOUT_MEDIUM)
            return

        # Get the current list
        current_list = None
        for lst in self._lists:
            if lst.id == self._current_list_id:
                current_list = lst
                break

        if not current_list:
            self.notify("Current list not found", severity="error", timeout=NOTIFICATION_TIMEOUT_MEDIUM)
            return

        # Open the list management modal in edit mode
        modal = ListManagementModal(mode="edit", edit_list=current_list)
        self.push_screen(modal)

    def action_delete_list(self) -> None:
        """Delete the current list (Ctrl+D)."""
        logger.debug("Delete list action triggered")

        if not self._current_list_id:
            self.notify("No list selected", severity="warning", timeout=NOTIFICATION_TIMEOUT_MEDIUM)
            return

        # Get the current list
        current_list = None
        for lst in self._lists:
            if lst.id == self._current_list_id:
                current_list = lst
                break

        if not current_list:
            self.notify("Current list not found", severity="error", timeout=NOTIFICATION_TIMEOUT_MEDIUM)
            return

        # Check if this is the last list
        if len(self._lists) <= 1:
            self.notify(
                "Cannot delete the last list",
                severity="warning",
                timeout=NOTIFICATION_TIMEOUT_MEDIUM
            )
            return

        # Open the list delete modal
        modal = ListDeleteModal(
            list_to_delete=current_list,
            available_lists=self._lists
        )
        self.push_screen(modal)

    # ==============================================================================
    # PRIVATE HELPERS - FOCUS & NAVIGATION
    # ==============================================================================

    def _set_column_focus(self, column_id: str) -> None:
        """Set focus to a specific column.

        Args:
            column_id: ID of the column to focus
        """
        try:
            # Column 3 is a DetailPanel, columns 1 and 2 are TaskColumns
            if column_id == COLUMN_3_ID:
                column = self.query_one(f"#{column_id}", DetailPanel)
            else:
                column = self.query_one(f"#{column_id}", TaskColumn)
            column.focus()
            self._focused_column_id = column_id
            logger.debug(f"Focus changed to column: {column_id}")
        except Exception as e:
            # Column not found or not focusable, ignore
            logger.debug(f"Could not set focus to column {column_id}: {e}")

    def _get_focused_column(self) -> Optional[TaskColumn]:
        """Get the currently focused column widget.

        Note: Queries UI state.

        Returns:
            TaskColumn widget or None if no column is focused
        """
        try:
            return self.query_one(f"#{self._focused_column_id}", TaskColumn)
        except Exception as e:
            logger.debug(f"Could not get focused column: {e}")
            return None

    # ==============================================================================
    # PRIVATE HELPERS - TASK OPERATIONS
    # ==============================================================================

    def _has_db_manager(self) -> bool:
        """Check if database manager is initialized.

        Returns:
            True if database manager is available
        """
        return self._db_manager is not None

    def _can_perform_task_operation(self) -> bool:
        """Check if prerequisites for task operations are met.

        Returns:
            True if database manager and current list are available
        """
        return self._db_manager is not None and self._current_list_id is not None

    @asynccontextmanager
    async def _with_task_service(self):
        """Context manager for TaskService with database session.

        Yields:
            TaskService instance with active database session

        Example:
            async with self._with_task_service() as task_service:
                task = await task_service.get_task_by_id(task_id)
        """
        async with self._db_manager.get_session() as session:
            yield TaskService(session)

    @asynccontextmanager
    async def _with_list_service(self):
        """Context manager for ListService with database session.

        Yields:
            ListService instance with active database session

        Example:
            async with self._with_list_service() as list_service:
                lists = await list_service.get_all_lists()
        """
        async with self._db_manager.get_session() as session:
            yield ListService(session)

    @asynccontextmanager
    async def _with_diary_service(self):
        """Context manager for DiaryService with database session.

        Yields:
            DiaryService instance with active database session

        Example:
            async with self._with_diary_service() as diary_service:
                entries = await diary_service.get_entries_for_task(task_id)
        """
        async with self._db_manager.get_session() as session:
            yield DiaryService(session)

    def _notify_task_success(self, action: str, title: str, icon: str = "✓") -> None:
        """Show success notification for task operation.

        Args:
            action: Action performed (e.g., "created", "updated", "archived")
            title: Task title to display (will be truncated)
            icon: Icon to display (default: "✓")
        """
        truncated = title[:MAX_TITLE_LENGTH_IN_NOTIFICATION]
        self.notify(
            f"{icon} Task {action}: {truncated}...",
            severity="information",
            timeout=NOTIFICATION_TIMEOUT_SHORT
        )

    def _notify_task_error(self, action: str) -> None:
        """Show error notification for task operation.

        Args:
            action: Action that failed (e.g., "create task", "toggle completion")
        """
        self.notify(
            f"Failed to {action}",
            severity="error",
            timeout=NOTIFICATION_TIMEOUT_MEDIUM
        )

    def _get_parent_id_for_sibling(self, parent_task: Optional[Task]) -> Optional[UUID]:
        """Determine parent ID for creating a sibling task.

        Args:
            parent_task: Currently selected task (sibling reference)

        Returns:
            Parent ID for new task, or None for top-level task
        """
        if parent_task is None or parent_task.parent_id is None:
            # No task selected OR selected task is top-level
            # Either way, create a top-level task
            return None

        # Selected task has a parent - create sibling under same parent
        return parent_task.parent_id

    async def _handle_edit_task(self, task_id: UUID, title: str, notes: Optional[str], url: Optional[str]) -> None:
        """Update an existing task in the database.

        Args:
            task_id: UUID of the task to update
            title: New title for the task
            notes: New notes for the task (can be None)
            url: New URL for the task (can be None)
        """
        if not self._has_db_manager():
            return

        try:
            async with self._with_task_service() as task_service:
                await task_service.update_task(task_id, title=title, notes=notes, url=url)

            # Notify user of successful edit
            self._notify_task_success("updated", title)

            # Refresh UI to show the updated task
            await self._refresh_ui_after_task_change()
        except Exception as e:
            logger.error("Error updating task", exc_info=True)
            self._notify_task_error("update task")

    async def _handle_create_sibling_task(
        self,
        title: str,
        notes: Optional[str],
        url: Optional[str],
        parent_task: Optional[Task]
    ) -> None:
        """Create a new sibling task at the same level as the selected task.

        Args:
            title: New task title
            notes: Optional task notes
            url: Optional URL
            parent_task: The currently selected task (sibling reference)
        """
        if not self._can_perform_task_operation():
            return

        try:
            parent_id = self._get_parent_id_for_sibling(parent_task)

            async with self._with_task_service() as task_service:
                if parent_id is None:
                    # Create top-level task
                    await task_service.create_task(
                        title=title,
                        list_id=self._current_list_id,
                        notes=notes,
                        url=url
                    )
                else:
                    # Create child under parent
                    await task_service.create_child_task(
                        parent_id=parent_id,
                        title=title,
                        notes=notes,
                        url=url
                    )

            # Notify user of successful creation
            self._notify_task_success("created", title)

        except Exception as e:
            logger.error("Error creating sibling task", exc_info=True)
            self._notify_task_error("create task")

    async def _handle_create_child_task(
        self,
        title: str,
        notes: Optional[str],
        url: Optional[str],
        parent_task: Optional[Task]
    ) -> None:
        """Create a new child task under the selected task.

        Args:
            title: New task title
            notes: Optional task notes
            url: Optional URL
            parent_task: The parent task (must not be None)
        """
        if not self._db_manager or not parent_task:
            return

        try:
            async with self._with_task_service() as task_service:
                # Create a child task under the selected parent
                await task_service.create_child_task(
                    parent_id=parent_task.id,
                    title=title,
                    notes=notes,
                    url=url
                )

            # Notify user of successful creation
            self._notify_task_success("created", title)

        except Exception as e:
            logger.error("Error creating child task", exc_info=True)
            self._notify_task_error("create subtask")

    # ==============================================================================
    # PRIVATE HELPERS - DATA FETCHING
    # ==============================================================================

    async def _ensure_default_list(self) -> None:
        """Ensure default lists (Work, Home, Personal) exist in the database.

        Creates default lists if they don't exist.
        """
        if not self._has_db_manager():
            return

        try:
            async with self._with_list_service() as list_service:
                # Ensure default lists exist (creates them if needed)
                self._lists = await list_service.ensure_default_lists()

                # Set the current list to the first one
                if self._lists:
                    self._current_list_id = self._lists[0].id

                    # Update the list bar with the loaded lists
                    list_bar = self.query_one(ListBar)
                    list_bar.update_lists(self._lists)
                    list_bar.set_active_list(self._current_list_id)

        except Exception as e:
            # Log error but don't crash the app
            logger.error("Error ensuring default lists", exc_info=True)
            # Create a fallback UUID for graceful degradation
            from uuid import uuid4
            self._current_list_id = uuid4()

    async def _refresh_lists(self) -> None:
        """Refresh the list of task lists from the database and update the UI.

        Reloads all lists and updates the list bar display.
        """
        if not self._has_db_manager():
            return

        try:
            async with self._with_list_service() as list_service:
                self._lists = await list_service.get_all_lists()

                # Update the list bar with the loaded lists
                list_bar = self.query_one(ListBar)
                list_bar.update_lists(self._lists)

                # If current list still exists, keep it selected
                if self._current_list_id:
                    list_exists = any(lst.id == self._current_list_id for lst in self._lists)
                    if list_exists:
                        list_bar.set_active_list(self._current_list_id)
                    elif self._lists:
                        # Current list was deleted, switch to first available list
                        self._current_list_id = self._lists[0].id
                        list_bar.set_active_list(self._current_list_id)
                elif self._lists:
                    # No current list set, use first one
                    self._current_list_id = self._lists[0].id
                    list_bar.set_active_list(self._current_list_id)

        except Exception as e:
            logger.error("Error refreshing lists", exc_info=True)

    async def _get_tasks_with_children(self, task_service: TaskService, list_id: UUID) -> List[Task]:
        """Get top-level tasks and their children for a list (2 levels).

        Note: Fetches from database.

        Args:
            task_service: TaskService instance
            list_id: UUID of the task list

        Returns:
            Flat list of tasks with parents followed by their children
        """
        top_level_tasks = await task_service.get_tasks_for_list(list_id)

        # Build flat list with children
        tasks_with_children = []
        for parent in top_level_tasks:
            tasks_with_children.append(parent)
            children = await task_service.get_children(parent.id)
            tasks_with_children.extend(children)

        return tasks_with_children

    async def _get_task_hierarchy(self, task_id: UUID) -> List[Task]:
        """Get the complete hierarchy path from root to the specified task.

        Note: Fetches from database.

        Args:
            task_id: UUID of the task

        Returns:
            List of tasks from root to current task (including the current task)
        """
        if not self._has_db_manager():
            return []

        try:
            async with self._with_task_service() as task_service:
                # Build the hierarchy by traversing up the parent chain
                hierarchy: List[Task] = []
                current_task = await task_service.get_task_by_id(task_id)

                if not current_task:
                    return []

                # Start with the current task
                hierarchy.insert(0, current_task)

                # Traverse up to the root
                while current_task.parent_id is not None:
                    parent = await task_service.get_task_by_id(current_task.parent_id)
                    if not parent:
                        break
                    hierarchy.insert(0, parent)
                    current_task = parent

                return hierarchy
        except Exception as e:
            logger.error("Error loading hierarchy", exc_info=True)
            return []

    async def _get_task_children(self, parent_id: UUID) -> List[Task]:
        """Get all descendants of a task in hierarchical order.

        Note: Fetches from database.

        Args:
            parent_id: UUID of the parent task

        Returns:
            List of all descendant tasks in hierarchical order
        """
        if not self._has_db_manager():
            return []

        try:
            async with self._with_task_service() as task_service:
                # Get all descendants (children, grandchildren, etc.)
                descendants = await task_service.get_all_descendants(parent_id)

                # Debug logging
                logger.debug(f"_get_task_children({parent_id}): fetched {len(descendants)} descendants")
                for task in descendants:
                    logger.debug(f"  - {task.title} (id={task.id}, parent_id={task.parent_id})")

                return descendants
        except Exception as e:
            logger.error("Error loading children", exc_info=True)
            return []

    # ==============================================================================
    # PRIVATE HELPERS - UI UPDATES
    # ==============================================================================

    async def _refresh_ui_after_task_change(
        self,
        clear_detail_panel: bool = False
    ) -> None:
        """Refresh all UI components after task modifications.

        Refreshes Column 1, Column 2 (if parent selected), detail panel,
        and list bar. Uses set_tasks() optimization to prevent unnecessary
        re-renders.

        Args:
            clear_detail_panel: Clear Column 3 after archiving/deleting
        """
        logger.debug(
            f"UI refresh: Refreshing all visible columns "
            f"(clear_detail_panel={clear_detail_panel})"
        )

        # Refresh Column 1 (top-level tasks)
        column1 = self.query_one(f"#{COLUMN_1_ID}", TaskColumn)
        await self._refresh_column_tasks(column1)
        logger.debug("UI refresh: Column 1 refreshed")

        # Refresh Column 2 if a parent is selected (children view)
        selected_task = column1.get_selected_task()
        if selected_task:
            logger.debug(
                f"UI refresh: Refreshing Column 2 for parent task {selected_task.id}"
            )
            column2 = self.query_one(f"#{COLUMN_2_ID}", TaskColumn)
            await self._refresh_column_tasks(column2)
        else:
            logger.debug("UI refresh: Skipping Column 2 (no parent selected)")

        # Clear detail panel if requested (e.g., after archiving)
        if clear_detail_panel:
            logger.debug("UI refresh: Clearing detail panel")
            detail_panel = self.query_one(f"#{COLUMN_3_ID}", DetailPanel)
            detail_panel.clear()
        # Update detail panel with refreshed task data (e.g., after editing)
        elif selected_task:
            logger.debug("UI refresh: Updating detail panel with refreshed task")
            await self._update_column3_for_selection(selected_task)

        # Refresh list bar (completion percentages)
        if self._current_list_id:
            logger.debug(
                f"UI refresh: Refreshing list bar for list {self._current_list_id}"
            )
            await self._refresh_list_bar_for_list(self._current_list_id)

        logger.debug("UI refresh: Complete")

    async def _refresh_column_tasks(self, column: TaskColumn) -> None:
        """Refresh tasks in a column from the database.

        Args:
            column: TaskColumn widget to refresh
        """
        # For Column 1, reload top-level tasks with their children (2 levels)
        if column.column_id == COLUMN_1_ID and self._current_list_id:
            async with self._with_task_service() as task_service:
                tasks = await self._get_tasks_with_children(
                    task_service,
                    self._current_list_id
                )
                column.set_tasks(tasks)
        # For Column 2, we need to reload children of the selected Column 1 task
        elif column.column_id == COLUMN_2_ID:
            column1 = self.query_one(f"#{COLUMN_1_ID}", TaskColumn)
            selected_task = column1.get_selected_task()
            if selected_task:
                await self._update_column2_for_selection(selected_task)

    async def _refresh_list_bar_for_list(self, list_id: UUID) -> None:
        """Refresh the specific list in the list bar.

        Reloads the affected list with current task counts and completion percentage.

        Args:
            list_id: UUID of the list to refresh
        """
        if not self._has_db_manager():
            return

        try:
            async with self._with_list_service() as list_service:
                # Reload only the affected list (3 queries: 1 list + 1 task count + 1 completed count)
                updated_list = await list_service.get_list_by_id(list_id)

            if not updated_list:
                return

            # Find and update just that list in self._lists
            for index, cached_list in enumerate(self._lists):
                if cached_list.id == list_id:
                    self._lists[index] = updated_list
                    break

            # Update the list bar with the modified list
            list_bar = self.query_one(ListBar)
            list_bar.update_lists(self._lists)

        except Exception as e:
            logger.error(f"Error refreshing list bar for list {list_id}", exc_info=True)

    async def _update_column2_for_selection(self, selected_task: Task) -> None:
        """Update Column 2 to show children of the selected task.

        Args:
            selected_task: The task selected in Column 1
        """
        column2 = self.query_one(f"#{COLUMN_2_ID}", TaskColumn)

        # Get children of the selected task
        children = await self._get_task_children(selected_task.id)

        # Update Column 2 header
        header_title = f"{selected_task.title} Subtasks"
        column2.update_header(header_title)

        # Update Column 2 with children
        column2.set_tasks(children)

    async def _update_column3_for_selection(self, selected_task: Task) -> None:
        """Update Column 3 to show details of the selected task.

        Args:
            selected_task: The task selected in Column 1 or Column 2
        """
        column3 = self.query_one(f"#{COLUMN_3_ID}", DetailPanel)

        # Get the hierarchy path (from root to selected task)
        hierarchy = await self._get_task_hierarchy(selected_task.id)

        # Get diary entries for the task (last 3 entries)
        async with self._with_diary_service() as diary_service:
            try:
                diary_entries = await diary_service.get_entries_for_task(
                    selected_task.id,
                    limit=3
                )
            except Exception as e:
                logger.error(f"Failed to fetch diary entries for task {selected_task.id}: {e}")
                diary_entries = []

        # Update Column 3 with task details and diary entries
        column3.set_task(selected_task, hierarchy, diary_entries)

    def _switch_to_list(self, list_number: int) -> None:
        """Switch to specified list number.

        Args:
            list_number: List number to switch to (1-3)
        """
        list_bar = self.query_one(ListBar)
        list_bar.select_list_by_number(list_number)
