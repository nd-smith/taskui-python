"""Detail panel widget for displaying comprehensive task information.

This module provides the DetailPanel widget which shows detailed information
about a selected task including:
- Task title and status
- Timestamps (created, completed, archived)
- Complete hierarchy path
- Parent information
- Notes
- Nesting warnings
"""

from typing import Optional, List
from datetime import datetime
from uuid import UUID

from textual.containers import VerticalScroll, Vertical
from textual.widget import Widget
from textual.reactive import reactive
from textual.widgets import Static

from taskui.models import Task
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
    get_level_color,
)


class DetailPanel(Widget):
    """A detail panel widget for displaying comprehensive task information.

    Shows:
    - Task title with status indicators
    - Creation, completion, and archive dates
    - Complete hierarchy path from root
    - Parent task information
    - Task notes
    - Nesting warnings when at maximum depth
    """

    # Enable keyboard focus
    can_focus = True

    DEFAULT_CSS = """
    DetailPanel {
        border: solid #3E3D32;
        padding: 0 1;
        margin: 0 1;
    }

    DetailPanel:focus {
        border: thick #66D9EF;
    }

    DetailPanel .panel-header {
        width: 100%;
        height: 1;
        background: #49483E;
        color: #F8F8F2;
        text-align: center;
        border-bottom: solid #3E3D32;
        padding: 0 1;
    }

    DetailPanel .panel-content {
        width: 100%;
        height: 1fr;
        padding: 1 1;
    }

    DetailPanel .empty-message {
        width: 100%;
        height: 100%;
        color: #75715E;
        text-align: center;
        padding: 2;
    }

    DetailPanel .section {
        padding: 0 0 1 0;
    }

    DetailPanel .section-title {
        color: #66D9EF;
        text-style: bold;
    }

    DetailPanel .task-title {
        color: #F8F8F2;
        text-style: bold;
        padding: 0 0 1 0;
    }

    DetailPanel .info-line {
        color: #F8F8F2;
        padding: 0 0 0 2;
    }

    DetailPanel .status-complete {
        color: #A6E22E;
    }

    DetailPanel .status-incomplete {
        color: #75715E;
    }

    DetailPanel .status-archived {
        color: #FD971F;
    }

    DetailPanel .warning {
        color: #FD971F;
        text-style: bold;
        padding: 1 0;
    }

    DetailPanel .hierarchy-item {
        color: #F8F8F2;
        padding: 0 0 0 2;
    }

    DetailPanel .notes-content {
        color: #F8F8F2;
        padding: 1 0 0 2;
        text-style: italic;
    }
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

        Yields:
            Widgets that make up the panel
        """
        # Header
        yield Static(self.panel_title, classes="panel-header", id=f"{self.column_id}-header")

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
        self.current_task = task
        self.task_hierarchy = hierarchy or []
        self._render_details()

    def _render_details(self) -> None:
        """Render the task details."""
        content_container = self.query_one(f"#{self.column_id}-content", VerticalScroll)
        empty_message = self.query_one(f"#{self.column_id}-empty", Static)

        # Clear existing detail widgets
        for widget in content_container.query(".section"):
            widget.remove()

        if not self.current_task:
            # Show empty message
            empty_message.display = True
            return

        # Hide empty message
        empty_message.display = False

        task = self.current_task

        # Build the detail sections
        details_text = self._build_details_text(task)

        # Mount the details as a single Static widget
        detail_widget = Static(details_text, classes="section", markup=True)
        content_container.mount(detail_widget)

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
        status_color = "#A6E22E" if task.is_completed else "#75715E"
        lines.append(f"  Completion: [{status_color}]{status_text}[/{status_color}]")

        if task.is_archived:
            lines.append(f"  Archive: [#FD971F]Archived[/#FD971F]")

        lines.append(f"  Level: {task.level}")
        lines.append("")

        # Dates Section
        lines.append("[bold #66D9EF]DATES[/bold #66D9EF]")
        lines.append(f"  Created: {self._format_datetime(task.created_at)}")

        if task.completed_at:
            lines.append(f"  Completed: {self._format_datetime(task.completed_at)}")

        if task.archived_at:
            lines.append(f"  Archived: {self._format_datetime(task.archived_at)}")

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
            status_color = "#A6E22E" if parent.is_completed else "#75715E"
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

        # Nesting Warning Section
        warning = self._get_nesting_warning(task)
        if warning:
            lines.append(f"[bold #FD971F]⚠ {warning}[/bold #FD971F]")
            lines.append("")

        # Task metadata
        lines.append("[bold #66D9EF]METADATA[/bold #66D9EF]")
        lines.append(f"  ID: {task.id}")
        if task.parent_id:
            lines.append(f"  Parent ID: {task.parent_id}")
        lines.append(f"  List ID: {task.list_id}")
        lines.append(f"  Position: {task.position}")

        return "\n".join(lines)

    def _format_datetime(self, dt: datetime) -> str:
        """Format a datetime for display.

        Args:
            dt: Datetime to format

        Returns:
            Formatted datetime string
        """
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def _get_nesting_warning(self, task: Task) -> Optional[str]:
        """Get nesting warning message if task is at maximum depth.

        Args:
            task: Task to check

        Returns:
            Warning message string or None
        """
        if task.level == 1:
            return "Maximum nesting depth for Column 1 (2 levels)"
        elif task.level == 2:
            return "Maximum nesting depth reached (3 levels)"
        return None

    def on_focus(self) -> None:
        """Handle focus event."""
        self.add_class("focused")

    def on_blur(self) -> None:
        """Handle blur (unfocus) event."""
        self.remove_class("focused")
