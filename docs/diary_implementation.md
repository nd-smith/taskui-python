# Diary Feature Implementation Plan

## Overview
Add a quick diary/progress logging feature to TaskUI that allows users to capture brief status updates on tasks with minimal friction.

### User Story
As a user, when I have a task selected, I want to press 'd' to quickly log a one or two sentence status update with an automatic timestamp, so I can track progress without breaking my workflow.

### Design Principles
- **Frictionless**: Minimal clicks, fast keyboard-driven workflow
- **Simple**: No icons, no complex UI, just timestamps and text
- **Focused**: Quick updates only, not long-form journaling

---

## Requirements

### Functional Requirements
1. User can press 'd' key when task is selected to open diary entry modal
2. Modal provides text input for brief status update (1-2 sentences)
3. Entries are automatically timestamped on save
4. Last 3 diary entries display in the detail panel
5. User can delete entries via the edit task modal
6. Maximum 100 diary entries per task
7. Timestamp format: `m/d/y h:mm AM/PM` (e.g., `1/19/2025 2:32 PM`)

### Non-Functional Requirements
- Follows existing modal pattern and UI conventions
- Maintains current One Monokai theme consistency
- Database schema change with migration
- Configuration-driven display count

---

## Data Model Changes

### New Model: DiaryEntry

**File**: `taskui/models.py`

```python
class DiaryEntry(BaseModel):
    """
    Represents a brief progress update for a task.

    Maximum 100 entries per task. Entries are append-only with
    deletion support via the task edit modal.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    task_id: UUID = Field(..., description="ID of the task this entry belongs to")
    content: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Brief status update (1-2 sentences)"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of entry creation"
    )

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174002",
                "task_id": "123e4567-e89b-12d3-a456-426614174001",
                "content": "Fixed authentication bug, moving to API integration",
                "created_at": "2025-01-19T14:32:00",
            }
        }

    def format_timestamp(self) -> str:
        """
        Format the created_at timestamp for display.

        Returns:
            Formatted timestamp string in m/d/y h:mm AM/PM format
            Example: "1/19/2025 2:32 PM"
        """
        return self.created_at.strftime("%-m/%-d/%Y %-I:%M %p")
```

**Notes**:
- `strftime` format uses `%-m`, `%-d`, `%-I` (Unix) for no zero-padding
- Windows compatibility may require `%#m`, `%#d`, `%#I` instead
- Consider platform detection or config for format string

---

## Database Schema Changes

### New Table: diary_entries

**File**: `taskui/database.py` (schema section)

```sql
CREATE TABLE IF NOT EXISTS diary_entries (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_diary_task_id ON diary_entries(task_id);
CREATE INDEX IF NOT EXISTS idx_diary_created_at ON diary_entries(created_at);
```

**Migration Strategy**:
1. Add migration script in `taskui/database.py` or separate migrations file
2. Detect schema version and apply migration on startup
3. Existing tables remain unchanged
4. New installations get full schema automatically

### SQLAlchemy Model

**File**: `taskui/database.py`

```python
class DiaryEntryDB(Base):
    """SQLAlchemy model for diary entries."""
    __tablename__ = "diary_entries"

    id = Column(String, primary_key=True)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship back to task
    task = relationship("TaskDB", back_populates="diary_entries")
```

**Update TaskDB model**:
```python
class TaskDB(Base):
    # ... existing fields ...

    # Add relationship
    diary_entries = relationship(
        "DiaryEntryDB",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="DiaryEntryDB.created_at.desc()"
    )
```

---

## Service Layer

### New Service: DiaryService

**File**: `taskui/services/diary_service.py`

