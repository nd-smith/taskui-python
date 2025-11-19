# Notepad Modal & Notes System - Planning & Research

## Feature Overview
Comprehensive notes system with:
- Quick-access notepad modal with global hotkey
- Standalone notes list (separate view from tasks)
- Notes can be associated with tasks
- Folder entity for visual organization
- Notes viewable in task details pane

## Expanded Vision
This is actually THREE interconnected features:
1. **Notes System**: Standalone note entities with their own list view
2. **Modal Interface**: Quick-capture UI via global hotkey
3. **Folder Organization**: New entity type for organizing notes (and tasks?)

## Core Requirements
- Modal interface for note-taking
- Global hotkey activation (needs definition)
- Notes stored as first-class entities (not just task.notes field)
- Separate notes list view
- Optional task association
- Folder-based organization
- Quick capture workflow

## Current System Context
**Existing Schema** (`schema.sql`):
- `task_lists` table: id, name, created_at
- `tasks` table: already has a `notes` TEXT field for task-specific notes
- Tasks have: parent_id (hierarchy), list_id (categorization), position (ordering)

**Key Insight**: Tasks already have inline notes. This feature introduces standalone note entities.

## Questions to Explore

### Notes vs Task Notes
- **Distinction**: How do standalone notes differ from task.notes field?
- **Migration**: Do we keep both? Convert task.notes to linked notes?
- **UI Clarity**: How to differentiate in UI between task inline notes and linked standalone notes?

### Folder Entity Design
- **Scope**: Do folders organize just notes, or both notes AND tasks?
- **Hierarchy**: Are folders a parent of lists, or separate organizational layer?
  - Option A: `folders > lists > tasks/notes`
  - Option B: `lists > (tasks | notes)` + `folders > notes` (parallel)
  - Option C: `folders > (tasks | notes)` (folders replace lists?)
- **Structure**: Can folders be nested? Or single-level only?
- **Relationship**: How do folders interact with existing `task_lists`?

### Notes Data Model (FINAL)
```sql
-- Notes table - standalone note entities
CREATE TABLE IF NOT EXISTS notes (
    id VARCHAR(36) PRIMARY KEY,              -- UUID
    title VARCHAR(200),                      -- Optional title
    content TEXT NOT NULL,                   -- Note content (markdown?)
    folder_id VARCHAR(36),                   -- Optional folder (NULL = unfiled)
    position INTEGER NOT NULL DEFAULT 0,     -- Order within folder
    is_archived BOOLEAN NOT NULL DEFAULT 0,  -- Archive status
    created_at DATETIME NOT NULL,            -- Creation timestamp
    updated_at DATETIME NOT NULL,            -- Last modification timestamp
    FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE SET NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_notes_folder_id ON notes(folder_id);
CREATE INDEX IF NOT EXISTS idx_notes_archived ON notes(is_archived);
CREATE INDEX IF NOT EXISTS idx_notes_created ON notes(created_at);
CREATE INDEX IF NOT EXISTS idx_notes_updated ON notes(updated_at);
```

### Folder Data Model (FINAL)
```sql
-- Folders table - organize notes (flat structure)
CREATE TABLE IF NOT EXISTS folders (
    id VARCHAR(36) PRIMARY KEY,         -- UUID
    name VARCHAR(100) NOT NULL,         -- Folder name
    position INTEGER NOT NULL DEFAULT 0, -- Display order
    created_at DATETIME NOT NULL        -- Creation timestamp
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_folders_position ON folders(position);
```

### Note-Task Link Junction Table (FINAL)
```sql
-- Many-to-many relationship between notes and tasks
CREATE TABLE IF NOT EXISTS note_task_links (
    id VARCHAR(36) PRIMARY KEY,          -- UUID
    note_id VARCHAR(36) NOT NULL,        -- Foreign key to notes
    task_id VARCHAR(36) NOT NULL,        -- Foreign key to tasks
    created_at DATETIME NOT NULL,        -- When link was created
    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    UNIQUE(note_id, task_id)             -- Prevent duplicate links
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_note_task_links_note_id ON note_task_links(note_id);
CREATE INDEX IF NOT EXISTS idx_note_task_links_task_id ON note_task_links(task_id);
```

### UI/UX
- **Modal design**: Size, placement, keyboard shortcuts
- **Editor type**: Plain text, rich text, or markdown?
- **Save behavior**: Auto-save, manual, or on-close?
- **List view**: Separate tab/pane for notes? Or integrated?
- **Folder UI**: Tree view, nested lists, tags?
- **Task details**: How to display linked notes in task pane?

### Functionality
- **Note creation flow**:
  1. Hotkey → Modal → Quick capture → Save to folder/list
  2. From task details → Create linked note
  3. From notes list → New note button
