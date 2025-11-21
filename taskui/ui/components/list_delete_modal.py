"""List deletion modal for TaskUI.

This module provides a modal dialog for deleting task lists with two options:
1. Migrate tasks to another list
2. Delete all tasks (cascade)

Features:
- Warning message showing task count
- List selection for migration
- Safety confirmations
- Keyboard shortcuts
"""

from typing import List, Optional
from uuid import UUID

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, RadioButton, RadioSet, Select, Static
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
    RED,
)

logger = get_logger(__name__)


class ListDeleteModal(ModalScreen):
    """Modal screen for deleting task lists with multiple options.

    Displays options for:
    - Migrating tasks to another list
    - Deleting all tasks (cascade)

    Messages:
        DeleteConfirmed: Emitted when deletion is confirmed with selected option
        DeleteCancelled: Emitted when deletion is cancelled
    """

    DEFAULT_CSS = f"""
    ListDeleteModal {{
        align: center middle;
        background: {MODAL_OVERLAY_BG};
    }}

    ListDeleteModal > Container {{
        width: 75;
        height: auto;
        background: {BACKGROUND};
        border: thick {RED};
        padding: 1 2;
    }}

    ListDeleteModal .modal-header {{
        width: 100%;
        height: 3;
        content-align: center middle;
        text-style: bold;
        color: {RED};
        border-bottom: solid {BORDER};
        margin-bottom: 1;
    }}

    ListDeleteModal .warning-box {{
        width: 100%;
        height: auto;
        background: {BORDER};
        color: {ORANGE};
        text-align: center;
        padding: 1;
        margin-bottom: 1;
        border: solid {ORANGE};
    }}

    ListDeleteModal .info-text {{
        width: 100%;
        height: auto;
        color: {FOREGROUND};
        text-align: center;
        margin-bottom: 1;
        padding: 0 1;
    }}

    ListDeleteModal .option-container {{
        width: 100%;
        height: auto;
        background: {BORDER};
        padding: 1;
        margin-bottom: 1;
        border: solid {SELECTION};
    }}

    ListDeleteModal RadioSet {{
        width: 100%;
        height: auto;
        background: {BORDER};
        padding: 0 1;
    }}

    ListDeleteModal RadioButton {{
        width: 100%;
        height: auto;
        margin: 1 0;
        color: {FOREGROUND};
    }}

    ListDeleteModal RadioButton:focus {{
        color: {LEVEL_0_COLOR};
    }}

    ListDeleteModal .option-label {{
        width: 100%;
        height: auto;
        color: {LEVEL_1_COLOR};
        margin-left: 2;
        text-style: italic;
    }}

    ListDeleteModal Select {{
        width: 100%;
        margin: 1 2;
        background: {BACKGROUND};
        color: {FOREGROUND};
        border: solid {SELECTION};
    }}

    ListDeleteModal Select:focus {{
        border: solid {LEVEL_0_COLOR};
    }}

    ListDeleteModal .button-container {{
        width: 100%;
        height: 3;
        align: center middle;
        margin-top: 1;
        layout: horizontal;
    }}

    ListDeleteModal Button {{
        margin: 0 1;
        min-width: 15;
        background: {SELECTION};
        color: {FOREGROUND};
        border: solid {BORDER};
    }}

    ListDeleteModal Button:hover {{
        background: {BORDER};
        border: solid {LEVEL_0_COLOR};
    }}

    ListDeleteModal Button.confirm-button {{
        border: solid {RED};
    }}

    ListDeleteModal Button.confirm-button:hover {{
        background: {RED};
        color: {BACKGROUND};
    }}

    ListDeleteModal Button.cancel-button {{
        border: solid {LEVEL_1_COLOR};
    }}

    ListDeleteModal Button.cancel-button:hover {{
        background: {LEVEL_1_COLOR};
        color: {BACKGROUND};
    }}
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    def __init__(
        self,
        list_to_delete: TaskList,
        available_lists: List[TaskList],
        **kwargs
    ) -> None:
        """Initialize the list deletion modal.

        Args:
            list_to_delete: The list that will be deleted
            available_lists: Other lists available for task migration
            **kwargs: Additional keyword arguments for ModalScreen
        """
        super().__init__(**kwargs)
        self.list_to_delete = list_to_delete
        self.available_lists = [lst for lst in available_lists if lst.id != list_to_delete.id]
        self.selected_option = "migrate"  # Default option
        self.selected_target_list: Optional[UUID] = None

        # Set default target list if available
        if self.available_lists:
            self.selected_target_list = self.available_lists[0].id

    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
        with Container():
            # Header
            yield Static("🗑️ Delete List", classes="modal-header")

            # Warning box
            task_count = self.list_to_delete._task_count
            completed_count = self.list_to_delete._completed_count
            yield Static(
                f"⚠️ WARNING ⚠️\n"
                f"You are about to delete '{self.list_to_delete.name}'\n"
                f"This list contains {task_count} task(s) ({completed_count} completed)",
                classes="warning-box"
            )

            # Info text
            yield Static(
                "Choose how to handle the tasks in this list:",
                classes="info-text"
            )

            # Options
            with Container(classes="option-container"):
                with RadioSet(id="delete-options"):
                    # Option 1: Migrate
                    yield RadioButton(
                        "📦 Migrate all tasks to another list",
                        value=True,
                        id="option-migrate"
                    )
                    if self.available_lists:
                        yield Label(
                            "Tasks will be moved to the selected list",
                            classes="option-label"
                        )
                        # List selector
                        options = [(f"{lst.name} ({lst._task_count} tasks)", lst.id) for lst in self.available_lists]
                        yield Select(
                            options=options,
                            prompt="Select target list",
                            id="target-list-select",
                            value=self.selected_target_list
                        )
                    else:
                        yield Label(
                            "⚠ No other lists available for migration",
                            classes="option-label"
                        )

                    # Option 2: Delete all
                    yield RadioButton(
                        "💥 Delete all tasks (cascade delete)",
                        id="option-delete-all"
                    )
                    yield Label(
                        "⚠ All tasks will be permanently deleted!",
                        classes="option-label"
                    )

            # Buttons
            with Container(classes="button-container"):
                yield Button("Confirm Delete", variant="error", id="confirm-button", classes="confirm-button")
                yield Button("Cancel [Esc]", variant="primary", id="cancel-button", classes="cancel-button")

    def on_mount(self) -> None:
        """Called when the modal is mounted."""
        logger.info(
            f"ListDeleteModal: Opened for list '{self.list_to_delete.name}' "
            f"(id={self.list_to_delete.id}, tasks={self.list_to_delete._task_count})"
        )

        # Disable migrate option if no other lists available
        if not self.available_lists:
            migrate_button = self.query_one("#option-migrate", RadioButton)
            migrate_button.disabled = True

            # Select delete_all option instead
            delete_all_button = self.query_one("#option-delete-all", RadioButton)
            delete_all_button.value = True
            self.selected_option = "delete_all"

            # Disable target list selector
            target_select = self.query_one("#target-list-select", Select)
            target_select.disabled = True

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle radio button selection changes."""
        pressed_id = event.pressed.id

        if pressed_id == "option-migrate":
            self.selected_option = "migrate"
            # Enable list selector
            if self.available_lists:
                target_select = self.query_one("#target-list-select", Select)
                target_select.disabled = False
        elif pressed_id == "option-delete-all":
            self.selected_option = "delete_all"
            # Disable list selector
            target_select = self.query_one("#target-list-select", Select)
            target_select.disabled = True

        logger.debug(f"ListDeleteModal: Option changed to '{self.selected_option}'")

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle target list selection changes."""
        if event.select.id == "target-list-select":
            self.selected_target_list = event.value
            logger.debug(f"ListDeleteModal: Target list changed to {self.selected_target_list}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        logger.debug(f"ListDeleteModal: Button pressed - {event.button.id}")
        if event.button.id == "confirm-button":
            self.action_confirm()
        elif event.button.id == "cancel-button":
            self.action_cancel()

    def action_confirm(self) -> None:
        """Confirm deletion and dismiss the modal."""
        # Validate migration option
        if self.selected_option == "migrate":
            if not self.available_lists:
                logger.warning("ListDeleteModal: Cannot migrate - no target lists available")
                return
            if self.selected_target_list is None:
                logger.warning("ListDeleteModal: Cannot migrate - no target list selected")
                return

        logger.info(
            f"ListDeleteModal: Delete confirmed - "
            f"option='{self.selected_option}', "
            f"target_list={self.selected_target_list if self.selected_option == 'migrate' else None}"
        )

        # Post DeleteConfirmed message
        self.post_message(
            self.DeleteConfirmed(
                list_to_delete=self.list_to_delete,
                option=self.selected_option,
                target_list_id=self.selected_target_list if self.selected_option == "migrate" else None,
            )
        )

        # Dismiss modal
        self.dismiss()

    def action_cancel(self) -> None:
        """Cancel and dismiss the modal."""
        logger.info(f"ListDeleteModal: Cancelled")
        self.post_message(self.DeleteCancelled())
        self.dismiss()

    class DeleteConfirmed(Message):
        """Message emitted when deletion is confirmed."""

        def __init__(
            self,
            list_to_delete: TaskList,
            option: str,
            target_list_id: Optional[UUID] = None,
        ) -> None:
            """Initialize the DeleteConfirmed message.

            Args:
                list_to_delete: The list being deleted
                option: Deletion option ("migrate" or "delete_all")
                target_list_id: Target list for migration (if applicable)
            """
            super().__init__()
            self.list_to_delete = list_to_delete
            self.option = option
            self.target_list_id = target_list_id

    class DeleteCancelled(Message):
        """Message emitted when deletion is cancelled."""
        pass
