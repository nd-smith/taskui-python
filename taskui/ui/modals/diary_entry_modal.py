"""Diary entry creation modal for TaskUI.

This module provides a modal dialog for creating diary/journal entries with:
- TextArea for content input (1-2000 characters)
- Character counter showing usage (e.g., "150/2000")
- Save button to create entry (disabled if content too short)
- Cancel button to close without saving
- Keyboard shortcuts (Escape to cancel, Ctrl+S to save)
"""

from typing import Optional
from uuid import UUID

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static, TextArea
from textual.message import Message
from textual.binding import Binding

from taskui.logging_config import get_logger
from taskui.models import DiaryEntry
from taskui.ui.base_styles import MODAL_BASE_CSS, BUTTON_BASE_CSS
from taskui.ui.theme import LEVEL_1_COLOR, ORANGE, COMMENT

logger = get_logger(__name__)


class DiaryEntryModal(ModalScreen):
    """Modal screen for creating diary entries.

    Displays a form with:
    - Content text area (required, 1-2000 characters)
    - Character counter
    - Action buttons (Save/Cancel)

    The modal is typically triggered by the 'd' hotkey and allows quick
    journal entry creation for the selected task.

    Messages:
        EntrySaved: Emitted when an entry is successfully created
        EntryCancelled: Emitted when the modal is cancelled
    """

    DEFAULT_CSS = MODAL_BASE_CSS + BUTTON_BASE_CSS + f"""
    DiaryEntryModal > Container {{
        width: 80;
        height: auto;
    }}

    DiaryEntryModal .modal-header {{
        width: 100%;
        height: 3;
        content-align: center middle;
        margin-bottom: 1;
    }}

    DiaryEntryModal .context-info {{
        width: 100%;
        height: auto;
        color: {LEVEL_1_COLOR};
        text-align: center;
        margin-bottom: 1;
        padding: 0 1;
    }}

    DiaryEntryModal .field-label {{
        width: 100%;
        height: 1;
        margin-top: 1;
    }}

    DiaryEntryModal TextArea {{
        width: 100%;
        height: 12;
        margin-bottom: 1;
    }}

    DiaryEntryModal .char-counter {{
        width: 100%;
        height: 1;
        color: {COMMENT};
        text-align: right;
        margin-bottom: 1;
    }}

    DiaryEntryModal .char-counter.warning {{
        color: {ORANGE};
        text-style: bold;
    }}

    DiaryEntryModal .button-container {{
        width: 100%;
        height: 3;
        align: center middle;
        margin-top: 1;
        layout: horizontal;
    }}

    DiaryEntryModal Button {{
        margin: 0 1;
        min-width: 15;
    }}
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
        Binding("ctrl+s", "save", "Save", priority=True),
    ]

    def __init__(self, task_id: UUID, **kwargs) -> None:
        """Initialize the diary entry modal.

        Args:
            task_id: UUID of the task this entry belongs to
            **kwargs: Additional keyword arguments for ModalScreen
        """
        super().__init__(**kwargs)
        self.task_id = task_id
        self.min_length = 1
        self.max_length = 2000

    def compose(self) -> ComposeResult:
        """Compose the modal layout.

        Yields:
            Widgets that make up the modal dialog
        """
        with Container():
            # Header
            yield Static("📝 New Diary Entry", classes="modal-header")

            # Context info
            yield Static(
                "Quick journal entry for this task",
                classes="context-info"
            )

            # Content field
            yield Label("Entry Content:", classes="field-label")
            yield TextArea(
                text="",
                id="content-input"
            )

            # Character counter
            yield Static("0/2000", id="char-counter", classes="char-counter")

            # Buttons
            with Container(classes="button-container"):
                yield Button("Save [Ctrl+S]", id="save-button", classes="success", disabled=True)
                yield Button("Cancel [Esc]", id="cancel-button", classes="error")

    def on_mount(self) -> None:
        """Called when the modal is mounted."""
        logger.info(f"DiaryEntryModal: Opened for task_id={self.task_id}")

        # Focus the content input
        content_input = self.query_one("#content-input", TextArea)
        content_input.focus()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Handle text area changes to update character counter and save button state.

        Args:
            event: The text area changed event
        """
        if event.text_area.id != "content-input":
            return

        content = event.text_area.text
        char_count = len(content)

        # Update character counter
        counter = self.query_one("#char-counter", Static)
        counter.update(f"{char_count}/{self.max_length}")

        # Update counter styling based on length
        if char_count > self.max_length * 0.9:  # Warning at 90%
            counter.add_class("warning")
        else:
            counter.remove_class("warning")

        # Enable/disable save button based on content length
        save_button = self.query_one("#save-button", Button)
        save_button.disabled = char_count < self.min_length

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: The button pressed event
        """
        logger.debug(f"DiaryEntryModal: Button pressed - {event.button.id}")
        if event.button.id == "save-button":
            self.action_save()
        elif event.button.id == "cancel-button":
            self.action_cancel()

    def action_save(self) -> None:
        """Save the diary entry and dismiss the modal.

        Validates:
        - Content must be at least 1 character
        - Content must not exceed 2000 characters
        """
        content_input = self.query_one("#content-input", TextArea)
        content = content_input.text.strip()

        # Validate content length
        if len(content) < self.min_length:
            logger.warning(f"DiaryEntryModal: Save validation failed - content too short ({len(content)} chars)")
            return

        if len(content) > self.max_length:
            logger.warning(f"DiaryEntryModal: Save validation failed - content too long ({len(content)} chars)")
            return

        logger.info(
            f"DiaryEntryModal: Entry saved - task_id={self.task_id}, "
            f"content_length={len(content)}"
        )

        # Create the diary entry model
        entry = DiaryEntry(
            task_id=self.task_id,
            content=content
        )

        # Post EntrySaved message with the created entry
        self.post_message(self.EntrySaved(entry=entry))

        # Dismiss modal
        self.dismiss(entry)

    def action_cancel(self) -> None:
        """Cancel and dismiss the modal."""
        logger.info(f"DiaryEntryModal: Cancelled (task_id={self.task_id})")
        self.post_message(self.EntryCancelled())
        self.dismiss(None)

    class EntrySaved(Message):
        """Message emitted when a diary entry is created."""

        def __init__(self, entry: DiaryEntry) -> None:
            """Initialize the EntrySaved message.

            Args:
                entry: The created DiaryEntry instance
            """
            super().__init__()
            self.entry = entry

    class EntryCancelled(Message):
        """Message emitted when diary entry creation is cancelled."""
        pass
