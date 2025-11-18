"""Main Textual application for TaskUI.

This module contains the main TaskUI application with three-column layout:
- Column 1: Tasks (max 2 levels)
- Column 2: Subtasks (max 3 levels, context-relative)
- Column 3: Details (task information)
"""

from typing import Optional, Any, List
from uuid import UUID

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Footer
from textual.events import Key

from taskui.database import DatabaseManager, get_database_manager
from taskui.logging_config import get_logger
from taskui.models import Task, TaskList
from taskui.services.nesting_rules import Column as NestingColumn
from taskui.services.task_service import TaskService
from taskui.services.list_service import ListService
from taskui.services.printer_service import PrinterService, PrinterConfig
from taskui.services.cloud_print_queue import CloudPrintQueue, CloudPrintConfig
from taskui.ui.components.task_modal import TaskCreationModal
from taskui.ui.components.archive_modal import ArchiveModal
from taskui.ui.components.detail_panel import DetailPanel
from taskui.ui.components.list_bar import ListBar
from taskui.ui.components.list_management_modal import ListManagementModal
from taskui.ui.components.list_delete_modal import ListDeleteModal
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
            cloud_config = CloudPrintConfig.from_config_file()
            self._printer_service = CloudPrintQueue(cloud_config)
            self._printer_service.connect()
            logger.info("Cloud print queue initialized and connected")
        except Exception as e:
            logger.warning(f"Cloud print queue not available at startup: {e}")
            # Continue without printer - user can still use the app

        logger.info("TaskUI application ready")

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
            async with self._db_manager.get_session() as session:
                task_service = TaskService(session)
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
        mode = message.mode
        parent_task = message.parent_task
        column = message.column
        edit_task = message.edit_task

        if not title:
            return

        # Handle edit mode
        if mode == "edit" and edit_task is not None:
            await self._handle_edit_task(edit_task.id, title, notes)
            return

        # Handle create modes (create_sibling, create_child)
        if mode == "create_sibling":
            await self._handle_create_sibling_task(title, notes, parent_task, column)
        elif mode == "create_child":
            await self._handle_create_child_task(title, notes, parent_task, column)

        # Refresh UI to show the new task
        await self._refresh_ui_after_task_change()

    async def on_task_creation_modal_task_cancelled(self, message: TaskCreationModal.TaskCancelled) -> None:
        """Handle TaskCancelled message from the task creation modal.

        Args:
            message: TaskCancelled message
        """
        pass

    async def on_archive_modal_task_restored(self, message: ArchiveModal.TaskRestored) -> None:
        """Handle task restore from archive modal.

        Args:
            message: The TaskRestored message with task_id
        """
        logger.debug(f"Handling restore for task_id={message.task_id}")

        if not self._has_db_manager():
            logger.debug("No database manager available for restore")
            return

        try:
            async with self._db_manager.get_session() as session:
                task_service = TaskService(session)
                # Unarchive (restore) the task
                restored_task = await task_service.unarchive_task(message.task_id)

            logger.info(f"Task restored: {restored_task.title[:50]}")

            # Notify user of successful restore
            self._notify_task_success("restored", restored_task.title)

            # Refresh UI to show the restored task
            await self._refresh_ui_after_task_change()

        except Exception as e:
            logger.error("Error restoring task from archive", exc_info=True)
            self._notify_task_error("restore task")

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
                async with self._db_manager.get_session() as session:
                    task_service = TaskService(session)
                    tasks = await self._get_tasks_with_children(
                        task_service,
                        self._current_list_id,
                        include_archived=False
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
            async with self._db_manager.get_session() as session:
                list_service = ListService(session)

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
            async with self._db_manager.get_session() as session:
                list_service = ListService(session)

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

                elif message.option == "archive":
                    # Archive completed tasks, delete the rest
                    success = await list_service.archive_tasks_and_delete_list(message.list_to_delete.id)

                    if success:
                        logger.info(f"Archived tasks and deleted list: {message.list_to_delete.name}")
                        self.notify(
                            f"✓ Archived tasks and deleted list: {message.list_to_delete.name}",
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

        # Determine the column context for nesting rules
        nesting_column = self._get_nesting_column_from_id(self._focused_column_id)

        selected_task = column.get_selected_task()

        modal = TaskCreationModal(
            mode="create_sibling",
            parent_task=selected_task,
            column=nesting_column
        )
        self.push_screen(modal)

    def action_new_child_task(self) -> None:
        """Create a new child task (C key).

        Opens the task creation modal to create a child task under the currently
        selected task. Respects nesting limits based on column context.
        """
        column = self._get_focused_column()
        if not column:
            return

        selected_task = column.get_selected_task()
        if not selected_task:
            # Can't create a child without a parent selected
            return

        # Determine the column context for nesting rules
        nesting_column = self._get_nesting_column_from_id(self._focused_column_id)

        modal = TaskCreationModal(
            mode="create_child",
            parent_task=selected_task,
            column=nesting_column
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

        # Determine the column context for nesting rules
        nesting_column = self._get_nesting_column_from_id(self._focused_column_id)

        # Show the modal in edit mode
        modal = TaskCreationModal(
            mode="edit",
            parent_task=None,  # Not needed for edit mode
            column=nesting_column,
            edit_task=selected_task
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
            async with self._db_manager.get_session() as session:
                task_service = TaskService(session)

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

    async def action_archive_task(self) -> None:
        """Archive the selected completed task ('a' key).

        Archives the currently selected task if it is completed.
        Only completed tasks can be archived. Archived tasks are removed
        from the normal view and can be viewed/restored via the archive modal.
        """
        logger.debug("Archive key pressed ('a')")

        column = self._get_focused_column()
        if not column:
            logger.debug("No focused column found for archive")
            return

        # Get the currently selected task
        selected_task = column.get_selected_task()
        if not selected_task:
            logger.debug("No task selected for archive")
            return

        # Check if task is completed
        if not selected_task.is_completed:
            logger.debug(f"Task {selected_task.id} is not completed, cannot archive")
            self.notify("Only completed tasks can be archived", severity="warning", timeout=NOTIFICATION_TIMEOUT_MEDIUM)
            return

        if not self._has_db_manager():
            logger.debug("No database manager available for archive")
            return

        try:
            async with self._db_manager.get_session() as session:
                task_service = TaskService(session)
                # Archive the task
                await task_service.archive_task(selected_task.id)

            # Notify user of successful archive
            self._notify_task_success("archived", selected_task.title, icon="📦")

            # Refresh UI to remove archived task and clear detail panel
            await self._refresh_ui_after_task_change(clear_detail_panel=True)

        except ValueError as e:
            # Task was not completed (shouldn't happen as we check above)
            logger.error(f"Error archiving task: {e}", exc_info=True)
            self._notify_task_error("archive task")
        except Exception as e:
            logger.error("Error archiving task", exc_info=True)
            self._notify_task_error("archive task")

    async def action_view_archives(self) -> None:
        """View archived tasks modal ('v' key).

        Opens a modal showing all archived tasks for the current list,
        with search/filter functionality and the ability to restore tasks.
        """
        logger.debug("View archives key pressed ('v')")

        if not self._can_perform_task_operation():
            logger.debug("No database manager or current list available for viewing archives")
            return

        try:
            # Get archived tasks for the current list
            async with self._db_manager.get_session() as session:
                task_service = TaskService(session)
                archived_tasks = await task_service.get_archived_tasks(
                    self._current_list_id
                )

            # Create and show the archive modal
            modal = ArchiveModal(archived_tasks=archived_tasks)
            self.push_screen(modal)

        except Exception as e:
            logger.error("Error loading archived tasks", exc_info=True)

    async def action_delete_task(self) -> None:
        """Delete the selected task (Delete/Backspace key).

        Soft deletes the task by archiving it. Unlike archive, this works on any task
        (completed or not). Deleted tasks can be restored via the archive modal.
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
            async with self._db_manager.get_session() as session:
                task_service = TaskService(session)
                # Soft delete the task (archives it without completion check)
                await task_service.soft_delete_task(selected_task.id)

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
            "Keybindings shown in footer. N=New Task, C=Child, E=Edit, Space=Complete, A=Archive, V=View Archives",
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
            async with self._db_manager.get_session() as session:
                task_service = TaskService(session)
                children = await task_service.get_children(selected_task.id, include_archived=False)

            # Send print job to cloud queue
            self._printer_service.send_print_job(selected_task, children)

            # Show success message
            self.notify("✓ Print job queued!", severity="information", timeout=NOTIFICATION_TIMEOUT_MEDIUM)
            logger.info(f"Print job queued for: {selected_task.title}")

        except Exception as e:
            # Show error message
            self.notify(f"Print failed: {str(e)}", severity="error", timeout=NOTIFICATION_TIMEOUT_LONG)
            logger.error(f"Failed to print task card: {e}", exc_info=True)

    def action_cancel(self) -> None:
        """Cancel current operation (Escape key)."""
        # Note: Textual handles Escape key for modal dismissal automatically.
        # This action is reserved for future custom cancel behaviors if needed.
        pass

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

    def _get_nesting_column_from_id(self, column_id: str) -> NestingColumn:
        """Convert column ID to NestingColumn enum.

        Note: Converts enum.

        Args:
            column_id: The UI column ID

        Returns:
            NestingColumn enum value
        """
        if column_id == COLUMN_1_ID:
            return NestingColumn.COLUMN1
        elif column_id == COLUMN_2_ID:
            return NestingColumn.COLUMN2
        else:
            # Default to COLUMN1 for column 3 or unknown
            return NestingColumn.COLUMN1

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

    async def _handle_edit_task(self, task_id: UUID, title: str, notes: Optional[str]) -> None:
        """Update an existing task in the database.

        Args:
            task_id: UUID of the task to update
            title: New title for the task
            notes: New notes for the task (can be None)
        """
        if not self._has_db_manager():
            return

        try:
            async with self._db_manager.get_session() as session:
                task_service = TaskService(session)
                await task_service.update_task(task_id, title=title, notes=notes)

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
        parent_task: Optional[Task],
        column: NestingColumn
    ) -> None:
        """Create a new sibling task at the same level as the selected task.

        Args:
            title: New task title
            notes: Optional task notes
            parent_task: The currently selected task (sibling reference)
            column: Column context for nesting rules
        """
        if not self._can_perform_task_operation():
            return

        try:
            parent_id = self._get_parent_id_for_sibling(parent_task)

            async with self._db_manager.get_session() as session:
                task_service = TaskService(session)

                if parent_id is None:
                    # Create top-level task
                    await task_service.create_task(
                        title=title,
                        list_id=self._current_list_id,
                        notes=notes
                    )
                else:
                    # Create child under parent
                    await task_service.create_child_task(
                        parent_id=parent_id,
                        title=title,
                        column=column,
                        notes=notes
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
        parent_task: Optional[Task],
        column: NestingColumn
    ) -> None:
        """Create a new child task under the selected task.

        Args:
            title: New task title
            notes: Optional task notes
            parent_task: The parent task (must not be None)
            column: Column context for nesting rules
        """
        if not self._db_manager or not parent_task:
            return

        try:
            async with self._db_manager.get_session() as session:
                task_service = TaskService(session)
                # Create a child task under the selected parent
                await task_service.create_child_task(
                    parent_id=parent_task.id,
                    title=title,
                    column=column,
                    notes=notes
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
            async with self._db_manager.get_session() as session:
                list_service = ListService(session)

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
            async with self._db_manager.get_session() as session:
                list_service = ListService(session)
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

    async def _get_tasks_with_children(self, task_service: TaskService, list_id: UUID, include_archived: bool = False) -> List[Task]:
        """Get top-level tasks and their children for a list (2 levels).

        Note: Fetches from database.

        Args:
            task_service: TaskService instance
            list_id: UUID of the task list
            include_archived: Whether to include archived tasks

        Returns:
            Flat list of tasks with parents followed by their children
        """
        top_level_tasks = await task_service.get_tasks_for_list(list_id, include_archived)

        # Build flat list with children
        tasks_with_children = []
        for parent in top_level_tasks:
            tasks_with_children.append(parent)
            children = await task_service.get_children(parent.id, include_archived)
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
            async with self._db_manager.get_session() as session:
                task_service = TaskService(session)
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
            async with self._db_manager.get_session() as session:
                task_service = TaskService(session)
                # Get all descendants (children, grandchildren, etc.)
                descendants = await task_service.get_all_descendants(parent_id, include_archived=False)

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
            async with self._db_manager.get_session() as session:
                task_service = TaskService(session)
                tasks = await self._get_tasks_with_children(
                    task_service,
                    self._current_list_id,
                    include_archived=False
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
            async with self._db_manager.get_session() as session:
                list_service = ListService(session)
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

        # Adjust levels to be context-relative (children start at level 0)
        adjusted_children = self._make_levels_context_relative(children, selected_task.level)

        # Update Column 2 header
        header_title = f"{selected_task.title} Subtasks"
        column2.update_header(header_title)

        # Update Column 2 with children
        column2.set_tasks(adjusted_children)

    async def _update_column3_for_selection(self, selected_task: Task) -> None:
        """Update Column 3 to show details of the selected task.

        Args:
            selected_task: The task selected in Column 1 or Column 2
        """
        column3 = self.query_one(f"#{COLUMN_3_ID}", DetailPanel)

        # Get the hierarchy path (from root to selected task)
        hierarchy = await self._get_task_hierarchy(selected_task.id)

        # Update Column 3 with task details
        column3.set_task(selected_task, hierarchy)

    def _make_levels_context_relative(self, tasks: List[Task], parent_level: int) -> List[Task]:
        """Adjust task levels to be context-relative for Column 2 display.

        Children of a selected task should start at level 0 in Column 2,
        regardless of their absolute level in the database.

        Args:
            tasks: List of tasks to adjust
            parent_level: Level of the parent task in Column 1

        Returns:
            List of tasks with adjusted levels for display
        """
        # The offset is parent_level + 1 (children are 1 level deeper than parent)
        level_offset = parent_level + 1

        adjusted_tasks = []
        for task in tasks:
            # Create a copy of the task with adjusted level
            adjusted_task = task.model_copy(update={
                "level": task.level - level_offset
            })
            adjusted_tasks.append(adjusted_task)

        return adjusted_tasks

    def _switch_to_list(self, list_number: int) -> None:
        """Switch to specified list number.

        Args:
            list_number: List number to switch to (1-3)
        """
        list_bar = self.query_one(ListBar)
        list_bar.select_list_by_number(list_number)
