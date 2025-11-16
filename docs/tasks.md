# TaskUI Implementation Tasks

## Overview
This document breaks down the TaskUI project into discrete, manageable tasks optimized for Claude Code CLI workflows. Each task is sized to fit within a single context window without compacting.

**Key Principles:**
- Each task produces working, testable code
- Tasks are as independent as possible to enable parallel work
- Clear inputs/outputs and success criteria
- MVP functionality first, enhancements later


## PHASE 1: MVP CORE (Project Foundation & Basic Functionality)

### - [x] 1.1 Project Setup and Structure ⚡ [STANDALONE]
**Size:** Small | **Time:** 15 mins | **Dependencies:** None

Create the initial project structure with all directories, configuration files, and dependency management.

**Deliverables:**
- `pyproject.toml` or `requirements.txt` with all dependencies
- Project directory structure
- `.gitignore` file
- `README.md` with setup instructions
- `pytest.ini` configuration
- Basic `__init__.py` files

**Success Criteria:**
- `pip install -r requirements.txt` works
- `pytest` runs (even with no tests)
- Project structure matches specification

---

### - [x] 1.2 Data Models ⚡ [STANDALONE]
**Size:** Small | **Time:** 20 mins | **Dependencies:** 1.1

Create Pydantic models for Task and TaskList with all fields, validation, and computed properties.

**Files to create:**
- `taskui/models.py`
- `tests/test_models.py`

**Success Criteria:**
- Models validate data correctly
- Computed fields (progress_string, completion_percentage) work
- All fields have correct types
- Tests pass for model creation and validation

---

### - [x] 1.3 Database Layer ⚡ [STANDALONE]
**Size:** Medium | **Time:** 30 mins | **Dependencies:** 1.2

Implement SQLite database setup with SQLAlchemy/aiosqlite, including schema creation and connection management.

**Files to create:**
- `taskui/database.py` (engine, session, Base)
- `taskui/schema.sql` (for reference)
- `tests/test_database.py`
- `tests/conftest.py` (database fixtures)

**Success Criteria:**
- Database creates successfully
- Tables match schema specification
- Async session management works
- In-memory test database fixture works

---

### - [x] 1.4 Basic Textual App Shell 🔄 [BLOCKS: UI Tasks]
**Size:** Medium | **Time:** 30 mins | **Dependencies:** 1.1

Create the main Textual application with three-column layout and One Monokai theme.

**Files to create:**
- `taskui/ui/app.py` (main App class)
- `taskui/ui/theme.py` (One Monokai colors)
- `taskui/ui/components/__init__.py`
- `taskui/__main__.py` (entry point)

**Success Criteria:**
- App launches with `python -m taskui`
- Three columns visible with correct layout
- One Monokai theme applied
- Columns have correct headers

---

### - [x] 1.5 Task Display Components ⚡ [DEPENDS ON: 1.4]
**Size:** Medium | **Time:** 30 mins | **Dependencies:** 1.4

Create TaskItem widget and Column components for displaying tasks with proper nesting visualization.

**Files to create:**
- `taskui/ui/components/task_item.py`
- `taskui/ui/components/column.py`
- `tests/test_ui_components.py`

**Success Criteria:**
- Tasks display with correct indentation
- Tree lines (└─) render properly
- Nesting levels have distinct colors
- Selection highlighting works

---

### - [x] 1.6 Nesting Rules Engine ⚡ [STANDALONE]
**Size:** Small | **Time:** 20 mins | **Dependencies:** 1.2

Implement the core nesting logic that enforces Column 1 (max 2 levels) and Column 2 (max 3 levels) rules.

**Files to create:**
- `taskui/services/nesting_rules.py`
- `tests/test_nesting_rules.py`

**Success Criteria:**
- `can_create_child()` method works correctly
- Context-relative level calculation works
- Maximum depth enforcement works
- Comprehensive tests pass

---

### - [x] 1.7 Task Service - Create & Read ⚡ [DEPENDS ON: 1.3, 1.6]
**Size:** Large | **Time:** 45 mins | **Dependencies:** 1.3, 1.6

Implement task creation and reading operations with database persistence and nesting validation.

