"""Archive viewer modal for TaskUI.

This module provides a modal dialog for viewing and restoring archived tasks with:
- Search/filter functionality
- List of archived tasks with details
- Restore (unarchive) functionality
- Keyboard shortcuts (Escape to close, R to restore)
"""

from typing import List, Optional
from uuid import UUID

from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static, ListItem, ListView
from textual.message import Message
from textual.binding import Binding

from taskui.logging_config import get_logger
from taskui.models import Task
from taskui.ui.theme import (
    BACKGROUND,
    FOREGROUND,
    BORDER,
    SELECTION,
    COMMENT,
    LEVEL_0_COLOR,
    LEVEL_1_COLOR,
    LEVEL_2_COLOR,
    MODAL_OVERLAY_BG,
)

# Initialize logger for this module
logger = get_logger(__name__)


class ArchiveModal(ModalScreen):
    """Modal screen for viewing and restoring archived tasks.

    Displays:
    - Search input for filtering archived tasks
    - List of archived tasks with title and archived date
    - Close button

    Keyboard shortcuts:
    - R: Restore selected task
    - Esc: Close modal

    Messages:
        TaskRestored: Emitted when a task is restored (unarchived)
        ArchiveClosed: Emitted when the modal is closed
    """

    DEFAULT_CSS = f"""
    ArchiveModal {{
        align: center middle;
        background: {MODAL_OVERLAY_BG};
    }}

    ArchiveModal > Container {{
        width: 90;
        height: 35;
        background: {BACKGROUND};
        border: thick {LEVEL_0_COLOR};
        padding: 1 2;
    }}

    ArchiveModal .modal-header {{
        width: 100%;
        height: 3;
        content-align: center middle;
        text-style: bold;
        color: {LEVEL_0_COLOR};
        border-bottom: solid {BORDER};
        margin-bottom: 1;
    }}

    ArchiveModal .search-container {{
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }}

    ArchiveModal .field-label {{
        width: 100%;
        height: 1;
        color: {FOREGROUND};
        margin-bottom: 0;
    }}

    ArchiveModal Input {{
        width: 100%;
        margin-bottom: 1;
        background: {BORDER};
        color: {FOREGROUND};
        border: solid {SELECTION};
    }}

    ArchiveModal Input:focus {{
        border: solid {LEVEL_0_COLOR};
    }}

    ArchiveModal .task-list-container {{
        width: 100%;
        height: 1fr;
        border: solid {SELECTION};
        margin-bottom: 1;
    }}

    ArchiveModal ListView {{
        width: 100%;
        height: 100%;
        background: {BORDER};
    }}

    ArchiveModal ListItem {{
        padding: 0 1;
        color: {FOREGROUND};
        background: {BORDER};
    }}

    ArchiveModal ListItem:hover {{
        background: {SELECTION};
    }}

    ArchiveModal ListItem.-selected {{
        background: {LEVEL_0_COLOR};
        color: {BACKGROUND};
    }}

    ArchiveModal .empty-message {{
        width: 100%;
        height: 100%;
        content-align: center middle;
        color: {COMMENT};
        text-style: italic;
    }}

    ArchiveModal .info-text {{
        width: 100%;
        height: auto;
        color: {COMMENT};
        text-align: center;
        margin-bottom: 1;
        padding: 0 1;
    }}

    ArchiveModal .button-container {{
        width: 100%;
        height: 3;
        align: center middle;
        margin-top: 1;
        layout: horizontal;
    }}

    ArchiveModal Button {{
        margin: 0 1;
        min-width: 15;
        background: {SELECTION};
        color: {FOREGROUND};
        border: solid {BORDER};
    }}

    ArchiveModal Button:hover {{
        background: {BORDER};
        border: solid {LEVEL_0_COLOR};
    }}

    ArchiveModal Button.close-button {{
        border: solid {LEVEL_2_COLOR};
    }}

    ArchiveModal Button.close-button:hover {{
        background: {LEVEL_2_COLOR};
        color: {BACKGROUND};
    }}
    """

    BINDINGS = [
        Binding("escape", "close", "Close", priority=True),
        Binding("r", "restore", "Restore", show=True),
    ]

    def __init__(
        self,
        archived_tasks: List[Task],
        **kwargs
    ) -> None:
        """Initialize the archive modal.

        Args:
            archived_tasks: List of archived tasks to display
            **kwargs: Additional keyword arguments for ModalScreen
        """
        super().__init__(**kwargs)
        self.all_archived_tasks = archived_tasks
        self.filtered_tasks = archived_tasks
        self.selected_task: Optional[Task] = None

    def compose(self) -> ComposeResult:
        """Compose the modal layout.

        Yields:
            Widgets that make up the modal dialog
        """
        with Container():
            # Header
            yield Static("📦 Archived Tasks", classes="modal-header")

            # Search field
            with Vertical(classes="search-container"):
                yield Label("Search (filter by title or notes):", classes="field-label")
                yield Input(
                    placeholder="Type to search...",
                    id="search-input"
                )

            # Info text
            task_count = len(self.all_archived_tasks)
            info_text = f"{task_count} archived task{'s' if task_count != 1 else ''} • Press R to restore"
            yield Static(info_text, classes="info-text", id="info-text")

            # Task list
            with VerticalScroll(classes="task-list-container"):
                if self.all_archived_tasks:
                    yield ListView(
                        *self._create_list_items(),
                        id="task-list"
                    )
                else:
                    yield Static(
                        "No archived tasks\n\nArchived tasks will appear here",
                        classes="empty-message"
                    )

            # Buttons
            with Container(classes="button-container"):
                yield Button("Close [Esc]", variant="error", id="close-button", classes="close-button")

    def _create_list_items(self) -> List[ListItem]:
        """Create list items for archived tasks.

        Converts the current filtered_tasks list into ListItem widgets for display
        in the ListView. Each list item shows:
        - Task title (truncated to 60 chars if necessary)
        - Archived date formatted as YYYY-MM-DD HH:MM
        - Unique ID based on task UUID for selection tracking

        The ListItem ID format "task-<uuid>" is used by on_list_view_selected
        to map ListView selections back to Task objects.

        Returns:
            List of ListItem widgets ready for ListView, or empty list if
            filtered_tasks is empty
        """
        items = []
        for task in self.filtered_tasks:
            # Format the archived date
            archived_date = task.archived_at.strftime("%Y-%m-%d %H:%M") if task.archived_at else "Unknown"

            # Truncate title if too long
            title = task.title[:60] + "..." if len(task.title) > 60 else task.title

            # Create list item text
            item_text = f"{title}\n  Archived: {archived_date}"

            item = ListItem(Static(item_text), id=f"task-{task.id}")
            items.append(item)

        return items

    def on_mount(self) -> None:
        """Called when the modal is mounted.

        Handles initial focus and selection:
        - If archived tasks exist: Focus the task list and select the first task
        - If no archived tasks: Focus the search input field
        - Falls back gracefully if task list is unavailable

        Logs the number of archived tasks for debugging purposes.
        """
        logger.info(f"Archive modal opened with {len(self.all_archived_tasks)} archived tasks")

        # Focus the task list if there are tasks, otherwise focus search input
        if self.all_archived_tasks:
            try:
                task_list = self.query_one("#task-list", ListView)
                task_list.focus()
                # Select the first task by default
                if len(self.filtered_tasks) > 0:
                    self.selected_task = self.filtered_tasks[0]
            except Exception:
                # Fallback to search input if list not available
                search_input = self.query_one("#search-input", Input)
                search_input.focus()
        else:
            # No tasks, focus search input
            search_input = self.query_one("#search-input", Input)
            search_input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes and trigger task filtering.

        This is the entry point for the search/filter functionality. When the user
        types in the search input field, this method:
        1. Validates that the event is from the search input
        2. Normalizes the search query (strips whitespace, converts to lowercase)
        3. Triggers task filtering via _filter_tasks

        Args:
            event: The Input.Changed event containing the new search value
        """
        if event.input.id == "search-input":
            search_query = event.value.strip().lower()
            self._filter_tasks(search_query)

    def _update_task_list_view(self, search_query: str = "") -> None:
        """Update the task list view based on current filtered tasks.

        This is a key helper method that manages the task list widget lifecycle.
        It handles two scenarios:

        1. When filtered_tasks is not empty:
           - Recreates the ListView with filtered tasks
           - Mounts it in the task list container
           - Automatically selects the first task
           - Focuses the list view for keyboard navigation

        2. When filtered_tasks is empty:
           - Displays an empty state message
           - Clears selected task

        Always updates the info text to reflect current filter state.

        Args:
            search_query: Current search query used for info text display.
                         Empty string indicates no active filter.
        """
        list_container = self.query_one(".task-list-container")
        list_container.remove_children()

        if self.filtered_tasks:
            list_view = ListView(
                *self._create_list_items(),
                id="task-list"
            )
            list_container.mount(list_view)
            list_view.focus()
            self.selected_task = self.filtered_tasks[0]
        else:
            empty_msg = Static(
                "No matching tasks\n\nTry a different search term",
                classes="empty-message"
            )
            list_container.mount(empty_msg)
            self.selected_task = None

        self._update_info_text(search_query)

    def _update_info_text(self, search_query: str = "") -> None:
        """Update the info text based on current filter state.

        This helper method updates the status bar text to reflect:
        - When no filter is active: Shows total number of archived tasks
        - When a filter is active: Shows filtered count and total count

        The info text also includes a reminder about the restore keyboard shortcut.
        Handles proper pluralization for task count display.

        Args:
            search_query: Current search query string. If empty, shows total count only.
                         If non-empty, shows filtered count vs total count.
        """
        info_text = self.query_one("#info-text", Static)
        filtered_count = len(self.filtered_tasks)
        total_count = len(self.all_archived_tasks)

        plural = 's' if total_count != 1 else ''

        if search_query:
            info_text.update(
                f"{filtered_count} of {total_count} archived task{plural} • Press R to restore"
            )
        else:
            info_text.update(
                f"{total_count} archived task{plural} • Press R to restore"
            )

    def _filter_tasks(self, search_query: str) -> None:
        """Filter tasks based on search query.

        This is the core search filtering logic that implements incremental filtering
        as the user types. The search:
        - Is case-insensitive (query is already lowercased by caller)
        - Searches across task titles and notes fields
        - Returns all tasks if query is empty
        - Supports partial/substring matching

        Search behavior:
        - Empty query: Returns all archived tasks
        - Non-empty query: Returns tasks where the query appears in either:
          1. Task title (substring match)
          2. Task notes/description (substring match, if notes exist)

        After filtering, automatically updates the task list view and info text.

        Args:
            search_query: The normalized search string (already lowercase, whitespace trimmed).
                         Empty string means no filter applied.
        """
        if not search_query:
            self.filtered_tasks = self.all_archived_tasks
        else:
            self.filtered_tasks = [
                task for task in self.all_archived_tasks
                if search_query in task.title.lower() or
                   (task.notes and search_query in task.notes.lower())
            ]

        self._update_task_list_view(search_query)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle task selection in the list view.

        When a user selects a task in the ListView, this method:
        1. Extracts the task UUID from the ListItem's ID (format: "task-<uuid>")
        2. Parses the UUID from the string representation
        3. Finds the corresponding Task object in filtered_tasks
        4. Updates self.selected_task for use by restore action
        5. Logs the selection for debugging

        Handles errors gracefully:
        - Invalid UUID format: Logs error and clears selection
        - Missing task: Sets selected_task to None if not found

        Args:
            event: The ListView.Selected event containing the selected ListItem
        """
        # Extract task ID from ListItem ID
        item_id = event.item.id
        if item_id and item_id.startswith("task-"):
            task_id_str = item_id[5:]  # Remove "task-" prefix
            try:
                task_id = UUID(task_id_str)
                # Find the selected task
                self.selected_task = next(
                    (task for task in self.filtered_tasks if task.id == task_id),
                    None
                )
                logger.debug(f"Selected archived task: {self.selected_task.title if self.selected_task else None}")
            except ValueError:
                logger.error(f"Invalid UUID in list item ID: {task_id_str}")
                self.selected_task = None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Routes button presses to appropriate action handlers:
        - Close button (id="close-button"): Triggers action_close

        Args:
            event: The Button.Pressed event containing the button that was pressed
        """
        if event.button.id == "close-button":
            self.action_close()

    def action_restore(self) -> None:
        """Restore (unarchive) the selected task.

        This method implements the restore functionality triggered by:
        - Pressing the R key (keyboard shortcut)
        - User selection via list navigation

        The restore process:
        1. Verifies a task is selected (from self.selected_task or ListView index)
        2. Logs the restore action for audit trail
        3. Emits a TaskRestored message with the task UUID
        4. Dismisses the modal (parent app handles actual unarchiving)

        Error handling:
        - If no task is selected: Logs debug message and returns without action
        - If ListView query fails: Gracefully falls back to self.selected_task

        The actual unarchiving is handled by the parent component listening to
        the TaskRestored message, allowing this modal to stay independent.

        Returns:
            None. Raises no exceptions; handles missing selection gracefully.
        """
        # Get the selected task from ListView if not already set
        if not self.selected_task and self.filtered_tasks:
            try:
                list_view = self.query_one("#task-list", ListView)
                if list_view.index is not None and list_view.index < len(self.filtered_tasks):
                    self.selected_task = self.filtered_tasks[list_view.index]
            except Exception:
                pass

        if not self.selected_task:
            logger.debug("No task selected for restore")
            return

        logger.info(f"Restoring archived task: {self.selected_task.title[:50]}")

        # Post TaskRestored message
        self.post_message(self.TaskRestored(task_id=self.selected_task.id))

        # Dismiss modal
        self.dismiss()

    def action_close(self) -> None:
        """Close the archive modal.

        Triggered by:
        - Pressing Escape key
        - Clicking the Close button

        This method:
        1. Logs the close action
        2. Posts an ArchiveClosed message for parent component notification
        3. Dismisses the modal from the screen

        The parent component can listen to ArchiveClosed to perform cleanup
        if needed.
        """
        logger.info("Archive modal closed")
        # Post ArchiveClosed message
        self.post_message(self.ArchiveClosed())
        # Dismiss modal
        self.dismiss()

    class TaskRestored(Message):
        """Message emitted when a task is restored.

        This message is posted when the user selects a task and presses R,
        or when the restore action is triggered. The parent component should
        listen to this message and handle the actual restoration (unarchiving)
        of the task in the data model.

        Attributes:
            task_id: UUID of the task to restore
        """

        def __init__(self, task_id: UUID) -> None:
            """Initialize the TaskRestored message.

            Args:
                task_id: UUID of the task to restore
            """
            super().__init__()
            self.task_id = task_id

    class ArchiveClosed(Message):
        """Message emitted when archive modal is closed.

        This message is posted when the user closes the modal via:
        - Pressing Escape key
        - Clicking the Close button

        The parent component can listen to this message to perform cleanup
        or state updates if needed.
        """
        pass
