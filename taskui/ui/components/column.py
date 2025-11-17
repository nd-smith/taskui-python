"""Column widget for displaying task lists with proper hierarchy.

This module provides the TaskColumn widget which manages and displays
a list of TaskItems with:
- Scrollable task list
- Focus/unfocus visual states
- Dynamic header updates
- Task selection management
- Proper hierarchy visualization
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime
import traceback

from textual.containers import VerticalScroll, Vertical
from textual.widget import Widget
from textual.reactive import reactive
from textual.message import Message
from textual.widgets import Static

from taskui.logging_config import get_logger
from taskui.models import Task
from taskui.ui.components.task_item import TaskItem
from taskui.ui.theme import (
    BORDER,
    SELECTION,
    FOREGROUND,
    LEVEL_0_COLOR,
    COMMENT,
)

# Initialize logger for this module
logger = get_logger(__name__)


class TaskColumn(Widget):
    """A column widget for displaying a hierarchical list of tasks.

    Manages:
    - Task list display with TaskItem widgets
    - Selection state and navigation
    - Focus/unfocus visual feedback
    - Dynamic header updates
    - Scrolling for large task lists
    """

    # Enable keyboard focus
    can_focus = True

    DEFAULT_CSS = f"""
    TaskColumn {{
        border: solid {BORDER};
        padding: 0 1;
        margin: 0 1;
    }}

    TaskColumn:focus {{
        border: thick {LEVEL_0_COLOR};
    }}

    TaskColumn .column-content {{
        width: 100%;
        height: 1fr;
        padding: 1 0;
    }}

    TaskColumn .empty-message {{
        width: 100%;
        height: 100%;
        color: {COMMENT};
        text-align: center;
        padding: 2;
    }}
    """

    # Reactive properties
    header_title: reactive[str] = reactive("Tasks")
    focused: reactive[bool] = reactive(False)
    selected_task_id: reactive[Optional[UUID]] = reactive(None)

    def __init__(
        self,
        column_id: str,
        title: str,
        empty_message: str = "No tasks",
        **kwargs
    ) -> None:
        """Initialize a TaskColumn widget.

        Args:
            column_id: Unique identifier for this column
            title: Column header title
            empty_message: Message to show when column is empty
            **kwargs: Additional keyword arguments for Widget
        """
        super().__init__(**kwargs)
        self.column_id = column_id
        self.header_title = title
        self.empty_message = empty_message
        self._tasks: List[Task] = []
        self._selected_index: int = 0

    def compose(self):
        """Compose the column layout.

        Yields:
            Widgets that make up the column
        """
        # Scrollable content area
        with VerticalScroll(classes="column-content", id=f"{self.column_id}-content"):
            yield Static(self.empty_message, classes="empty-message", id=f"{self.column_id}-empty")

    def set_tasks(self, tasks: List[Task], preserve_selection: bool = True) -> None:
        """Update the column with a new list of tasks.

        Args:
            tasks: List of Task objects to display
            preserve_selection: If True, try to maintain the current selection by task ID
        """
        logger.debug(f"{self.column_id}: set_tasks() called with {len(tasks)} tasks")

        # Check if tasks are identical (same IDs in same order AND same attributes)
        # to avoid unnecessary re-renders
        tasks_unchanged = (
            len(tasks) == len(self._tasks) and
            all(
                new.id == old.id and
                new._child_count == old._child_count and
                new._completed_child_count == old._completed_child_count and
                new.is_completed == old.is_completed
                for new, old in zip(tasks, self._tasks)
            )
        )

        if tasks_unchanged:
            logger.debug(f"{self.column_id}: Tasks unchanged, skipping re-render")
            return

        # Remember currently selected task ID
        previously_selected_id = None
        if preserve_selection and 0 <= self._selected_index < len(self._tasks):
            previously_selected_id = self._tasks[self._selected_index].id

        self._tasks = tasks

        # Try to find the previously selected task in the new list
        if preserve_selection and previously_selected_id:
            for i, task in enumerate(tasks):
                if task.id == previously_selected_id:
                    self._selected_index = i
                    break
            else:
                # Previously selected task not found, default to first task
                self._selected_index = 0 if tasks else -1
        else:
            # Not preserving selection, default to first task
            self._selected_index = 0 if tasks else -1

        self._render_tasks()

        # If column is focused and has tasks, trigger selection to update dependent columns
        # This ensures Column 2/3 update when switching lists
        if self.focused and self._tasks and 0 <= self._selected_index < len(self._tasks):
            # Use call_after_refresh to ensure widgets are mounted before selecting
            def trigger_selection():
                try:
                    self._update_selection(self._selected_index)
                except Exception:
                    # Widgets not ready yet, which is fine
                    pass
            self.call_after_refresh(trigger_selection)

    def _group_tasks_by_parent(self, tasks: List[Task]) -> dict:
        """Group tasks by parent ID for hierarchy visualization.

        Args:
            tasks: List of tasks to group

        Returns:
            Dictionary mapping parent_id (or "root") to list of children
        """
        parent_groups = {}
        for task in tasks:
            parent_id = task.parent_id or "root"
            if parent_id not in parent_groups:
                parent_groups[parent_id] = []
            parent_groups[parent_id].append(task)
        return parent_groups

    def _create_task_items(
        self,
        tasks: List[Task],
        parent_groups: dict,
        selected_index: int
    ) -> List[TaskItem]:
        """Create TaskItem widgets for a list of tasks.

        Args:
            tasks: Tasks to create items for
            parent_groups: Parent grouping for last-child detection
            selected_index: Currently selected task index

        Returns:
            List of TaskItem widgets ready to mount
        """
        task_items = []
        for i, task in enumerate(tasks):
            parent_id = task.parent_id or "root"
            siblings = parent_groups[parent_id]
            is_last_child = task == siblings[-1] if siblings else False

            task_item = TaskItem(
                task=task,
                is_last_child=is_last_child,
                id=f"task-{task.id}"
            )
            task_item.selected = (i == selected_index)
            task_items.append(task_item)

        return task_items

    def _render_tasks(self) -> None:
        """Render the task list with TaskItem widgets."""
        logger.debug(f"{self.column_id}: _render_tasks() called with {len(self._tasks)} tasks")
        try:
            content_container = self.query_one(f"#{self.column_id}-content", VerticalScroll)
            empty_message = self.query_one(f"#{self.column_id}-empty", Static)
        except Exception as e:
            # Container not yet mounted, skip rendering
            logger.debug(f"{self.column_id}: Container not ready - {e}")
            return

        # Handle empty state
        if not self._tasks:
            existing_items = list(content_container.query(TaskItem))
            for widget in existing_items:
                try:
                    widget.remove()
                except Exception:
                    pass
            empty_message.display = True
            return

        empty_message.display = False

        # Group tasks and create items
        parent_groups = self._group_tasks_by_parent(self._tasks)
        task_items = self._create_task_items(self._tasks, parent_groups, self._selected_index)

        # Mount widgets
        existing_items = list(content_container.query(TaskItem))
        if existing_items:
            content_container.remove_children(TaskItem)
            self.call_after_refresh(lambda: self._mount_task_items(content_container, task_items))
        else:
            self._mount_task_items(content_container, task_items)

    def _mount_task_items(self, container: VerticalScroll, task_items: List[TaskItem]) -> None:
        """Mount task items in container.

        Args:
            container: Container to mount items in
            task_items: List of TaskItem widgets to mount
        """
        logger.debug(f"{self.column_id}: Mounting {len(task_items)} task items")
        for task_item in task_items:
            try:
                container.mount(task_item)
            except Exception as e:
                logger.error(f"{self.column_id}: ERROR mounting task widget: {e}", exc_info=True)
        logger.debug(f"{self.column_id}: Mounting completed")

    def update_header(self, title: str) -> None:
        """Update the column header title.

        Args:
            title: New header title

        Note:
            This method is a no-op since column headers have been removed.
            Kept for backward compatibility.
        """
        self.header_title = title
        # No-op: headers removed for space efficiency

    def navigate_up(self) -> None:
        """Navigate to the previous task in the list."""
        if not self._tasks:
            return

        if self._selected_index > 0:
            self._update_selection(self._selected_index - 1)

    def navigate_down(self) -> None:
        """Navigate to the next task in the list."""
        if not self._tasks:
            return

        if self._selected_index < len(self._tasks) - 1:
            self._update_selection(self._selected_index + 1)

    def _update_selection(self, new_index: int) -> None:
        """Update the selected task index.

        Args:
            new_index: New selection index
        """
        logger.debug(f"{self.column_id}: _update_selection({new_index}), current_index={self._selected_index}, num_tasks={len(self._tasks)}")
        if not self._tasks or new_index < 0 or new_index >= len(self._tasks):
            logger.debug(f"{self.column_id}: Invalid selection index, skipping")
            return

        # Deselect old item
        if 0 <= self._selected_index < len(self._tasks):
            old_task_id = self._tasks[self._selected_index].id
            logger.debug(f"{self.column_id}: Deselecting old item task-{old_task_id}")
            old_item = self.query_one(f"#task-{old_task_id}", TaskItem)
            old_item.selected = False

        # Select new item
        self._selected_index = new_index
        new_task = self._tasks[new_index]
        logger.debug(f"{self.column_id}: Selecting new item task-{new_task.id}")
        new_item = self.query_one(f"#task-{new_task.id}", TaskItem)
        new_item.selected = True
        logger.debug(f"{self.column_id}: Selection updated successfully")

        # Update reactive property
        self.selected_task_id = new_task.id

        # Emit selection change message
        self.post_message(self.TaskSelected(new_task, self.column_id))

        # Scroll to selected item
        new_item.scroll_visible()

    def get_selected_task(self) -> Optional[Task]:
        """Get the currently selected task.

        Returns:
            Selected Task object or None if no selection
        """
        if 0 <= self._selected_index < len(self._tasks):
            return self._tasks[self._selected_index]
        return None

    def clear_selection(self) -> None:
        """Clear the current selection."""
        if 0 <= self._selected_index < len(self._tasks):
            task_id = self._tasks[self._selected_index].id
            task_item = self.query_one(f"#task-{task_id}", TaskItem)
            task_item.selected = False

        self._selected_index = -1
        self.selected_task_id = None

    def on_focus(self) -> None:
        """Handle focus event - ensure selection is properly activated."""
        logger.debug(f"{self.column_id}: on_focus() called, {len(self._tasks)} tasks, selected_index={self._selected_index}")
        self.focused = True
        self.add_class("focused")

        # Ensure we have a selection when focusing a column with tasks
        retry_count = [0]  # Use list to allow modification in nested function
        max_retries = 3

        def ensure_selection():
            logger.debug(f"{self.column_id}: ensure_selection() running (retry {retry_count[0]})")
            if not self._tasks:
                logger.debug(f"{self.column_id}: No tasks, skipping selection")
                return

            try:
                # Check if task widgets actually exist before trying to select
                first_task_id = f"task-{self._tasks[0].id}"
                try:
                    self.query_one(f"#{first_task_id}", TaskItem)
                except:
                    # Widgets not mounted yet, retry if under limit
                    if retry_count[0] < max_retries:
                        retry_count[0] += 1
                        logger.debug(f"{self.column_id}: Widgets not ready, will retry")
                        self.call_after_refresh(ensure_selection)
                    else:
                        logger.debug(f"{self.column_id}: Max retries reached, giving up on selection")
                    return

                if self._selected_index == -1:
                    # No selection, auto-select first task
                    logger.debug(f"{self.column_id}: Auto-selecting first task")
                    self._update_selection(0)
                elif 0 <= self._selected_index < len(self._tasks):
                    # Valid index exists - always trigger to ensure TaskSelected message is sent
                    # This is important for Column 2 which needs to trigger Column 3 detail view
                    logger.debug(f"{self.column_id}: Triggering selection for index {self._selected_index}")
                    self._update_selection(self._selected_index)
            except Exception as e:
                # Unexpected error
                logger.error(f"{self.column_id}: Exception in ensure_selection", exc_info=True)

        # Defer to ensure widgets are mounted
        self.call_after_refresh(ensure_selection)

    def on_blur(self) -> None:
        """Handle blur (unfocus) event."""
        self.focused = False
        self.remove_class("focused")

    def on_task_item_selected(self, message: TaskItem.Selected) -> None:
        """Handle task item selection from click.

        Args:
            message: TaskItem.Selected message
        """
        # Find the index of the selected task
        for i, task in enumerate(self._tasks):
            if task.id == message.task_id:
                self._update_selection(i)
                break
        
        # Ensure column regains focus to maintain keyboard navigation
        self.focus()

    class TaskSelected(Message):
        """Message emitted when a task is selected in the column."""

        def __init__(self, task: Task, column_id: str) -> None:
            """Initialize the TaskSelected message.

            Args:
                task: The selected Task object
                column_id: The ID of the column that emitted this message
            """
            super().__init__()
            self.task = task
            self.column_id = column_id
