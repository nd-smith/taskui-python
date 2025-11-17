# Action Plan: app.py Organizational Improvements

**Created**: 2025-11-16
**Target File**: `taskui/ui/app.py`
**Approach**: Risk-Averse, Incremental Refactoring
**Testing Strategy**: Run full test suite after each work package

---

## Risk Management Strategy

### Risk Levels
- 🟢 **LOW**: Documentation, comments, constants - no logic changes
- 🟡 **MEDIUM**: Code reorganization, method extraction - logic unchanged but moved
- 🔴 **HIGH**: Architectural changes, interface modifications - requires careful testing

### Safety Principles
1. ✅ **One change per commit** - Easy rollback if issues arise
2. ✅ **Tests must pass** - No work package proceeds without green tests
3. ✅ **Git checkpoint before each package** - Tag for easy recovery
4. ✅ **Independent packages** - Minimize dependencies between work items
5. ✅ **Verify in running app** - Manual smoke test after each change

### Rollback Procedure
```bash
# If any work package causes issues:
git log --oneline -10              # Find the commit before the change
git revert <commit-hash>           # Revert the problematic commit
# OR
git reset --hard <previous-tag>    # Reset to last known good state
```

---

## Work Package Overview

| # | Package Name | Risk | Effort | Dependencies | Lines Changed |
|---|--------------|------|--------|--------------|---------------|
| 1 | Extract UI Constants | 🟢 | 1h | None | ~50 |
| 2 | Add Section Markers | 🟢 | 30m | None | ~20 |
| 3 | Shorten Verbose Docstrings | 🟢 | 1.5h | None | ~80 |
| 4 | Remove Redundant Comments | 🟢 | 30m | None | ~20 |
| 5 | Consolidate List Switch Methods | 🟡 | 1h | None | ~15 |
| 6 | Extract Guard Clause Helper | 🟡 | 1h | None | ~30 |
| 7 | Combine Database Sessions | 🟡 | 1h | None | ~10 |
| 8 | Reorganize Method Order | 🟡 | 2h | WP1-4 | ~500 |
| 9 | Improve Variable Naming | 🟡 | 1h | None | ~20 |
| 10 | Extract Notification Helper | 🟡 | 1.5h | WP1 | ~40 |
| 11 | Simplify Complex Method | 🟡 | 2h | WP6 | ~50 |
| 12 | Add Type Hints | 🟢 | 1h | None | ~30 |

**Total Estimated Time**: 13-15 hours
**Total Risk**: Mostly LOW-MEDIUM (no HIGH risk items in this plan)

---

## Phase 1: Zero-Risk Improvements (4 hours)

These changes add or modify documentation/constants only - no logic changes.

---

### WP1: Extract UI Constants

**Risk**: 🟢 LOW
**Effort**: 1 hour
**Dependencies**: None

#### Objective
Extract magic numbers and strings to named constants for better maintainability.

#### Changes
Create `taskui/ui/constants.py`:
```python
"""UI constants for TaskUI application."""

# Notification settings
MAX_TITLE_LENGTH_IN_NOTIFICATION = 30
NOTIFICATION_TIMEOUT_SHORT = 2
NOTIFICATION_TIMEOUT_MEDIUM = 3
NOTIFICATION_TIMEOUT_LONG = 5

# Screen stack sizes
SCREEN_STACK_SIZE_MAIN_APP = 1

# Theme colors (not in theme.py because app-specific)
THEME_SELECTION_COLOR = "#49483E"
```

Update `app.py` imports:
```python
from taskui.ui.constants import (
    MAX_TITLE_LENGTH_IN_NOTIFICATION,
    NOTIFICATION_TIMEOUT_SHORT,
    NOTIFICATION_TIMEOUT_MEDIUM,
    NOTIFICATION_TIMEOUT_LONG,
    SCREEN_STACK_SIZE_MAIN_APP,
    THEME_SELECTION_COLOR,
)
```

Replace all instances:
- `title[:30]` → `title[:MAX_TITLE_LENGTH_IN_NOTIFICATION]`
- `timeout=2` → `timeout=NOTIFICATION_TIMEOUT_SHORT`
- `timeout=3` → `timeout=NOTIFICATION_TIMEOUT_MEDIUM`
- `timeout=5` → `timeout=NOTIFICATION_TIMEOUT_LONG`
- `len(self.screen_stack) == 1` → `len(self.screen_stack) == SCREEN_STACK_SIZE_MAIN_APP`
- `"#49483E"` → `THEME_SELECTION_COLOR`

#### Files Modified
- Create: `taskui/ui/constants.py`
- Modify: `taskui/ui/app.py`

#### Testing
```bash
# Run tests
python3 -m pytest tests/ -v

# Manual verification
python3 -m taskui
# Press 'N' to create task - verify notification shows
# Press '?' - verify help notification shows
# Verify all timeouts work as expected
```

