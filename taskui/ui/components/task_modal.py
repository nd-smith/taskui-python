"""Task creation/editing modal for TaskUI.

This module provides a modal dialog for creating and editing tasks with:
- Title input (required)
- Notes input (optional)
- Context display (sibling vs child creation)
- Nesting limit validation
- Keyboard shortcuts (Enter to save, Escape to cancel)
"""

from typing import Optional
from uuid import UUID

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static, TextArea
from textual.message import Message
from textual.binding import Binding

from taskui.logging_config import get_logger
from taskui.models import Task
from taskui.services.nesting_rules import Column, NestingRules
from taskui.ui.theme import (
    BACKGROUND,
    FOREGROUND,
    BORDER,
    SELECTION,
    LEVEL_0_COLOR,
    LEVEL_1_COLOR,
    LEVEL_2_COLOR,
    MODAL_OVERLAY_BG,
    ORANGE,
)

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

    DEFAULT_CSS = f"""
    TaskCreationModal {{
        align: center middle;
        background: {MODAL_OVERLAY_BG};
    }}

    TaskCreationModal > Container {{
        width: 70;
        height: auto;
        background: {BACKGROUND};
        border: thick {LEVEL_0_COLOR};
        padding: 1 2;
    }}

    TaskCreationModal .modal-header {{
        width: 100%;
        height: 3;
        content-align: center middle;
        text-style: bold;
        color: {LEVEL_0_COLOR};
        border-bottom: solid {BORDER};
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
        color: {FOREGROUND};
        margin-top: 1;
    }}

    TaskCreationModal Input {{
        width: 100%;
        margin-bottom: 1;
        background: {BORDER};
        color: {FOREGROUND};
        border: solid {SELECTION};
    }}

    TaskCreationModal Input:focus {{
        border: solid {LEVEL_0_COLOR};
    }}

    TaskCreationModal TextArea {{
        width: 100%;
        height: 8;
        margin-bottom: 1;
        background: {BORDER};
        color: {FOREGROUND};
        border: solid {SELECTION};
    }}

    TaskCreationModal TextArea:focus {{
        border: solid {LEVEL_0_COLOR};
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
        background: {SELECTION};
        color: {FOREGROUND};
        border: solid {BORDER};
    }}

    TaskCreationModal Button:hover {{
        background: {BORDER};
        border: solid {LEVEL_0_COLOR};
    }}

    TaskCreationModal Button.save-button {{
        border: solid {LEVEL_1_COLOR};
    }}

    TaskCreationModal Button.save-button:hover {{
        background: {LEVEL_1_COLOR};
        color: {BACKGROUND};
    }}

    TaskCreationModal Button.cancel-button {{
        border: solid {LEVEL_2_COLOR};
    }}

    TaskCreationModal Button.cancel-button:hover {{
        background: {LEVEL_2_COLOR};
        color: {BACKGROUND};
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
        column: Column = Column.COLUMN1,
        edit_task: Optional[Task] = None,
        **kwargs
    ) -> None:
        """Initialize the task creation modal.

        This constructor sets up the modal for three modes of operation:
        1. "create_sibling": Create a task at the same level as parent_task (or top-level if no parent)
        2. "create_child": Create a task nested under parent_task
        3. "edit": Edit an existing task specified in edit_task

        Validation Logic:
            For "create_child" mode, performs nesting constraint validation before the modal
            is even displayed. If the parent task has reached the maximum nesting depth for
            the specified column, a validation_error is set and the save button is disabled.
            This prevents users from attempting an operation that would violate nesting rules.

        Nesting Limit Checks:
            - Uses NestingRules.can_create_child() to check if a child can be created
            - Calls NestingRules.get_max_depth() to retrieve the column-specific max depth
            - Stores error message if constraints are violated (e.g., "Cannot create child:
              Parent at level 2 has reached max nesting depth (3) for COLUMN1")

        Args:
            mode: Creation mode - "create_sibling", "create_child", or "edit"
            parent_task: Parent task for child creation or sibling reference
            column: Column context (COLUMN1 or COLUMN2) used for nesting limit validation
            edit_task: Task to edit (for edit mode)
            **kwargs: Additional keyword arguments for ModalScreen

        Attributes:
            validation_error: Set to an error message if nesting constraints are violated,
                             None otherwise
        """
        super().__init__(**kwargs)
        self.mode = mode
        self.parent_task = parent_task
        self.column = column
        self.edit_task = edit_task
        self.validation_error: Optional[str] = None

        # Validate nesting constraints for child creation
        if mode == "create_child" and parent_task is not None:
            if not NestingRules.can_create_child(parent_task, column):
                max_depth = NestingRules.get_max_depth(column)
                self.validation_error = (
                    f"Cannot create child: Parent at level {parent_task.level} "
                    f"has reached max nesting depth ({max_depth}) for {column.value}"
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

            # Buttons
            with Container(classes="button-container"):
                yield Button("Save [Enter]", variant="success", id="save-button", classes="save-button")
                yield Button("Cancel [Esc]", variant="error", id="cancel-button", classes="cancel-button")

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
        the parent task and calculated child level. It uses NestingRules to determine the
        appropriate level for the new child task based on the parent's level and column.

        Nesting Limit Validation:
            - Calls NestingRules.get_allowed_child_level() to determine the child's level
            - This method respects column-specific nesting limits already validated in __init__
            - The child level is always parent.level + 1 if child creation is allowed
            - If nesting limits were exceeded, a validation_error would be set in __init__
              and this method would not be called

        Returns:
            Context string showing parent task and child level (e.g., "Creating child under:
            Parent Task...\nNew task level: 2 | Column: COLUMN1") or empty string if
            parent_task is not set
        """
        if not self.parent_task:
            return ""

        child_level = NestingRules.get_allowed_child_level(self.parent_task, self.column)
        return (
            f"Creating child under: {self.parent_task.title[:30]}...\n"
            f"New task level: {child_level} | Column: {self.column.value}"
        )

    def _get_sibling_context_text(self) -> str:
        """Get context text for sibling creation.

        This helper method generates context information for sibling task creation. A sibling
        is created at the same nesting level as the reference parent_task (or at level 0 if
        no parent is specified, indicating a top-level task).

        Validation Considerations:
            - No explicit nesting limit check is performed for sibling creation
            - Top-level tasks (level 0) have no nesting depth constraints
            - Column information is always displayed to help users understand the context
            - Sibling creation does not require parent_task to be set

        Returns:
            Context string showing sibling level and column (e.g., "Creating sibling at
            level: 1 | Column: COLUMN1") or "Creating new top-level task | Column: COLUMN1"
            if no parent task is specified
        """
        if self.parent_task:
            return (
                f"Creating sibling at level: {self.parent_task.level} | "
                f"Column: {self.column.value}"
            )
        return f"Creating new top-level task | Column: {self.column.value}"

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

        Validation Error Handling:
            - Checks self.validation_error set during __init__ (nesting limit violations)
            - Disables save button to prevent users from submitting invalid data
            - Logs the validation error for debugging purposes
            - The error message is displayed to the user in the modal's context area
        """
        logger.info(f"Task modal opened in {self.mode} mode")

        # Focus the title input
        title_input = self.query_one("#title-input", Input)
        title_input.focus()

        # Disable save button if there's a validation error
        if self.validation_error:
            logger.debug(f"Validation error in modal: {self.validation_error}")
            save_button = self.query_one("#save-button", Button)
            save_button.disabled = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: The button pressed event
        """
        if event.button.id == "save-button":
            self.action_save()
        elif event.button.id == "cancel-button":
            self.action_cancel()

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

        title = title_input.value.strip()
        notes = notes_input.text.strip() if notes_input.text else None

        # Validate title
        if not title:
            logger.debug("Save cancelled: empty title")
            # Show error - could add a validation label here
            return

        logger.info(f"Task {self.mode} saved: {title[:50]}")

        # Post TaskCreated message
        self.post_message(
            self.TaskCreated(
                title=title,
                notes=notes,
                mode=self.mode,
                parent_task=self.parent_task,
                column=self.column,
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
        logger.info("Task modal cancelled")
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
            self.action_save()

    class TaskCreated(Message):
        """Message emitted when a task is created/edited."""

        def __init__(
            self,
            title: str,
            notes: Optional[str],
            mode: str,
            parent_task: Optional[Task],
            column: Column,
            edit_task: Optional[Task] = None,
        ) -> None:
            """Initialize the TaskCreated message.

            Args:
                title: Task title
                notes: Optional task notes
                mode: Creation mode
                parent_task: Parent task reference
                column: Column context
                edit_task: Task being edited (if any)
            """
            super().__init__()
            self.title = title
            self.notes = notes
            self.mode = mode
            self.parent_task = parent_task
            self.column = column
            self.edit_task = edit_task

    class TaskCancelled(Message):
        """Message emitted when task creation is cancelled."""
        pass
