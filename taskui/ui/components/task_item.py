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

        This method builds a Rich Text object that displays the task with proper formatting,
        including tree lines for hierarchy, completion status, archive status, and
        level-specific styling. The rendering process consists of:

        1. Calculate indentation based on nesting level (2 spaces per level)
        2. Determine base color using color selection logic (white for selected, level color otherwise)
        3. Add tree lines (└─ for last child, ├─ for others) with proper spacing for nested items
        4. Add completion checkbox ([✓] for completed, [ ] for pending)
        5. Add archive icon (📦) for archived tasks
        6. Add task title with appropriate styling:
           - Strikethrough + complete color for completed tasks
           - Dimmed archive color for archived tasks
           - Level-specific color for normal tasks
        7. Add child progress indicator (e.g., "2/3") if task has children
        8. Apply selection background to entire text if selected

        Color Selection Logic:
        - When selected: Always use FOREGROUND color (white) for maximum contrast
        - When not selected: Use level-specific colors from theme (LEVEL_0, LEVEL_1, LEVEL_2)
        - Completion status: COMPLETE_COLOR for completed tasks (green)
        - Archive status: ARCHIVE_COLOR for archived tasks (reduced opacity)
        - Progress indicator: Always dimmed foreground color for subtle appearance

        Returns:
            Rich Text object with formatted task display, including colors and styling
        """
        # Determine base color (use white for selected items for better contrast)
        base_color = FOREGROUND if self.selected else get_level_color(self._task_model.level)

        # Build the text content first
        text = Text()

        # Add tree line for nested items
        if self._task_model.level > 0:
            tree_line, tree_color = self._get_tree_line()
            text.append(tree_line, style=tree_color)
        else:
            # Top level tasks just get indentation (2 spaces per level)
            indent_spaces = "  " * self._task_model.level
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

    def _get_tree_line(self) -> tuple[str, str]:
        """Generate tree line characters and styling for nested items.

        Tree Line Rendering:
        The tree line uses Unicode box-drawing characters to visualize the task hierarchy:
        - └─ (box drawings light up and right): Used for the last child in a sibling group
        - ├─ (box drawings light vertical and right): Used for non-last children

        This creates a visual hierarchy where:
        - The └─ character indicates "this is the last item"
        - The ├─ character indicates "there are more items below"

        The tree line is only rendered for nested items (level > 0). Top-level tasks
        receive only indentation without tree characters.

        Returns:
            Tuple of (tree_line_string, tree_color) where:
            - tree_line_string: The indentation + tree character + space (e.g., "  └─ ")
            - tree_color: The color for the tree line (white if selected, level color otherwise)
        """
        tree_char = "└─" if self._is_last_child else "├─"
        indent_spaces = "  " * self._task_model.level
        tree_line = f"{indent_spaces}{tree_char} "
        tree_color = FOREGROUND if self.selected else get_level_color(self._task_model.level)
        return tree_line, tree_color

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