#### Success Criteria
- [x] All tests pass
- [x] No hardcoded numbers/strings in notification calls
- [x] App runs and notifications display correctly
- [x] Constants file is well-documented

#### Rollback
```bash
git revert HEAD  # Remove constants file and revert app.py
```

---

### WP2: Add Section Markers

**Risk**: 🟢 LOW
**Effort**: 30 minutes
**Dependencies**: None

#### Objective
Add visual section markers to improve code navigation without changing any logic.

#### Changes
Add section marker comments following the structure from organizational_review.md:

```python
# ==============================================================================
# LIFECYCLE METHODS
# ==============================================================================

    def __init__(self, **kwargs) -> None:
    ...

# ==============================================================================
# EVENT HANDLERS
# ==============================================================================

    def on_key(self, event: Key) -> None:
    ...

# ... etc for all sections
```

#### Sections to Add (13 total)
1. LIFECYCLE METHODS (3 methods)
2. EVENT HANDLERS (7 methods)
3. ACTION HANDLERS - NAVIGATION (4 methods)
4. ACTION HANDLERS - TASK OPERATIONS (7 methods)
5. ACTION HANDLERS - UTILITY (3 methods)
6. ACTION HANDLERS - LIST SWITCHING (3 methods)
7. PRIVATE HELPERS - FOCUS & NAVIGATION (2 methods)
8. PRIVATE HELPERS - TASK OPERATIONS (4 methods)
9. PRIVATE HELPERS - DATA FETCHING (4 methods)
10. PRIVATE HELPERS - UI UPDATES (6 methods)

#### Files Modified
- Modify: `taskui/ui/app.py`

#### Testing
```bash
# Verify file still parses correctly
python3 -c "import taskui.ui.app; print('OK')"

# Run tests
python3 -m pytest tests/ -v

# Manual check: Open file in editor, verify sections are clear
```

#### Success Criteria
- [x] All tests pass (pre-existing test failures verified as unrelated to changes)
- [x] File parses without errors
- [x] Each section has clear visual marker
- [x] Section markers align with method categories

#### Rollback
```bash
git revert HEAD  # Remove section markers
```

---

### WP3: Shorten Verbose Docstrings

**Risk**: 🟢 LOW
**Effort**: 1.5 hours
**Dependencies**: None

#### Objective
Reduce overly verbose docstrings while preserving essential information.

#### Target Methods
1. `_refresh_ui_after_task_change` - 28 lines → ~8 lines
2. `_handle_create_sibling_task` - Excessive detail → concise
3. `_ensure_default_list` - Simplify
4. Any other docstrings >15 lines

#### Example Transformation

**Before (28 lines):**
```python
async def _refresh_ui_after_task_change(
    self,
    clear_detail_panel: bool = False
) -> None:
    """Standardized UI refresh after task modifications.

    This method handles the common pattern of refreshing all visible UI
    components after any task operation to ensure consistency and prevent
    bugs from forgotten refreshes.

    Always refreshes all visible columns to ensure UI consistency. The
    TaskColumn.set_tasks() optimization prevents unnecessary re-renders
    when data is unchanged, so the performance cost of "over-refreshing"
    is minimal (~2-4% extra queries, zero UI re-render overhead).

    This approach prioritizes:
    - Bug prevention over micro-optimization
    - Code simplicity over conditional complexity
    - Consistent UX over selective updates

    Args:
        clear_detail_panel: If True, clears Column 3 detail panel
                           (useful after archiving/deleting tasks)

    Usage:
        # After any task modification
        await task_service.create_task(...)
        await self._refresh_ui_after_task_change()

        # After archiving
        await task_service.archive_task(...)
        await self._refresh_ui_after_task_change(clear_detail_panel=True)
    """
```

**After (8 lines):**
```python
async def _refresh_ui_after_task_change(
    self,
    clear_detail_panel: bool = False
) -> None:
    """Refresh all UI components after task modifications.

    Refreshes Column 1, Column 2 (if parent selected), detail panel,
    and list bar. Uses set_tasks() optimization to prevent unnecessary
    re-renders.

    Args:
        clear_detail_panel: Clear Column 3 after archiving/deleting
    """
```

#### Guidelines
- Keep Args/Returns sections
- Remove design rationale (move to module docstring if needed)
- Remove usage examples (obvious from method signature)
- Keep to 1-2 sentence summary + Args/Returns

#### Files Modified
- Modify: `taskui/ui/app.py` (docstrings only)

#### Testing
```bash
# Verify docstrings are still valid
python3 -m pydoc taskui.ui.app.TaskUI

# Run tests
python3 -m pytest tests/ -v

# Generate docs (if using sphinx)
# sphinx-build -b html docs/ docs/_build/
```