**Files to create:**
- `taskui/services/task_service.py` (create, read methods)
- `tests/test_task_service.py`

**Key Methods:**
- `create_task(title, notes, list_id)`
- `create_child_task(parent_id, title, notes, column)`
- `get_tasks_for_list(list_id)`
- `get_children(task_id)`
- `get_all_descendants(task_id)`

**Success Criteria:**
- Tasks save to database
- Parent-child relationships work
- Nesting limits enforced
- Can retrieve task hierarchies

---

### - [x] 1.8 Keyboard Navigation ⚡ [DEPENDS ON: 1.5]
**Size:** Medium | **Time:** 30 mins | **Dependencies:** 1.5

Implement keyboard navigation within and between columns (arrows, tab, shift+tab).

**Files to create:**
- `taskui/ui/keybindings.py`
- Update `taskui/ui/app.py` with handlers

**Success Criteria:**
- Up/Down arrows navigate within column
- Tab/Shift+Tab switches columns
- Focus indicators clearly visible
- Navigation wraps at boundaries

---

### - [x] 1.9 Task Creation Modal ⚡ [DEPENDS ON: 1.5, 1.7]
**Size:** Medium | **Time:** 35 mins | **Dependencies:** 1.5, 1.7

Create modal dialog for task creation with title and notes fields.

**Files to create:**
- `taskui/ui/components/task_modal.py`
- Update keybindings for 'N' and 'C' keys
- Update app.py to integrate modal with task_service
- `tests/test_task_modal.py`

**Success Criteria:**
- Modal appears on 'N' (new sibling) and 'C' (new child)
- Can input title and notes
- Enter saves, Escape cancels
- Modal shows context (creating sibling vs child)
- Respects nesting limits
- Tasks persist to database via task_service integration

**Implementation Notes:**
- Modal component should be fully functional and tested independently
- App integration should wire modal results to task_service.create_task() and create_child_task()
- Database session management will be added in Story 1.16 if not yet available

---

### - [x] 1.10 Column 2 Dynamic Updates ⚡ [DEPENDS ON: 1.7, 1.8]
**Size:** Medium | **Time:** 30 mins | **Dependencies:** 1.7, 1.8

Implement Column 2 to show children of Column 1 selection with dynamic header.

**Files to create:**
- `taskui/ui/components/column2.py` (if needed)
- Update app.py selection handler

**Success Criteria:**
- Column 2 updates when Column 1 selection changes
- Header shows "[Parent] Subtasks"
- Levels are context-relative (start at 0)
- Empty state when no children

---

### - [x] 1.11 Task Service - Update & Delete ⚡ [DEPENDS ON: 1.7]
**Size:** Medium | **Time:** 30 mins | **Dependencies:** 1.7

Complete CRUD operations with update and delete functionality.

**Files to update:**
- `taskui/services/task_service.py` (update, delete methods)
- `tests/test_task_service.py`

**Key Methods:**
- `update_task(task_id, title, notes)`
- `delete_task(task_id)` (handle children)
- `move_task(task_id, new_parent_id, position)`

**Success Criteria:**
- Can update task properties
- Delete handles cascade properly
- Position/order maintained
- Database consistency preserved

---

### - [x] 1.12 Task Editing ⚡ [DEPENDS ON: 1.9, 1.11]
**Size:** Small | **Time:** 20 mins | **Dependencies:** 1.9, 1.11

Add edit functionality to existing tasks (press 'E' to edit selected task).

**Files to update:**
- Update `taskui/ui/components/task_modal.py` for edit mode
- Add 'E' key handler
- Update task service integration

**Success Criteria:**
- 'E' opens modal with existing task data
- Can modify title and notes
- Save updates database
- UI refreshes after edit

---

### - [x] 1.13 Column 3 Detail View ⚡ [DEPENDS ON: 1.8]
**Size:** Medium | **Time:** 25 mins | **Dependencies:** 1.8

Implement Column 3 to show detailed task information and metadata.

**Files to create:**
- `taskui/ui/components/detail_panel.py`
- Update selection handlers

