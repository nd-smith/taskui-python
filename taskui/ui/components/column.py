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

from textual.containers import VerticalScroll, Vertical
from textual.widget import Widget
from textual.reactive import reactive
from textual.message import Message
from textual.widgets import Static

from taskui.models import Task
from taskui.ui.components.task_item import TaskItem
from taskui.ui.theme import BORDER, SELECTION, FOREGROUND


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

    DEFAULT_CSS = """
    TaskColumn {
        border: solid #3E3D32;
        padding: 0 1;
        margin: 0 1;
    }

    TaskColumn:focus {
        border: thick #66D9EF;
    }

    TaskColumn .column-header {
        width: 100%;
        height: 1;
        background: #49483E;
        color: #F8F8F2;
        text-align: center;
        border-bottom: solid #3E3D32;
        padding: 0 1;
    }

    TaskColumn .column-content {
        width: 100%;
        height: 1fr;
        padding: 1 0;
    }

    TaskColumn .empty-message {
        width: 100%;
        height: 100%;
        color: #75715E;
        text-align: center;
        padding: 2;
    }
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
        # Header
        yield Static(self.header_title, classes="column-header", id=f"{self.column_id}-header")

        # Scrollable content area
        with VerticalScroll(classes="column-content", id=f"{self.column_id}-content"):
            yield Static(self.empty_message, classes="empty-message", id=f"{self.column_id}-empty")

    def set_tasks(self, tasks: List[Task]) -> None:
        """Update the column with a new list of tasks.

        Args:
            tasks: List of Task objects to display
        """
        self._tasks = tasks
        self._selected_index = 0 if tasks else -1
        self._render_tasks()

    def _render_tasks(self) -> None:
        """Render the task list with TaskItem widgets."""
        try:
            content_container = self.query_one(f"#{self.column_id}-content", VerticalScroll)
            empty_message = self.query_one(f"#{self.column_id}-empty", Static)
        except Exception:
            # Container not yet mounted, skip rendering
            return

        if not self._tasks:
            # Clear all existing task items
            existing_items = list(content_container.query(TaskItem))
            for widget in existing_items:
                try:
                    widget.remove()
                except Exception:
                    pass
            # Show empty message
            empty_message.display = True
            return

        # Hide empty message
        empty_message.display = False

        # Get current task IDs that should be displayed
        current_task_ids = {f"task-{task.id}" for task in self._tasks}

        # Remove widgets for tasks that are no longer in the list
        existing_items = list(content_container.query(TaskItem))
        for widget in existing_items:
            if widget.id not in current_task_ids:
                try:
                    widget.remove()
                except Exception:
                    pass

        # Group tasks by parent to determine last child status
        parent_groups = {}
        for task in self._tasks:
            parent_id = task.parent_id or "root"
            if parent_id not in parent_groups:
                parent_groups[parent_id] = []
            parent_groups[parent_id].append(task)

        # Render each task
        for i, task in enumerate(self._tasks):
            # Determine if this is the last child in its parent group
            parent_id = task.parent_id or "root"
            siblings = parent_groups[parent_id]
            is_last_child = task == siblings[-1] if siblings else False

            task_id = f"task-{task.id}"

            # Check if widget already exists
            try:
                existing = content_container.query_one(f"#{task_id}", TaskItem)
                # Widget exists, update its state
                existing.selected = (i == self._selected_index)
                continue
            except:
                # Widget doesn't exist, create it
                pass

            # Create and mount new task item
            task_item = TaskItem(
                task=task,
                is_last_child=is_last_child,
                id=task_id
            )
            task_item.selected = (i == self._selected_index)

            try:
                content_container.mount(task_item)
            except Exception as e:
                # Widget ID collision - this shouldn't happen anymore but log if it does
                print(f"Error mounting task widget: {e}")

    def update_header(self, title: str) -> None:
        """Update the column header title.

        Args:
            title: New header title
        """
        self.header_title = title
        header = self.query_one(f"#{self.column_id}-header", Static)
        header.update(title)

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
        if not self._tasks or new_index < 0 or new_index >= len(self._tasks):
            return

        # Deselect old item
        if 0 <= self._selected_index < len(self._tasks):
            old_task_id = self._tasks[self._selected_index].id
            old_item = self.query_one(f"#task-{old_task_id}", TaskItem)
            old_item.selected = False

        # Select new item
        self._selected_index = new_index
        new_task = self._tasks[new_index]
        new_item = self.query_one(f"#task-{new_task.id}", TaskItem)
        new_item.selected = True

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
        """Handle focus event."""
        self.focused = True
        self.add_class("focused")

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