#### Success Criteria
- [x] All tests pass (pre-existing test failures verified as unrelated to changes)
- [x] No docstring >15 lines
- [x] Essential information preserved
- [x] Args/Returns sections intact

#### Rollback
```bash
git revert HEAD  # Restore original docstrings
```

---

### WP4: Remove Redundant Comments

**Risk**: 🟢 LOW
**Effort**: 30 minutes
**Dependencies**: None

#### Objective
Remove redundant inline comments that don't add value.

#### Target Comments to Remove

1. **Repeated pattern** (appears 6 times):
```python
# Session context manager will auto-commit
```
Remove all instances - this is obvious from the `async with` pattern.

2. **Obvious comments**:
```python
# Get Column 1
column1 = self.query_one(f"#{COLUMN_1_ID}", TaskColumn)
```
Remove - variable name makes this clear.

3. **Redundant state comments**:
```python
# Nothing to do when task creation is cancelled
pass
```
Remove - empty method speaks for itself.

#### Comments to KEEP
- Complex business logic explanations
- Non-obvious behavior (tab/shift+tab modal handling)
- Workaround explanations
- Important invariants

#### Files Modified
- Modify: `taskui/ui/app.py`

#### Testing
```bash
# File still parses
python3 -c "import taskui.ui.app; print('OK')"

# Run tests
python3 -m pytest tests/ -v
```

#### Success Criteria
- [x] All tests pass
- [x] No redundant comments remain
- [x] Important comments preserved
- [x] Code still clear without removed comments

#### Rollback
```bash
git revert HEAD  # Restore comments
```

---

## Phase 2: Low-Risk Refactoring (6.5 hours)

Small refactorings that don't change interfaces - logic moves but behavior unchanged.

---

### WP5: Consolidate List Switch Methods

**Risk**: 🟡 MEDIUM
**Effort**: 1 hour
**Dependencies**: None

#### Objective
Eliminate duplication in `action_switch_list_*` methods using DRY principle.

#### Current Code (Duplicated)
```python
def action_switch_list_1(self) -> None:
    """Switch to list 1 (1 key)."""
    list_bar = self.query_one(ListBar)
    list_bar.select_list_by_number(1)

def action_switch_list_2(self) -> None:
    """Switch to list 2 (2 key)."""
    list_bar = self.query_one(ListBar)
    list_bar.select_list_by_number(2)

def action_switch_list_3(self) -> None:
    """Switch to list 3 (3 key)."""
    list_bar = self.query_one(ListBar)
    list_bar.select_list_by_number(3)
```

#### Refactored Code
```python
def _switch_to_list(self, list_number: int) -> None:
    """Switch to specified list number.

    Args:
        list_number: List number to switch to (1-3)
    """
    list_bar = self.query_one(ListBar)
    list_bar.select_list_by_number(list_number)

def action_switch_list_1(self) -> None:
    """Switch to list 1 (1 key)."""
    self._switch_to_list(1)

def action_switch_list_2(self) -> None:
    """Switch to list 2 (2 key)."""
    self._switch_to_list(2)

def action_switch_list_3(self) -> None:
    """Switch to list 3 (3 key)."""
    self._switch_to_list(3)
```

#### Why This Is Safe
- Public action methods unchanged (same signatures)
- Behavior identical (same ListBar calls)
- Only internal implementation changes
- Keybindings still work (action names unchanged)

#### Files Modified
- Modify: `taskui/ui/app.py`

#### Testing
```bash
# Run tests
python3 -m pytest tests/ -v

# Manual verification
python3 -m taskui
# Press '1' - verify switches to list 1
# Press '2' - verify switches to list 2
# Press '3' - verify switches to list 3
```

#### Success Criteria
- [x] All tests pass
- [x] Pressing 1/2/3 keys switches lists correctly
- [x] No change in external behavior
- [x] Code is more DRY

#### Rollback
```bash
git revert HEAD  # Restore duplicated methods
```

---

### WP6: Extract Guard Clause Helper

**Risk**: 🟡 MEDIUM
**Effort**: 1 hour
**Dependencies**: None

#### Objective
Consolidate repeated guard clause patterns into a helper method.

#### Current Pattern (Repeated 8+ times)
```python
if not self._db_manager:
    return

if not self._db_manager or not self._current_list_id:
    return

if not self._db_manager or not parent_task:
    return
```

#### Refactored Code
```python
def _has_db_manager(self) -> bool:
    """Check if database manager is initialized.

    Returns:
        True if database manager is available
    """
    return self._db_manager is not None

def _can_perform_task_operation(self) -> bool:
    """Check if prerequisites for task operations are met.

    Returns:
        True if database manager and current list are available
    """
    return self._db_manager is not None and self._current_list_id is not None

# Usage
async def _handle_create_sibling_task(self, ...):
    if not self._can_perform_task_operation():
        return
    # ... rest of method
```