**Success Criteria:**
- Shows task title, dates, status
- Shows complete hierarchy path
- Shows parent information
- Displays notes
- Shows max nesting warning when applicable

---

### - [x] 1.14 List Management ⚡ [DEPENDS ON: 1.3]
**Size:** Small | **Time:** 20 mins | **Dependencies:** 1.3

Create default lists (Work, Home, Personal) and list bar display.

**Files to create:**
- `taskui/services/list_service.py`
- `taskui/ui/components/list_bar.py`
- Database migration/seed script

**Success Criteria:**
- Three default lists created on first run
- List bar shows all lists
- Active list highlighted
- Can store list-specific tasks

---

### - [x] 1.15 Data Persistence & Auto-save ⚡ [DEPENDS ON: 1.7, 1.11]
**Size:** Small | **Time:** 20 mins | **Dependencies:** 1.7, 1.11

Implement automatic saving and session persistence.

**Files to update:**
- Add auto-save to all modification operations
- Ensure database commits properly
- Add error recovery

**Success Criteria:**
- All changes persist immediately
- App restores state on restart
- No data loss on crash
- Database transactions handled correctly

---

### - [x] 1.16 MVP Integration & Testing 🏁 [DEPENDS ON: ALL MVP]
**Size:** Large | **Time:** 45 mins | **Dependencies:** All MVP tasks

Integration testing and bug fixes for complete MVP functionality.

**Files to create:**
- `tests/test_integration_mvp.py`
- Bug fixes as needed

**Key Integration Points:**
- Wire app.py database session to task_service
- Complete modal-to-database persistence flow (1.9)
- Column updates on task creation/modification (1.10)
- Ensure all keyboard shortcuts work end-to-end

**Success Criteria:**
- Can create nested task hierarchy via modal (N/C keys)
- Tasks persist to database and reload on app restart
- All CRUD operations work end-to-end
- Navigation is smooth across all columns
- Column 2 updates when Column 1 selection changes
- Data persists across restarts
- No critical bugs


## PHASE 1.1: LOGGING INFRASTRUCTURE & IMPLEMENTATION

### - [x] 1.1.1 Core Logging Infrastructure ⚡ [STANDALONE]
**Size:** Small | **Time:** 20 mins | **Dependencies:** None

Create centralized file-based logging configuration module with rotating log files.

**Files to create:**
- `taskui/logging_config.py` (logging setup and configuration)
 
**Implementation:**
- `LOG_DIR`, `LOG_FILE` constants (`~/.taskui/logs/taskui.log`)
- `setup_logging()` function with RotatingFileHandler
  - 10MB max file size
  - 5 backup files
  - Structured format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- `get_logger(name)` helper function
- Environment variable support (`TASKUI_LOG_LEVEL`)

**Files to update:**
- `taskui/__main__.py` - Call `setup_logging()` on startup

**Success Criteria:**
- Log directory created automatically at `~/.taskui/logs/`
- Log file created on first log message
- Log format includes timestamp, module, level, message
- Environment variable `TASKUI_LOG_LEVEL` controls verbosity
- Basic smoke test: import and call `setup_logging()`


### - [x] 1.1.2 Database & Service Layer Logging ⚡ [DEPENDS ON: 1.1.1]
**Size:** Small | **Time:** 20 mins | **Dependencies:** 1.1.1

Integrate logging into database and service modules with comprehensive error tracking.

**Files to update:**
- `taskui/database.py`
  - Add logger instance: `logger = get_logger(__name__)`
  - Log database initialization, connection events
  - Log errors with `exc_info=True`

- `taskui/services/task_service.py`
  - Add logger instance
  - INFO: Task CRUD operations (created, updated, deleted)
  - DEBUG: Task state changes, validation
  - ERROR: Database errors, constraint violations

- `taskui/services/list_service.py`
  - Add logger instance
  - INFO: List operations
  - ERROR: List-related errors

**Success Criteria:**
- Logger instances added to all service modules
- CRUD operations logged at INFO level
- All exceptions logged with tracebacks
- Run app and verify service logs appear in `taskui.log`


### - [x] 1.1.3 UI & Component Logging ⚡ [DEPENDS ON: 1.1.1]
**Size:** Small | **Time:** 20 mins | **Dependencies:** 1.1.1

