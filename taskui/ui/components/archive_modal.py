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

        Returns:
            List of ListItem widgets for the ListView
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
        """Called when the modal is mounted."""
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
        """Handle search input changes.

        Args:
            event: The input changed event
        """
        if event.input.id == "search-input":
            search_query = event.value.strip().lower()
            self._filter_tasks(search_query)

    def _update_task_list_view(self, search_query: str = "") -> None:
        """Update the task list view based on current filtered tasks.

        Args:
            search_query: Current search query (for info text)
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

        Args:
            search_query: Current search query
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

        Args:
            search_query: The search string (case-insensitive)
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

        Args:
            event: The list view selected event
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

        Args:
            event: The button pressed event
        """
        if event.button.id == "close-button":
            self.action_close()

    def action_restore(self) -> None:
        """Restore (unarchive) the selected task."""
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
        """Close the archive modal."""
        logger.info("Archive modal closed")
        # Post ArchiveClosed message
        self.post_message(self.ArchiveClosed())
        # Dismiss modal
        self.dismiss()

    class TaskRestored(Message):
        """Message emitted when a task is restored."""

        def __init__(self, task_id: UUID) -> None:
            """Initialize the TaskRestored message.

            Args:
                task_id: UUID of the task to restore
            """
            super().__init__()
            self.task_id = task_id

    class ArchiveClosed(Message):
        """Message emitted when archive modal is closed."""
        pass