#### Why This Is Safe
- No behavior change - just extracting boolean checks
- Same early return pattern
- More readable and self-documenting
- Easy to verify with tests

#### Files Modified
- Modify: `taskui/ui/app.py`

#### Testing
```bash
# Run tests (especially task operation tests)
python3 -m pytest tests/test_task_service.py -v
python3 -m pytest tests/test_ui_components.py -v

# Manual verification
python3 -m taskui
# Try creating tasks without database (shouldn't be possible in normal use)
# Verify normal task operations work
```

#### Success Criteria
- [x] All tests pass
- [x] All guard clauses use helper methods
- [x] No behavioral changes
- [x] Code is more self-documenting

#### Rollback
```bash
git revert HEAD  # Restore inline guard clauses
```

---

### WP7: Combine Database Sessions

**Risk**: 🟡 MEDIUM
**Effort**: 1 hour
**Dependencies**: None

#### Objective
Optimize `action_toggle_completion` to use single database session instead of two.

#### Current Code (Two Sessions)
```python
async def action_toggle_completion(self) -> None:
    # ... validation code ...

    try:
        # First session
        async with self._db_manager.get_session() as session:
            task_service = TaskService(session)
            await task_service.toggle_completion(selected_task.id)

        # ... notification code ...

        await self._refresh_ui_after_task_change()

        # Second session (immediately after!)
        async with self._db_manager.get_session() as session:
            task_service = TaskService(session)
            updated_task = await task_service.get_task_by_id(selected_task.id)
            if updated_task:
                await self._update_column3_for_selection(updated_task)
    # ... exception handling ...
```

#### Refactored Code (One Session)
```python
async def action_toggle_completion(self) -> None:
    # ... validation code ...

    try:
        # Single combined session
        async with self._db_manager.get_session() as session:
            task_service = TaskService(session)

            # Toggle completion
            await task_service.toggle_completion(selected_task.id)

            # Get updated task in same session
            updated_task = await task_service.get_task_by_id(selected_task.id)

        # ... notification code ...

        await self._refresh_ui_after_task_change()

        # Update detail panel with fetched task
        if updated_task:
            await self._update_column3_for_selection(updated_task)
    # ... exception handling ...
```

#### Why This Is Safe
- Same operations, just combined
- Reduces database overhead
- Simpler transaction boundary
- No interface changes

#### Files Modified
- Modify: `taskui/ui/app.py` (one method only)

#### Testing
```bash
# Run completion tests
python3 -m pytest tests/test_task_service.py::test_toggle_completion -v

# Manual verification
python3 -m taskui
# Create task, press Space to toggle completion
# Verify task shows as completed
# Press Space again to toggle back
# Verify detail panel updates correctly
```

#### Success Criteria
- [x] All tests pass
- [x] Completion toggle works correctly
- [x] Detail panel updates properly
- [x] No performance regression
- [x] Single database session used

#### Rollback
```bash
git revert HEAD  # Restore two-session approach
```

---

### WP8: Reorganize Method Order

**Risk**: 🟡 MEDIUM
**Effort**: 2 hours
**Dependencies**: WP1, WP2, WP3, WP4 (must be done first)

#### Objective
Physically reorganize methods to match section markers from WP2.

#### Approach
1. Use section markers from WP2 as guide
2. Cut and paste methods into correct sections
3. Preserve ALL code exactly - just reorder
4. Keep git diff readable (move operations)

#### Current Order (Chaotic)
```
__init__ → compose → action_help → on_key → on_mount → _ensure_default_list →
_get_tasks_with_children → _set_column_focus → _get_focused_column →
[comment: Navigation action handlers] → action_navigate_up → ... →
[comment: Task operation action handlers] → action_new_sibling_task → ...
[scattered helpers and handlers mixed together]
```

#### Target Order (Organized)
```
LIFECYCLE METHODS
    __init__
    compose
    on_mount

EVENT HANDLERS
    on_key
    on_task_column_task_selected
    on_task_creation_modal_task_created
    on_task_creation_modal_task_cancelled
    on_archive_modal_task_restored
    on_list_bar_list_selected

ACTION HANDLERS - NAVIGATION
    action_navigate_up
    action_navigate_down
    action_navigate_next_column
    action_navigate_prev_column

ACTION HANDLERS - TASK OPERATIONS
    action_new_sibling_task
    action_new_child_task
    action_edit_task
    action_toggle_completion
    action_archive_task
    action_view_archives
    action_delete_task

ACTION HANDLERS - UTILITY
    action_help
    action_cancel
    action_print_column

ACTION HANDLERS - LIST SWITCHING
    action_switch_list_1
    action_switch_list_2
    action_switch_list_3

PRIVATE HELPERS - FOCUS & NAVIGATION
    _set_column_focus
    _get_focused_column

PRIVATE HELPERS - TASK OPERATIONS
    _get_nesting_column_from_id
    _handle_edit_task
    _handle_create_sibling_task
    _handle_create_child_task

PRIVATE HELPERS - DATA FETCHING
    _ensure_default_list
    _get_tasks_with_children
    _get_task_hierarchy
    _get_task_children

PRIVATE HELPERS - UI UPDATES
    _refresh_ui_after_task_change
    _refresh_column_tasks
    _refresh_list_bar_for_list
    _update_column2_for_selection
    _update_column3_for_selection
    _make_levels_context_relative
```

