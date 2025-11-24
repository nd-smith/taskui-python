"""Task creation/editing modal for TaskUI.

This module provides a modal dialog for creating and editing tasks with:
- Title input (required)
- Notes input (optional)
- Diary entries display and management (edit mode only)
- Context display (sibling vs child creation)
- Nesting limit validation
- Keyboard shortcuts (Enter to save, Escape to cancel)
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static, TextArea
from textual.message import Message
from textual.binding import Binding

from taskui.logging_config import get_logger
from taskui.models import Task, DiaryEntry
from taskui.services.nesting_validation import can_create_child, MAX_NESTING_DEPTH
from taskui.ui.base_styles import MODAL_BASE_CSS, BUTTON_BASE_CSS
from taskui.ui.theme import (
    LEVEL_1_COLOR,
    ORANGE,
    LEVEL_2_COLOR,
)
from taskui.utils.datetime_utils import format_diary_timestamp
from taskui.config import Config

# Initialize logger for this module
logger = get_logger(__name__)


class TaskCreationModal(ModalScreen):
    """Modal screen for creating or editing tasks.

    Displays a form with:
    - Title input field (required)
    - Notes text area (optional)
    - Context information (creating sibling/child, current level)
    - Action buttons (Save/Cancel)

    Messages:
        TaskCreated: Emitted when a task is successfully created/edited
        TaskCancelled: Emitted when the modal is cancelled
    """

    # Use base modal and button styles, plus modal-specific overrides
    DEFAULT_CSS = MODAL_BASE_CSS + BUTTON_BASE_CSS + f"""
    TaskCreationModal > Container {{
        width: 80;
        height: auto;
        max-height: 90%;
        overflow-y: auto;
    }}

    TaskCreationModal .modal-header {{
        width: 100%;
        height: 3;
        content-align: center middle;
        margin-bottom: 1;
    }}

    TaskCreationModal .context-info {{
        width: 100%;
        height: auto;
        color: {LEVEL_1_COLOR};
        text-align: center;
        margin-bottom: 1;
        padding: 0 1;
    }}

    TaskCreationModal .error-message {{
        width: 100%;
        height: auto;
        color: {ORANGE};
        text-align: center;
        margin-bottom: 1;
        padding: 0 1;
        text-style: bold;
    }}

    TaskCreationModal .field-label {{
        width: 100%;
        height: 1;
        margin-top: 1;
    }}

    TaskCreationModal Input {{
        width: 100%;
        margin-bottom: 1;
    }}

    TaskCreationModal TextArea {{
        width: 100%;
        height: 8;
        margin-bottom: 1;
    }}

    TaskCreationModal .diary-section {{
        width: 100%;
        height: auto;
        margin-top: 2;
        padding: 1;
        border: solid {LEVEL_2_COLOR};
    }}

    TaskCreationModal .diary-header {{
        width: 100%;
        height: 1;
        color: {LEVEL_1_COLOR};
        text-style: bold;
        margin-bottom: 1;
    }}

    TaskCreationModal .diary-entry {{
        width: 100%;
        height: auto;
        margin-bottom: 1;
        padding: 1;
        background: $surface;
        border: solid {LEVEL_2_COLOR};
    }}

    TaskCreationModal .diary-timestamp {{
        width: 100%;
        height: 1;
        color: {LEVEL_2_COLOR};
        text-style: italic;
    }}

    TaskCreationModal .diary-content {{
        width: 100%;
        height: auto;
        margin: 1 0;
    }}

    TaskCreationModal .diary-edit-area {{
        width: 100%;
        height: 6;
        margin: 1 0;
    }}

    TaskCreationModal .diary-buttons {{
        width: 100%;
        height: 1;
        layout: horizontal;
    }}

    TaskCreationModal .diary-buttons Button {{
        margin: 0 1 0 0;
        min-width: 10;
    }}

    TaskCreationModal .button-container {{
        width: 100%;
        height: 3;
        align: center middle;
        margin-top: 1;
        layout: horizontal;
    }}

    TaskCreationModal Button {{
        margin: 0 1;
        min-width: 15;
    }}
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
        Binding("ctrl+s", "save", "Save", priority=True),
    ]

    def __init__(
        self,
        mode: str = "create_sibling",
        parent_task: Optional[Task] = None,
        edit_task: Optional[Task] = None,
        diary_service_getter=None,
        **kwargs
    ) -> None:
        """Initialize the task creation modal.

        This constructor sets up the modal for three modes of operation:
        1. "create_sibling": Create a task at the same level as parent_task (or top-level if no parent)
        2. "create_child": Create a task nested under parent_task
        3. "edit": Edit an existing task specified in edit_task

        Validation Logic:
            For "create_child" mode, performs nesting constraint validation before the modal
            is even displayed. If the parent task has reached the maximum nesting depth,
            a validation_error is set and the save button is disabled.
            This prevents users from attempting an operation that would violate nesting rules.

        Nesting Limit Checks:
            - Uses global MAX_NESTING_DEPTH to check if a child can be created
            - Stores error message if constraints are violated

        Args:
            mode: Creation mode - "create_sibling", "create_child", or "edit"
            parent_task: Parent task for child creation or sibling reference
            edit_task: Task to edit (for edit mode)
            diary_service_getter: Async context manager to get DiaryService instance
            **kwargs: Additional keyword arguments for ModalScreen

        Attributes:
            validation_error: Set to an error message if nesting constraints are violated,
                             None otherwise
        """
        super().__init__(**kwargs)
        self.mode = mode
        self.parent_task = parent_task
        self.edit_task = edit_task
        self.diary_service_getter = diary_service_getter
        self.validation_error: Optional[str] = None
        self.diary_entries: List[DiaryEntry] = []
        self.editing_entry_id: Optional[UUID] = None

        # Get timezone from config for timestamp formatting
        config = Config()
        self.timezone = config.get_display_config()['timezone']

        # Validate nesting constraints for child creation
        if mode == "create_child" and parent_task is not None:
            if not can_create_child(parent_task.level):
                self.validation_error = (
                    f"Cannot create child: Parent at level {parent_task.level} "
                    f"has reached maximum nesting depth ({MAX_NESTING_DEPTH})"
                )
                logger.warning(
                    f"TaskModal: Nesting limit violation - parent_id={parent_task.id}, "
                    f"parent_level={parent_task.level}, max_depth={MAX_NESTING_DEPTH}"
                )

    def compose(self) -> ComposeResult:
        """Compose the modal layout.

        Yields:
            Widgets that make up the modal dialog
        """
        with Container():
            # Header
            header_text = self._get_header_text()
            yield Static(header_text, classes="modal-header")

            # Context info
            context_text = self._get_context_text()
            if context_text:
                yield Static(context_text, classes="context-info")

            # Error message if validation failed
            if self.validation_error:
                yield Static(f"⚠ {self.validation_error}", classes="error-message")

            # Title field
            yield Label("Task Title:", classes="field-label")
            title_value = self.edit_task.title if self.edit_task else ""
            yield Input(
                placeholder="Enter task title...",
                value=title_value,
                id="title-input"
            )

            # Notes field
            yield Label("Notes (optional):", classes="field-label")
            notes_value = self.edit_task.notes if self.edit_task and self.edit_task.notes else ""
            yield TextArea(
                text=notes_value,
                id="notes-input"
            )

            # URL field
            yield Label("URL (optional):", classes="field-label")
            url_value = self.edit_task.url if self.edit_task and self.edit_task.url else ""
            yield Input(
                placeholder="https://example.com",
                value=url_value,
                id="url-input"
            )

            # Diary entries section (edit mode only)
            if self.mode == "edit":
                with Vertical(classes="diary-section", id="diary-section"):
                    yield Static("📔 Diary Entries", classes="diary-header")
                    yield Vertical(id="diary-entries-container")

            # Buttons
            with Container(classes="button-container"):
                yield Button("Save [Enter]", id="save-button", classes="success")
                yield Button("Cancel [Esc]", id="cancel-button", classes="error")

    def _get_header_text(self) -> str:
        """Get the modal header text based on mode.

        Returns:
            Header text string
        """
        if self.mode == "edit":
            return "✏️ Edit Task"
        elif self.mode == "create_child":
            return "➕ Create Child Task"
        else:  # create_sibling
            return "➕ Create New Task"

    def _get_edit_context_text(self) -> str:
        """Get context text for edit mode.

        This helper method generates the context information displayed to the user when
        editing an existing task. It provides a truncated preview of the task being edited
        to help users confirm they have the right task open.

        Validation Considerations:
            - Returns empty string if edit_task is None (defensive programming for edit mode)
            - Truncates title to 40 characters to prevent UI overflow

        Returns:
            Context string showing the task being edited (e.g., "Editing: Task title...")
            or empty string if edit_task is not set
        """
        if not self.edit_task:
            return ""
        return f"Editing: {self.edit_task.title[:40]}..."

    def _get_child_context_text(self) -> str:
        """Get context text for child creation.

        This helper method generates context information for child task creation, showing
        the parent task and calculated child level.

        Nesting Limit Validation:
            - Child level is always parent.level + 1 if child creation is allowed
            - If nesting limits were exceeded, a validation_error would be set in __init__
              and this method would not be called

        Returns:
            Context string showing parent task and child level (e.g., "Creating child under:
            Parent Task...\nNew task level: 2") or empty string if parent_task is not set
        """
        if not self.parent_task:
            return ""

        child_level = self.parent_task.level + 1
        return (
            f"Creating child under: {self.parent_task.title[:30]}...\n"
            f"New task level: {child_level}"
        )

    def _get_sibling_context_text(self) -> str:
        """Get context text for sibling creation.

        This helper method generates context information for sibling task creation. A sibling
        is created at the same nesting level as the reference parent_task (or at level 0 if
        no parent is specified, indicating a top-level task).

        Validation Considerations:
            - No explicit nesting limit check is performed for sibling creation
            - Top-level tasks (level 0) have no nesting depth constraints
            - Sibling creation does not require parent_task to be set

        Returns:
            Context string showing sibling level (e.g., "Creating sibling at level: 1")
            or "Creating new top-level task" if no parent task is specified
        """
        if self.parent_task:
            return f"Creating sibling at level: {self.parent_task.level}"
        return "Creating new top-level task"

    def _get_context_text(self) -> str:
        """Get the context information text.

        This method routes to the appropriate helper based on the modal's mode. It serves as
        a dispatcher that selects between _get_edit_context_text, _get_child_context_text,
        and _get_sibling_context_text based on the current mode.

        Validation Logic:
            - Returns empty string if validation_error is set, preventing context display
            - This allows the error message to be shown instead of context information
            - The mode determines which helper method is called

        Returns:
            Context description string from the appropriate helper method, or empty string
            if validation_error is set
        """
        if self.validation_error:
            return ""

        if self.mode == "edit":
            return self._get_edit_context_text()
        elif self.mode == "create_child":
            return self._get_child_context_text()
        else:  # create_sibling
            return self._get_sibling_context_text()

    def on_mount(self) -> None:
        """Called when the modal is mounted.

        This lifecycle hook is called when the modal is first displayed. It handles:
        1. Logging modal open event for debugging
        2. Setting focus to the title input field
        3. Disabling the save button if validation errors were detected in __init__
        4. Loading diary entries if in edit mode

        Validation Error Handling:
            - Checks self.validation_error set during __init__ (nesting limit violations)
            - Disables save button to prevent users from submitting invalid data
            - Logs the validation error for debugging purposes
            - The error message is displayed to the user in the modal's context area
        """
        context_info = ""
        if self.mode == "edit" and self.edit_task:
            context_info = f", edit_task_id={self.edit_task.id}"
        elif self.parent_task:
            context_info = f", parent_id={self.parent_task.id}"

        logger.info(f"TaskModal: Opened in {self.mode} mode{context_info}")

        # Focus the title input
        title_input = self.query_one("#title-input", Input)
        title_input.focus()

        # Disable save button if there's a validation error
        if self.validation_error:
            logger.warning(f"TaskModal: Save button disabled due to validation error: {self.validation_error}")
            save_button = self.query_one("#save-button", Button)
            save_button.disabled = True

        # Load diary entries if in edit mode
        if self.mode == "edit" and self.edit_task and self.diary_service_getter:
            self.run_worker(self._load_diary_entries(), exclusive=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: The button pressed event
        """
        logger.debug(f"TaskModal: Button pressed - {event.button.id}")
        if event.button.id == "save-button":
            self.action_save()
        elif event.button.id == "cancel-button":
            self.action_cancel()
        else:
            # Check if it's a diary entry button
            self._handle_diary_button(event.button.id)

    def action_save(self) -> None:
        """Save the task and dismiss the modal.

        This method implements the save operation with multiple layers of validation:

        Validation Logic:
            1. Nesting Constraint Validation: Checks self.validation_error set in __init__
               - If validation errors occurred during initialization (e.g., nesting limits
                 exceeded), the save is cancelled immediately
               - This is a defensive check; the save button should be disabled in on_mount()
               - Logs and returns early if this check fails

            2. Input Validation: Validates user input from form fields
               - Title field: Required and must not be empty after stripping whitespace
               - Notes field: Optional; empty string is treated as None
               - Only proceeds if title passes validation
               - Logs and returns early if title is empty

        Behavior:
            - On successful validation, posts TaskCreated message with form data
            - Dismisses the modal after posting the message
            - Does NOT dismiss if validation fails; allows user to correct input
        """
        # Don't save if there's a validation error
        if self.validation_error:
            logger.debug("Save cancelled due to validation error")
            return

        # Get input values
        title_input = self.query_one("#title-input", Input)
        notes_input = self.query_one("#notes-input", TextArea)
        url_input = self.query_one("#url-input", Input)

        title = title_input.value.strip()
        notes = notes_input.text.strip() if notes_input.text else None
        url = url_input.value.strip() if url_input.value else None

        # Validate title
        if not title:
            logger.warning(f"TaskModal: Save validation failed - empty title (mode={self.mode})")
            # Show error - could add a validation label here
            return

        logger.info(
            f"TaskModal: Task {self.mode} saved - title='{title[:50]}', "
            f"has_notes={bool(notes)}, notes_length={len(notes) if notes else 0}, "
            f"has_url={bool(url)}"
        )

        # Post TaskCreated message
        self.post_message(
            self.TaskCreated(
                title=title,
                notes=notes,
                url=url,
                mode=self.mode,
                parent_task=self.parent_task,
                edit_task=self.edit_task,
            )
        )

        # Dismiss modal without result (message already posted)
        self.dismiss()

    def action_cancel(self) -> None:
        """Cancel and dismiss the modal.

        This method handles the cancel action without performing any validation checks.
        Unlike the save action, cancel does not validate nesting constraints or input data.
        Any task data entered into the form is discarded.

        Behavior:
            - Posts a TaskCancelled message to notify listeners
            - Dismisses the modal, returning to the previous screen
            - Does not validate or persist any user input
        """
        logger.info(f"TaskModal: Cancelled (mode={self.mode})")
        # Post TaskCancelled message
        self.post_message(self.TaskCancelled())
        # Dismiss modal
        self.dismiss()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input fields.

        This event handler is triggered when the user presses Enter in an input field.
        Currently, pressing Enter in the title input field triggers the save action,
        providing a keyboard shortcut for task creation/editing.

        Note:
            - Enter in notes field (TextArea) does not trigger save; it adds a newline
            - Escape key can be used as an alternative cancel action
            - Ctrl+S can be used as an alternative save action

        Args:
            event: The input submitted event containing information about which input
                   was submitted
        """
        # Enter key in title input should save
        if event.input.id == "title-input":
            logger.debug("TaskModal: Enter pressed in title field, triggering save")
            self.action_save()

    # ========================================================================
    # DIARY ENTRY MANAGEMENT
    # ========================================================================

    async def _load_diary_entries(self) -> None:
        """Load diary entries for the task being edited."""
        if not self.edit_task or not self.diary_service_getter:
            return

        try:
            async with self.diary_service_getter() as diary_service:
                # Get all entries (not just last 3) - use large limit
                self.diary_entries = await diary_service.get_entries_for_task(
                    self.edit_task.id,
                    limit=1000
                )
                logger.info(f"Loaded {len(self.diary_entries)} diary entries for task {self.edit_task.id}")
                self._render_diary_entries()
        except Exception as e:
            logger.error(f"Failed to load diary entries: {e}", exc_info=True)
            self.notify(f"Failed to load diary entries: {str(e)}", severity="error")

    def _render_diary_entries(self) -> None:
        """Render all diary entries in the container."""
        container = self.query_one("#diary-entries-container", Vertical)
        container.remove_children()

        if not self.diary_entries:
            container.mount(Static("No diary entries yet.", classes="diary-content"))
            return

        for entry in self.diary_entries:
            self._render_single_entry(container, entry)

    def _render_single_entry(self, container: Vertical, entry: DiaryEntry) -> None:
        """Render a single diary entry.

        Args:
            container: Container to add entry to
            entry: DiaryEntry to render
        """
        entry_id = str(entry.id)
        is_editing = self.editing_entry_id == entry.id

        with container.compose():
            with Vertical(classes="diary-entry", id=f"entry-{entry_id}"):
                # Timestamp - use new format_diary_timestamp function
                timestamp_str = format_diary_timestamp(entry.created_at, self.timezone)
                yield Static(f"🕐 {timestamp_str}", classes="diary-timestamp")

                if is_editing:
                    # Edit mode: show TextArea
                    yield TextArea(
                        text=entry.content,
                        classes="diary-edit-area",
                        id=f"edit-area-{entry_id}"
                    )
                    # Edit buttons
                    with Horizontal(classes="diary-buttons"):
                        yield Button("Save", id=f"save-{entry_id}", classes="success")
                        yield Button("Cancel", id=f"cancel-{entry_id}")
                else:
                    # View mode: show content and action buttons
                    yield Static(entry.content, classes="diary-content")
                    with Horizontal(classes="diary-buttons"):
                        yield Button("Edit", id=f"edit-{entry_id}")
                        yield Button("Delete", id=f"delete-{entry_id}", classes="error")

    def _handle_diary_button(self, button_id: str) -> None:
        """Handle diary entry button clicks.

        Args:
            button_id: ID of the button that was clicked
        """
        parts = button_id.split("-", 1)
        if len(parts) != 2:
            return

        action, entry_id_str = parts
        try:
            entry_id = UUID(entry_id_str)
        except ValueError:
            logger.error(f"Invalid entry ID in button: {button_id}")
            return

        if action == "edit":
            self._start_editing_entry(entry_id)
        elif action == "delete":
            self.run_worker(self._delete_entry(entry_id))
        elif action == "save":
            self.run_worker(self._save_entry_edit(entry_id))
        elif action == "cancel":
            self._cancel_editing_entry()

    def _start_editing_entry(self, entry_id: UUID) -> None:
        """Start editing a diary entry.

        Args:
            entry_id: ID of entry to edit
        """
        self.editing_entry_id = entry_id
        self._render_diary_entries()

    def _cancel_editing_entry(self) -> None:
        """Cancel editing the current entry."""
        self.editing_entry_id = None
        self._render_diary_entries()

    async def _save_entry_edit(self, entry_id: UUID) -> None:
        """Save edited diary entry content.

        Args:
            entry_id: ID of entry being edited
        """
        if not self.diary_service_getter:
            return

        try:
            # Get the edited content
            edit_area = self.query_one(f"#edit-area-{entry_id}", TextArea)
            new_content = edit_area.text.strip()

            if not new_content:
                self.notify("Entry content cannot be empty", severity="warning")
                return

            # Update via service
            async with self.diary_service_getter() as diary_service:
                updated_entry = await diary_service.update_entry(entry_id, new_content)

                # Update local cache
                for i, entry in enumerate(self.diary_entries):
                    if entry.id == entry_id:
                        self.diary_entries[i] = updated_entry
                        break

            self.editing_entry_id = None
            self._render_diary_entries()
            self.notify("Diary entry updated", severity="information")
            logger.info(f"Updated diary entry {entry_id}")

        except Exception as e:
            logger.error(f"Failed to update diary entry: {e}", exc_info=True)
            self.notify(f"Failed to update entry: {str(e)}", severity="error")

    async def _delete_entry(self, entry_id: UUID) -> None:
        """Delete a diary entry.

        Args:
            entry_id: ID of entry to delete
        """
        if not self.diary_service_getter:
            return

        try:
            async with self.diary_service_getter() as diary_service:
                await diary_service.delete_entry(entry_id)

                # Remove from local cache
                self.diary_entries = [e for e in self.diary_entries if e.id != entry_id]

            self._render_diary_entries()
            self.notify("Diary entry deleted", severity="information")
            logger.info(f"Deleted diary entry {entry_id}")

        except Exception as e:
            logger.error(f"Failed to delete diary entry: {e}", exc_info=True)
            self.notify(f"Failed to delete entry: {str(e)}", severity="error")

    class TaskCreated(Message):
        """Message emitted when a task is created/edited."""

        def __init__(
            self,
            title: str,
            notes: Optional[str],
            url: Optional[str],
            mode: str,
            parent_task: Optional[Task],
            edit_task: Optional[Task] = None,
        ) -> None:
            """Initialize the TaskCreated message.

            Args:
                title: Task title
                notes: Optional task notes
                url: Optional URL/link
                mode: Creation mode
                parent_task: Parent task reference
                edit_task: Task being edited (if any)
            """
            super().__init__()
            self.title = title
            self.notes = notes
            self.url = url
            self.mode = mode
            self.parent_task = parent_task
            self.edit_task = edit_task

    class TaskCancelled(Message):
        """Message emitted when task creation is cancelled."""
        pass