```python
"""Service for managing task diary entries."""

from typing import List, Optional
from uuid import UUID
from datetime import datetime

from taskui.models import DiaryEntry
from taskui.database import get_session, DiaryEntryDB
from taskui.logging_config import get_logger

logger = get_logger(__name__)


class DiaryService:
    """Service for managing diary entries."""

    MAX_ENTRIES_PER_TASK = 100

    @staticmethod
    def create_entry(task_id: UUID, content: str) -> DiaryEntry:
        """
        Create a new diary entry for a task.

        Enforces the maximum entry limit per task by deleting
        oldest entries if limit is exceeded.

        Args:
            task_id: ID of the task
            content: Brief status update text

        Returns:
            The created DiaryEntry

        Raises:
            ValueError: If content is empty or invalid
        """
        # Validate content
        if not content or not content.strip():
            raise ValueError("Diary entry content cannot be empty")

        content = content.strip()
        if len(content) > 500:
            raise ValueError("Diary entry content exceeds 500 characters")

        # Check entry count and enforce limit
        with get_session() as session:
            entry_count = session.query(DiaryEntryDB).filter_by(
                task_id=str(task_id)
            ).count()

            if entry_count >= DiaryService.MAX_ENTRIES_PER_TASK:
                # Delete oldest entry to make room
                oldest = session.query(DiaryEntryDB).filter_by(
                    task_id=str(task_id)
                ).order_by(DiaryEntryDB.created_at.asc()).first()

                if oldest:
                    logger.info(
                        f"Deleting oldest diary entry (id={oldest.id}) "
                        f"to enforce limit of {DiaryService.MAX_ENTRIES_PER_TASK}"
                    )
                    session.delete(oldest)
                    session.flush()

            # Create new entry
            entry = DiaryEntry(
                task_id=task_id,
                content=content,
                created_at=datetime.utcnow()
            )

            db_entry = DiaryEntryDB(
                id=str(entry.id),
                task_id=str(entry.task_id),
                content=entry.content,
                created_at=entry.created_at
            )

            session.add(db_entry)
            session.commit()
            session.refresh(db_entry)

            logger.info(f"Created diary entry for task_id={task_id}")
            return entry

    @staticmethod
    def get_entries_for_task(
        task_id: UUID,
        limit: Optional[int] = None
    ) -> List[DiaryEntry]:
        """
        Get diary entries for a task, ordered newest first.

        Args:
            task_id: ID of the task
            limit: Optional limit on number of entries to return

        Returns:
            List of DiaryEntry objects, newest first
        """
        with get_session() as session:
            query = session.query(DiaryEntryDB).filter_by(
                task_id=str(task_id)
            ).order_by(DiaryEntryDB.created_at.desc())

            if limit:
                query = query.limit(limit)

            db_entries = query.all()

            return [
                DiaryEntry(
                    id=UUID(db_entry.id),
                    task_id=UUID(db_entry.task_id),
                    content=db_entry.content,
                    created_at=db_entry.created_at
                )
                for db_entry in db_entries
            ]

    @staticmethod
    def delete_entry(entry_id: UUID) -> bool:
        """
        Delete a diary entry.

        Args:
            entry_id: ID of the entry to delete

        Returns:
            True if deleted, False if not found
        """
        with get_session() as session:
            db_entry = session.query(DiaryEntryDB).filter_by(
                id=str(entry_id)
            ).first()

            if not db_entry:
                logger.warning(f"Diary entry not found: {entry_id}")
                return False

            session.delete(db_entry)
            session.commit()
            logger.info(f"Deleted diary entry: {entry_id}")
            return True

    @staticmethod
    def get_entry_count(task_id: UUID) -> int:
        """
        Get the total number of diary entries for a task.

        Args:
            task_id: ID of the task

        Returns:
            Number of diary entries
        """
        with get_session() as session:
            return session.query(DiaryEntryDB).filter_by(
                task_id=str(task_id)
            ).count()
```

---

## UI Components

### 1. New Component: DiaryModal

**File**: `taskui/ui/components/diary_modal.py`

