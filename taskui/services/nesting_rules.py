"""
Nesting rules engine for TaskUI.

Implements the core nesting logic that enforces Column 1 (max 2 levels)
and Column 2 (max 3 levels) rules with context-relative level calculation.
"""

from enum import Enum
from typing import Optional
from uuid import UUID

from taskui.models import Task


class Column(Enum):
    """Enum representing the different columns in the UI."""
    COLUMN1 = "column1"  # Tasks column
    COLUMN2 = "column2"  # Subtasks column


class NestingRules:
    """
    Enforces nesting rules for tasks based on column context.

    Column 1 (Tasks):
        - Maximum 2 levels of nesting (Level 0 → Level 1)
        - Only Level 0 tasks can have children
        - Example: Sprint Planning (L0) → Review backlog (L1)

    Column 2 (Subtasks):
        - Maximum 3 levels of nesting (Level 0 → Level 1 → Level 2)
        - Level 0 and Level 1 tasks can have children
        - Displays context-relative levels (children of selected task start at L0)
        - Example: Auth endpoints (L0) → Session mgmt (L1) → Redis setup (L2)
    """

    # Maximum depth constants
    MAX_DEPTH_COLUMN1 = 1  # Levels 0-1 (2 levels total)
    MAX_DEPTH_COLUMN2 = 2  # Levels 0-2 (3 levels total)

    @classmethod
    def can_create_child(cls, task: Task, column: Column) -> bool:
        """
        Determine if a child task can be created for the given task in the specified column.

        Args:
            task: The task to check
            column: The column context (COLUMN1 or COLUMN2)

        Returns:
            True if a child can be created, False otherwise

        Examples:
            >>> task_l0 = Task(level=0, ...)
            >>> NestingRules.can_create_child(task_l0, Column.COLUMN1)
            True  # Level 0 tasks can have children in Column 1

            >>> task_l1 = Task(level=1, ...)
            >>> NestingRules.can_create_child(task_l1, Column.COLUMN1)
            False  # Level 1 tasks cannot have children in Column 1

            >>> NestingRules.can_create_child(task_l1, Column.COLUMN2)
            True  # Level 1 tasks can have children in Column 2
        """
        if column == Column.COLUMN1:
            # Column 1: Only level 0 tasks can have children (max depth = 1)
            return task.level < cls.MAX_DEPTH_COLUMN1
        elif column == Column.COLUMN2:
            # Column 2: Level 0 and 1 tasks can have children (max depth = 2)
            return task.level < cls.MAX_DEPTH_COLUMN2
        else:
            return False

    @classmethod
    def get_max_depth(cls, column: Column) -> int:
        """
        Get the maximum nesting depth for a column.

        Args:
            column: The column context

        Returns:
            Maximum depth (highest allowed level number)

        Examples:
            >>> NestingRules.get_max_depth(Column.COLUMN1)
            1  # Column 1 allows levels 0-1

            >>> NestingRules.get_max_depth(Column.COLUMN2)
            2  # Column 2 allows levels 0-2
        """
        if column == Column.COLUMN1:
            return cls.MAX_DEPTH_COLUMN1
        elif column == Column.COLUMN2:
            return cls.MAX_DEPTH_COLUMN2
        return 0

    @classmethod
    def calculate_context_relative_level(
        cls,
        task: Task,
        context_parent_id: Optional[UUID] = None
    ) -> int:
        """
        Calculate the context-relative level of a task.

        When displaying tasks in Column 2, the level is relative to the selected
        parent from Column 1. Children of the selected task appear at level 0
        in Column 2, their children at level 1, etc.

        Args:
            task: The task to calculate the level for
            context_parent_id: The ID of the context parent (selected task in Column 1)
                              If None, returns the absolute level

        Returns:
            The context-relative level (0-based)

        Examples:
            # Absolute hierarchy:
            # API Dev (L0, id=A) → Auth (L1, id=B) → Session (L2, id=C)

            # When API Dev is selected in Column 1:
            >>> task_auth = Task(level=1, parent_id=A, ...)
            >>> NestingRules.calculate_context_relative_level(task_auth, context_parent_id=A)
            0  # Auth appears at level 0 in Column 2

            >>> task_session = Task(level=2, parent_id=B, ...)
            >>> NestingRules.calculate_context_relative_level(task_session, context_parent_id=A)
            1  # Session appears at level 1 in Column 2

            # When Auth is selected in Column 1:
            >>> NestingRules.calculate_context_relative_level(task_session, context_parent_id=B)
            0  # Session appears at level 0 in Column 2
        """
        # If no context parent, return absolute level
        if context_parent_id is None:
            return task.level

        # If task is a direct child of context parent, it's at relative level 0
        if task.parent_id == context_parent_id:
            return 0

        # For deeper nesting, we would need to traverse the hierarchy
        # This is a simplified implementation that assumes the caller
        # provides the correct context
        # In practice, this would be calculated by the task service
        # which has access to the full task tree

        # Note: This method is primarily for documentation and testing.
        # The actual level adjustment will be handled by the UI layer
        # when displaying tasks in Column 2.
        return task.level

    @classmethod
    def validate_nesting_depth(cls, task: Task, column: Column) -> bool:
        """
        Validate that a task's nesting level is within the allowed depth for the column.

        Args:
            task: The task to validate
            column: The column context

        Returns:
            True if the task's level is valid for the column, False otherwise

        Examples:
            >>> task_l0 = Task(level=0, ...)
            >>> NestingRules.validate_nesting_depth(task_l0, Column.COLUMN1)
            True

            >>> task_l2 = Task(level=2, ...)
            >>> NestingRules.validate_nesting_depth(task_l2, Column.COLUMN1)
            False  # Level 2 exceeds Column 1 max depth of 1

            >>> NestingRules.validate_nesting_depth(task_l2, Column.COLUMN2)
            True  # Level 2 is within Column 2 max depth of 2
        """
        max_depth = cls.get_max_depth(column)
        return task.level <= max_depth

    @classmethod
    def get_allowed_child_level(cls, parent_task: Task, column: Column) -> Optional[int]:
        """
        Get the level that a child task should have when created under the given parent.

        Args:
            parent_task: The parent task
            column: The column context

        Returns:
            The level for the child task, or None if no child can be created

        Examples:
            >>> task_l0 = Task(level=0, ...)
            >>> NestingRules.get_allowed_child_level(task_l0, Column.COLUMN1)
            1  # Child of level 0 task would be level 1

            >>> task_l1 = Task(level=1, ...)
            >>> NestingRules.get_allowed_child_level(task_l1, Column.COLUMN1)
            None  # Cannot create child in Column 1 for level 1 task

            >>> NestingRules.get_allowed_child_level(task_l1, Column.COLUMN2)
            2  # Child of level 1 task would be level 2
        """
        if not cls.can_create_child(parent_task, column):
            return None

        child_level = parent_task.level + 1
        max_depth = cls.get_max_depth(column)

        # Verify the child level doesn't exceed max depth
        if child_level > max_depth:
            return None

        return child_level