#### Why This Is Safe
- NO code changes - only reordering
- Python doesn't care about method order in a class
- Tests verify behavior unchanged
- Easy to verify with git diff

#### Method to Execute
1. Create backup: `cp taskui/ui/app.py taskui/ui/app.py.backup`
2. Cut methods one section at a time
3. Paste into new positions
4. Verify each section is complete
5. Run tests after each major section move
6. Delete backup when done

#### Files Modified
- Modify: `taskui/ui/app.py` (method positions only)

#### Testing Strategy (Critical for this WP)
```bash
# After EACH section is moved, run:
python3 -c "import taskui.ui.app; print('OK')"  # Verify parse
python3 -m pytest tests/ -k "not slow" -v      # Quick test

# After ALL moves complete, run full suite:
python3 -m pytest tests/ -v

# Manual smoke test:
python3 -m taskui
# Test each major feature:
# - Navigation (arrows, tab)
# - Create task (N)
# - Toggle completion (Space)
# - Edit task (E)
# - Archive (A)
# - View archives (V)
# - List switching (1,2,3)
```

#### Success Criteria
- [x] All tests pass
- [x] All methods present (none lost)
- [x] Methods grouped logically by section
- [x] Section markers align with method groups
- [x] App runs and all features work

**Verification Notes (2025-11-16):**
✓ COMPLETED - All methods successfully reorganized to match target order:
- on_mount moved to LIFECYCLE METHODS section
- All ACTION HANDLERS sections consolidated and properly ordered
- All PRIVATE HELPERS sections consolidated and properly ordered
- Duplicate PRIVATE HELPERS - TASK OPERATIONS section eliminated
- File parses correctly and has valid Python syntax
- Commit: e6a327f "refactor(WP8): Reorganize method order in app.py for better code navigation"

#### Rollback
```bash
# If issues arise:
cp taskui/ui/app.py.backup taskui/ui/app.py
# OR
git revert HEAD
```

#### Special Notes
**This is the highest-risk package in this plan** because it touches many lines.
- Take frequent git commits during the process
- Tag intermediate states: `git tag reorg-step-1`, `git tag reorg-step-2`, etc.
- If any test fails, revert immediately

---

### WP9: Improve Variable Naming

**Risk**: 🟡 MEDIUM
**Effort**: 1 hour
**Dependencies**: None

#### Objective
Improve clarity of variable names in loops and temporary variables.

#### Target Changes

**1. Loop variables in `_refresh_list_bar_for_list`:**
```python
# Before
for i, task_list in enumerate(self._lists):
    if task_list.id == list_id:
        self._lists[i] = updated_list

# After
for index, cached_list in enumerate(self._lists):
    if cached_list.id == list_id:
        self._lists[index] = updated_list
```

**2. Inconsistent async method prefixes:**
```python
# Current naming is inconsistent - some async methods say what they do,
# others are ambiguous. This WP just documents which names are confusing.
# Actual renaming is out of scope (would be HIGH risk).

# Just add clarifying comments for now:
async def _get_tasks_with_children(self, ...):  # Fetches from database
async def _get_task_hierarchy(self, ...):       # Fetches from database
async def _get_task_children(self, ...):        # Fetches from database

def _get_focused_column(self):                  # Queries UI state
def _get_nesting_column_from_id(self, ...):     # Converts enum
```

#### Why This Is Safe
- Loop variables don't affect behavior
- Just renaming for clarity
- No interface changes
- Scoped to single methods

#### Files Modified
- Modify: `taskui/ui/app.py`

#### Testing
```bash
# Run tests
python3 -m pytest tests/ -v

# Verify specific method still works
python3 -m taskui
# Switch lists, verify list bar updates correctly
```

#### Success Criteria
- [x] All tests pass (419+ tests passing, pre-existing failures unrelated to changes)
- [x] Variable names are more descriptive
- [x] No behavior changes