Integrate logging into UI application and components with event tracking.

**Files to update:**
- `taskui/ui/app.py`
  - Add logger instance: `logger = get_logger(__name__)`
  - INFO: App lifecycle (mount, exit)
  - DEBUG: Key press events, focus changes, column switches
  - ERROR: UI-related errors

- `taskui/ui/components/*.py` (TaskItem, Column, Modal, etc.)
  - Add logger instances to key components
  - DEBUG: Component state changes, interactions
  - ERROR: Component errors

**Cleanup Tasks:**
- Search codebase for `print()` statements
- Replace with appropriate logger calls
- Verify no stdout/stderr writes remain

**Success Criteria:**
- Logger instances added to app and components
- App lifecycle events logged
- Key interactions logged at DEBUG level
- No print statements remain in codebase
- TUI display unaffected by logging


### - [x] 1.1.4 Textual Devtools Integration & Testing 🧪 [DEPENDS ON: 1.1.1]
**Size:** Small | **Time:** 20 mins | **Dependencies:** 1.1.1

Add Textual devtools handler for development and create comprehensive tests.

**Files to update:**
- `taskui/logging_config.py`
  - Add `use_textual_handler` parameter to `setup_logging()`
  - Import and configure `TextualHandler` when enabled
  - Graceful fallback if TextualHandler unavailable

- `taskui/__main__.py`
  - Detect dev mode (`--dev` flag or `TEXTUAL_DEVTOOLS` env var)
  - Pass `use_textual_handler=is_dev_mode` to `setup_logging()`

**Files to create:**
- `tests/test_logging_config.py`
  - Test log directory creation
  - Test log file creation and writing
  - Test per-module logger naming
  - Test log rotation (mock large file writes)
  - Test environment variable log level control

**Manual Testing:**
- Run with `TASKUI_LOG_LEVEL=DEBUG python -m taskui`
- Verify logs capture all events
- Test log rotation by generating large logs
- Run with `textual run --dev taskui/__main__.py`
- Verify logs appear in devtools console

**Success Criteria:**
- TextualHandler integrates in dev mode
- All tests pass
- Log rotation verified (5 backup files created)
- Manual testing confirms DEBUG logs capture detailed events
- Documentation: Add logging usage to README


## PHASE 2: ENHANCED FEATURES

### - [x] 2.1 Task Completion Toggle ⚡ [DEPENDS ON: MVP]
**Size:** Small | **Time:** 20 mins | **Dependencies:** MVP

Implement Space key to toggle task completion with visual feedback.

**Files to update:**
- Add completion handler
- Update task display for completed state
- Update database

**Logging Requirements:**
- INFO: Task completion toggled (task_id, new state, timestamp)
- DEBUG: Completion key press event
- ERROR: Database update failures with exc_info=True

**Success Criteria:**
- Space toggles completion
- Visual feedback (strikethrough, checkmark, opacity)
- Completion timestamp saved
- State persists
- All completion events logged appropriately

---

### - [x] 2.2 Progress Indicators ⚡ [DEPENDS ON: 2.1]
**Size:** Small | **Time:** 20 mins | **Dependencies:** 2.1

Show parent task progress based on child completion.

**Files to update:**
- Calculate progress in task service
- Display "2/5" style indicators
- Update on child changes

**Logging Requirements:**
- DEBUG: Progress calculation updates (task_id, completed_count, total_count)
- DEBUG: Progress display refresh events
- ERROR: Progress calculation errors with exc_info=True

**Success Criteria:**
- Parents show child progress
- Updates in real-time
- Doesn't auto-complete parents
- Accurate calculations
- Progress updates logged at DEBUG level

---

### - [x] 2.3 Archive Functionality ⚡ [DEPENDS ON: 2.1]
**Size:** Medium | **Time:** 25 mins | **Dependencies:** 2.1

Implement 'a' key to archive completed tasks.  Create new modal to search, display and restore archived tasks.  "As a user I might want to un-archive a task I archived by mistake". "As a user I might want to archive completed tasks to clean up my projects list"

