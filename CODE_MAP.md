# TaskUI Code Map
*Generated after bloat removal refactoring*

**Total Production Code:** 8,284 lines (down from ~11,159)

---

## Core Features

### 1. Task Management (Core CRUD)
**Total: ~1,555 lines**

| File | Lines | Purpose |
|------|-------|---------|
| `taskui/services/task_service.py` | 980 | Task CRUD, hierarchy, completion, deletion |
| `taskui/models.py` | 275 | Task & TaskList Pydantic models |
| `taskui/database.py` | 218 | SQLAlchemy ORM (TaskORM, TaskListORM) |
| `taskui/services/nesting_validation.py` | 76 | Global depth validation (MAX_DEPTH=4) |
| `taskui/__main__.py` | 6 | Application entry point |

**Capabilities:**
- Create/read/update/delete tasks
- Task hierarchy (parent-child, up to 4 levels deep)
- Task completion/uncomplete
- Position management (ordering)
- Permanent deletion (no restore)

---

### 2. List Management
**Total: ~744 lines**

| File | Lines | Purpose |
|------|-------|---------|
| `taskui/services/list_service.py` | 446 | List CRUD, task counts, list deletion |
| `taskui/ui/components/list_management_modal.py` | 298 | Create/edit/rename lists UI |

**Capabilities:**
- Multiple task lists (Work, Personal, Projects)
- Create/rename/delete lists
- List switching (1-3 keys)
- Task count tracking per list
- List deletion with migrate/delete options

---

### 3. User Interface (TUI)
**Total: ~4,144 lines**

#### Main App & Layout
| File | Lines | Purpose |
|------|-------|---------|
| `taskui/ui/app.py` | 1,348 | Main application, event handlers, navigation |
| `taskui/ui/keybindings.py` | 133 | Keyboard shortcuts configuration |

#### UI Components
| File | Lines | Purpose |
|------|-------|---------|
| `taskui/ui/components/task_modal.py` | 542 | Task create/edit modal |
| `taskui/ui/components/column.py` | 499 | Task column widget (Column 1 & 2) |
| `taskui/ui/components/list_bar.py` | 454 | List selector bar at top |
| `taskui/ui/components/list_delete_modal.py` | 388 | List deletion confirmation modal |
| `taskui/ui/components/detail_panel.py` | 344 | Task details panel (Column 3) |
| `taskui/ui/components/task_item.py` | 259 | Individual task widget rendering |

#### Styling & Theme
| File | Lines | Purpose |
|------|-------|---------|
| `taskui/ui/theme.py` | 379 | One Monokai color theme |
| `taskui/ui/base_styles.py` | 308 | Reusable CSS patterns |
| `taskui/ui/constants.py` | 13 | UI constants |

**Capabilities:**
- Three-column layout (Tasks, Subtasks, Details)
- Keyboard-driven navigation (vim-style)
- Task creation with 'a' or Enter keys
- Task editing with 'e'
- Permanent deletion with Delete/Backspace
- Completion toggle with Space
- Visual hierarchy indicators (tree lines, colors)
- Level-based color coding (20 predefined colors + algorithmic generation)

---

### 4. Thermal Printing (CORE FEATURE)
**Total: ~895 lines**

| File | Lines | Purpose |
|------|-------|---------|
| `taskui/services/cloud_print_queue.py` | 384 | AWS SQS queue for print relay |
| `taskui/services/printer_service.py` | 340 | ESC/POS thermal printer driver |
| `taskui/services/encryption.py` | 171 | AES-256-GCM encryption for print jobs |

**Capabilities:**
- Print selected task to thermal printer (press 'P')
- Cloud relay via AWS SQS (work proxy workaround)
- End-to-end AES-256-GCM encryption
- ESC/POS protocol support
- Prints task hierarchy to physical kanban cards

**Dependencies:**
- boto3 (AWS SQS)
- python-escpos (thermal printer)
- cryptography (AES-256-GCM)

---

### 5. Configuration & Logging
**Total: ~352 lines**

| File | Lines | Purpose |
|------|-------|---------|
| `taskui/config.py` | 194 | Printer & logging configuration |
| `taskui/logging_config.py` | 127 | Logging setup (file + console) |
| `taskui/config/__init__.py` | 31 | Config package (mostly backward compatibility) |

**Capabilities:**
- TOML-based printer configuration
- Configurable logging levels
- File and console logging
- Printer detail levels (MINIMAL, STANDARD, DETAILED)

---

## Feature Summary by Lines of Code

| Feature Category | Lines | % of Codebase |
|-----------------|-------|---------------|
| UI (App + Components + Theme) | 4,144 | 50% |
| Task Management (Core) | 1,555 | 19% |
| Thermal Printing | 895 | 11% |
| List Management | 744 | 9% |
| Configuration & Logging | 352 | 4% |
| Infrastructure | 594 | 7% |
| **TOTAL** | **8,284** | **100%** |

---

## Key Design Decisions

### Simplified Architecture (After Refactoring)
1. **Global Max Depth:** 4 levels (0-4) for all tasks, no column-specific rules
2. **Single Theme:** One Monokai only, no theme switching
3. **Permanent Delete:** No archive/restore functionality
4. **Two-Column View:** Column 1 shows high-level, Column 2 shows descendants

### What Was Removed
- ❌ Column-specific nesting configuration (~1,724 lines)
- ❌ Unused pre-built themes (~996 lines)
- ❌ Archive/restore functionality (~1,215 lines)
- **Total removed: ~3,935 lines (35% reduction)**

### Essential Features (Kept)
- ✅ Thermal printer via SQS (THE core feature)
- ✅ Task hierarchy (up to 4 levels)
- ✅ Multiple lists
- ✅ Keyboard-driven TUI
- ✅ Task completion tracking

---

## Lines of Code Breakdown by Directory

```
taskui/
├── ui/               4,667 lines (56%)
│   ├── app.py        1,348
│   ├── components/   2,884
│   ├── theme.py        379
│   └── base_styles     308
│
├── services/         2,227 lines (27%)
│   ├── task_service    980
│   ├── list_service    446
│   ├── cloud_print     384
│   ├── printer         340
│   └── encryption      171
│
├── models.py           275 lines (3%)
├── database.py         218 lines (3%)
├── config/             225 lines (3%)
└── other               672 lines (8%)
```

---

## Keyboard Shortcuts Reference

| Key | Action |
|-----|--------|
| `a, A` | Add new task |
| `Enter` | Create child task |
| `e, E` | Edit task |
| `Space` | Toggle completion |
| `Delete/Backspace` | **Permanently delete** task |
| `P` | Print to thermal printer |
| `↑/↓, k/j` | Navigate tasks |
| `Tab` | Switch columns |
| `1-3` | Switch lists |
| `Ctrl+N` | New list |
| `Ctrl+E` | Edit list |
| `Ctrl+D` | Delete list |
| `q` | Quit |

---

## Database Schema

**Tables:** 2
- `task_lists` - Task list metadata
- `tasks` - Task data with hierarchy

**Key Fields (tasks):**
- `id`, `title`, `notes`, `is_completed`
- `parent_id`, `level`, `position`
- `list_id` (foreign key)
- `created_at`, `completed_at`

**Removed Fields:**
- ~~`is_archived`~~ - Removed with archive functionality
- ~~`archived_at`~~ - Removed with archive functionality

---

*This map represents the codebase after removing ~3,935 lines of bloat through systematic refactoring.*
