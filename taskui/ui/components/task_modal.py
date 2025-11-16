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

        Args:
            mode: Creation mode - "create_sibling", "create_child", or "edit"
            parent_task: Parent task for child creation or sibling reference
            column: Column context (COLUMN1 or COLUMN2)
            edit_task: Task to edit (for edit mode)
            **kwargs: Additional keyword arguments for ModalScreen
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

    def _get_context_text(self) -> str:
        """Get the context information text.

        Returns:
            Context description string
        """
        if self.validation_error:
            return ""

        if self.mode == "edit":
            return f"Editing: {self.edit_task.title[:40]}..." if self.edit_task else ""

        if self.mode == "create_child" and self.parent_task:
            child_level = NestingRules.get_allowed_child_level(self.parent_task, self.column)
            return (
                f"Creating child under: {self.parent_task.title[:30]}...\n"
                f"New task level: {child_level} | Column: {self.column.value}"
            )

        if self.mode == "create_sibling" and self.parent_task:
            return (
                f"Creating sibling at level: {self.parent_task.level} | "
                f"Column: {self.column.value}"
            )

        return f"Creating new top-level task | Column: {self.column.value}"

    def on_mount(self) -> None:
        """Called when the modal is mounted."""
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
        """Save the task and dismiss the modal."""
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
        """Cancel and dismiss the modal."""
        logger.info("Task modal cancelled")
        # Post TaskCancelled message
        self.post_message(self.TaskCancelled())
        # Dismiss modal
        self.dismiss()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input fields.

        Args:
            event: The input submitted event
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