**Files to update:**
- Add archive handler
- Update task display for archived state
- Update trash icon percentage
- Add new modal for viewing archived tasks. 

**Logging Requirements:**
- INFO: Task archived (task_id, archive_timestamp)
- DEBUG: Archive key press event
- DEBUG: Completion percentage calculations updated
- ERROR: Archive operation failures with exc_info=True

**Success Criteria:**
- 'a' archives completed tasks
- User can open the new task modal 
- User can search archived tasks in the new modal 
- User can restore a task from the new modal
- Archive operations logged appropriately
- When a task is archived it should no longer be part of completion % calculation (% complete should only consider tasks in completed or in progress states)

---

### - [ ] 2.4 List Switching ⚡ [DEPENDS ON: 1.14]
**Size:** Medium | **Time:** 25 mins | **Dependencies:** 1.14

Implement number keys (1-3) to switch between lists.

**Files to update:**
- Add number key handlers
- Update column displays
- Reset navigation state

**Logging Requirements:**
- INFO: List switched (from_list_id, to_list_id, list_name)
- DEBUG: Number key press events
- DEBUG: Column update and navigation reset events
- ERROR: List switching failures with exc_info=True

**Success Criteria:**
- 1-3 keys switch lists
- Column 1 updates with new list tasks
- Column 2 clears
- Selection resets
- Active list highlighted
- List switching events logged appropriately

---

### - [ ] 2.5 Delete Key Support ⚡ [DEPENDS ON: 1.11]
**Size:** Small | **Time:** 15 mins | **Dependencies:** 1.11

Add Delete/Backspace key to delete selected task.

**Files to update:**
- Add delete key handler
- Confirmation dialog (optional)
- Handle cascade deletion

**Logging Requirements:**
- INFO: Task deleted (task_id, has_children, cascade_count)
- DEBUG: Delete key press event
- DEBUG: Confirmation dialog interactions
- ERROR: Deletion failures with exc_info=True

**Success Criteria:**
- Delete key removes task
- Handles children appropriately
- Updates UI immediately
- Maintains selection position
- All deletion events logged appropriately

---

## PHASE 3: POLISH & OPTIMIZATION

### - [ ] 3.1 Error Handling & Recovery ⚡ [STANDALONE]
**Size:** Medium | **Time:** 30 mins | **Dependencies:** MVP

Comprehensive error handling throughout the application.

**Files to create:**
- `taskui/exceptions.py`
- Update all services with try/catch
- Add user-friendly error messages

**Logging Requirements:**
- ERROR: All caught exceptions with exc_info=True and context
- INFO: Error recovery attempts and outcomes
- DEBUG: Error handling flow (try/catch boundaries)
- CRITICAL: Unrecoverable errors requiring app shutdown

**Success Criteria:**
- No crashes on errors
- Clear error messages
- Database recovery on corruption
- Graceful degradation
- All errors logged with full context and stack traces

---

### - [ ] 3.2 JSON Backup System ⚡ [DEPENDS ON: MVP]
**Size:** Medium | **Time:** 30 mins | **Dependencies:** MVP

Import/export functionality for JSON backups.

**Files to create:**
- `taskui/backup.py`
- CLI commands for backup/restore
- Auto-backup on major operations

**Logging Requirements:**
- INFO: Backup created (file_path, task_count, list_count, size_bytes)
- INFO: Restore initiated (file_path, validation_status)
- DEBUG: Backup/restore progress (items_processed, total_items)
- ERROR: Backup/restore failures with exc_info=True
- WARNING: Data integrity issues during restore

**Success Criteria:**
- Can export entire database to JSON
- Can import from JSON
- Preserves all relationships
- Command-line interface works
- All backup/restore operations logged with progress tracking

---

### - [ ] 3.3 Performance Optimization ⚡ [DEPENDS ON: MVP]
**Size:** Medium | **Time:** 30 mins | **Dependencies:** MVP

Optimize database queries and UI rendering.

**Updates needed:**
- Add database indexes
- Optimize query patterns
- Implement query caching
- Lazy loading for large lists