```python
"""Quick diary entry modal for TaskUI.

Provides a minimal modal for capturing brief status updates on tasks.
"""

from typing import Optional
from uuid import UUID

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static, TextArea
from textual.message import Message
from textual.binding import Binding

from taskui.logging_config import get_logger
from taskui.models import Task
from taskui.ui.theme import (
    BACKGROUND,
    FOREGROUND,
    BORDER,
    SELECTION,
    LEVEL_0_COLOR,
    LEVEL_1_COLOR,
    LEVEL_2_COLOR,
    MODAL_OVERLAY_BG,
)

logger = get_logger(__name__)


class DiaryModal(ModalScreen):
    """Modal for quick diary entry creation.

    Displays a simple form with:
    - Task context (title)
    - TextArea for brief update
    - Save/Cancel buttons

    Messages:
        EntryCreated: Emitted when entry is saved
        EntryCancelled: Emitted when modal is cancelled
    """

    DEFAULT_CSS = f"""
    DiaryModal {{
        align: center middle;
        background: {MODAL_OVERLAY_BG};
    }}

    DiaryModal > Container {{
        width: 70;
        height: auto;
        background: {BACKGROUND};
        border: thick {LEVEL_0_COLOR};
        padding: 1 2;
    }}

    DiaryModal .modal-header {{
        width: 100%;
        height: 3;
        content-align: center middle;
        text-style: bold;
        color: {LEVEL_0_COLOR};
        border-bottom: solid {BORDER};
        margin-bottom: 1;
    }}

    DiaryModal .task-context {{
        width: 100%;
        height: auto;
        color: {LEVEL_1_COLOR};
        text-align: center;
        margin-bottom: 1;
        padding: 0 1;
    }}

    DiaryModal .field-label {{
        width: 100%;
        height: 1;
        color: {FOREGROUND};
        margin-top: 1;
    }}

    DiaryModal TextArea {{
        width: 100%;
        height: 6;
        margin-bottom: 1;
        background: {BORDER};
        color: {FOREGROUND};
        border: solid {SELECTION};
    }}

    DiaryModal TextArea:focus {{
        border: solid {LEVEL_0_COLOR};
    }}

    DiaryModal .button-container {{
        width: 100%;
        height: 3;
        align: center middle;
        margin-top: 1;
        layout: horizontal;
    }}

    DiaryModal Button {{
        margin: 0 1;
        min-width: 15;
        background: {SELECTION};
        color: {FOREGROUND};
        border: solid {BORDER};
    }}

    DiaryModal Button:hover {{
        background: {BORDER};
        border: solid {LEVEL_0_COLOR};
    }}

    DiaryModal Button.save-button {{
        border: solid {LEVEL_1_COLOR};
    }}

    DiaryModal Button.save-button:hover {{
        background: {LEVEL_1_COLOR};
        color: {BACKGROUND};
    }}

    DiaryModal Button.cancel-button {{
        border: solid {LEVEL_2_COLOR};
    }}

    DiaryModal Button.cancel-button:hover {{
        background: {LEVEL_2_COLOR};
        color: {BACKGROUND};
    }}
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
        Binding("ctrl+s", "save", "Save", priority=True),
    ]

    def __init__(self, task: Task, **kwargs) -> None:
        """Initialize the diary modal.

        Args:
            task: The task to create a diary entry for
            **kwargs: Additional keyword arguments for ModalScreen
        """
        super().__init__(**kwargs)
        self.task = task

    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
        with Container():
            yield Static("📝 Quick Update", classes="modal-header")

            # Task context
            task_title = self.task.title[:50] + "..." if len(self.task.title) > 50 else self.task.title
            yield Static(f"Task: {task_title}", classes="task-context")

            # Entry field
            yield Label("Status update (1-2 sentences):", classes="field-label")
            yield TextArea(
                id="entry-input",
            )

            # Buttons
            with Container(classes="button-container"):
                yield Button("Save [Enter]", variant="success", id="save-button", classes="save-button")
                yield Button("Cancel [Esc]", variant="error", id="cancel-button", classes="cancel-button")

    def on_mount(self) -> None:
        """Focus the entry input on mount."""
        logger.info(f"DiaryModal: Opened for task_id={self.task.id}")
        entry_input = self.query_one("#entry-input", TextArea)
        entry_input.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        logger.debug(f"DiaryModal: Button pressed - {event.button.id}")
        if event.button.id == "save-button":
            self.action_save()
        elif event.button.id == "cancel-button":
            self.action_cancel()

    def action_save(self) -> None:
        """Save the entry and dismiss the modal."""
        entry_input = self.query_one("#entry-input", TextArea)
        content = entry_input.text.strip() if entry_input.text else ""

        # Validate content
        if not content:
            logger.warning("DiaryModal: Save cancelled - empty content")
            return

        logger.info(f"DiaryModal: Entry saved - content_length={len(content)}")

        # Post EntryCreated message
        self.post_message(self.EntryCreated(content=content))

        # Dismiss modal
        self.dismiss()

    def action_cancel(self) -> None:
        """Cancel and dismiss the modal."""
        logger.info("DiaryModal: Cancelled")
        self.post_message(self.EntryCancelled())
        self.dismiss()

    class EntryCreated(Message):
        """Message emitted when a diary entry is created."""

        def __init__(self, content: str) -> None:
            super().__init__()
            self.content = content

    class EntryCancelled(Message):
        """Message emitted when diary entry is cancelled."""
        pass
```

### 2. Update Component: DetailPanel

**File**: `taskui/ui/components/detail_panel.py`

**Changes Required**:

1. Import DiaryService:
```python
from taskui.services.diary_service import DiaryService
```

