"""
Simple global nesting depth validation for TaskUI.

Replaces complex column-specific validation with a single global max depth.
Tasks can nest up to MAX_NESTING_DEPTH levels (0-based, so max_depth=4 allows 5 levels).
"""

from taskui.logging_config import get_logger

logger = get_logger(__name__)

# Global maximum nesting depth (levels 0-4 = 5 levels total)
# Level 0: Top-level tasks
# Level 1: Children
# Level 2: Grandchildren
# Level 3: Great-grandchildren
# Level 4: Great-great-grandchildren
MAX_NESTING_DEPTH = 4


class NestingLimitError(Exception):
    """Raised when task nesting exceeds the maximum allowed depth."""
    pass


def validate_task_depth(task_level: int) -> None:
    """
    Validate that a task's level doesn't exceed maximum depth.

    Args:
        task_level: The nesting level to validate (0-based)

    Raises:
        NestingLimitError: If level exceeds MAX_NESTING_DEPTH
    """
    if task_level > MAX_NESTING_DEPTH:
        logger.warning(f"Task level {task_level} exceeds max depth {MAX_NESTING_DEPTH}")
        raise NestingLimitError(
            f"Task depth cannot exceed {MAX_NESTING_DEPTH}. Got level {task_level}."
        )


def can_create_child(parent_level: int) -> bool:
    """
    Check if a child task can be created under a parent at given level.

    Args:
        parent_level: The nesting level of the parent task (0-based)

    Returns:
        True if child can be created, False if parent is at max depth
    """
    return parent_level < MAX_NESTING_DEPTH


def get_child_level(parent_level: int) -> int:
    """
    Calculate the level for a child of the given parent.

    Args:
        parent_level: The nesting level of the parent task (0-based)

    Returns:
        The level the child should have (parent_level + 1)

    Raises:
        NestingLimitError: If child would exceed max depth
    """
    child_level = parent_level + 1
    if child_level > MAX_NESTING_DEPTH:
        raise NestingLimitError(
            f"Cannot create child: parent at level {parent_level} "
            f"would create child at level {child_level}, "
            f"exceeding max depth {MAX_NESTING_DEPTH}."
        )
    return child_level
