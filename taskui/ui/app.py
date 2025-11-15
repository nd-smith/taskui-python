"""Main Textual application for TaskUI.

This module contains the main TaskUI application with three-column layout:
- Column 1: Tasks (max 2 levels)
- Column 2: Subtasks (max 3 levels, context-relative)
- Column 3: Details (task information)
"""

from typing import Optional, Any, List
from uuid import UUID

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static
from textual.binding import Binding
from textual.events import Key

from taskui.database import DatabaseManager, get_database_manager
from taskui.models import Task, TaskList
from taskui.services.nesting_rules import Column as NestingColumn
from taskui.services.task_service import TaskService
from taskui.services.list_service import ListService
from taskui.ui.components.task_modal import TaskCreationModal
from taskui.ui.components.detail_panel import DetailPanel
from taskui.ui.components.list_bar import ListBar
from taskui.ui.theme import (
    BACKGROUND,
    FOREGROUND,
    BORDER,
    LEVEL_0_COLOR,
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


class TaskUI(App):
    """Main TaskUI application with three-column layout."""

    CSS = """
    Screen {
        background: #272822;
        layout: vertical;
    }

    #main-container {
        width: 100%;
        height: 1fr;
        background: #272822;
        margin-top: 1;
    }

    #columns-container {
        width: 100%;
        height: 100%;
        layout: horizontal;
    }

    #column-1 {
        width: 1fr;
        height: 100%;
    }

    #column-2 {
        width: 1fr;
        height: 100%;
    }

    #column-3 {
        width: 1fr;
        height: 100%;
    }

    Footer {
        background: #49483E;
    }
    """

    BINDINGS = get_all_bindings()

    def __init__(self, **kwargs) -> None:
        """Initialize the TaskUI application."""
        super().__init__(**kwargs)
        self.title = "TaskUI - Nested Task Manager"
        self.sub_title = "Press ? for help"
        self._focused_column_id: str = COLUMN_1_ID  # Track which column has focus
        self._db_manager: Optional[DatabaseManager] = None
        self._current_list_id: Optional[UUID] = None  # Will be set after database initialization
        self._lists: List[TaskList] = []  # Store available lists

    def compose(self) -> ComposeResult:
        """Compose the application layout.

        Yields:
            Widgets that make up the application
        """
        yield Header()

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

    def action_help(self) -> None:
        """Show help information."""
        self.push_screen("help")

    def on_key(self, event: Key) -> None:
        """Handle key events to manage tab navigation in main app vs modals.

        Intercepts tab and shift+tab keys to provide direct column navigation
        in the main app, while allowing normal form field navigation in modals.

        Args:
            event: The key event
        """
        # Only intercept tab/shift+tab when not in a modal (screen stack size is 1)
        if len(self.screen_stack) == 1:
            if event.key == "tab":
                # Prevent default focus cycling and handle column navigation
                event.prevent_default()
                event.stop()
                self.action_navigate_next_column()
            elif event.key == "shift+tab":
                # Prevent default focus cycling and handle column navigation
                event.prevent_default()
                event.stop()
                self.action_navigate_prev_column()

    async def on_mount(self) -> None:
        """Called when app is mounted and ready."""
        # Set up the theme colors
        self.theme_variables.update({
            "background": BACKGROUND,
            "foreground": FOREGROUND,
            "border": BORDER,
            "selection": "#49483E",
            "level-0": LEVEL_0_COLOR,
        })

        # Initialize database
        self._db_manager = get_database_manager()
        await self._db_manager.initialize()

        # Ensure default list exists and load initial state
        await self._ensure_default_list()
        await self._restore_app_state()

        # Set initial focus to Column 1
        self._set_column_focus(COLUMN_1_ID)

    async def _ensure_default_list(self) -> None:
        """Ensure that default lists (Work, Home, Personal) exist in the database.

        Creates default lists if they don't exist. This supports the MVP
        requirement for data persistence and app state restoration.
        """
        if not self._db_manager:
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
            # TODO: Add proper logging in Phase 3
            print(f"Error ensuring default lists: {e}")
            # Create a fallback UUID for graceful degradation
            from uuid import uuid4
            self._current_list_id = uuid4()

    async def _restore_app_state(self) -> None:
        """Restore the application state from the database.

        Loads tasks for the current list into Column 1, ensuring the app
        shows previous state on restart (supporting no data loss requirement).
        """
        if not self._db_manager or not self._current_list_id:
            return

        try:
            # Get Column 1
            column1 = self.query_one(f"#{COLUMN_1_ID}", TaskColumn)

            # Load tasks from database (with 2 levels of hierarchy)
            async with self._db_manager.get_session() as session:
                task_service = TaskService(session)
                tasks = await self._get_tasks_with_children(
                    task_service,
                    self._current_list_id,
                    include_archived=False
                )

            # Set tasks in Column 1
            column1.set_tasks(tasks)

        except Exception as e:
            # Log error but don't crash the app
            # TODO: Add proper logging in Phase 3
            print(f"Error restoring app state: {e}")

    async def _get_tasks_with_children(self, task_service: TaskService, list_id: UUID, include_archived: bool = False) -> List[Task]:
        """Get top-level tasks and their children for a list (2 levels).

        Args:
            task_service: TaskService instance
            list_id: UUID of the task list
            include_archived: Whether to include archived tasks

        Returns:
            Flat list of tasks with parents followed by their children
        """
        # Get top-level tasks
        top_level_tasks = await task_service.get_tasks_for_list(list_id, include_archived)

        # Build flat list with children
        tasks_with_children = []
        for parent in top_level_tasks:
            tasks_with_children.append(parent)
            # Get children of this parent
            children = await task_service.get_children(parent.id, include_archived)
            tasks_with_children.extend(children)

        return tasks_with_children

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
        except Exception:
            # Column not found or not focusable, ignore
            pass

    def _get_focused_column(self) -> Optional[TaskColumn]:
        """Get the currently focused column widget.

        Returns:
            TaskColumn widget or None if no column is focused
        """
        try:
            return self.query_one(f"#{self._focused_column_id}", TaskColumn)
        except Exception:
            return None

    # Navigation action handlers

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

    # Task operation action handlers

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

        # Get the currently selected task (if any)
        selected_task = column.get_selected_task()

        # Show the modal
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

        # Get the currently selected task
        selected_task = column.get_selected_task()
        if not selected_task:
            # Can't create a child without a parent selected
            return

        # Determine the column context for nesting rules
        nesting_column = self._get_nesting_column_from_id(self._focused_column_id)

        # Show the modal
        modal = TaskCreationModal(
            mode="create_child",
            parent_task=selected_task,
            column=nesting_column
        )
        self.push_screen(modal)

    def _get_nesting_column_from_id(self, column_id: str) -> NestingColumn:
        """Convert column ID to NestingColumn enum.

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

    async def on_task_creation_modal_task_created(self, message: TaskCreationModal.TaskCreated) -> None:
        """Handle TaskCreated message from the task creation modal.

        Args:
            message: TaskCreated message containing task data
        """
        # Extract the task data from message
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

        # Refresh the focused column to show the new task
        focused_column = self._get_focused_column()
        if focused_column:
            # Reload tasks from database
            await self._refresh_column_tasks(focused_column)

            # If we created a child task and we're in Column 1, also refresh Column 2
            # to show the new child under the selected parent
            if mode == "create_child" and focused_column.column_id == COLUMN_1_ID:
                selected_task = focused_column.get_selected_task()
                if selected_task:
                    await self._update_column2_for_selection(selected_task)

        # Refresh the list bar to update completion percentage (only for current list)
        if self._current_list_id:
            await self._refresh_list_bar_for_list(self._current_list_id)

    async def on_task_creation_modal_task_cancelled(self, message: TaskCreationModal.TaskCancelled) -> None:
        """Handle TaskCancelled message from the task creation modal.

        Args:
            message: TaskCancelled message
        """
        # Nothing to do when task creation is cancelled
        pass

    async def _handle_edit_task(self, task_id: UUID, title: str, notes: Optional[str]) -> None:
        """Update an existing task in the database.

        Args:
            task_id: UUID of the task to update
            title: New title for the task
            notes: New notes for the task (can be None)
        """
        if not self._db_manager:
            return

        try:
            async with self._db_manager.get_session() as session:
                task_service = TaskService(session)
                # Update the task
                await task_service.update_task(task_id, title=title, notes=notes)
                # Session context manager will auto-commit

            # Refresh the focused column to show the updated task
            focused_column = self._get_focused_column()
            if focused_column:
                # Reload tasks from database
                await self._refresh_column_tasks(focused_column)
        except Exception as e:
            # TODO: Add proper error handling in Phase 3
            print(f"Error updating task: {e}")

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
        if not self._db_manager or not self._current_list_id:
            return

        try:
            async with self._db_manager.get_session() as session:
                task_service = TaskService(session)

                if parent_task is None:
                    # No task selected, create a top-level task
                    await task_service.create_task(
                        title=title,
                        list_id=self._current_list_id,
                        notes=notes
                    )
                elif parent_task.parent_id is None:
                    # Selected task is top-level, create another top-level task
                    await task_service.create_task(
                        title=title,
                        list_id=self._current_list_id,
                        notes=notes
                    )
                else:
                    # Selected task has a parent, create a sibling under the same parent
                    await task_service.create_child_task(
                        parent_id=parent_task.parent_id,
                        title=title,
                        column=column,
                        notes=notes
                    )
                # Session context manager will auto-commit

        except Exception as e:
            # TODO: Add proper error handling in Phase 3
            print(f"Error creating sibling task: {e}")

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
                # Session context manager will auto-commit

        except Exception as e:
            # TODO: Add proper error handling in Phase 3
            print(f"Error creating child task: {e}")

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
        """Refresh only the specific list that changed in the list bar.

        This method reloads only the affected list from the database with its current
        task counts and completion percentage, then updates the list bar display.
        Much more efficient than reloading all lists.

        Args:
            list_id: UUID of the list to refresh
        """
        if not self._db_manager:
            return

        try:
            async with self._db_manager.get_session() as session:
                list_service = ListService(session)
                # Reload only the affected list (3 queries: 1 list + 1 task count + 1 completed count)
                updated_list = await list_service.get_list_by_id(list_id)

            if not updated_list:
                return

            # Find and update just that list in self._lists
            for i, task_list in enumerate(self._lists):
                if task_list.id == list_id:
                    self._lists[i] = updated_list
                    break

            # Update the list bar with the modified list
            list_bar = self.query_one(ListBar)
            list_bar.update_lists(self._lists)

        except Exception as e:
            # TODO: Add proper error handling in Phase 3
            print(f"Error refreshing list bar for list {list_id}: {e}")

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
        column = self._get_focused_column()
        if not column:
            return

        # Get the currently selected task
        selected_task = column.get_selected_task()
        if not selected_task:
            # No task selected, nothing to toggle
            return

        if not self._db_manager:
            return

        try:
            async with self._db_manager.get_session() as session:
                task_service = TaskService(session)
                # Toggle the task completion status
                await task_service.toggle_completion(selected_task.id)
                # Session context manager will auto-commit

            # Refresh the focused column to show the updated task with strikethrough
            await self._refresh_column_tasks(column)

            # If toggling in Column 2, also refresh Column 1 to update parent's progress indicator
            if column.column_id == COLUMN_2_ID:
                column1 = self.query_one(f"#{COLUMN_1_ID}", TaskColumn)
                await self._refresh_column_tasks(column1)

            # Refresh Column 3 to show updated details
            async with self._db_manager.get_session() as session:
                task_service = TaskService(session)
                updated_task = await task_service.get_task_by_id(selected_task.id)
                if updated_task:
                    await self._update_column3_for_selection(updated_task)

            # Refresh the list bar to update completion percentage (only for current list)
            if self._current_list_id:
                await self._refresh_list_bar_for_list(self._current_list_id)

        except Exception as e:
            # TODO: Add proper error handling in Phase 3
            print(f"Error toggling task completion: {e}")

    def action_archive_task(self) -> None:
        """Archive the selected task (A key)."""
        # TODO: Implement in Story 2.3
        pass

    def action_delete_task(self) -> None:
        """Delete the selected task (Delete/Backspace key)."""
        # TODO: Implement in Story 2.5
        pass

    def action_switch_list_1(self) -> None:
        """Switch to list 1 (1 key)."""
        list_bar = self.query_one(ListBar)
        list_bar.select_list_by_number(1)

    def action_switch_list_2(self) -> None:
        """Switch to list 2 (2 key)."""
        list_bar = self.query_one(ListBar)
        list_bar.select_list_by_number(2)

    def action_switch_list_3(self) -> None:
        """Switch to list 3 (3 key)."""
        list_bar = self.query_one(ListBar)
        list_bar.select_list_by_number(3)

    def action_print_column(self) -> None:
        """Print the current column to thermal printer (P key)."""
        # TODO: Implement in Story 4.1
        pass

    def action_cancel(self) -> None:
        """Cancel current operation (Escape key)."""
        # TODO: Implement when modals are added
        pass

    # Message handlers

    async def on_task_column_task_selected(self, message: TaskColumn.TaskSelected) -> None:
        """Handle task selection in columns to update Column 2 and Column 3.

        When a task is selected in Column 1, Column 2 updates to show
        the children of that task wiTh context-relative levels.
        Column 3 is always updated to show details of the selected task.

        Args:
            message: TaskSelected message containing the selected task
        """
        # Get the columns
        column1 = self.query_one(f"#{COLUMN_1_ID}", TaskColumn)
        column3 = self.query_one(f"#{COLUMN_3_ID}", DetailPanel)

        # Update Column 3 with task details (for any selected task from any column)
        await self._update_column3_for_selection(message.task)

        # Update Column 2 only for selections from Column 1
        if message.column_id == COLUMN_1_ID:
            await self._update_column2_for_selection(message.task)

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

    async def _get_task_hierarchy(self, task_id: UUID) -> List[Task]:
        """Get the complete hierarchy path from root to the specified task.

        Args:
            task_id: UUID of the task

        Returns:
            List of tasks from root to current task (including the current task)
        """
        if not self._db_manager:
            return []

        try:
            async with self._db_manager.get_session() as session:
                task_service = TaskService(session)
                # Build the hierarchy by traversing up the parent chain
                hierarchy = []
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
            # TODO: Add proper error handling in Phase 3
            print(f"Error loading hierarchy: {e}")
            return []

    async def _get_task_children(self, parent_id: UUID) -> List[Task]:
        """Get all descendants of a task in hierarchical order.

        Args:
            parent_id: UUID of the parent task

        Returns:
            List of all descendant tasks in hierarchical order
        """
        if not self._db_manager:
            return []

        try:
            async with self._db_manager.get_session() as session:
                task_service = TaskService(session)
                # Get all descendants (children, grandchildren, etc.)
                descendants = await task_service.get_all_descendants(parent_id, include_archived=False)
                return descendants
        except Exception as e:
            # TODO: Add proper error handling in Phase 3
            print(f"Error loading children: {e}")
            return []

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

    async def on_list_bar_list_selected(self, message: ListBar.ListSelected) -> None:
        """Handle list selection from the list bar.

        When a list is selected, Column 1 updates to show tasks from that list,
        and Column 2 is cleared since no task is selected yet.

        Args:
            message: ListSelected message containing the selected list info
        """
        # Update the current list ID
        self._current_list_id = message.list_id

        # Get the columns
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
            except Exception as e:
                # TODO: Add proper error handling in Phase 3
                print(f"Error loading tasks for list: {e}")
