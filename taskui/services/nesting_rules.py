"""
Nesting rules engine for TaskUI.

Implements the core nesting logic that enforces Column 1 (max 2 levels)
and Column 2 (max 3 levels) rules with context-relative level calculation.
"""

import warnings
from enum import Enum
from typing import Optional
from uuid import UUID

from taskui.config.nesting_config import NestingConfig
from taskui.logging_config import get_logger
from taskui.models import Task

logger = get_logger(__name__)


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

    Usage:
        # New usage with config:
        config = NestingConfig.from_toml_file()
        rules = NestingRules(config)
        rules.can_create_child(task, Column.COLUMN1)

        # Or use the class method:
        rules = NestingRules.from_config()

        # Backward compatible usage (with deprecation warning):
        NestingRules.can_create_child(task, Column.COLUMN1)
    """

    # Maximum depth constants (DEPRECATED - use config instead)
    MAX_DEPTH_COLUMN1 = 1  # Levels 0-1 (2 levels total)
    MAX_DEPTH_COLUMN2 = 2  # Levels 0-2 (3 levels total)

    def __init__(self, config: Optional[NestingConfig] = None) -> None:
        """
        Initialize NestingRules with optional configuration.

        Args:
            config: NestingConfig object. If None, uses default values matching
                   the legacy hardcoded constants for backward compatibility.
        """
        if config is None:
            # Use defaults matching legacy constants for backward compatibility
            logger.debug("NestingRules: Initialized with default config (backward compatibility mode)")
            self._config = NestingConfig(
                column1={'max_depth': 1},
                column2={'max_depth': 2}
            )
        else:
            logger.debug(
                f"NestingRules: Initialized with config - "
                f"column1.max_depth={config.column1.max_depth}, "
                f"column2.max_depth={config.column2.max_depth}"
            )
            self._config = config

    @classmethod
    def from_config(cls, config_path: Optional[str] = None) -> 'NestingRules':
        """
        Create NestingRules instance from configuration file.

        This is an alternative constructor that loads configuration from a TOML
        file and creates a NestingRules instance.

        Args:
            config_path: Optional path to TOML config file. If None, uses default
                        location (~/.taskui/nesting.toml).

        Returns:
            NestingRules instance configured from file or defaults

        Example:
            >>> rules = NestingRules.from_config()
            >>> rules = NestingRules.from_config('/custom/path/config.toml')
        """
        from pathlib import Path

        path = Path(config_path) if config_path else None
        config = NestingConfig.from_toml_file(path)
        logger.info(
            f"NestingRules: Loaded from config - "
            f"column1.max_depth={config.column1.max_depth}, "
            f"column2.max_depth={config.column2.max_depth}"
        )
        return cls(config)

    def _get_max_depth_for_column(self, column: Column) -> int:
        """
        Get the maximum depth for a column from config.

        Args:
            column: The column to get max depth for

        Returns:
            Maximum depth value
        """
        if column == Column.COLUMN1:
            return self._config.column1.max_depth
        elif column == Column.COLUMN2:
            return self._config.column2.max_depth
        return 0

    def can_create_child_instance(self, task: Task, column: Column) -> bool:
        """
        Determine if a child task can be created for the given task in the specified column.

        This is the instance method that uses the configuration.

        Args:
            task: The task to check
            column: The column context (COLUMN1 or COLUMN2)

        Returns:
            True if a child can be created, False otherwise

        Examples:
            >>> rules = NestingRules()
            >>> task_l0 = Task(level=0, ...)
            >>> rules.can_create_child_instance(task_l0, Column.COLUMN1)
            True  # Level 0 tasks can have children in Column 1

            >>> task_l1 = Task(level=1, ...)
            >>> rules.can_create_child_instance(task_l1, Column.COLUMN1)
            False  # Level 1 tasks cannot have children in Column 1

            >>> rules.can_create_child_instance(task_l1, Column.COLUMN2)
            True  # Level 1 tasks can have children in Column 2
        """
        max_depth = self._get_max_depth_for_column(column)
        return task.level < max_depth

    @classmethod
    def can_create_child(cls, task: Task, column: Column) -> bool:
        """
        Determine if a child task can be created for the given task in the specified column.

        .. deprecated::
            Use instance method can_create_child_instance() with a NestingRules instance instead.
            Class methods are deprecated and will be removed in a future version.

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
        warnings.warn(
            "NestingRules class methods are deprecated. "
            "Use instance methods with NestingRules(config) instead.",
            DeprecationWarning,
            stacklevel=2
        )
        logger.debug(
            f"NestingRules.can_create_child (deprecated): task_level={task.level}, "
            f"column={column.value}"
        )
        # Delegate to instance method with default config
        instance = cls()
        return instance.can_create_child_instance(task, column)

    def get_max_depth_instance(self, column: Column) -> int:
        """
        Get the maximum nesting depth for a column from config.

        This is the instance method that uses the configuration.

        Args:
            column: The column context

        Returns:
            Maximum depth (highest allowed level number)

        Examples:
            >>> rules = NestingRules()
            >>> rules.get_max_depth_instance(Column.COLUMN1)
            1  # Column 1 allows levels 0-1

            >>> rules.get_max_depth_instance(Column.COLUMN2)
            2  # Column 2 allows levels 0-2
        """
        return self._get_max_depth_for_column(column)

    @classmethod
    def get_max_depth(cls, column: Column) -> int:
        """
        Get the maximum nesting depth for a column.

        .. deprecated::
            Use instance method get_max_depth_instance() with a NestingRules instance instead.
            Class methods are deprecated and will be removed in a future version.

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
        warnings.warn(
            "NestingRules class methods are deprecated. "
            "Use instance methods with NestingRules(config) instead.",
            DeprecationWarning,
            stacklevel=2
        )
        logger.debug(f"NestingRules.get_max_depth (deprecated): column={column.value}")
        # Delegate to instance method with default config
        instance = cls()
        return instance.get_max_depth_instance(column)

    def calculate_context_relative_level_instance(
        self,
        task: Task,
        context_parent_id: Optional[UUID] = None
    ) -> int:
        """
        Calculate the context-relative level of a task.

        When displaying tasks in Column 2, the level is relative to the selected
        parent from Column 1. Children of the selected task appear at level 0
        in Column 2, their children at level 1, etc.

        This is the instance method (config-independent for this operation).

        Args:
            task: The task to calculate the level for
            context_parent_id: The ID of the context parent (selected task in Column 1)
                              If None, returns the absolute level

        Returns:
            The context-relative level (0-based)

        Examples:
            >>> rules = NestingRules()
            # Absolute hierarchy:
            # API Dev (L0, id=A) → Auth (L1, id=B) → Session (L2, id=C)

            # When API Dev is selected in Column 1:
            >>> task_auth = Task(level=1, parent_id=A, ...)
            >>> rules.calculate_context_relative_level_instance(task_auth, context_parent_id=A)
            0  # Auth appears at level 0 in Column 2

            >>> task_session = Task(level=2, parent_id=B, ...)
            >>> rules.calculate_context_relative_level_instance(task_session, context_parent_id=A)
            1  # Session appears at level 1 in Column 2

            # When Auth is selected in Column 1:
            >>> rules.calculate_context_relative_level_instance(task_session, context_parent_id=B)
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
    def calculate_context_relative_level(
        cls,
        task: Task,
        context_parent_id: Optional[UUID] = None
    ) -> int:
        """
        Calculate the context-relative level of a task.

        .. deprecated::
            Use instance method calculate_context_relative_level_instance() with a
            NestingRules instance instead. Class methods are deprecated and will be
            removed in a future version.

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
        warnings.warn(
            "NestingRules class methods are deprecated. "
            "Use instance methods with NestingRules(config) instead.",
            DeprecationWarning,
            stacklevel=2
        )
        logger.debug(
            f"NestingRules.calculate_context_relative_level (deprecated): "
            f"task_level={task.level}, context_parent_id={context_parent_id}"
        )
        # Delegate to instance method
        instance = cls()
        return instance.calculate_context_relative_level_instance(task, context_parent_id)

    def validate_nesting_depth_instance(self, task: Task, column: Column) -> bool:
        """
        Validate that a task's nesting level is within the allowed depth for the column.

        This is the instance method that uses the configuration.

        Args:
            task: The task to validate
            column: The column context

        Returns:
            True if the task's level is valid for the column, False otherwise

        Examples:
            >>> rules = NestingRules()
            >>> task_l0 = Task(level=0, ...)
            >>> rules.validate_nesting_depth_instance(task_l0, Column.COLUMN1)
            True

            >>> task_l2 = Task(level=2, ...)
            >>> rules.validate_nesting_depth_instance(task_l2, Column.COLUMN1)
            False  # Level 2 exceeds Column 1 max depth of 1

            >>> rules.validate_nesting_depth_instance(task_l2, Column.COLUMN2)
            True  # Level 2 is within Column 2 max depth of 2
        """
        max_depth = self.get_max_depth_instance(column)
        return task.level <= max_depth

    @classmethod
    def validate_nesting_depth(cls, task: Task, column: Column) -> bool:
        """
        Validate that a task's nesting level is within the allowed depth for the column.

        .. deprecated::
            Use instance method validate_nesting_depth_instance() with a NestingRules
            instance instead. Class methods are deprecated and will be removed in a future version.

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
        warnings.warn(
            "NestingRules class methods are deprecated. "
            "Use instance methods with NestingRules(config) instead.",
            DeprecationWarning,
            stacklevel=2
        )
        logger.debug(
            f"NestingRules.validate_nesting_depth (deprecated): "
            f"task_level={task.level}, column={column.value}"
        )
        # Delegate to instance method with default config
        instance = cls()
        return instance.validate_nesting_depth_instance(task, column)

    def get_allowed_child_level_instance(
        self, parent_task: Task, column: Column
    ) -> Optional[int]:
        """
        Get the level that a child task should have when created under the given parent.

        This is the instance method that uses the configuration.

        Args:
            parent_task: The parent task
            column: The column context

        Returns:
            The level for the child task, or None if no child can be created

        Examples:
            >>> rules = NestingRules()
            >>> task_l0 = Task(level=0, ...)
            >>> rules.get_allowed_child_level_instance(task_l0, Column.COLUMN1)
            1  # Child of level 0 task would be level 1

            >>> task_l1 = Task(level=1, ...)
            >>> rules.get_allowed_child_level_instance(task_l1, Column.COLUMN1)
            None  # Cannot create child in Column 1 for level 1 task

            >>> rules.get_allowed_child_level_instance(task_l1, Column.COLUMN2)
            2  # Child of level 1 task would be level 2
        """
        if not self.can_create_child_instance(parent_task, column):
            return None

        child_level = parent_task.level + 1
        max_depth = self.get_max_depth_instance(column)

        # Verify the child level doesn't exceed max depth
        if child_level > max_depth:
            return None

        return child_level

    @classmethod
    def get_allowed_child_level(cls, parent_task: Task, column: Column) -> Optional[int]:
        """
        Get the level that a child task should have when created under the given parent.

        .. deprecated::
            Use instance method get_allowed_child_level_instance() with a NestingRules
            instance instead. Class methods are deprecated and will be removed in a future version.

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
        warnings.warn(
            "NestingRules class methods are deprecated. "
            "Use instance methods with NestingRules(config) instead.",
            DeprecationWarning,
            stacklevel=2
        )
        logger.debug(
            f"NestingRules.get_allowed_child_level (deprecated): "
            f"parent_level={parent_task.level}, column={column.value}"
        )
        # Delegate to instance method with default config
        instance = cls()
        return instance.get_allowed_child_level_instance(parent_task, column)
