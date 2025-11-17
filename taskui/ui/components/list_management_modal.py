"""List creation/editing modal for TaskUI.

This module provides a modal dialog for creating and editing task lists with:
- Name input (required)
- Validation for duplicate names
- Keyboard shortcuts (Enter to save, Escape to cancel)
"""

from typing import Optional
from uuid import UUID

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static
from textual.message import Message
from textual.binding import Binding

from taskui.logging_config import get_logger
from taskui.models import TaskList
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

logger = get_logger(__name__)


class ListManagementModal(ModalScreen):
    """Modal screen for creating or editing task lists.

    Displays a form with:
    - Name input field (required)
    - Action buttons (Save/Cancel)

    Messages:
        ListSaved: Emitted when a list is successfully created/edited
        ListCancelled: Emitted when the modal is cancelled
    """

    DEFAULT_CSS = f"""
    ListManagementModal {{
        align: center middle;
        background: {MODAL_OVERLAY_BG};
    }}

    ListManagementModal > Container {{
        width: 60;
        height: auto;
        background: {BACKGROUND};
        border: thick {LEVEL_0_COLOR};
        padding: 1 2;
    }}

    ListManagementModal .modal-header {{
        width: 100%;
        height: 3;
        content-align: center middle;
        text-style: bold;
        color: {LEVEL_0_COLOR};
        border-bottom: solid {BORDER};
        margin-bottom: 1;
    }}

    ListManagementModal .context-info {{
        width: 100%;
        height: auto;
        color: {LEVEL_1_COLOR};
        text-align: center;
        margin-bottom: 1;
        padding: 0 1;
    }}

    ListManagementModal .error-message {{
        width: 100%;
        height: auto;
        color: {ORANGE};
        text-align: center;
        margin-bottom: 1;
        padding: 0 1;
        text-style: bold;
    }}

    ListManagementModal .field-label {{
        width: 100%;
        height: 1;
        color: {FOREGROUND};
        margin-top: 1;
    }}

    ListManagementModal Input {{
        width: 100%;
        margin-bottom: 1;
        background: {BORDER};
        color: {FOREGROUND};
        border: solid {SELECTION};
    }}

    ListManagementModal Input:focus {{
        border: solid {LEVEL_0_COLOR};
    }}

    ListManagementModal .button-container {{
        width: 100%;
        height: 3;
        align: center middle;
        margin-top: 1;
        layout: horizontal;
    }}

    ListManagementModal Button {{
        margin: 0 1;
        min-width: 15;
        background: {SELECTION};
        color: {FOREGROUND};
        border: solid {BORDER};
    }}

    ListManagementModal Button:hover {{
        background: {BORDER};
        border: solid {LEVEL_0_COLOR};
    }}

    ListManagementModal Button.save-button {{
        border: solid {LEVEL_1_COLOR};
    }}

    ListManagementModal Button.save-button:hover {{
        background: {LEVEL_1_COLOR};
        color: {BACKGROUND};
    }}

    ListManagementModal Button.cancel-button {{
        border: solid {LEVEL_2_COLOR};
    }}

    ListManagementModal Button.cancel-button:hover {{
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
        mode: str = "create",
        edit_list: Optional[TaskList] = None,
        **kwargs
    ) -> None:
        """Initialize the list management modal.

        Args:
            mode: Creation mode - "create" or "edit"
            edit_list: List to edit (for edit mode)
            **kwargs: Additional keyword arguments for ModalScreen
        """
        super().__init__(**kwargs)
        self.mode = mode
        self.edit_list = edit_list
        self.validation_error: Optional[str] = None

    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
        with Container():
            # Header
            header_text = "✏️ Edit List" if self.mode == "edit" else "➕ Create New List"
            yield Static(header_text, classes="modal-header")

            # Context info
            if self.mode == "edit" and self.edit_list:
                yield Static(
                    f"Editing: {self.edit_list.name}",
                    classes="context-info"
                )

            # Error message if validation failed
            if self.validation_error:
                yield Static(f"⚠ {self.validation_error}", classes="error-message", id="error-message")

            # Name field
            yield Label("List Name:", classes="field-label")
            name_value = self.edit_list.name if self.edit_list else ""
            yield Input(
                placeholder="Enter list name...",
                value=name_value,
                id="name-input"
            )

            # Buttons
            with Container(classes="button-container"):
                yield Button("Save [Enter]", variant="success", id="save-button", classes="save-button")
                yield Button("Cancel [Esc]", variant="error", id="cancel-button", classes="cancel-button")

    def on_mount(self) -> None:
        """Called when the modal is mounted."""
        context_info = ""
        if self.mode == "edit" and self.edit_list:
            context_info = f", edit_list_id={self.edit_list.id}"

        logger.info(f"ListManagementModal: Opened in {self.mode} mode{context_info}")

        # Focus the name input
        name_input = self.query_one("#name-input", Input)
        name_input.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        logger.debug(f"ListManagementModal: Button pressed - {event.button.id}")
        if event.button.id == "save-button":
            self.action_save()
        elif event.button.id == "cancel-button":
            self.action_cancel()

    def action_save(self) -> None:
        """Save the list and dismiss the modal."""
        # Get input value
        name_input = self.query_one("#name-input", Input)
        name = name_input.value.strip()

        # Validate name
        if not name:
            logger.warning(f"ListManagementModal: Save validation failed - empty name (mode={self.mode})")
            self._show_error("List name cannot be empty")
            return

        logger.info(f"ListManagementModal: List {self.mode} saved - name='{name}'")

        # Post ListSaved message
        self.post_message(
            self.ListSaved(
                name=name,
                mode=self.mode,
                edit_list=self.edit_list,
            )
        )

        # Dismiss modal
        self.dismiss()

    def action_cancel(self) -> None:
        """Cancel and dismiss the modal."""
        logger.info(f"ListManagementModal: Cancelled (mode={self.mode})")
        self.post_message(self.ListCancelled())
        self.dismiss()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input field."""
        if event.input.id == "name-input":
            logger.debug("ListManagementModal: Enter pressed in name field, triggering save")
            self.action_save()

    def _show_error(self, message: str) -> None:
        """Show an error message in the modal."""
        self.validation_error = message

        # Try to update existing error message or log
        try:
            error_widget = self.query_one("#error-message", Static)
            error_widget.update(f"⚠ {message}")
        except Exception:
            # Error widget doesn't exist yet
            logger.warning(f"Validation error: {message}")

    class ListSaved(Message):
        """Message emitted when a list is created/edited."""

        def __init__(
            self,
            name: str,
            mode: str,
            edit_list: Optional[TaskList] = None,
        ) -> None:
            """Initialize the ListSaved message.

            Args:
                name: List name
                mode: Creation mode ("create" or "edit")
                edit_list: List being edited (if any)
            """
            super().__init__()
            self.name = name
            self.mode = mode
            self.edit_list = edit_list

    class ListCancelled(Message):
        """Message emitted when list creation/edit is cancelled."""
        pass