2. Add method to get diary entries display count from config:
```python
def _get_diary_display_count(self) -> int:
    """Get number of diary entries to display from config."""
    # TODO: Get from config, default to 3
    return 3
```

3. Update the `update_content()` method to include diary entries section:

```python
def update_content(self, task: Task) -> None:
    """Update the detail panel with task information.

    Args:
        task: The task to display details for
    """
    if not task:
        self.clear()
        return

    # ... existing code for title, notes, metadata ...

    # Add diary entries section
    diary_count = self._get_diary_display_count()
    entries = DiaryService.get_entries_for_task(task.id, limit=diary_count)

    if entries:
        content.append("\n\n--- Recent Updates ---\n")
        for entry in entries:
            timestamp = entry.format_timestamp()
            content.append(f"[{timestamp}] {entry.content}\n")

    # ... rest of existing code ...
```

### 3. Update Component: TaskModal (Edit Mode)

**File**: `taskui/ui/components/task_modal.py`

**Changes Required**:

1. Import DiaryService:
```python
from taskui.services.diary_service import DiaryService
```

2. Add diary entries section to `compose()` method when in edit mode:

```python
def compose(self) -> ComposeResult:
    """Compose the modal layout."""
    with Container():
        # ... existing header, context, title, notes ...

        # Add diary entries section for edit mode
        if self.mode == "edit" and self.edit_task:
            yield Label("Diary Entries:", classes="field-label")

            entries = DiaryService.get_entries_for_task(self.edit_task.id)

            if entries:
                with Vertical(id="diary-entries-list"):
                    for entry in entries:
                        with Container(classes="diary-entry-item"):
                            timestamp = entry.format_timestamp()
                            yield Static(
                                f"[{timestamp}] {entry.content}",
                                classes="diary-entry-text"
                            )
                            yield Button(
                                "Delete",
                                id=f"delete-diary-{entry.id}",
                                classes="delete-diary-button"
                            )
            else:
                yield Static("No diary entries yet", classes="no-entries")

        # ... existing buttons section ...
```

3. Add CSS for diary entries section:
```python
DEFAULT_CSS = f"""
    # ... existing CSS ...

    TaskCreationModal .diary-entry-item {{
        layout: horizontal;
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }}

    TaskCreationModal .diary-entry-text {{
        width: 1fr;
        color: {FOREGROUND};
    }}

    TaskCreationModal .delete-diary-button {{
        width: auto;
        min-width: 10;
        margin-left: 1;
    }}

    TaskCreationModal .no-entries {{
        width: 100%;
        color: {LEVEL_2_COLOR};
        text-align: center;
        margin-bottom: 1;
    }}
"""
```

4. Handle delete button presses in `on_button_pressed()`:
```python
def on_button_pressed(self, event: Button.Pressed) -> None:
    """Handle button press events."""
    logger.debug(f"TaskModal: Button pressed - {event.button.id}")

    if event.button.id == "save-button":
        self.action_save()
    elif event.button.id == "cancel-button":
        self.action_cancel()
    elif event.button.id and event.button.id.startswith("delete-diary-"):
        # Extract entry ID and delete
        entry_id_str = event.button.id.replace("delete-diary-", "")
        entry_id = UUID(entry_id_str)

        if DiaryService.delete_entry(entry_id):
            logger.info(f"TaskModal: Deleted diary entry {entry_id}")
            # Refresh the modal to update the list
            self.refresh()
        else:
            logger.error(f"TaskModal: Failed to delete diary entry {entry_id}")
```

---

## Application Integration

### Keybinding Registration

**File**: `taskui/ui/app.py`

1. Add binding for 'd' key:
```python
BINDINGS = [
    # ... existing bindings ...
    Binding("d", "open_diary_modal", "Quick Update", show=True),
    # ... rest of bindings ...
]
```

2. Add action handler:
```python
def action_open_diary_modal(self) -> None:
    """Open diary modal for the selected task."""
    from taskui.ui.components.diary_modal import DiaryModal

    # Get currently selected task
    selected_task = self._get_selected_task()

    if not selected_task:
        logger.warning("No task selected for diary entry")
        return

    logger.info(f"Opening diary modal for task_id={selected_task.id}")

    # Push the diary modal
    self.push_screen(
        DiaryModal(task=selected_task),
        callback=self._handle_diary_modal_result
    )

def _handle_diary_modal_result(self, result: Optional[DiaryModal.EntryCreated]) -> None:
    """Handle the result from diary modal.

    Args:
        result: The EntryCreated message or None if cancelled
    """
    if result is None:
        logger.info("Diary modal cancelled")
        return

    # This is called via screen callback, handle EntryCreated message separately
    pass
```

