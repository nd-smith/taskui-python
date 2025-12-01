"""
Pydantic models for JSON export/import schema.

Defines the structure for full-state sync with nested tasks and lists.
Schema versioning supports forward-compatible migrations.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


CURRENT_SCHEMA_VERSION = 1


class ConflictStrategy(str, Enum):
    """Strategy for resolving import conflicts."""

    REMOTE_WINS = "remote_wins"  # Always take remote (dangerous)
    LOCAL_WINS = "local_wins"    # Always keep local (safe but may miss updates)
    PROMPT = "prompt"            # Always ask user (safest but interactive)
    NEWER_WINS = "newer_wins"    # Timestamp comparison (default)


class ExportedTask(BaseModel):
    """
    Exported task with nested children.

    The nested children array eliminates parent/child ordering issues
    that plagued the V1 per-operation sync.
    """

    id: UUID = Field(..., description="Unique task identifier")
    title: str = Field(..., description="Task title")
    notes: Optional[str] = Field(default=None, description="Task notes")
    url: Optional[str] = Field(default=None, description="Optional URL/link")
    is_completed: bool = Field(default=False, description="Completion status")
    position: int = Field(default=0, description="Order within siblings")
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")
    children: List["ExportedTask"] = Field(default_factory=list, description="Nested child tasks")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "title": "Parent task",
                "notes": "Some notes",
                "is_completed": False,
                "position": 0,
                "created_at": "2025-01-14T10:00:00Z",
                "children": []
            }
        }
    )


class ExportedList(BaseModel):
    """
    Exported task list with all its tasks.

    Contains hierarchical tasks with nested children for atomic transfer.
    """

    id: UUID = Field(..., description="Unique list identifier")
    name: str = Field(..., description="List name")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last modification timestamp")
    tasks: List[ExportedTask] = Field(default_factory=list, description="Top-level tasks (children nested)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Work Tasks",
                "created_at": "2025-01-14T10:00:00Z",
                "updated_at": "2025-01-14T12:00:00Z",
                "tasks": []
            }
        }
    )


class ExportedState(BaseModel):
    """
    Full application state export.

    Single JSON object containing all lists and tasks for atomic sync.
    Schema version enables forward-compatible migrations.
    """

    schema_version: int = Field(default=CURRENT_SCHEMA_VERSION, description="Schema version for migrations")
    exported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Export timestamp")
    client_id: str = Field(..., description="Unique machine/client identifier")
    lists: List[ExportedList] = Field(default_factory=list, description="All task lists")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "schema_version": 1,
                "exported_at": "2025-11-26T18:00:00Z",
                "client_id": "machine-uuid-here",
                "lists": []
            }
        }
    )


def migrate_data(data: dict) -> dict:
    """
    Migrate old schema versions to current.

    Rules:
    - New fields get sensible defaults when missing
    - Unknown fields are preserved (forward compatibility)
    - Migration functions handle structural changes

    Args:
        data: Raw JSON data from import

    Returns:
        Migrated data compatible with current schema
    """
    version = data.get("schema_version", 1)

    # Future migrations go here:
    # if version < 2:
    #     data = migrate_v1_to_v2(data)
    # if version < 3:
    #     data = migrate_v2_to_v3(data)

    data["schema_version"] = CURRENT_SCHEMA_VERSION
    return data


# Enable forward references for nested ExportedTask
ExportedTask.model_rebuild()