- **Association**: Can one note link to multiple tasks? Or 1:1?
- **Searchability**: Should notes be full-text searchable?
- **Filtering**: By folder, by linked/unlinked, by date?

### Technical Implementation
- Hotkey handling mechanism
- Modal rendering approach
- State management
- Storage backend
- Integration with existing codebase

### Hotkey Considerations
- Which key combination? (Ctrl+N, Ctrl+Shift+N, custom?)
- Conflict with existing hotkeys?
- Platform compatibility (Linux, Windows, Mac)
- Toggle behavior (open/close with same key)

### Integration Points
- How does this fit with existing task creation flow?
- Can notes be converted to tasks later?
- Should notes be searchable?
- Export capabilities?

## Use Cases
1. Quick thought capture during work
2. Temporary reminders not worthy of full tasks
3. Meeting notes or brainstorming
4. Copy-paste staging area
5. Quick command/snippet storage

## Design Decisions ✅

### 1. Folder Scope & Hierarchy
**DECIDED**: Notes only (folders are note-specific)
- Folders organize notes, NOT tasks
- `task_lists` remains unchanged for task organization
- Future: May extend folders to tasks if successful

### 2. Note-Task Relationship
**DECIDED**: Many:many (no restrictions)
- Notes can link to multiple tasks
- Tasks can have multiple linked notes
- Need junction table: `note_task_links`

### 3. Existing `tasks.notes` Field
**DECIDED**: Keep both
- `tasks.notes` TEXT field stays (inline quick notes)
- Standalone notes are separate entities (richer content, linkable)
- Both serve different purposes

### 4. Folder Structure
**DECIDED**: Flat structure (for now)
- No nested folders initially
- Folders have: id, name, position, created_at
- No folder types/categories yet
- Simple flat list in UI

### 5. Modal Behavior
**DECIDED**: Always create new unlinked note
- Hotkey → Modal → Create new note
- Note appears in notes list (unlinked)
- Note shows in "list tab" view
- Future: May add context-aware behavior

### 6. Timestamps & Ordering
**DECIDED**: Capture for future flexibility
- `created_at` - when note was created
- `updated_at` - last modification time
- Enables future sorting options (newest, oldest, recently modified)

## Open Questions
- [ ] Should notes have tags in addition to folders?
- [ ] Should notes support markdown formatting?
- [ ] Should there be note templates?
- [ ] Version history for notes?
- [ ] Sharing/export capabilities?
- [ ] Should folders be nested or flat?
- [ ] Color coding for folders?
- [ ] Icons for different note types?

## Architecture Considerations
- Minimal dependencies
- Fast load time (modal should appear instantly)
- Non-blocking UI
- Graceful failure handling

## Implementation Phases (REVISED)

### Phase 1: Database Foundation
**Goal**: Core data infrastructure for notes system
- [ ] Create `notes` table schema
- [ ] Create `folders` table schema
- [ ] Create `note_task_links` junction table
- [ ] Write migration script
- [ ] Add to `schema.sql` for documentation

### Phase 2: Models & Services
**Goal**: Business logic layer
- [ ] `Note` model class (data structure)
- [ ] `Folder` model class (data structure)
- [ ] `NoteTaskLink` model class (data structure)
- [ ] `NoteService` (CRUD operations for notes)
- [ ] `FolderService` (CRUD operations for folders)
- [ ] Link/unlink operations (note-task associations)

### Phase 3: Basic UI Components
**Goal**: Visual building blocks
- [ ] Note editor component (text area, title input)
- [ ] Note list item component (display in list)
- [ ] Folder list item component
- [ ] Notes list container (shows all notes)
- [ ] Basic styling to match existing UI

### Phase 4: Notes View/Screen
**Goal**: Dedicated notes interface
- [ ] Notes screen/tab (new main view)
- [ ] Folder sidebar/section
- [ ] Unfiled notes section
- [ ] Note detail pane (when selected)
- [ ] Create/delete folder functionality
- [ ] Create/delete note functionality
- [ ] Move notes between folders (drag-drop or menu)

### Phase 5: Modal & Hotkey
**Goal**: Quick-capture workflow
- [ ] Modal component (popup dialog)
- [ ] Hotkey registration (global listener)
- [ ] Hotkey handler (open modal)
- [ ] Quick capture form (title + content)
- [ ] Save → creates unlinked note
- [ ] Auto-focus on content field
- [ ] Escape/cancel handling

### Phase 6: Task Integration
**Goal**: Link notes to tasks
- [ ] Display linked notes in task details pane
- [ ] "Link to task" UI in note editor
- [ ] "Unlink from task" functionality
- [ ] Show task associations in note view
- [ ] Navigate from note → linked tasks
- [ ] Navigate from task → linked notes