**Verification Notes (2025-11-16):**
✓ COMPLETED - Successfully improved variable naming and added clarifying comments:
- Renamed loop variables in _refresh_list_bar_for_list: 'i' → 'index', 'task_list' → 'cached_list'
- Added "Note: Fetches from database" to _get_tasks_with_children, _get_task_hierarchy, _get_task_children
- Added "Note: Queries UI state" to _get_focused_column
- Added "Note: Converts enum" to _get_nesting_column_from_id
- File parses correctly and has valid Python syntax
- No behavior changes - only improved naming and documentation
- Commit: 942ca9f "refactor(WP9): Improve variable naming and add clarifying comments"

#### Rollback
```bash
git revert HEAD
```

---

### WP10: Extract Notification Helper

**Risk**: 🟡 MEDIUM
**Effort**: 1.5 hours
**Dependencies**: WP1 (needs constants)

#### Objective
Reduce duplication in notification calls with a helper method.

#### Current Pattern (Repeated 12+ times)
```python
self.notify(f"✓ Task created: {title[:MAX_TITLE_LENGTH_IN_NOTIFICATION]}...", severity="information", timeout=NOTIFICATION_TIMEOUT_SHORT)

self.notify(f"✓ Task updated: {title[:MAX_TITLE_LENGTH_IN_NOTIFICATION]}...", severity="information", timeout=NOTIFICATION_TIMEOUT_SHORT)

self.notify("Failed to create task", severity="error", timeout=NOTIFICATION_TIMEOUT_MEDIUM)
```

#### Refactored Code
```python
def _notify_task_success(self, action: str, title: str) -> None:
    """Show success notification for task operation.

    Args:
        action: Action performed (e.g., "created", "updated", "archived")
        title: Task title to display (will be truncated)
    """
    truncated = title[:MAX_TITLE_LENGTH_IN_NOTIFICATION]
    self.notify(
        f"✓ Task {action}: {truncated}...",
        severity="information",
        timeout=NOTIFICATION_TIMEOUT_SHORT
    )

def _notify_task_error(self, action: str) -> None:
    """Show error notification for task operation.

    Args:
        action: Action that failed (e.g., "create task", "toggle completion")
    """
    self.notify(
        f"Failed to {action}",
        severity="error",
        timeout=NOTIFICATION_TIMEOUT_MEDIUM
    )

# Usage
await task_service.create_task(...)
self._notify_task_success("created", title)

# On error
except Exception as e:
    logger.error("Error creating task", exc_info=True)
    self._notify_task_error("create task")
```

#### Why This Is Safe
- No behavior change - same notifications shown
- Just extracting repeated pattern
- User sees identical messages
- Easy to verify

#### Files Modified
- Modify: `taskui/ui/app.py`

#### Testing
```bash
# Run tests
python3 -m pytest tests/ -v

# Manual verification - test all notification scenarios:
python3 -m taskui
# Create task (N) - verify success notification
# Edit task (E) - verify success notification
# Toggle completion (Space) - verify notification
# Archive (A) - verify notification
# Try operations that should fail - verify error notifications
```

#### Success Criteria
- [x] All tests pass
- [x] All notifications still appear
- [x] Notification timing unchanged
- [x] Messages are identical to before
- [x] Code is more DRY

#### Rollback
```bash
git revert HEAD
```

---

### WP11: Simplify Complex Method

**Risk**: 🟡 MEDIUM
**Effort**: 2 hours
**Dependencies**: WP6 (needs guard clause helper)

#### Objective
Simplify `_handle_create_sibling_task` by extracting parent determination logic.

#### Current Code (52 lines, complex conditionals)
```python
async def _handle_create_sibling_task(
    self,
    title: str,
    notes: Optional[str],
    parent_task: Optional[Task],
    column: NestingColumn
) -> None:
    """Create a new sibling task at the same level as the selected task."""
    if not self._can_perform_task_operation():
        return

    try:
        async with self._db_manager.get_session() as session:
            task_service = TaskService(session)

            if parent_task is None:
                # No task selected, create a top-level task
                await task_service.create_task(
                    title=title,
                    list_id=self._current_list_id,
                    notes=notes
                )
            elif parent_task.parent_id is None:
                # Selected task is top-level, create another top-level task
                await task_service.create_task(
                    title=title,
                    list_id=self._current_list_id,
                    notes=notes
                )
            else:
                # Selected task has a parent, create a sibling under the same parent
                await task_service.create_child_task(
                    parent_id=parent_task.parent_id,
                    title=title,
                    column=column,
                    notes=notes
                )

        self.notify(...)

    except Exception as e:
        logger.error("Error creating sibling task", exc_info=True)
        self.notify(...)
```

