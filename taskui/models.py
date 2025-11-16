"""
Pydantic models for TaskUI application.

Defines the core data structures for tasks and task lists with validation,
computed properties, and proper typing.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, PrivateAttr, field_validator, model_validator, computed_field


class TaskList(BaseModel):
    """
    Represents a task list (e.g., Work, Home, Personal).

    A task list is a container for organizing tasks into different categories.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique identifier for the list")
    name: str = Field(..., min_length=1, max_length=100, description="List name")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    # Private attributes for computed properties
    _task_count: int = PrivateAttr(default=0)
    _completed_count: int = PrivateAttr(default=0)

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Work",
                "created_at": "2025-01-14T10:00:00",
            }
        }

    @computed_field
    @property
    def completion_percentage(self) -> float:
        """
        Calculate completion percentage for this list.

        Returns:
            Percentage of completed tasks (0-100)
        """
        if self._task_count == 0:
            return 0.0
        return round((self._completed_count / self._task_count) * 100, 1)

    @computed_field
    @property
    def task_count(self) -> int:
        """
        Get the total number of tasks in this list.

        Returns:
            Total number of tasks
        """
        return self._task_count

    def update_counts(self, task_count: int, completed_count: int) -> None:
        """
        Update the task counts for computed properties.

        Args:
            task_count: Total number of tasks
            completed_count: Number of completed tasks
        """
        self._task_count = task_count
        self._completed_count = completed_count


class Task(BaseModel):
    """
    Represents a single task with support for hierarchical nesting.

    Tasks can be nested up to specific levels depending on the column:
    - Column 1 (Tasks): Maximum 2 levels (0-1)
    - Column 2 (Subtasks): Maximum 3 levels (0-2)
    """

    id: UUID = Field(default_factory=uuid4, description="Unique identifier for the task")
    title: str = Field(..., min_length=1, max_length=500, description="Task title/name")
    notes: Optional[str] = Field(default=None, max_length=5000, description="Optional task notes")

    # Status flags
    is_completed: bool = Field(default=False, description="Whether the task is completed")
    is_archived: bool = Field(default=False, description="Whether the task is archived")

    # Hierarchy
    parent_id: Optional[UUID] = Field(default=None, description="Parent task ID for nesting")
    level: int = Field(default=0, ge=0, le=2, description="Nesting level (0-2)")
    position: int = Field(default=0, ge=0, description="Order within siblings")

    # Relationships
    list_id: UUID = Field(..., description="ID of the list this task belongs to")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")
    archived_at: Optional[datetime] = Field(default=None, description="Archive timestamp")

    # Private attributes for computed properties
    _child_count: int = PrivateAttr(default=0)
    _completed_child_count: int = PrivateAttr(default=0)

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "title": "Complete project documentation",
                "notes": "Include API docs and user guide",
                "is_completed": False,
                "is_archived": False,
                "parent_id": None,
                "level": 0,
                "position": 0,
                "list_id": "123e4567-e89b-12d3-a456-426614174000",
                "created_at": "2025-01-14T10:00:00",
            }
        }

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: int) -> int:
        """
        Validate that the nesting level is within acceptable range.

        Args:
            v: The level value to validate

        Returns:
            The validated level value

        Raises:
            ValueError: If level is not between 0 and 2
        """
        if v < 0 or v > 2:
            raise ValueError("Task level must be between 0 and 2")
        return v

    @model_validator(mode='after')
    def validate_parent_level_consistency(self) -> 'Task':
        """
        Validate parent_id consistency with level.

        Returns:
            The validated task instance

        Raises:
            ValueError: If parent_id and level are inconsistent
        """
        # Level 0 tasks should not have a parent
        if self.level == 0 and self.parent_id is not None:
            raise ValueError("Level 0 tasks cannot have a parent_id")

        # Level 1+ tasks should have a parent
        if self.level > 0 and self.parent_id is None:
            raise ValueError(f"Level {self.level} tasks must have a parent_id")

        return self

    @computed_field
    @property
    def progress_string(self) -> str:
        """
        Generate progress string for tasks with children (e.g., "2/5").

        Returns:
            Progress string showing completed/total children, or empty string if no children
        """
        if self._child_count == 0:
            return ""
        return f"{self._completed_child_count}/{self._child_count}"

    @computed_field
    @property
    def completion_percentage(self) -> float:
        """
        Calculate completion percentage for this task's children.

        Returns:
            Percentage of completed children (0-100), or 0 if no children
        """
        if self._child_count == 0:
            return 0.0
        return round((self._completed_child_count / self._child_count) * 100, 1)

    @computed_field
    @property
    def has_children(self) -> bool:
        """
        Check if this task has any children.

        Returns:
            True if the task has children, False otherwise
        """
        return self._child_count > 0

    @computed_field
    @property
    def can_have_children_in_column1(self) -> bool:
        """
        Check if this task can have children in Column 1 context.

        Column 1 allows maximum 2 levels (0-1), so only level 0 tasks can have children.

        Returns:
            True if task can have children in Column 1, False otherwise
        """
        return self.level == 0

    @computed_field
    @property
    def can_have_children_in_column2(self) -> bool:
        """
        Check if this task can have children in Column 2 context.

        Column 2 allows maximum 3 levels (0-2), so level 0 and 1 tasks can have children.

        Returns:
            True if task can have children in Column 2, False otherwise
        """
        return self.level <= 1

    def update_child_counts(self, child_count: int, completed_child_count: int) -> None:
        """
        Update the child counts for computed properties.

        Args:
            child_count: Total number of children
            completed_child_count: Number of completed children
        """
        self._child_count = child_count
        self._completed_child_count = completed_child_count

    def mark_completed(self) -> None:
        """Mark the task as completed with timestamp."""
        self.is_completed = True
        self.completed_at = datetime.utcnow()

    def mark_incomplete(self) -> None:
        """Mark the task as incomplete, removing completion timestamp."""
        self.is_completed = False
        self.completed_at = None

    def archive(self) -> None:
        """
        Archive the task.

        Raises:
            ValueError: If task is not completed
        """
        if not self.is_completed:
            raise ValueError("Only completed tasks can be archived")
        self.is_archived = True
        self.archived_at = datetime.utcnow()

    def unarchive(self) -> None:
        """Remove the task from archive."""
        self.is_archived = False
        self.archived_at = None