**Logging Requirements:**
- DEBUG: Query execution times (query_type, duration_ms, row_count)
- DEBUG: Cache hit/miss events (cache_key, cache_status)
- INFO: Performance threshold violations (operation, expected_ms, actual_ms)
- WARNING: Slow operations exceeding performance targets
- ERROR: Performance-related failures with exc_info=True

**Success Criteria:**
- <50ms navigation response
- <100ms task creation
- Handles 1000+ tasks smoothly
- Memory usage stays low
- Performance metrics logged for analysis and optimization

---

### - [ ] 3.4 Configuration System ⚡ [STANDALONE]
**Size:** Small | **Time:** 20 mins | **Dependencies:** None

Implement settings management with .env support.

**Files to create:**
- `taskui/config.py`
- `.env.example`
- Update app to use config

**Logging Requirements:**
- INFO: Configuration loaded (source, settings_count)
- DEBUG: Individual setting values (key, value, source)
- WARNING: Missing or invalid configuration values (using defaults)
- ERROR: Configuration load failures with exc_info=True

**Success Criteria:**
- Settings load from .env
- Defaults work without .env
- Can configure all key settings
- Settings documented
- Configuration loading and validation logged

---

### - [ ] 3.5 Comprehensive Testing Suite 🧪 [DEPENDS ON: MVP]
**Size:** Large | **Time:** 45 mins | **Dependencies:** MVP

Complete test coverage for all components.

**Files to create/update:**
- All test files per specification
- Factories and fixtures
- Integration tests
- Performance benchmarks

**Logging Requirements:**
- DEBUG: Test execution flow (test_name, status, duration)
- INFO: Test suite summary (total_tests, passed, failed, coverage_percent)
- ERROR: Test failures with exc_info=True
- WARNING: Coverage gaps or performance test failures

**Success Criteria:**
- >80% code coverage
- All critical paths tested
- UI snapshot tests pass
- Performance benchmarks met
- Test execution and results logged appropriately

---

## PHASE 4: ADVANCED FEATURES

### - [x] 4.1 Network Printer Support ✅ [COMPLETE]
**Size:** Large | **Time:** Completed | **Dependencies:** MVP

Thermal printer integration for physical kanban cards - COMPLETE!

**Files created:**
- `taskui/services/printer_service.py` - Full printer service implementation
- `taskui/config.py` - Configuration management with env overrides
- `.taskui/config.ini.example` - Example configuration
- `tests/test_printer_service.py` - 18 passing unit tests
- `tests/test_config.py` - 11 passing config tests
- `scripts/validate_printer.py` - Hardware validation script
- `docs/PRINTER_SETUP_GUIDE.md` - Complete user guide
- `docs/PRINTER_TROUBLESHOOTING.md` - Troubleshooting guide
- `docs/PRINT_TASKS.md` - Implementation details

**Features implemented:**
- ✅ 'P' key prints selected task with children
- ✅ Clean MINIMAL format (title + checkboxes)
- ✅ Configuration file with environment overrides
- ✅ Graceful handling when printer offline
- ✅ Network communication via python-escpos
- ✅ Comprehensive logging (INFO/DEBUG/WARNING/ERROR)
- ✅ Status notifications in UI
- ✅ 29 passing tests (18 printer + 11 config)
- ✅ Hardware validation script
- ✅ Complete user documentation

**Success Criteria:**
- [x] 'P' prints current task (tested and working!)
- [x] Proper receipt formatting (minimal, clean, readable)
- [x] Handles printer offline (graceful fallback)
- [x] Network communication works (python-escpos)
- [x] All print operations logged (comprehensive logging)

---

### - [ ] 4.2 PyInstaller Build ⚡ [DEPENDS ON: All]
**Size:** Medium | **Time:** 30 mins | **Dependencies:** All features

Create standalone executable distribution.

**Files to create:**
- `taskui.spec` (PyInstaller config)
- Build scripts
- Distribution documentation

**Logging Requirements:**
- INFO: Build process initiated (platform, build_mode, version)
- INFO: Build completed (output_path, size_bytes, duration)
- DEBUG: Build steps (collecting_dependencies, bundling, compressing)
- WARNING: Build warnings (missing_files, size_exceeded)
- ERROR: Build failures with exc_info=True