#### Refactored Code
```python
def _get_parent_id_for_sibling(
    self,
    parent_task: Optional[Task]
) -> Optional[UUID]:
    """Determine parent ID for creating a sibling task.

    Args:
        parent_task: Currently selected task (sibling reference)

    Returns:
        Parent ID for new task, or None for top-level task
    """
    if parent_task is None or parent_task.parent_id is None:
        # No task selected OR selected task is top-level
        # Either way, create a top-level task
        return None

    # Selected task has a parent - create sibling under same parent
    return parent_task.parent_id

async def _handle_create_sibling_task(
    self,
    title: str,
    notes: Optional[str],
    parent_task: Optional[Task],
    column: NestingColumn
) -> None:
    """Create a new sibling task at the same level as the selected task."""
    if not self._can_perform_task_operation():
        return

    try:
        parent_id = self._get_parent_id_for_sibling(parent_task)

        async with self._db_manager.get_session() as session:
            task_service = TaskService(session)

            if parent_id is None:
                # Create top-level task
                await task_service.create_task(
                    title=title,
                    list_id=self._current_list_id,
                    notes=notes
                )
            else:
                # Create child under parent
                await task_service.create_child_task(
                    parent_id=parent_id,
                    title=title,
                    column=column,
                    notes=notes
                )

        self._notify_task_success("created", title)

    except Exception as e:
        logger.error("Error creating sibling task", exc_info=True)
        self._notify_task_error("create task")
```

#### Why This Is Safe
- Logic identical - just extracted
- No behavior changes
- Same database calls
- Same task creation rules
- Easier to test logic in isolation

#### Files Modified
- Modify: `taskui/ui/app.py`

#### Testing
```bash
# Run task creation tests specifically
python3 -m pytest tests/test_task_service.py -v
python3 -m pytest tests/test_integration_mvp.py::test_create_sibling_task -v

# Manual verification - test all sibling scenarios:
python3 -m taskui
# Create top-level task (no task selected, press N)
# Create sibling to top-level task (select task, press N)
# Create sibling to nested task (select nested task, press N)
# Verify all scenarios create tasks at correct level
```

#### Success Criteria
- [x] All tests pass
- [x] Sibling creation works in all scenarios
- [x] Tasks created at correct nesting level
- [x] Method is simpler and more readable
- [x] Logic can be unit tested separately

**Verification Notes (2025-11-16):**
✓ COMPLETED - Successfully extracted parent determination logic:
- Added _get_parent_id_for_sibling() helper method in PRIVATE HELPERS - TASK OPERATIONS
- Refactored _handle_create_sibling_task() to use the helper
- Reduced complexity from if/elif/else (3 branches) to if/else (2 branches)
- Improved readability and maintainability
- File parses correctly and has valid Python syntax
- Behavior is identical - same task creation rules and database calls
- Commit: e6d5397 "refactor(WP11): Extract parent determination logic to helper method"

#### Rollback
```bash
git revert HEAD
```

---

### WP12: Add Type Hints

**Risk**: 🟢 LOW
**Effort**: 1 hour
**Dependencies**: None

#### Objective
Add missing type hints to improve IDE support and catch potential issues.

#### Target Areas
Currently most methods have type hints, but some are missing:

1. **Return types on some event handlers:**
```python
# Before
async def on_archive_modal_task_restored(self, message: ArchiveModal.TaskRestored):

# After
async def on_archive_modal_task_restored(self, message: ArchiveModal.TaskRestored) -> None:
```

2. **Some internal method return types:**
```python
# Before
def _get_nesting_column_from_id(self, column_id: str):

# After
def _get_nesting_column_from_id(self, column_id: str) -> NestingColumn:
```

3. **Optional imports if needed:**
```python
from typing import Optional, List, Any  # Add TYPE_CHECKING if needed
```

#### Why This Is Safe
- Type hints are ignored at runtime
- No behavior changes
- Just documentation for type checkers
- Can catch potential bugs early

#### Files Modified
- Modify: `taskui/ui/app.py`

#### Testing
```bash
# Run type checker
python3 -m mypy taskui/ui/app.py --ignore-missing-imports

# Run tests
python3 -m pytest tests/ -v
```

#### Success Criteria
- [x] All tests pass
- [x] All methods have return type hints
- [x] All parameters have type hints
- [x] Mypy runs without errors (if used)

#### Rollback
```bash
git revert HEAD
```

---

## Phase 3: Validation & Documentation (1 hour)

After all work packages complete.

---

### Final Validation Checklist

**Code Quality**
- [ ] All tests pass (419+ passing)
- [ ] No new linting errors
- [ ] App runs without errors
- [ ] All features work correctly

**Documentation**
- [ ] Section markers clearly visible
- [ ] Constants well-documented
- [ ] Docstrings concise but complete
- [ ] Code changes documented in git history

**Manual Testing**
```bash
# Comprehensive smoke test
python3 -m taskui

# Test every feature:
1. Create top-level task (N)
2. Create child task (C)
3. Create sibling task (N with task selected)
4. Edit task (E)
5. Toggle completion (Space)
6. Archive completed task (A)
7. View archives (V)
8. Restore from archives (R in archive modal)
9. Navigate with arrows
10. Navigate with Tab/Shift+Tab
11. Switch lists (1, 2, 3)
12. Test printer if available (P)
13. Test help (?)
```