3. Add message handler for DiaryModal.EntryCreated:
```python
def on_diary_modal_entry_created(self, message: DiaryModal.EntryCreated) -> None:
    """Handle diary entry creation.

    Args:
        message: The EntryCreated message
    """
    from taskui.services.diary_service import DiaryService

    selected_task = self._get_selected_task()

    if not selected_task:
        logger.error("No task selected when saving diary entry")
        return

    try:
        DiaryService.create_entry(
            task_id=selected_task.id,
            content=message.content
        )
        logger.info(f"Created diary entry for task_id={selected_task.id}")

        # Refresh detail panel to show new entry
        self._refresh_detail_panel()

    except ValueError as e:
        logger.error(f"Failed to create diary entry: {e}")
        # TODO: Show error notification to user
```

---

## Configuration

### Config File Update

**File**: `taskui/config.py` (or wherever config is managed)

Add configuration option:
```python
# Diary settings
diary_entries_to_show: int = 3  # Number of diary entries to display in detail panel
```

**Usage in DetailPanel**:
```python
def _get_diary_display_count(self) -> int:
    """Get number of diary entries to display from config."""
    from taskui.config import get_config
    config = get_config()
    return config.get("diary_entries_to_show", 3)
```

---

## Testing Strategy

### Unit Tests

**File**: `tests/test_diary_service.py`
- Test `create_entry()` with valid content
- Test `create_entry()` with empty content (should fail)
- Test `create_entry()` with content > 500 chars (should fail)
- Test entry limit enforcement (101st entry deletes oldest)
- Test `get_entries_for_task()` returns correct order (newest first)
- Test `get_entries_for_task()` with limit parameter
- Test `delete_entry()` removes entry
- Test `delete_entry()` with non-existent ID returns False
- Test `get_entry_count()` returns correct count

**File**: `tests/test_diary_modal.py`
- Test modal opens with task context
- Test save with valid content posts EntryCreated message
- Test save with empty content does nothing
- Test cancel posts EntryCancelled message
- Test escape key triggers cancel
- Test ctrl+s triggers save

**File**: `tests/test_diary_integration.py`
- Test 'd' key opens modal when task selected
- Test 'd' key does nothing when no task selected
- Test diary entry appears in detail panel after creation
- Test detail panel shows correct number of entries (config-driven)
- Test diary entry deletion from edit modal
- Test detail panel updates after deletion

### Manual Testing Checklist

- [ ] Create diary entry via 'd' key shortcut
- [ ] Verify timestamp format is correct (m/d/y h:mm AM/PM)
- [ ] Verify entry appears in detail panel immediately
- [ ] Verify only last 3 entries show in detail panel
- [ ] Create 100+ entries, verify oldest is deleted
- [ ] Delete entry from edit modal
- [ ] Verify detail panel updates after deletion
- [ ] Test with empty content (should not save)
- [ ] Test with 500+ character content (should fail or truncate)
- [ ] Verify diary entries deleted when task is deleted (cascade)
- [ ] Test escape key cancels modal
- [ ] Test ctrl+s saves entry
- [ ] Verify theme consistency with existing modals

---

## Implementation Order

### Phase 1: Data Layer
1. Add `DiaryEntry` model to `models.py`
2. Add database schema and migration
3. Add `DiaryEntryDB` SQLAlchemy model
4. Update `TaskDB` with relationship
5. Implement `DiaryService` with all methods
6. Write unit tests for `DiaryService`

### Phase 2: UI Components
1. Create `DiaryModal` component
2. Write unit tests for `DiaryModal`
3. Update `DetailPanel` to display entries
4. Test detail panel with mock data

### Phase 3: Integration
1. Add keybinding to `app.py`
2. Wire up modal open/close handlers
3. Wire up `EntryCreated` message handler
4. Test full workflow (open → save → display)

### Phase 4: Edit Modal Integration
1. Update `TaskModal` edit mode to list entries
2. Add delete button handlers
3. Test deletion workflow

### Phase 5: Configuration & Polish
1. Add config option for display count
2. Update detail panel to use config
3. Final integration testing
4. Manual testing checklist verification

---

## Database Migration

### Migration Script

**File**: `taskui/database.py` or new `migrations/001_add_diary_entries.py`