**Success Criteria:**
- Single executable builds
- Runs on target platforms
- Includes all resources
- <50MB file size
- Build process and outcomes logged

---

### - [ ] 4.3 CLI Enhancements ⚡ [DEPENDS ON: MVP]
**Size:** Small | **Time:** 20 mins | **Dependencies:** MVP

Add command-line arguments and operations.

**Files to update:**
- `taskui/__main__.py`
- Add Typer CLI commands
- Help documentation

**Logging Requirements:**
- INFO: CLI command executed (command, arguments)
- DEBUG: Command argument parsing (arg_name, arg_value)
- DEBUG: Command execution flow
- ERROR: Invalid arguments or command failures with exc_info=True

**Success Criteria:**
- --help shows usage
- Can specify database path
- Backup/restore commands work
- Version command works
- All CLI operations logged with arguments

---

### - [ ] 4.4 Help System ⚡ [DEPENDS ON: MVP]
**Size:** Small | **Time:** 20 mins | **Dependencies:** MVP

Add in-app help panel (press '?').

**Files to create:**
- `taskui/ui/components/help_panel.py`
- Help text content
- '?' key handler

**Logging Requirements:**
- DEBUG: Help panel opened
- DEBUG: Help panel closed
- DEBUG: Help key press event
- ERROR: Help panel display failures with exc_info=True

**Success Criteria:**
- '?' shows help overlay
- Lists all keyboard shortcuts
- Escape closes help
- Well-formatted display
- Help panel interactions logged

---

## IMPLEMENTATION NOTES

### Parallel Work Opportunities
These task groups can be worked on simultaneously by different contexts:
- **Group A:** 1.1, 1.2, 1.3, 1.6 (Models & Database)
- **Group B:** 1.4, 1.5 (UI Foundation)
- **Group C:** 1.14, 3.4 (Configuration & Lists)
- **Group D:** 3.1, Tests (Quality & Testing)

### Critical Path (Sequential Dependencies)
1. Project Setup (1.1)
2. Basic App Shell (1.4)
3. Task Display (1.5)
4. Task Service CRUD (1.7, 1.11)
5. Task Creation Modal (1.9)
6. Integration (1.16)

### Size Guidelines for Claude Code CLI
- **Small (15-20 mins):** Single file, <150 lines
- **Medium (25-35 mins):** 2-3 files, <300 lines total
- **Large (40-45 mins):** Multiple files, <500 lines total

### Testing Strategy
- Write tests alongside implementation
- Use TDD for business logic
- Integration tests after each phase
- Performance tests in Phase 3

### Success Metrics
- **MVP Complete:** User can create, edit, delete nested tasks with persistence
- **Phase 2 Complete:** Full keyboard navigation and task management
- **Phase 3 Complete:** Production-ready with testing and optimization
- **Phase 4 Complete:** Advanced features and distribution

---

## QUICK START SEQUENCE

For fastest MVP delivery, execute tasks in this order:

**Day 1 - Foundation:**
1. 1.1 Project Setup (15m)
2. 1.2 Data Models (20m)
3. 1.3 Database Layer (30m)
4. 1.4 Basic App Shell (30m)
5. 1.6 Nesting Rules (20m)

**Day 2 - Core Features:**
1. 1.5 Task Display (30m)
2. 1.7 Task Service Create/Read (45m)
3. 1.8 Keyboard Navigation (30m)
4. 1.9 Task Creation Modal (35m)

**Day 3 - Complete MVP:**
1. 1.10 Column 2 Updates (30m)
2. 1.11 Task Service Update/Delete (30m)
3. 1.13 Column 3 Details (25m)
4. 1.14 List Management (20m)
5. 1.15 Persistence (20m)
6. 1.16 Integration (45m)

Total MVP: ~7 hours of focused work

---

*Each task is designed to be completed in one Claude Code CLI session without context overflow. Tasks marked with ⚡ can be worked in parallel. Tasks marked with 🔄 block other UI work. Tasks marked with 🧪 are testing-focused. Tasks marked with 🏁 are integration points.*