"""ListBar widget for displaying and switching between task lists.

This module provides the ListBar widget which renders a horizontal bar showing
all available task lists with:
- Active list highlighting
- Completion percentage display
- Number key shortcuts (1-3)
- One Monokai theme styling

The ListBar manages tab creation through the _create_all_tabs() and
_create_tab_for_list() helper methods, which handle the creation of ListTab
widgets for each task list. List switching is accomplished through the
select_list_by_number() method (keyboard shortcuts) and set_active_list()
method (programmatic selection). The active list state is tracked reactively,
automatically updating tab highlighting when the active list changes.
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
from taskui.logging_config import get_logger
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

# Initialize logger for this module
logger = get_logger(__name__)


class ListTab(Widget):
    """A single list tab widget displaying a task list.

    This widget represents a single task list as a tab in the ListBar. It displays
    the list name, completion percentage, keyboard shortcut number, and is
    highlighted when active.

    The tab's appearance changes based on:
    - The active state (highlighted with bold primary color when active)
    - Hover state (applies selection background with opacity)
    - Whether it's the last tab (controls separator rendering)

    The active state is reactive, so when the parent ListBar updates the active
    list, this tab automatically updates its styling via the watch_active() method.
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
        """Render the list tab with list information and completion status.

        This method generates the visual representation of the tab, including:
        - The keyboard shortcut number in brackets (e.g., "[1]")
        - The list name, styled in bold primary color if active
        - The completion percentage (only if there are tasks)
        - A separator pipe character (except for the last tab)

        The completion percentage is shown in yellow if incomplete (<100%) and
        in the primary color if complete (100%).

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
        """React to active state changes and update styling.

        This is a Textual reactive watcher that is automatically called whenever
        the active property changes. It adds or removes the "active" CSS class
        based on the new active state.

        When active = True:
        - The "active" class is added
        - The render() method will display the list name in bold primary color
        - The parent ListBar's reactive watcher triggers this when setting active

        When active = False:
        - The "active" class is removed
        - The render() method will display the list name in normal foreground color

        Args:
            active: New active state
        """
        if active:
            self.add_class("active")
        else:
            self.remove_class("active")


class ListBar(Horizontal):
    """Horizontal bar displaying all task lists with interactive switching.

    This widget renders a horizontal container showing all available task lists,
    each represented as a ListTab widget. The active list is highlighted with
    a special style to indicate which list is currently selected.

    Tab Creation and Management:
    - Tabs are created lazily in the compose() method using _create_all_tabs()
    - Each tab is created via _create_tab_for_list() helper for consistent setup
    - Tabs are refreshed when the list of tasks changes via refresh_tabs()
    - The is_last flag is set per-tab to control separator rendering

    List Selection and Switching:
    - Active list tracking via the reactive active_list_id property
    - Keyboard shortcuts via select_list_by_number() for number keys (1-3)
    - Programmatic selection via set_active_list() for direct list activation
    - The watch_active_list_id() reactive watcher automatically updates tab
      highlighting when the active list changes
    - ListSelected message emitted when a list is selected for other widgets

    Attributes:
        lists: The current list of TaskList models being displayed
        tabs: List of ListTab widgets created and managed by this bar
        active_list_id: UUID of the currently active list (reactive property)
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

    def _create_tab_for_list(
        self,
        task_list: TaskList,
        shortcut_number: int,
        is_last: bool
    ) -> ListTab:
        """Create a ListTab widget for a task list.

        This helper method extracts the logic for creating a single ListTab widget,
        ensuring consistent configuration across all tabs. It handles the
        initialization of the tab with the correct active state based on whether
        the task_list matches the current active_list_id.

        The created tab is configured with:
        - The task_list model to display
        - The shortcut_number for keyboard shortcuts (1-3)
        - The active state matching current selection
        - The is_last flag for controlling separator rendering

        Args:
            task_list: Task list to create tab for
            shortcut_number: Keyboard shortcut number (1-3), mapped to keys 1-3
            is_last: Whether this is the last tab (affects separator rendering)

        Returns:
            Configured ListTab widget ready to be mounted in the ListBar
        """
        is_active = task_list.id == self.active_list_id
        return ListTab(
            task_list=task_list,
            shortcut_number=shortcut_number,
            is_active=is_active,
            is_last=is_last
        )

    def _create_all_tabs(self) -> List[ListTab]:
        """Create ListTab widgets for all lists.

        This helper method orchestrates the creation of all tabs for the current
        list of task lists. It iterates through self.lists, creating a ListTab
        for each list using _create_tab_for_list(). This method is called during
        composition and when refreshing the tab display.

        The method maintains consistent shortcut numbering (starting from 1) and
        correctly identifies the last tab for separator rendering. This separation
        of concerns makes it easier to update the tab creation logic in one place.

        Returns:
            List of ListTab widgets in the same order as self.lists
        """
        tabs = []
        total_lists = len(self.lists)

        for idx, task_list in enumerate(self.lists, start=1):
            is_last = idx == total_lists
            tab = self._create_tab_for_list(task_list, idx, is_last)
            tabs.append(tab)

        return tabs

    def compose(self):
        """Compose the list bar with list tabs.

        This method is called by Textual during widget initialization to populate
        the ListBar with its child widgets. It clears any existing tabs and creates
        new tabs for all task lists using _create_all_tabs(), then yields them to
        be mounted in the widget tree.

        This lazy initialization approach ensures tabs are created with the correct
        active state based on the current active_list_id.

        Yields:
            ListTab widgets for each list in order
        """
        self.tabs.clear()
        self.tabs = self._create_all_tabs()
        yield from self.tabs

    def update_lists(self, lists: List[TaskList]) -> None:
        """Update the displayed lists and refresh tab display.

        This method is called when the list of task lists has changed (e.g., when
        lists are added, removed, or their data is updated). It updates the internal
        self.lists reference and calls refresh_tabs() to rebuild all tabs with the
        new data.

        Args:
            lists: New list of TaskList models
        """
        logger.debug(f"ListBar: Updating lists, count={len(lists)}")
        self.lists = lists
        self.refresh_tabs()

    def refresh_tabs(self) -> None:
        """Refresh all tabs to reflect current data.

        This method is called when the task lists have been updated and the tab
        display needs to be refreshed. It removes all existing child tabs from
        the widget tree, clears the tabs list, creates new tabs via _create_all_tabs(),
        and mounts them back into the widget tree.

        This approach ensures:
        - All tabs are recreated with fresh data from the task lists
        - The active state matches the current active_list_id
        - The display is fully synchronized with the underlying data
        - No orphaned widgets remain in the widget tree
        """
        logger.debug(f"ListBar: Refreshing tabs, list_count={len(self.lists)}, active_list_id={self.active_list_id}")

        # Remove existing tabs
        for child in list(self.children):
            child.remove()

        # Create and mount new tabs
        self.tabs.clear()
        self.tabs = self._create_all_tabs()

        for tab in self.tabs:
            self.mount(tab)

        logger.debug(f"ListBar: Tabs refreshed, tab_count={len(self.tabs)}")

    def set_active_list(self, list_id: UUID) -> None:
        """Set the active list and update tab highlighting.

        This method handles programmatic list selection. It updates the
        active_list_id reactive property, which automatically triggers the
        watch_active_list_id() reactive watcher to update all tab highlighting.

        Additionally, this method finds the matching task list by UUID and emits
        the ListSelected message to notify other widgets of the selection change.

        The reactive property update ensures that:
        - All tabs are updated to reflect the new active state
        - The active tab is highlighted with the active style class
        - Inactive tabs have the active class removed

        Args:
            list_id: UUID of the list to make active
        """
        # Find and emit the selected list
        list_name = None
        for task_list in self.lists:
            if task_list.id == list_id:
                list_name = task_list.name
                logger.info(f"ListBar: Setting active list '{list_name}' (id={list_id})")
                self.post_message(
                    self.ListSelected(list_id=list_id, list_name=task_list.name)
                )
                break

        if not list_name:
            logger.warning(f"ListBar: Attempted to set active list with unknown id={list_id}")

        self.active_list_id = list_id
        # Note: watch_active_list_id() will automatically update tab highlighting

    def select_list_by_number(self, number: int) -> bool:
        """Select a list by its shortcut number (1-3).

        This method handles keyboard shortcut-based list selection. When the user
        presses a number key (1-3), this method is called to switch to the
        corresponding list. It validates that the number is within the valid range
        (1 to the number of available lists).

        If the number is valid, the method calls set_active_list() to switch to
        the selected list and emit the ListSelected message.

        Args:
            number: The shortcut number (1-3), typically from keyboard input

        Returns:
            True if list was successfully selected, False if number is out of range
            or there are no lists available
        """
        if 1 <= number <= len(self.lists):
            selected_list = self.lists[number - 1]
            logger.debug(f"ListBar: Selected list by shortcut [{number}]: '{selected_list.name}' (id={selected_list.id})")
            self.set_active_list(selected_list.id)
            return True
        else:
            logger.warning(f"ListBar: Invalid list number {number}, available lists: {len(self.lists)}")
            return False

    def watch_active_list_id(self, list_id: Optional[UUID]) -> None:
        """React to active list ID changes and update tab highlighting.

        This is a Textual reactive watcher that is automatically called whenever
        the active_list_id property changes. It updates the active state of all
        tabs to match the current active_list_id, ensuring visual consistency.

        The watcher iterates through all tabs and:
        - Sets tab.active = True only for the tab matching the new active list_id
        - Sets tab.active = False for all other tabs

        This mechanism enables reactive updates where tab highlighting is
        automatically synchronized with the active list state, without requiring
        manual updates throughout the codebase. Each tab's watch_active() method
        handles adding/removing the "active" CSS class for styling.

        Args:
            list_id: New active list ID (None for no active list)
        """
        logger.debug(f"ListBar: Active list ID changed to {list_id}, updating {len(self.tabs)} tabs")

        if list_id:
            active_count = 0
            for tab in self.tabs:
                tab.active = (tab.list_id == list_id)
                if tab.active:
                    active_count += 1

            logger.debug(f"ListBar: Tab highlighting updated, active_tabs={active_count}")
