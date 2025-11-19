"""Detail panel widget for displaying comprehensive task information.

This module provides the DetailPanel widget which shows detailed information
about a selected task including:
- Task title and status
- Timestamps (created, completed, archived)
- Complete hierarchy path
- Parent information
- Notes
"""

from typing import Optional, List
from datetime import datetime
from uuid import UUID

from textual.containers import VerticalScroll, Vertical
from textual.widget import Widget
from textual.reactive import reactive
from textual.widgets import Static

from taskui.models import Task
from taskui.logging_config import get_logger
from taskui.ui.theme import (
    BACKGROUND,
    FOREGROUND,
    BORDER,
    SELECTION,
    COMMENT,
    LEVEL_0_COLOR,
    LEVEL_1_COLOR,
    LEVEL_2_COLOR,
    COMPLETE_COLOR,
    ARCHIVE_COLOR,
    YELLOW,
    ORANGE,
    PURPLE,
    get_level_color,
)

# Initialize logger for this module
logger = get_logger(__name__)


class DetailPanel(Widget):
    """A detail panel widget for displaying comprehensive task information.

    Shows:
    - Task title with status indicators
    - Creation, completion, and archive dates
    - Complete hierarchy path from root
    - Parent task information
    - Task notes
    """

    # Disable keyboard focus - Column 3 is display-only
    can_focus = False

    DEFAULT_CSS = f"""
    DetailPanel {{
        border: solid {BORDER};
        padding: 0 1;
        margin: 0 1;
    }}

    DetailPanel:focus {{
        border: thick {LEVEL_2_COLOR};
    }}

    DetailPanel .panel-header {{
        width: 100%;
        height: 1;
        background: {SELECTION};
        color: {FOREGROUND};
        text-align: center;
        border-bottom: solid {BORDER};
        padding: 0 1;
    }}

    DetailPanel .panel-content {{
        width: 100%;
        height: 1fr;
        padding: 1 1;
    }}

    DetailPanel .empty-message {{
        width: 100%;
        height: 100%;
        color: {COMMENT};
        text-align: center;
        padding: 2;
    }}

    DetailPanel .section {{
        padding: 0 0 1 0;
    }}

    DetailPanel .section-title {{
        color: {LEVEL_0_COLOR};
        text-style: bold;
    }}

    DetailPanel .task-title {{
        color: {FOREGROUND};
        text-style: bold;
        padding: 0 0 1 0;
    }}

    DetailPanel .info-line {{
        color: {FOREGROUND};
        padding: 0 0 0 2;
    }}

    DetailPanel .status-complete {{
        color: {LEVEL_1_COLOR};
    }}

    DetailPanel .status-incomplete {{
        color: {YELLOW};
    }}

    DetailPanel .status-archived {{
        color: {ORANGE};
    }}

    DetailPanel .warning {{
        color: {ORANGE};
        text-style: bold;
        padding: 1 0;
    }}

    DetailPanel .hierarchy-item {{
        color: {FOREGROUND};
        padding: 0 0 0 2;
    }}

    DetailPanel .metadata {{
        color: {PURPLE};
        padding: 0 0 0 2;
        text-style: italic;
    }}

    DetailPanel .notes-content {{
        color: {FOREGROUND};
        padding: 1 0 0 2;
        text-style: italic;
    }}
    """

    # Reactive properties
    current_task: reactive[Optional[Task]] = reactive(None)
    task_hierarchy: reactive[List[Task]] = reactive([])

    def __init__(
        self,
        column_id: str = "column-3",
        title: str = "Details",
        **kwargs
    ) -> None:
        """Initialize a DetailPanel widget.

        Args:
            column_id: Unique identifier for this panel
            title: Panel header title
            **kwargs: Additional keyword arguments for Widget
        """
        super().__init__(**kwargs)
        self.column_id = column_id
        self.panel_title = title

    def compose(self):
        """Compose the panel layout.

        Creates the scrollable content area with an empty message placeholder.

        Yields:
            Static widgets that form the panel's initial structure
        """
        # Scrollable content area
        with VerticalScroll(classes="panel-content", id=f"{self.column_id}-content"):
            yield Static(
                "No task selected\nSelect a task to view details",
                classes="empty-message",
                id=f"{self.column_id}-empty"
            )

    def set_task(self, task: Optional[Task], hierarchy: Optional[List[Task]] = None) -> None:
        """Update the panel with task details.

        Args:
            task: Task object to display, or None to show empty state
            hierarchy: List of tasks from root to current task (for hierarchy path)
        """
        if task:
            logger.debug(
                f"DetailPanel: Setting task '{task.title[:50]}' (id={task.id}, level={task.level}), "
                f"hierarchy_depth={len(hierarchy) if hierarchy else 0}"
            )
        else:
            logger.debug("DetailPanel: Clearing task (no task selected)")

        self.current_task = task
        self.task_hierarchy = hierarchy or []
        self._render_details()

    def _render_details(self) -> None:
        """Render the task details to the content container.

        Updates the panel by removing old detail widgets and mounting new ones,
        or showing the empty message if no task is selected.
        """
        content_container = self.query_one(f"#{self.column_id}-content", VerticalScroll)
        empty_message = self.query_one(f"#{self.column_id}-empty", Static)

        # Clear existing detail widgets
        for widget in content_container.query(".section"):
            widget.remove()

        if not self.current_task:
            # Show empty message
            empty_message.display = True
            logger.debug("DetailPanel: Rendered empty state")
            return

        # Hide empty message
        empty_message.display = False

        task = self.current_task
        logger.debug(
            f"DetailPanel: Rendering task details - id={task.id}, "
            f"completed={task.is_completed}, archived={task.is_archived}, "
            f"has_notes={bool(task.notes)}, has_parent={bool(task.parent_id)}"
        )

        # Build the detail sections
        details_text = self._build_details_text(task)

        # Mount the details as a single Static widget
        detail_widget = Static(details_text, classes="section", markup=True)
        content_container.mount(detail_widget)
        logger.debug("DetailPanel: Detail widgets mounted successfully")

    def _build_details_text(self, task: Task) -> str:
        """Build the formatted text for task details.

        Args:
            task: Task to display

        Returns:
            Formatted text string with markup
        """
        lines = []

        # Task Title Section
        lines.append(f"[bold #66D9EF]TASK[/bold #66D9EF]")

        # Title with status indicators
        title_line = f"  {task.title}"
        if task.is_completed:
            title_line += " [#A6E22E]✓ Complete[/#A6E22E]"
        if task.is_archived:
            title_line += " [#FD971F]📦 Archived[/#FD971F]"
        lines.append(title_line)
        lines.append("")

        # Status Section
        lines.append("[bold #66D9EF]STATUS[/bold #66D9EF]")

        status_text = "Completed" if task.is_completed else "Incomplete"
        status_color = "#A6E22E" if task.is_completed else "#E6DB74"  # YELLOW for incomplete
        lines.append(f"  Completion: [{status_color}]{status_text}[/{status_color}]")

        if task.is_archived:
            lines.append(f"  Archive: [#FD971F]Archived[/#FD971F]")

        lines.append(f"  Level: {task.level}")
        lines.append("")

        # Dates Section
        lines.append("[bold #66D9EF]DATES[/bold #66D9EF]")
        lines.append(f"  Created: [#AE81FF]{self._format_datetime(task.created_at)}[/#AE81FF]")

        if task.completed_at:
            lines.append(f"  Completed: [#AE81FF]{self._format_datetime(task.completed_at)}[/#AE81FF]")

        if task.archived_at:
            lines.append(f"  Archived: [#AE81FF]{self._format_datetime(task.archived_at)}[/#AE81FF]")

        lines.append("")

        # Hierarchy Section
        if self.task_hierarchy:
            lines.append("[bold #66D9EF]HIERARCHY[/bold #66D9EF]")
            for i, ancestor in enumerate(self.task_hierarchy):
                indent = "  " + ("  " * i)
                level_color = get_level_color(ancestor.level)
                connector = "└─ " if i == len(self.task_hierarchy) - 1 else "├─ "
                lines.append(f"{indent}[{level_color}]{connector}{ancestor.title}[/{level_color}]")
            lines.append("")

        # Parent Section
        if task.parent_id and self.task_hierarchy and len(self.task_hierarchy) > 1:
            parent = self.task_hierarchy[-2]  # Second to last is the parent
            lines.append("[bold #66D9EF]PARENT[/bold #66D9EF]")
            parent_color = get_level_color(parent.level)
            lines.append(f"  [{parent_color}]{parent.title}[/{parent_color}]")

            parent_status = "Complete" if parent.is_completed else "Incomplete"
            status_color = "#A6E22E" if parent.is_completed else "#E6DB74"  # YELLOW for incomplete
            lines.append(f"  Status: [{status_color}]{parent_status}[/{status_color}]")
            lines.append("")

        # Notes Section
        if task.notes:
            lines.append("[bold #66D9EF]NOTES[/bold #66D9EF]")
            # Split notes by newlines and indent each line
            note_lines = task.notes.split('\n')
            for note_line in note_lines:
                lines.append(f"  [italic]{note_line}[/italic]")
            lines.append("")

        return "\n".join(lines)

    def _format_datetime(self, dt: datetime) -> str:
        """Format a datetime for display.

        Args:
            dt: Datetime to format

        Returns:
            Formatted datetime string
        """
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def on_focus(self) -> None:
        """Handle widget focus event.

        Adds the 'focused' CSS class to highlight the panel as focused.
        """
        logger.debug(f"DetailPanel: Focused (current_task={self.current_task.title[:30] if self.current_task else 'None'})")
        self.add_class("focused")

    def on_blur(self) -> None:
        """Handle widget blur (unfocus) event.

        Removes the 'focused' CSS class when the panel loses focus.
        """
        logger.debug("DetailPanel: Blurred (lost focus)")
        self.remove_class("focused")