### Phase 7: Polish & Refinement
**Goal**: Quality of life improvements
- [ ] Search/filter notes by title/content
- [ ] Archive/unarchive notes
- [ ] Keyboard shortcuts for notes view
- [ ] Confirmation dialogs (delete folder, etc.)
- [ ] Empty states (no notes, no folders)
- [ ] Loading states
- [ ] Error handling and user feedback

## Architectural Impact Analysis

### Database Changes
- New tables: `notes`, possibly `folders`
- Potential migration of existing `tasks.notes` data
- New indexes for performance
- Foreign key relationships

### Code Structure
```
taskui/
  models/
    note.py          # New
    folder.py        # New
  services/
    note_service.py  # New
    folder_service.py # New
  ui/
    components/
      note_modal.py  # New
      note_list.py   # New
      note_editor.py # New
    screens/
      notes_screen.py # New (if separate view)
```

### Integration Points
- **Hotkey system**: New global hotkey handler
- **Task details**: Extend to show linked notes
- **Navigation**: Add notes view to main navigation
- **State management**: Notes state, folder state, modal state
- **Database**: Schema updates, migrations

## Trade-offs & Considerations

### Complexity vs Features
- **Simple**: Notes only, no folders, no task linking → Fast to implement
- **Medium**: Notes + folders, simple task linking → Balanced approach
- **Complex**: Full-featured with folders, many:many relationships, tags → Longer development

### Backwards Compatibility
- Existing `tasks.notes` field: Keep or migrate?
- Database migration strategy for existing users
- UI changes impact on current workflow

### Performance
- Notes list could grow large → Need pagination/virtual scrolling
- Search performance → Full-text search indexing?
- Modal load time → Lazy loading? Pre-caching?

## Next Steps
1. **Decision Phase**: Answer key design decisions above
2. **Schema Design**: Finalize database schema based on decisions
3. **UI Mockups**: Sketch out the UI flows and layouts
4. **Review Codebase**: Study existing modal/hotkey patterns in taskui
5. **Technical Spike**: Prototype hotkey handling and modal rendering
6. **Implementation Plan**: Create detailed task breakdown for Phase 1

## Remaining Open Questions

### Still To Decide
1. **Folder creation**: Where in UI? Dedicated button? Right-click menu?
2. **Note display**: How to show truncated content in list view?
3. **Deletion**: Soft delete (archive) or hard delete for notes/folders?

### Recently Decided ✅
1. **Hotkey combination**: `t` key (simple, easy to test)
2. **Note title behavior**: Optional - auto-generate from first line of content if blank
3. **Content format**: Plain text (no markdown, keep it simple)
4. **Note editor**: Simple textarea (plain text editing)

### Future Enhancements (Post-MVP)
- Tags for notes (in addition to folders)
- Note templates
- Rich text formatting toolbar
- Note version history
- Export capabilities (markdown, PDF, etc.)
- Full-text search
- Note sharing/collaboration
- Nested folders
- Folder color coding
- Context-aware modal behavior (linked notes when viewing task)

## Summary of Decisions Made

### Data Model
✅ **Folders**: Notes only, flat structure
✅ **Note-Task Linking**: Many:many (junction table)
✅ **Existing task.notes**: Keep it (different purpose)
✅ **Timestamps**: Capture created_at and updated_at
✅ **Database**: 3 new tables (notes, folders, note_task_links)

### User Interface
✅ **Modal behavior**: Always create new unlinked note
✅ **Hotkey**: `t` key for quick capture
✅ **Note titles**: Optional, auto-generate from first line if blank
✅ **Content format**: Plain text (no markdown)
✅ **Editor**: Simple textarea component

## Implementation Details

### Auto-Title Generation Logic
When saving a note with blank title:
1. Extract first line of content (up to newline or max 50 chars)
2. Trim whitespace
3. If result is empty, use timestamp: "Note - YYYY-MM-DD HH:MM"
4. Store generated title in `notes.title` field

Example:
```python
def generate_title_from_content(content: str) -> str:
    if not content or not content.strip():
        return f"Note - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    first_line = content.split('\n')[0].strip()
    if len(first_line) > 50:
        first_line = first_line[:47] + "..."

    return first_line if first_line else f"Note - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
```

### Hotkey Behavior
- **Key**: `t` (lowercase, no modifiers for now)
- **Action**: Open modal, focus content field
- **Scope**: Global (works from any view)
- **Toggle**: Press `t` → modal opens, press Escape → modal closes
- Future: May need modifier (Ctrl+t) if conflicts arise with text input

## Next Session Goals
1. Answer remaining open questions (hotkey, title behavior, format)
2. Review existing codebase structure (models, services, UI patterns)
3. Identify any similar existing patterns (modals, hotkeys, list views)
4. Begin Phase 1 implementation (database schema)

---
*Session: Research & Planning*
*Implementation: Future session*
*Status: Ready for technical review & implementation start* ✅