```python
def migrate_add_diary_entries(session):
    """Add diary_entries table to existing database."""

    # Check if table exists
    inspector = inspect(session.bind)
    if 'diary_entries' in inspector.get_table_names():
        logger.info("diary_entries table already exists, skipping migration")
        return

    logger.info("Running migration: add diary_entries table")

    # Create table
    session.execute("""
        CREATE TABLE diary_entries (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
        )
    """)

    # Create indexes
    session.execute("""
        CREATE INDEX idx_diary_task_id ON diary_entries(task_id)
    """)

    session.execute("""
        CREATE INDEX idx_diary_created_at ON diary_entries(created_at)
    """)

    session.commit()
    logger.info("Migration completed: diary_entries table created")
```

**Run on Application Startup**:
```python
def initialize_database():
    """Initialize database and run migrations."""
    # ... existing database setup ...

    # Run migrations
    with get_session() as session:
        migrate_add_diary_entries(session)
```

---

## Edge Cases & Error Handling

### Edge Cases to Handle
1. **No task selected**: 'd' key should do nothing, log warning
2. **Empty content**: Save button should not create entry, stay in modal
3. **Content too long**: Enforce 500 char limit with validation error
4. **101st entry**: Automatically delete oldest entry to maintain limit
5. **Task deletion**: Diary entries should cascade delete (FK constraint)
6. **Concurrent edits**: Last write wins (no conflict resolution needed)
7. **Missing timestamps**: Should not happen (default in model), but handle gracefully
8. **Invalid entry ID for deletion**: Return False, log warning

### Error Messages
- Empty content: "Status update cannot be empty"
- Content too long: "Status update must be 500 characters or less"
- No task selected: (Silent - just don't open modal)
- Delete failed: (Log warning, no user notification needed)

---

## Future Enhancements (Out of Scope)

These are intentionally NOT part of this implementation but noted for future consideration:

1. **Search/Filter**: Search diary entries across all tasks
2. **Export**: Export diary entries to file (markdown, CSV)
3. **Entry types**: Tag entries as "progress", "blocker", "milestone"
4. **Edit entries**: Allow editing existing entries (currently delete + recreate)
5. **Bulk delete**: Delete all entries for a task
6. **Date range filter**: Show entries from last week/month
7. **Entry statistics**: Show total entry count, average per day
8. **Rich text**: Support markdown or formatting in entries
9. **Attachments**: Link files/screenshots to entries
10. **Multi-task view**: Aggregate diary entries across tasks

---

## Files to Create/Modify

### New Files
- `taskui/ui/components/diary_modal.py` - DiaryModal component
- `taskui/services/diary_service.py` - DiaryService for CRUD operations
- `tests/test_diary_service.py` - Unit tests for service
- `tests/test_diary_modal.py` - Unit tests for modal
- `tests/test_diary_integration.py` - Integration tests

### Modified Files
- `taskui/models.py` - Add DiaryEntry model
- `taskui/database.py` - Add DiaryEntryDB, migration, update TaskDB
- `taskui/ui/components/detail_panel.py` - Display diary entries
- `taskui/ui/components/task_modal.py` - Add diary management to edit mode
- `taskui/ui/app.py` - Add keybinding and handlers
- `taskui/config.py` - Add diary_entries_to_show config

---

## Success Criteria

Feature is considered complete when:

1. ✅ User can press 'd' with task selected to open diary modal
2. ✅ User can enter 1-2 sentence update and save with Enter or button
3. ✅ Entry is saved with automatic timestamp in m/d/y h:mm AM/PM format
4. ✅ Last 3 entries display in detail panel immediately after save
5. ✅ User can delete entries via edit task modal
6. ✅ Maximum 100 entries per task is enforced (oldest deleted automatically)
7. ✅ All unit and integration tests pass
8. ✅ Manual testing checklist is verified
9. ✅ No theme or style inconsistencies with existing UI
10. ✅ Database migration runs successfully on existing installations

---

## Notes for Developer

- **Follow existing patterns**: DiaryModal should closely mirror TaskModal structure
- **Theme consistency**: Use existing color constants from `theme.py`
- **Logging**: Follow existing logging patterns with module-level logger
- **Error handling**: Use try/except with appropriate logging, fail gracefully
- **Database sessions**: Always use context manager `with get_session():`
- **Message passing**: Use Textual's message system for component communication
- **Testing**: Run existing tests to ensure no regressions
- **Platform compatibility**: Test timestamp formatting on both Unix and Windows

**Estimated effort**: 4-6 hours for experienced developer familiar with codebase
