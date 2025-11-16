"""TaskItem widget for displaying individual tasks with tree visualization.

This module provides the TaskItem widget which renders a single task with:
- Proper indentation based on nesting level
- Tree lines (└─) for visual hierarchy
- Level-specific accent colors
- Selection highlighting
- Completion and archive status indicators
"""

from typing import Optional
from uuid import UUID

from textual.widget import Widget
from textual.reactive import reactive
from textual.message import Message
from rich.text import Text

from taskui.models import Task
from taskui.ui.theme import (
    get_level_color,
    FOREGROUND,
    COMPLETE_COLOR,
    ARCHIVE_COLOR,
    SELECTION,
    LEVEL_0_COLOR,
    LEVEL_1_COLOR,
    LEVEL_2_COLOR,
    HOVER_OPACITY,
    with_alpha,
)


class TaskItem(Widget):
    """A widget representing a single task in the task list.

    Displays task with:
    - Indentation based on nesting level
    - Tree lines for hierarchy visualization
    - Level-specific border colors
    - Completion status (strikethrough, checkmark)
    - Archive status (📦 icon, reduced opacity)
    - Selection highlighting
    """

    DEFAULT_CSS = f"""
    TaskItem {{
        height: 1;
        width: 100%;
        background: transparent;
        opacity: 0;
    }}

    TaskItem:hover {{
        background: {with_alpha(SELECTION, HOVER_OPACITY)};
    }}

    TaskItem.selected {{
        background: {SELECTION};
    }}

    TaskItem.level-0 {{
        border-left: thick {LEVEL_0_COLOR};
    }}

    TaskItem.level-1 {{
        border-left: thick {LEVEL_1_COLOR};
    }}

    TaskItem.level-2 {{
        border-left: thick {LEVEL_2_COLOR};
    }}
    """

    # Reactive properties
    selected: reactive[bool] = reactive(False)
    task_id: reactive[Optional[UUID]] = reactive(None)

    def __init__(
        self,
        task: Task,
        is_last_child: bool = False,
        **kwargs
    ) -> None:
        """Initialize a TaskItem widget.

        Args:
            task: The Task model to display
            is_last_child: Whether this is the last child in its parent's children
            **kwargs: Additional keyword arguments for Widget
        """
        super().__init__(**kwargs)
        self._task_model = task
        self._is_last_child = is_last_child
        self.task_id = task.id

        # Set level-specific CSS class
        self.add_class(f"level-{task.level}")

    def on_mount(self) -> None:
        """Fade in the task item when mounted."""
        self.styles.animate("opacity", value=1.0, duration=0.3, easing="out_cubic")

    @property
    def task(self) -> Task:
        """Get the task associated with this item.

        Returns:
            The Task object
        """
        return self._task_model

    def update_task(self, task: Task) -> None:
        """Update the task data and refresh the display.

        Args:
            task: Updated Task object
        """
        self._task_model = task
        self.refresh()

    def render(self) -> Text:
        """Render the task item as Rich Text with tree visualization.

        Returns:
            Rich Text object with formatted task display
        """
        # Calculate indentation (2 spaces per level)
        indent_spaces = "  " * self._task_model.level

        # Determine base color (use white for selected items for better contrast)
        base_color = FOREGROUND if self.selected else get_level_color(self._task_model.level)

        # Build the text content first
        text = Text()

        # Add tree line for nested items
        if self._task_model.level > 0:
            # Use └─ for last child, ├─ for others
            tree_char = "└─" if self._is_last_child else "├─"
            tree_line = f"{indent_spaces}{tree_char} "

            # Use level-specific color for tree line (or white if selected)
            tree_color = FOREGROUND if self.selected else get_level_color(self._task_model.level)
            text.append(tree_line, style=tree_color)
        else:
            # Top level tasks just get indentation
            text.append(indent_spaces)

        # Add completion checkbox
        if self._task_model.is_completed:
            checkbox = "[✓] "
            checkbox_color = FOREGROUND if self.selected else COMPLETE_COLOR
            text.append(checkbox, style=checkbox_color)
        else:
            checkbox = "[ ] "
            text.append(checkbox, style=FOREGROUND)

        # Add archive icon if archived
        if self._task_model.is_archived:
            archive_color = FOREGROUND if self.selected else ARCHIVE_COLOR
            text.append("📦 ", style=archive_color)

        # Add task title with appropriate styling
        title = self._task_model.title

        if self._task_model.is_completed:
            # Strikethrough for completed tasks
            title_color = FOREGROUND if self.selected else COMPLETE_COLOR
            text.append(title, style=f"strike {title_color}")
        elif self._task_model.is_archived:
            # Dimmed for archived tasks
            title_color = FOREGROUND if self.selected else ARCHIVE_COLOR
            text.append(title, style=title_color)
        else:
            # Normal styling with level-specific color (or white if selected)
            text.append(title, style=base_color)

        # Add child progress indicator if task has children
        if self._task_model.has_children:
            progress = f" ({self._task_model.progress_string})"
            text.append(progress, style=FOREGROUND + " dim")

        # Apply selection background to entire text if selected
        if self.selected:
            text.stylize(f"on {SELECTION}")

        return text

    def on_click(self) -> None:
        """Handle click event on the task item."""
        self.selected = True
        self.post_message(self.Selected(self.task_id))

    def watch_selected(self, selected: bool) -> None:
        """React to selection state changes.

        Args:
            selected: New selection state
        """
        if selected:
            self.add_class("selected")
        else:
            self.remove_class("selected")
        self.refresh()

    class Selected(Message):
        """Message emitted when a task item is selected."""

        def __init__(self, task_id: UUID) -> None:
            """Initialize the Selected message.

            Args:
                task_id: ID of the selected task
            """
            super().__init__()
            self.task_id = task_id
