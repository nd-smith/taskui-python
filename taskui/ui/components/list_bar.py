"""ListBar widget for displaying and switching between task lists.

This module provides the ListBar widget which renders a horizontal bar showing
all available task lists with:
- Active list highlighting
- Completion percentage display
- Number key shortcuts (1-3)
- One Monokai theme styling
"""

from typing import List, Optional
from uuid import UUID

from textual.widget import Widget
from textual.reactive import reactive
from textual.message import Message
from textual.containers import Horizontal
from rich.text import Text
from rich.console import RenderableType

from taskui.models import TaskList
from taskui.ui.theme import (
    LEVEL_0_COLOR,
    FOREGROUND,
    SELECTION,
    BACKGROUND,
    COMMENT,
    YELLOW,
    BORDER,
    HOVER_OPACITY,
    with_alpha,
)


class ListTab(Widget):
    """A single list tab widget displaying a task list.

    Shows the list name, completion percentage, and highlights when active.
    """

    DEFAULT_CSS = f"""
    ListTab {{
        height: 1;
        width: auto;
        padding: 0 1;
        background: transparent;
    }}

    ListTab:hover {{
        background: {with_alpha(SELECTION, HOVER_OPACITY)};
    }}

    ListTab.active {{
        background: transparent;
    }}
    """

    # Reactive properties
    active: reactive[bool] = reactive(False)
    list_id: reactive[Optional[UUID]] = reactive(None)

    def __init__(
        self,
        task_list: TaskList,
        shortcut_number: int,
        is_active: bool = False,
        is_last: bool = False,
        **kwargs
    ) -> None:
        """Initialize a ListTab widget.

        Args:
            task_list: The TaskList model to display
            shortcut_number: The number key shortcut (1-3)
            is_active: Whether this list is currently active
            is_last: Whether this is the last tab (for separator logic)
            **kwargs: Additional widget arguments
        """
        super().__init__(**kwargs)
        self.task_list = task_list
        self.shortcut_number = shortcut_number
        self.active = is_active
        self.is_last = is_last
        self.list_id = task_list.id

    def render(self) -> RenderableType:
        """Render the list tab.

        Returns:
            Rich Text object with formatted list information
        """
        text = Text()

        # Add shortcut number
        text.append(f"[{self.shortcut_number}] ", style=f"bold {COMMENT}")

        # Add list name
        name_style = f"bold {LEVEL_0_COLOR}" if self.active else FOREGROUND
        text.append(self.task_list.name, style=name_style)

        # Add completion percentage if there are tasks
        if self.task_list.task_count > 0:
            completion = self.task_list.completion_percentage
            percentage_color = YELLOW if completion < 100 else LEVEL_0_COLOR
            text.append(f" {completion:.0f}%", style=percentage_color)

        # Add separator if not the last tab
        if not self.is_last:
            text.append("  │  ", style=COMMENT)

        return text

    def watch_active(self, active: bool) -> None:
        """React to active state changes.

        Args:
            active: New active state
        """
        if active:
            self.add_class("active")
        else:
            self.remove_class("active")


class ListBar(Horizontal):
    """Horizontal bar displaying all task lists.

    Shows all available lists with the active one highlighted.
    Supports switching lists via number keys (1-3).
    """

    DEFAULT_CSS = f"""
    ListBar {{
        height: 2;
        width: 100%;
        background: {BACKGROUND};
        padding: 1 1 0 1;
        layout: horizontal;
        align: left middle;
    }}
    """

    # Reactive properties
    active_list_id: reactive[Optional[UUID]] = reactive(None)

    class ListSelected(Message):
        """Message emitted when a list is selected.

        Attributes:
            list_id: UUID of the selected list
            list_name: Name of the selected list
        """

        def __init__(self, list_id: UUID, list_name: str) -> None:
            super().__init__()
            self.list_id = list_id
            self.list_name = list_name

    def __init__(
        self,
        lists: List[TaskList],
        active_list_id: Optional[UUID] = None,
        **kwargs
    ) -> None:
        """Initialize the ListBar.

        Args:
            lists: List of TaskList models to display
            active_list_id: UUID of the currently active list
            **kwargs: Additional widget arguments
        """
        super().__init__(**kwargs)
        self.lists = lists
        self.tabs: List[ListTab] = []  # Initialize tabs list first
        self.active_list_id = active_list_id or (lists[0].id if lists else None)

    def compose(self):
        """Compose the list bar with list tabs.

        Yields:
            ListTab widgets for each list
        """
        # Clear tabs list before composing to avoid duplicates on recompose
        self.tabs.clear()

        total_lists = len(self.lists)
        for idx, task_list in enumerate(self.lists, start=1):
            is_active = task_list.id == self.active_list_id
            is_last = idx == total_lists
            tab = ListTab(
                task_list=task_list,
                shortcut_number=idx,
                is_active=is_active,
                is_last=is_last
            )
            self.tabs.append(tab)
            yield tab

    def update_lists(self, lists: List[TaskList]) -> None:
        """Update the displayed lists.

        Args:
            lists: New list of TaskList models
        """
        self.lists = lists
        self.refresh_tabs()

    def refresh_tabs(self) -> None:
        """Refresh all tabs to reflect current data."""
        # Remove all existing tabs
        for child in list(self.children):
            child.remove()

        # Clear tabs list
        self.tabs.clear()

        # Create and mount new tabs
        total_lists = len(self.lists)
        for idx, task_list in enumerate(self.lists, start=1):
            is_active = task_list.id == self.active_list_id
            is_last = idx == total_lists
            tab = ListTab(
                task_list=task_list,
                shortcut_number=idx,
                is_active=is_active,
                is_last=is_last
            )
            self.tabs.append(tab)
            self.mount(tab)

    def set_active_list(self, list_id: UUID) -> None:
        """Set the active list and update tab highlighting.

        Args:
            list_id: UUID of the list to make active
        """
        self.active_list_id = list_id
        # Note: watch_active_list_id() will automatically update tab highlighting

        # Find and emit the selected list
        for task_list in self.lists:
            if task_list.id == list_id:
                self.post_message(
                    self.ListSelected(list_id=list_id, list_name=task_list.name)
                )
                break

    def select_list_by_number(self, number: int) -> bool:
        """Select a list by its shortcut number (1-3).

        Args:
            number: The shortcut number (1-3)

        Returns:
            True if list was selected, False if number is out of range
        """
        if 1 <= number <= len(self.lists):
            selected_list = self.lists[number - 1]
            self.set_active_list(selected_list.id)
            return True
        return False

    def watch_active_list_id(self, list_id: Optional[UUID]) -> None:
        """React to active list ID changes.

        Args:
            list_id: New active list ID
        """
        if list_id:
            for tab in self.tabs:
                tab.active = (tab.list_id == list_id)