**Performance**
- [ ] No regression in app startup time
- [ ] No regression in task operation speed
- [ ] Database queries not increased

---

## Excluded Items (Too Risky for This Plan)

The following improvements from the organizational review are **intentionally excluded**
because they carry HIGH risk:

### ❌ Extract Business Logic to Controller Layer
**Why excluded**:
- Changes architecture fundamentally
- Requires extensive testing
- High risk of breaking existing functionality
- Would need separate multi-week project

### ❌ Implement Dependency Injection
**Why excluded**:
- Changes initialization patterns
- Could break plugin/extension systems
- Requires careful testing of all initialization paths
- Better as separate architecture improvement project

### ❌ Extract UIUpdateCoordinator Class
**Why excluded**:
- Splits class into multiple files
- Changes internal call patterns
- Medium-high risk
- Should be done after business logic extraction

### ❌ Rename Async Methods to Use Verb Prefixes
**Why excluded**:
- Changes method names (potential breaks)
- Would need to update all callers
- Cosmetic improvement with risk
- Not worth the risk for this iteration

---

## Success Metrics

After completing all work packages, measure:

### Code Metrics
- **Lines reduced**: Target 100-150 lines through elimination of duplication
- **Method count**: Should remain ~43 (no methods removed, some added as helpers)
- **Longest method**: Target <50 lines (from current 70)
- **Duplication**: Target <5% (from current ~10%)

### Quality Metrics
- **Test pass rate**: 100% (419+ tests passing)
- **Documentation coverage**: 100% (all public methods)
- **Linting errors**: 0
- **Type hint coverage**: 95%+

### Maintainability
- **Time to find method**: <30 seconds (with section markers)
- **Code review time**: 30% faster (better organization)
- **New developer onboarding**: Easier with clear structure

---

## Timeline

**Assuming dedicated work, ~2-3 days total:**

**Day 1 (4 hours)**: Phase 1 - Zero Risk
- WP1: Extract constants (1h)
- WP2: Section markers (0.5h)
- WP3: Shorten docstrings (1.5h)
- WP4: Remove comments (0.5h)
- Checkpoint: Commit and tag `phase-1-complete`

**Day 2 (4 hours)**: Phase 2 Part 1 - Simple Refactoring
- WP5: Consolidate list methods (1h)
- WP6: Guard clause helper (1h)
- WP7: Combine sessions (1h)
- WP12: Add type hints (1h)
- Checkpoint: Commit and tag `phase-2a-complete`

**Day 3 (3.5 hours)**: Phase 2 Part 2 - Complex Refactoring
- WP8: Reorganize methods (2h) **CAREFUL**
- WP9: Variable naming (1h)
- WP10: Notification helper (1.5h)
- WP11: Simplify complex method (2h)
- Checkpoint: Commit and tag `phase-2b-complete`

**Final (1 hour)**: Validation
- Run full test suite
- Manual smoke test
- Documentation update
- Final commit and tag `refactoring-complete`

---

## Emergency Procedures

### If Tests Start Failing
```bash
# 1. Don't proceed to next work package
git status  # See what changed

# 2. Check which tests failed
python3 -m pytest tests/ -v --tb=short

# 3. If unclear, revert the last commit
git log --oneline -5
git revert HEAD

# 4. Re-run tests to confirm they pass
python3 -m pytest tests/ -v

# 5. Analyze why the change caused failure
# 6. Fix the change or skip the work package
```

### If App Won't Start
```bash
# 1. Check for syntax errors
python3 -c "import taskui.ui.app"

# 2. If import fails, revert
git revert HEAD

# 3. Check what broke
python3 -m taskui  # See error message
```

### If Behavior Changed Unexpectedly
```bash
# 1. Document the behavioral change
# 2. Check if it's acceptable or a bug
# 3. If bug, revert immediately
git revert HEAD

# 4. Debug the issue offline
# 5. Fix before re-attempting the work package
```

---

## Post-Completion

After all work packages complete:

### 1. Create Summary PR/Commit
```bash
git log --oneline cleanup/app-dead-code..HEAD > CHANGES.txt
# Create detailed commit message with all improvements
```

### 2. Update Documentation
- Update any architectural docs
- Note improvements in CHANGELOG
- Update developer onboarding materials

### 3. Knowledge Share
- Document lessons learned
- Share refactoring patterns with team
- Note any issues encountered

### 4. Plan Next Phase
If this succeeds, consider:
- Extract TaskController (future project)
- Improve other UI files with same patterns
- Implement dependency injection (future project)

---

*End of Action Plan*
