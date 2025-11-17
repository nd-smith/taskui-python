# Action Plan: Codebase-Wide Refactoring

**Created**: 2025-11-17
**Target**: All modules except `taskui/ui/app.py` (recently refactored)
**Approach**: Risk-Averse, Incremental Refactoring
**Testing Strategy**: Run full test suite after each work package

---

## Executive Summary

Following the successful refactoring of `app.py`, this plan targets the remaining codebase for improvements in:
- Code maintainability and readability
- Elimination of duplication (DRY principle)
- Consistent naming and documentation
- Adherence to Python best practices
- Better separation of concerns

**Scope**:
- UI Components (6 files, ~2,200 lines)
- Services (3 files, ~1,500 lines)
- Core modules already well-structured, minimal changes needed

---

## Risk Management Strategy

### Risk Levels
- 🟢 **LOW**: Documentation, constants, type hints - no logic changes
- 🟡 **MEDIUM**: Code reorganization, method extraction - logic unchanged but moved
- 🔴 **HIGH**: Interface changes, architectural modifications - requires careful testing

### Safety Principles
1. ✅ **One change per commit** - Easy rollback if issues arise
2. ✅ **Tests must pass** - No work package proceeds without green tests
3. ✅ **Independent packages** - Minimize dependencies between work items
4. ✅ **Verify in running app** - Manual smoke test after each change

---

## Work Package Overview

**Note**: Work packages are sized to fit within a single Claude Code context window for safer, more focused refactoring.

| # | Package Name | Risk | Effort | Target Files | Lines Changed |
|---|--------------|------|--------|--------------|---------------|
| 1a | Extract Column Parent Grouping | 🟡 | 0.5h | column.py | ~20 |
| 1b | Extract Column Task Item Creation | 🟡 | 1h | column.py | ~40 |
| 1c | Simplify Column Render Logic | 🟡 | 1h | column.py | ~30 |
| 2 | Simplify Archive Modal Logic | 🟡 | 1.5h | archive_modal.py | ~40 |
| 3 | Extract List Bar Tab Creation | 🟡 | 1h | list_bar.py | ~30 |
| 4a | Add Type Hints to task_service.py | 🟢 | 1h | task_service.py | ~30 |
| 4b | Add Type Hints to list_service.py | 🟢 | 0.5h | list_service.py | ~20 |
| 5a | Extract Task Fetch Helpers | 🟡 | 1h | task_service.py | ~40 |
| 5b | Extract Query Builder Helpers | 🟡 | 1h | task_service.py | ~35 |
| 5c | Refactor Methods to Use Helpers | 🟡 | 1h | task_service.py | ~50 |
| 6 | Consolidate List Service ORM | 🟡 | 1.5h | list_service.py | ~60 |
| 7a | Add Section Markers to task_service | 🟢 | 0.5h | task_service.py | ~30 |
| 7b | Reorganize task_service Methods | 🟡 | 1.5h | task_service.py | ~500 |
| 8 | Extract Task Modal Context Logic | 🟢 | 1h | task_modal.py | ~30 |
| 9a | Document column.py | 🟢 | 0.5h | column.py | ~20 |
| 9b | Document archive_modal.py | 🟢 | 0.5h | archive_modal.py | ~15 |
| 9c | Document list_bar.py | 🟢 | 0.5h | list_bar.py | ~15 |
| 9d | Document task_modal.py | 🟢 | 0.5h | task_modal.py | ~15 |
| 9e | Document task_item.py | 🟢 | 0.5h | task_item.py | ~15 |
| 9f | Document detail_panel.py | 🟢 | 0.5h | detail_panel.py | ~10 |
| 10 | Database Manager Cleanup | 🟡 | 1h | database.py | ~20 |

**Total Work Packages**: 21 (split for optimal context window size)
**Total Estimated Time**: 16-18 hours
**Total Risk**: Mostly LOW-MEDIUM (no HIGH risk items in this plan)

---

## Phase 1: UI Component Improvements (8.5 hours)

These changes focus on eliminating duplication and improving readability in UI components.

---

### WP1a: Extract Column Parent Grouping

**Risk**: 🟡 MEDIUM
**Effort**: 0.5 hours
**Dependencies**: None
**Target**: `taskui/ui/components/column.py`

#### Objective
Extract parent grouping logic that's duplicated in `_render_tasks()`.

#### Issues Identified

**Parent Grouping Logic Duplicated** (lines 213-219, 251-257):
- Same parent grouping code appears twice in _render_tasks()
- ~14 lines duplicated

#### Changes

**Extract parent grouping helper:**
```python
def _group_tasks_by_parent(self, tasks: List[Task]) -> dict:
    """Group tasks by parent ID for hierarchy visualization.

    Args:
        tasks: List of tasks to group

    Returns:
        Dictionary mapping parent_id (or "root") to list of children
    """
    parent_groups = {}
    for task in tasks:
        parent_id = task.parent_id or "root"
        if parent_id not in parent_groups:
            parent_groups[parent_id] = []
        parent_groups[parent_id].append(task)
    return parent_groups
```

**Update _render_tasks() to use helper:**
Replace both instances of the grouping loop with:
```python
parent_groups = self._group_tasks_by_parent(self._tasks)
```

#### Files Modified
- `taskui/ui/components/column.py`

#### Testing
```bash
# Run column-specific tests
python3 -m pytest tests/test_ui_components.py -v -k column

# Manual verification
python3 -m taskui
# Navigate through tasks
# Verify tree lines display correctly
```

#### Success Criteria
- [ ] All tests pass
- [ ] Parent grouping logic consolidated
- [ ] Tree visualization works correctly
- [ ] Lines of code reduced by ~10 lines

#### Rollback
```bash
git revert HEAD
```

---

### WP1b: Extract Column Task Item Creation

**Risk**: 🟡 MEDIUM
**Effort**: 1 hour
**Dependencies**: WP1a
**Target**: `taskui/ui/components/column.py`

#### Objective
Extract task item creation logic that's duplicated in two code paths.

#### Issues Identified

**Duplicate Widget Creation Code** (lines 222-243, 260-281):
- Nearly identical loops creating TaskItem widgets
- One inside `mount_widgets()` callback, one inline
- ~40 lines duplicated

#### Changes

**Extract task item creation:**
```python
def _create_task_items(
    self,
    tasks: List[Task],
    parent_groups: dict,
    selected_index: int
) -> List[TaskItem]:
    """Create TaskItem widgets for a list of tasks.

    Args:
        tasks: Tasks to create items for
        parent_groups: Parent grouping for last-child detection
        selected_index: Currently selected task index

    Returns:
        List of TaskItem widgets ready to mount
    """
    task_items = []
    for i, task in enumerate(tasks):
        parent_id = task.parent_id or "root"
        siblings = parent_groups[parent_id]
        is_last_child = task == siblings[-1] if siblings else False

        task_item = TaskItem(
            task=task,
            is_last_child=is_last_child,
            id=f"task-{task.id}"
        )
        task_item.selected = (i == selected_index)
        task_items.append(task_item)

    return task_items
```

**Update both code paths to use helper:**
Replace the duplicate loops in both locations with:
```python
task_items = self._create_task_items(self._tasks, parent_groups, self._selected_index)
for task_item in task_items:
    content_container.mount(task_item)
```

#### Files Modified
- `taskui/ui/components/column.py`

#### Testing
```bash
# Run column-specific tests
python3 -m pytest tests/test_ui_components.py -v -k column

# Manual verification
python3 -m taskui
# Navigate through tasks
# Create/delete tasks to trigger re-renders
# Verify selection state preserved
```

#### Success Criteria
- [ ] All tests pass
- [ ] Task item creation consolidated
- [ ] Task rendering works correctly
- [ ] Selection state preserved across re-renders
- [ ] Lines of code reduced by ~35 lines

#### Rollback
```bash
git revert HEAD
```

---

### WP1c: Simplify Column Render Logic

**Risk**: 🟡 MEDIUM
**Effort**: 1 hour
**Dependencies**: WP1a, WP1b
**Target**: `taskui/ui/components/column.py`

#### Objective
Simplify the main `_render_tasks()` method using extracted helpers.

#### Changes

**Simplified _render_tasks():**
```python
def _render_tasks(self) -> None:
    """Render the task list with TaskItem widgets."""
    logger.debug(f"{self.column_id}: _render_tasks() called with {len(self._tasks)} tasks")

    content_container = self.query_one(f"#{self.column_id}-content", VerticalScroll)
    empty_message = self.query_one(f"#{self.column_id}-empty", Static)

    # Handle empty state
    if not self._tasks:
        existing_items = list(content_container.query(TaskItem))
        for widget in existing_items:
            try:
                widget.remove()
            except Exception:
                pass
        empty_message.display = True
        return

    empty_message.display = False

    # Group tasks and create items
    parent_groups = self._group_tasks_by_parent(self._tasks)
    task_items = self._create_task_items(self._tasks, parent_groups, self._selected_index)

    # Mount widgets
    existing_items = list(content_container.query(TaskItem))
    if existing_items:
        content_container.remove_children(TaskItem)
        self.call_after_refresh(lambda: self._mount_task_items(content_container, task_items))
    else:
        self._mount_task_items(content_container, task_items)

def _mount_task_items(self, container: VerticalScroll, task_items: List[TaskItem]) -> None:
    """Mount task items in container.

    Args:
        container: Container to mount items in
        task_items: List of TaskItem widgets to mount
    """
    logger.debug(f"{self.column_id}: Mounting {len(task_items)} task items")
    for task_item in task_items:
        try:
            container.mount(task_item)
        except Exception as e:
            logger.error(f"{self.column_id}: ERROR mounting task widget: {e}", exc_info=True)
    logger.debug(f"{self.column_id}: Mounting completed")
```

#### Files Modified
- `taskui/ui/components/column.py`

#### Testing
```bash
# Run column-specific tests
python3 -m pytest tests/test_ui_components.py -v -k column

# Run full test suite
python3 -m pytest tests/ -v

# Manual verification
python3 -m taskui
# Navigate through tasks
# Create/delete tasks to trigger re-renders
# Verify no visual regressions
```

#### Success Criteria
- [ ] All tests pass
- [ ] _render_tasks() is simplified and readable
- [ ] All functionality preserved
- [ ] Total lines reduced by ~70 lines across WP1a-c

#### Rollback
```bash
git revert HEAD
```

---

### WP2: Simplify Archive Modal Logic

**Risk**: 🟡 MEDIUM
**Effort**: 1.5 hours
**Dependencies**: None
**Target**: `taskui/ui/components/archive_modal.py`

#### Objective
Consolidate duplicate task list update logic and simplify filter update flow.

#### Issues Identified

1. **Duplicate List Update Logic** (lines 310-340):
   - Similar code for updating task list after filtering
   - Repeated mounting logic

2. **Verbose Info Text Updates**:
   - Repetitive string formatting for info text

#### Changes

**Extract list view update helper:**
```python
def _update_task_list_view(self, search_query: str = "") -> None:
    """Update the task list view based on current filtered tasks.

    Args:
        search_query: Current search query (for info text)
    """
    list_container = self.query_one(".task-list-container")
    list_container.remove_children()

    if self.filtered_tasks:
        list_view = ListView(
            *self._create_list_items(),
            id="task-list"
        )
        list_container.mount(list_view)
        list_view.focus()
        self.selected_task = self.filtered_tasks[0]
    else:
        empty_msg = Static(
            "No matching tasks\n\nTry a different search term",
            classes="empty-message"
        )
        list_container.mount(empty_msg)
        self.selected_task = None

    self._update_info_text(search_query)

def _update_info_text(self, search_query: str = "") -> None:
    """Update the info text based on current filter state.

    Args:
        search_query: Current search query
    """
    info_text = self.query_one("#info-text", Static)
    filtered_count = len(self.filtered_tasks)
    total_count = len(self.all_archived_tasks)

    plural = 's' if total_count != 1 else ''

    if search_query:
        info_text.update(
            f"{filtered_count} of {total_count} archived task{plural} • Press R to restore"
        )
    else:
        info_text.update(
            f"{total_count} archived task{plural} • Press R to restore"
        )
```

**Simplify _filter_tasks:**
```python
def _filter_tasks(self, search_query: str) -> None:
    """Filter tasks based on search query.

    Args:
        search_query: The search string (case-insensitive)
    """
    if not search_query:
        self.filtered_tasks = self.all_archived_tasks
    else:
        self.filtered_tasks = [
            task for task in self.all_archived_tasks
            if search_query in task.title.lower() or
               (task.notes and search_query in task.notes.lower())
        ]

    self._update_task_list_view(search_query)
```

#### Files Modified
- `taskui/ui/components/archive_modal.py`

#### Testing
```bash
# Run archive modal tests
python3 -m pytest tests/test_archive_modal.py -v

# Manual verification
python3 -m taskui
# Create and complete tasks
# Archive them (A)
# View archives (V)
# Test search functionality
# Test restore (R)
```

#### Success Criteria
- [ ] All tests pass
- [ ] Archive search works correctly
- [ ] Info text updates properly
- [ ] Restore functionality unchanged
- [ ] Code is more DRY

#### Rollback
```bash
git revert HEAD
```

---

### WP3: Extract List Bar Tab Creation

**Risk**: 🟡 MEDIUM
**Effort**: 1 hour
**Dependencies**: None
**Target**: `taskui/ui/components/list_bar.py`

#### Objective
Eliminate duplication between `compose()` and `refresh_tabs()` methods.

#### Issues Identified

1. **Duplicate Tab Creation Logic** (lines 187-197, 219-229):
   - Same loop and logic appears in both methods
   - Creates inconsistency risk if one is updated but not the other

#### Changes

**Extract tab creation helper:**
```python
def _create_tab_for_list(
    self,
    task_list: TaskList,
    shortcut_number: int,
    is_last: bool
) -> ListTab:
    """Create a ListTab widget for a task list.

    Args:
        task_list: Task list to create tab for
        shortcut_number: Keyboard shortcut number (1-3)
        is_last: Whether this is the last tab

    Returns:
        Configured ListTab widget
    """
    is_active = task_list.id == self.active_list_id
    return ListTab(
        task_list=task_list,
        shortcut_number=shortcut_number,
        is_active=is_active,
        is_last=is_last
    )

def _create_all_tabs(self) -> List[ListTab]:
    """Create ListTab widgets for all lists.

    Returns:
        List of ListTab widgets
    """
    tabs = []
    total_lists = len(self.lists)

    for idx, task_list in enumerate(self.lists, start=1):
        is_last = idx == total_lists
        tab = self._create_tab_for_list(task_list, idx, is_last)
        tabs.append(tab)

    return tabs
```

**Simplify compose() and refresh_tabs():**
```python
def compose(self):
    """Compose the list bar with list tabs."""
    self.tabs.clear()
    self.tabs = self._create_all_tabs()
    yield from self.tabs

def refresh_tabs(self) -> None:
    """Refresh all tabs to reflect current data."""
    # Remove existing tabs
    for child in list(self.children):
        child.remove()

    # Create and mount new tabs
    self.tabs.clear()
    self.tabs = self._create_all_tabs()

    for tab in self.tabs:
        self.mount(tab)
```

#### Files Modified
- `taskui/ui/components/list_bar.py`

#### Testing
```bash
# Run list bar tests
python3 -m pytest tests/test_list_bar.py -v

# Manual verification
python3 -m taskui
# Switch between lists (1, 2, 3)
# Create tasks in different lists
# Verify completion percentages update
```

#### Success Criteria
- [ ] All tests pass
- [ ] List switching works correctly
- [ ] Tab highlighting updates properly
- [ ] Completion percentages display
- [ ] Code is more DRY

#### Rollback
```bash
git revert HEAD
```

---

### WP8: Extract Task Modal Context Logic

**Risk**: 🟢 LOW
**Effort**: 1 hour
**Dependencies**: None
**Target**: `taskui/ui/components/task_modal.py`

#### Objective
Simplify context text generation with helper method extraction.

#### Issues Identified

1. **Complex _get_context_text() method** (lines 262-287):
   - Multiple conditional branches
   - Could be broken into smaller helpers

#### Changes

**Extract context text helpers:**
```python
def _get_edit_context_text(self) -> str:
    """Get context text for edit mode."""
    if not self.edit_task:
        return ""
    return f"Editing: {self.edit_task.title[:40]}..."

def _get_child_context_text(self) -> str:
    """Get context text for child creation."""
    if not self.parent_task:
        return ""

    child_level = NestingRules.get_allowed_child_level(self.parent_task, self.column)
    return (
        f"Creating child under: {self.parent_task.title[:30]}...\n"
        f"New task level: {child_level} | Column: {self.column.value}"
    )

def _get_sibling_context_text(self) -> str:
    """Get context text for sibling creation."""
    if self.parent_task:
        return (
            f"Creating sibling at level: {self.parent_task.level} | "
            f"Column: {self.column.value}"
        )
    return f"Creating new top-level task | Column: {self.column.value}"

def _get_context_text(self) -> str:
    """Get the context information text."""
    if self.validation_error:
        return ""

    if self.mode == "edit":
        return self._get_edit_context_text()
    elif self.mode == "create_child":
        return self._get_child_context_text()
    else:  # create_sibling
        return self._get_sibling_context_text()
```

#### Files Modified
- `taskui/ui/components/task_modal.py`

#### Testing
```bash
# Run task modal tests
python3 -m pytest tests/test_task_modal.py -v

# Manual verification
python3 -m taskui
# Test N (create sibling)
# Test C (create child)
# Test E (edit task)
# Verify context text displays correctly
```

#### Success Criteria
- [ ] All tests pass
- [ ] Context text displays correctly
- [ ] Modal behavior unchanged
- [ ] Code is more readable

#### Rollback
```bash
git revert HEAD
```

---

### WP9a: Document column.py

**Risk**: 🟢 LOW
**Effort**: 0.5 hours
**Dependencies**: WP1a, WP1b, WP1c
**Target**: `taskui/ui/components/column.py`

#### Objective
Add comprehensive docstrings to column component.

#### Focus Areas
- Document retry mechanism in ensure_selection
- Add docstrings to extracted helpers
- Ensure all public methods documented
- Add Args/Returns sections

#### Files Modified
- `taskui/ui/components/column.py`

#### Testing
```bash
python3 -m pydoc taskui.ui.components.column
python3 -m pytest tests/test_ui_components.py -v -k column
```

#### Success Criteria
- [ ] All tests pass
- [ ] All public methods have docstrings
- [ ] pydoc output is readable

#### Rollback
```bash
git revert HEAD
```

---

### WP9b: Document archive_modal.py

**Risk**: 🟢 LOW
**Effort**: 0.5 hours
**Dependencies**: WP2
**Target**: `taskui/ui/components/archive_modal.py`

#### Objective
Add comprehensive docstrings to archive modal component.

#### Focus Areas
- Document search filtering logic
- Add docstrings to extracted helpers
- Document restore functionality

#### Files Modified
- `taskui/ui/components/archive_modal.py`

#### Testing
```bash
python3 -m pydoc taskui.ui.components.archive_modal
python3 -m pytest tests/test_archive_modal.py -v
```

#### Success Criteria
- [ ] All tests pass
- [ ] All public methods have docstrings
- [ ] pydoc output is readable

#### Rollback
```bash
git revert HEAD
```

---

### WP9c: Document list_bar.py

**Risk**: 🟢 LOW
**Effort**: 0.5 hours
**Dependencies**: WP3
**Target**: `taskui/ui/components/list_bar.py`

#### Objective
Add comprehensive docstrings to list bar component.

#### Focus Areas
- Document tab creation and switching
- Add docstrings to extracted helpers
- Document list selection logic

#### Files Modified
- `taskui/ui/components/list_bar.py`

#### Testing
```bash
python3 -m pydoc taskui.ui.components.list_bar
python3 -m pytest tests/test_list_bar.py -v
```

#### Success Criteria
- [ ] All tests pass
- [ ] All public methods have docstrings
- [ ] pydoc output is readable

#### Rollback
```bash
git revert HEAD
```

---

### WP9d: Document task_modal.py

**Risk**: 🟢 LOW
**Effort**: 0.5 hours
**Dependencies**: WP8
**Target**: `taskui/ui/components/task_modal.py`

#### Objective
Add comprehensive docstrings to task modal component.

#### Focus Areas
- Document validation logic
- Add docstrings to extracted helpers
- Document nesting limit checks

#### Files Modified
- `taskui/ui/components/task_modal.py`

#### Testing
```bash
python3 -m pydoc taskui.ui.components.task_modal
python3 -m pytest tests/test_task_modal.py -v
```

#### Success Criteria
- [ ] All tests pass
- [ ] All public methods have docstrings
- [ ] pydoc output is readable

#### Rollback
```bash
git revert HEAD
```

---

### WP9e: Document task_item.py

**Risk**: 🟢 LOW
**Effort**: 0.5 hours
**Dependencies**: None
**Target**: `taskui/ui/components/task_item.py`

#### Objective
Enhance docstrings in task item component.

#### Focus Areas
- Add more detailed render() docstring
- Document color selection logic
- Document tree line rendering

#### Files Modified
- `taskui/ui/components/task_item.py`

#### Testing
```bash
python3 -m pydoc taskui.ui.components.task_item
python3 -m pytest tests/test_ui_components.py -v -k task_item
```

#### Success Criteria
- [ ] All tests pass
- [ ] All public methods have docstrings
- [ ] pydoc output is readable

#### Rollback
```bash
git revert HEAD
```

---

### WP9f: Document detail_panel.py

**Risk**: 🟢 LOW
**Effort**: 0.5 hours
**Dependencies**: None
**Target**: `taskui/ui/components/detail_panel.py`

#### Objective
Minor docstring enhancements (already well-documented).

#### Focus Areas
- Verify all methods documented
- Add any missing Args/Returns
- Minor clarifications only

#### Files Modified
- `taskui/ui/components/detail_panel.py`

#### Testing
```bash
python3 -m pydoc taskui.ui.components.detail_panel
python3 -m pytest tests/ -v -k detail_panel
```

#### Success Criteria
- [ ] All tests pass
- [ ] All public methods have docstrings
- [ ] pydoc output is readable

#### Rollback
```bash
git revert HEAD
```

---

## Phase 2: Service Layer Improvements (7.5 hours)

These changes focus on reducing duplication and improving organization in service classes.

---

### WP4a: Add Type Hints to task_service.py

**Risk**: 🟢 LOW
**Effort**: 1 hour
**Dependencies**: None
**Target**: `taskui/services/task_service.py`

#### Objective
Add missing return type hints to all task service methods for better IDE support and type checking.

#### Issues Identified

1. **Missing return types on some methods**
2. **Some parameters lack type hints**

#### Changes

Add complete type hints to all methods in `TaskService`.

Ensure all methods follow this pattern:
```python
async def method_name(self, param: Type) -> ReturnType:
    """Docstring."""
    ...
```

Focus on:
- Public async methods (create, read, update, delete operations)
- Private helper methods
- Query builder methods

#### Files Modified
- `taskui/services/task_service.py`

#### Testing
```bash
# Run type checker
python3 -m mypy taskui/services/task_service.py --ignore-missing-imports

# Run service tests
python3 -m pytest tests/test_task_service.py -v
```

#### Success Criteria
- [ ] All tests pass
- [ ] All methods have return type hints
- [ ] All parameters have type hints
- [ ] Mypy runs without errors for this file

#### Rollback
```bash
git revert HEAD
```

---

### WP4b: Add Type Hints to list_service.py

**Risk**: 🟢 LOW
**Effort**: 0.5 hours
**Dependencies**: None
**Target**: `taskui/services/list_service.py`

#### Objective
Add missing return type hints to all list service methods.

#### Changes

Add complete type hints to all methods in `ListService`.

Focus on:
- CRUD methods (create_list, get_all_lists, etc.)
- Count helper methods
- ensure_default_lists method

#### Files Modified
- `taskui/services/list_service.py`

#### Testing
```bash
# Run type checker
python3 -m mypy taskui/services/list_service.py --ignore-missing-imports

# Run service tests
python3 -m pytest tests/test_list_service.py -v
```

#### Success Criteria
- [ ] All tests pass
- [ ] All methods have return type hints
- [ ] All parameters have type hints
- [ ] Mypy runs without errors for this file

#### Rollback
```bash
git revert HEAD
```

---

### WP5a: Extract Task Fetch Helpers

**Risk**: 🟡 MEDIUM
**Effort**: 1 hour
**Dependencies**: WP4a
**Target**: `taskui/services/task_service.py`

#### Objective
Extract helpers for fetching tasks with child counts (repeated 8+ times).

#### Issues Identified

**Repetitive task fetching with child counts** (appears 8+ times):
```python
# Pattern repeated throughout:
task = self._orm_to_pydantic(task_orm)
child_count = await self._count_children(task.id)
completed_child_count = await self._count_completed_children(task.id)
task.update_child_counts(child_count, completed_child_count)
```

#### Changes

**Extract task fetching with counts:**
```python
async def _fetch_task_with_counts(
    self,
    task_orm: TaskORM
) -> Task:
    """Convert ORM task to Pydantic with child counts populated.

    Args:
        task_orm: SQLAlchemy task instance

    Returns:
        Pydantic Task with child counts
    """
    task = self._orm_to_pydantic(task_orm)

    # Get child counts
    child_count = await self._count_children(task.id)
    completed_child_count = await self._count_completed_children(task.id)
    task.update_child_counts(child_count, completed_child_count)

    return task

async def _fetch_tasks_with_counts(
    self,
    task_orms: List[TaskORM]
) -> List[Task]:
    """Convert list of ORM tasks to Pydantic with child counts.

    Args:
        task_orms: List of SQLAlchemy task instances

    Returns:
        List of Pydantic Tasks with child counts
    """
    tasks = []
    for task_orm in task_orms:
        task = await self._fetch_task_with_counts(task_orm)
        tasks.append(task)
    return tasks
```

**Do NOT extract query builders yet** (that's WP5b).

#### Files Modified
- `taskui/services/task_service.py`

#### Testing
```bash
# Run task service tests
python3 -m pytest tests/test_task_service.py -v

# Manual verification
python3 -m taskui
# Verify child counts display correctly
```

#### Success Criteria
- [ ] All tests pass
- [ ] Fetch helpers extracted
- [ ] No behavioral changes
- [ ] Lines of code reduced by ~30 lines

#### Rollback
```bash
git revert HEAD
```

---

### WP5b: Extract Query Builder Helpers

**Risk**: 🟡 MEDIUM
**Effort**: 1 hour
**Dependencies**: WP5a
**Target**: `taskui/services/task_service.py`

#### Objective
Extract common query building patterns for active tasks, top-level tasks, and children.

#### Issues Identified

**Repetitive query patterns**:
- Active (non-archived) tasks queries
- Top-level tasks queries
- Child tasks queries

#### Changes

**Extract query builders:**
```python
def _query_active_tasks(self, list_id: UUID):
    """Build query for active (non-archived) tasks in a list.

    Args:
        list_id: List to query

    Returns:
        SQLAlchemy select statement
    """
    return (
        select(TaskORM)
        .where(TaskORM.list_id == str(list_id))
        .where(TaskORM.is_archived == False)
        .order_by(TaskORM.position)
    )

def _query_top_level_tasks(self, list_id: UUID):
    """Build query for top-level tasks in a list.

    Args:
        list_id: List to query

    Returns:
        SQLAlchemy select statement
    """
    return (
        self._query_active_tasks(list_id)
        .where(TaskORM.parent_id.is_(None))
    )

def _query_child_tasks(self, parent_id: UUID):
    """Build query for children of a parent task.

    Args:
        parent_id: Parent task ID

    Returns:
        SQLAlchemy select statement
    """
    return (
        select(TaskORM)
        .where(TaskORM.parent_id == str(parent_id))
        .where(TaskORM.is_archived == False)
        .order_by(TaskORM.position)
    )
```

#### Files Modified
- `taskui/services/task_service.py`

#### Testing
```bash
# Run task service tests
python3 -m pytest tests/test_task_service.py -v

# Manual verification
python3 -m taskui
# Verify queries work correctly
```

#### Success Criteria
- [ ] All tests pass
- [ ] Query builders extracted
- [ ] No behavioral changes
- [ ] Lines of code reduced by ~25 lines

#### Rollback
```bash
git revert HEAD
```

---

### WP5c: Refactor Methods to Use Helpers

**Risk**: 🟡 MEDIUM
**Effort**: 1 hour
**Dependencies**: WP5a, WP5b
**Target**: `taskui/services/task_service.py`

#### Objective
Update methods like `get_tasks_for_list()`, `get_task_children()`, etc. to use the extracted helpers.

#### Changes

Update approximately 6-8 methods to use:
- `_fetch_task_with_counts()` and `_fetch_tasks_with_counts()` from WP5a
- `_query_active_tasks()`, `_query_top_level_tasks()`, `_query_child_tasks()` from WP5b

#### Files Modified
- `taskui/services/task_service.py`

#### Testing
```bash
# Run task service tests
python3 -m pytest tests/test_task_service.py -v

# Run integration tests
python3 -m pytest tests/test_integration_mvp.py -v

# Manual verification
python3 -m taskui
# Test all task operations
```

#### Success Criteria
- [ ] All tests pass
- [ ] All methods use helpers
- [ ] No behavioral changes
- [ ] Total lines reduced by ~80 lines across WP5a-c

#### Rollback
```bash
git revert HEAD
```

---

### WP6: Consolidate List Service ORM Conversion

**Risk**: 🟡 MEDIUM
**Effort**: 1.5 hours
**Dependencies**: WP4
**Target**: `taskui/services/list_service.py`

#### Objective
Extract repeated ORM-to-Pydantic conversion logic with count population.

#### Issues Identified

1. **Repeated conversion pattern** (appears in 4 methods):
```python
task_list = TaskList(
    id=UUID(list_orm.id),
    name=list_orm.name,
    created_at=list_orm.created_at
)
task_count = await self._get_task_count(UUID(list_orm.id))
completed_count = await self._get_completed_count(UUID(list_orm.id))
task_list.update_counts(task_count, completed_count)
```

2. **Repeated count queries**:
   - Could be optimized with a single combined query

#### Changes

**Extract ORM conversion helper:**
```python
async def _orm_to_pydantic_with_counts(
    self,
    list_orm: TaskListORM
) -> TaskList:
    """Convert TaskListORM to Pydantic with counts populated.

    Args:
        list_orm: SQLAlchemy task list instance

    Returns:
        Pydantic TaskList with counts
    """
    list_id = UUID(list_orm.id)

    task_list = TaskList(
        id=list_id,
        name=list_orm.name,
        created_at=list_orm.created_at
    )

    # Get counts
    task_count = await self._get_task_count(list_id)
    completed_count = await self._get_completed_count(list_id)
    task_list.update_counts(task_count, completed_count)

    return task_list

async def _orms_to_pydantic_with_counts(
    self,
    list_orms: List[TaskListORM]
) -> List[TaskList]:
    """Convert list of TaskListORMs to Pydantic with counts.

    Args:
        list_orms: List of SQLAlchemy task list instances

    Returns:
        List of Pydantic TaskLists with counts
    """
    task_lists = []
    for list_orm in list_orms:
        task_list = await self._orm_to_pydantic_with_counts(list_orm)
        task_lists.append(task_list)
    return task_lists
```

**Refactor methods to use helpers:**

Update `get_all_lists()`, `get_list_by_id()`, `get_list_by_name()`, `update_list()` to use the helper.

**Before:**
```python
async def get_list_by_id(self, list_id: UUID) -> Optional[TaskList]:
    result = await self.session.execute(
        select(TaskListORM).where(TaskListORM.id == str(list_id))
    )
    list_orm = result.scalar_one_or_none()

    if not list_orm:
        return None

    task_list = TaskList(
        id=UUID(list_orm.id),
        name=list_orm.name,
        created_at=list_orm.created_at
    )

    task_count = await self._get_task_count(list_id)
    completed_count = await self._get_completed_count(list_id)
    task_list.update_counts(task_count, completed_count)

    return task_list
```

**After:**
```python
async def get_list_by_id(self, list_id: UUID) -> Optional[TaskList]:
    result = await self.session.execute(
        select(TaskListORM).where(TaskListORM.id == str(list_id))
    )
    list_orm = result.scalar_one_or_none()

    if not list_orm:
        return None

    return await self._orm_to_pydantic_with_counts(list_orm)
```

#### Files Modified
- `taskui/services/list_service.py`

#### Testing
```bash
# Run list service tests
python3 -m pytest tests/test_list_service.py -v

# Manual verification
python3 -m taskui
# Switch between lists
# Verify completion percentages
```

#### Success Criteria
- [ ] All tests pass
- [ ] Conversion logic consolidated
- [ ] No behavioral changes
- [ ] Code is more DRY
- [ ] Lines of code reduced by ~40 lines

#### Rollback
```bash
git revert HEAD
```

---

### WP7a: Add Section Markers to task_service

**Risk**: 🟢 LOW
**Effort**: 0.5 hours
**Dependencies**: WP5c
**Target**: `taskui/services/task_service.py`

#### Objective
Add section marker comments to organize task service methods (no code movement yet).

#### Approach

Add section markers similar to app.py refactoring:

```python
# ==============================================================================
# CONVERSION HELPERS
# ==============================================================================

@staticmethod
def _orm_to_pydantic(task_orm: TaskORM) -> Task:
    ...

@staticmethod
def _pydantic_to_orm(task: Task) -> TaskORM:
    ...

# ==============================================================================
# VALIDATION HELPERS
# ==============================================================================

async def _verify_list_exists(self, list_id: UUID) -> None:
    ...

async def _get_task_or_raise(self, task_id: UUID) -> TaskORM:
    ...

# ==============================================================================
# QUERY HELPERS
# ==============================================================================

def _query_active_tasks(self, list_id: UUID):
    ...

def _query_top_level_tasks(self, list_id: UUID):
    ...

# ==============================================================================
# CREATE OPERATIONS
# ==============================================================================

async def create_task(...) -> Task:
    ...

async def create_child_task(...) -> Task:
    ...

# ==============================================================================
# READ OPERATIONS
# ==============================================================================

async def get_task_by_id(...) -> Optional[Task]:
    ...

async def get_tasks_for_list(...) -> List[Task]:
    ...

# ==============================================================================
# UPDATE OPERATIONS
# ==============================================================================

async def update_task(...) -> Optional[Task]:
    ...

async def toggle_completion(...) -> Optional[Task]:
    ...

# ==============================================================================
# DELETE/ARCHIVE OPERATIONS
# ==============================================================================

async def delete_task(...) -> bool:
    ...

async def archive_task(...) -> Optional[Task]:
    ...

# ==============================================================================
# HIERARCHY OPERATIONS
# ==============================================================================

async def get_task_children(...) -> List[Task]:
    ...

async def get_task_hierarchy(...) -> List[Task]:
    ...

# ==============================================================================
# COUNTING HELPERS
# ==============================================================================

async def _count_children(...) -> int:
    ...

async def _count_completed_children(...) -> int:
    ...
```

#### Files Modified
- `taskui/services/task_service.py`

#### Testing
```bash
# Verify file still parses
python3 -c "import taskui.services.task_service; print('OK')"

# Run tests
python3 -m pytest tests/test_task_service.py -v
```

#### Success Criteria
- [ ] All tests pass
- [ ] Section markers added
- [ ] File parses correctly
- [ ] No logic changes

#### Rollback
```bash
git revert HEAD
```

---

### WP7b: Reorganize task_service Methods

**Risk**: 🟡 MEDIUM
**Effort**: 1.5 hours
**Dependencies**: WP7a
**Target**: `taskui/services/task_service.py`

#### Objective
Move methods to match section markers from WP7a.

#### Approach

Physically reorganize methods to match the sections:
- CONVERSION HELPERS
- VALIDATION HELPERS
- QUERY HELPERS
- CREATE OPERATIONS
- READ OPERATIONS
- UPDATE OPERATIONS
- DELETE/ARCHIVE OPERATIONS
- HIERARCHY OPERATIONS
- COUNTING HELPERS

**Important**: This is ONLY moving methods, no code changes.

#### Files Modified
- `taskui/services/task_service.py`

#### Testing
```bash
# Verify file still parses
python3 -c "import taskui.services.task_service; print('OK')"

# Run tests
python3 -m pytest tests/test_task_service.py -v

# Run integration tests
python3 -m pytest tests/test_integration_mvp.py -v

# Manual verification
python3 -m taskui
```

#### Success Criteria
- [ ] All tests pass
- [ ] Methods organized in logical sections
- [ ] No behavioral changes
- [ ] Easier to navigate

#### Rollback
```bash
git revert HEAD
```

---

## Phase 3: Minor Cleanup (1.5 hours)

Final polish and cleanup tasks.

---

### WP10: Database Manager Cleanup

**Risk**: 🟡 MEDIUM
**Effort**: 1 hour
**Dependencies**: None
**Target**: `taskui/database.py`

#### Objective
Review and potentially remove/relocate helper methods that may belong in service layer.

#### Issues Identified

1. **Helper methods on DatabaseManager** (lines 185-215):
   - `get_task_list_by_id()`
   - `get_task_by_id()`

   These duplicate service layer functionality and create mixed concerns.

#### Decision Points

**Option A: Remove helpers entirely**
- Force all queries through service layer
- Cleaner separation of concerns
- May break existing code

**Option B: Mark as deprecated**
- Add deprecation warnings
- Document that service layer should be used
- Gradual migration

**Option C: Keep as convenience methods**
- Document their purpose
- Ensure they're only used in specific contexts

#### Recommended Approach

Option B: Mark as deprecated and document migration path.

```python
import warnings

async def get_task_list_by_id(
    self,
    session: AsyncSession,
    list_id: UUID
) -> Optional[TaskListORM]:
    """Retrieve a task list by ID.

    .. deprecated:: 1.0
        Use ListService.get_list_by_id() instead.
        This method will be removed in version 2.0.

    Args:
        session: Active database session
        list_id: UUID of the task list

    Returns:
        TaskListORM instance or None if not found
    """
    warnings.warn(
        "DatabaseManager.get_task_list_by_id() is deprecated. "
        "Use ListService.get_list_by_id() instead.",
        DeprecationWarning,
        stacklevel=2
    )

    result = await session.execute(
        select(TaskListORM).where(TaskListORM.id == str(list_id))
    )
    return result.scalar_one_or_none()
```

#### Files Modified
- `taskui/database.py`
- Update any direct calls to use service layer

#### Testing
```bash
# Check for direct calls to deprecated methods
grep -r "get_task_list_by_id\|get_task_by_id" taskui/ tests/

# Run tests to ensure no breakage
python3 -m pytest tests/ -v
```

#### Success Criteria
- [x] All tests pass
- [x] Deprecation warnings in place
- [x] Documentation updated
- [x] No new usage of deprecated methods

#### Rollback
```bash
git revert HEAD
```

---

## Testing Strategy

### After Each Work Package

1. **Unit Tests**:
   ```bash
   python3 -m pytest tests/test_<relevant_module>.py -v
   ```

2. **Integration Tests**:
   ```bash
   python3 -m pytest tests/test_integration_mvp.py -v
   ```

3. **Full Test Suite**:
   ```bash
   python3 -m pytest tests/ -v
   ```

4. **Manual Smoke Test**:
   ```bash
   python3 -m taskui
   # Test affected functionality
   ```

### Final Validation

After all work packages complete:

```bash
# Full test suite
python3 -m pytest tests/ -v --cov=taskui --cov-report=term-missing

# Type checking (if using mypy)
python3 -m mypy taskui/ --ignore-missing-imports

# Lint check (if using flake8/ruff)
python3 -m flake8 taskui/
# OR
ruff check taskui/

# Manual comprehensive test
python3 -m taskui
# Test every major feature
```

---

## Success Metrics

After completing all work packages, measure:

### Code Quality Metrics

- **Lines of code reduced**: Target 150-200 lines (duplication elimination)
- **Duplication**: Target <3% (from current ~8-10% in services)
- **Documentation coverage**: Target 100% (all public methods)
- **Type hint coverage**: Target 100% (all methods)

### Maintainability Metrics

- **Average method length**: Target <30 lines
- **Maximum method length**: Target <50 lines (from current 70+)
- **Cyclomatic complexity**: Reduce by 15-20%

### Test Metrics

- **Test pass rate**: 100% (419+ tests passing)
- **Code coverage**: Maintain or improve current coverage
- **No regressions**: All existing functionality works

---

## File Summary

Files targeted for refactoring:

### UI Components (6 files)
- ✅ `taskui/ui/components/column.py` - WP1, WP9
- ✅ `taskui/ui/components/task_item.py` - WP9
- ✅ `taskui/ui/components/task_modal.py` - WP8, WP9
- ✅ `taskui/ui/components/detail_panel.py` - WP9
- ✅ `taskui/ui/components/list_bar.py` - WP3, WP9
- ✅ `taskui/ui/components/archive_modal.py` - WP2, WP9

### Services (3 files)
- ✅ `taskui/services/task_service.py` - WP4, WP5, WP7
- ✅ `taskui/services/list_service.py` - WP4, WP6
- ✅ `taskui/services/nesting_rules.py` - No changes needed (already excellent)

### Core Modules (1 file)
- ✅ `taskui/database.py` - WP10

### No Changes Needed (excellent as-is)
- ✅ `taskui/models.py` - Well-structured Pydantic models
- ✅ `taskui/config.py` - Simple and clean
- ✅ `taskui/logging_config.py` - Well-organized
- ✅ `taskui/ui/theme.py` - Excellently documented

---

## Timeline

**Assuming dedicated work, ~4-5 days total (work packages sized for single context windows):**

**Day 1 (6 hours)**: Phase 1 Part 1 - UI Components
- WP1a: Extract Column Parent Grouping (0.5h)
- WP1b: Extract Column Task Item Creation (1h)
- WP1c: Simplify Column Render Logic (1h)
- WP2: Simplify Archive Modal Logic (1.5h)
- WP3: Extract List Bar Tab Creation (1h)
- WP8: Extract Task Modal Context Logic (1h)
- Checkpoint: Commit and tag `phase-1a-ui-refactor`

**Day 2 (3 hours)**: Phase 1 Part 2 - UI Documentation
- WP9a: Document column.py (0.5h)
- WP9b: Document archive_modal.py (0.5h)
- WP9c: Document list_bar.py (0.5h)
- WP9d: Document task_modal.py (0.5h)
- WP9e: Document task_item.py (0.5h)
- WP9f: Document detail_panel.py (0.5h)
- Checkpoint: Commit and tag `phase-1b-ui-docs`

**Day 3 (4.5 hours)**: Phase 2 Part 1 - Service Layer Foundation
- WP4a: Add Type Hints to task_service.py (1h)
- WP4b: Add Type Hints to list_service.py (0.5h)
- WP5a: Extract Task Fetch Helpers (1h)
- WP5b: Extract Query Builder Helpers (1h)
- WP5c: Refactor Methods to Use Helpers (1h)
- Checkpoint: Commit and tag `phase-2a-services-foundation`

**Day 4 (3.5 hours)**: Phase 2 Part 2 - Service Layer Organization
- WP6: Consolidate List Service ORM Conversion (1.5h)
- WP7a: Add Section Markers to task_service (0.5h)
- WP7b: Reorganize task_service Methods (1.5h)
- Checkpoint: Commit and tag `phase-2b-services-complete`

**Day 5 (1.5 hours)**: Phase 3 - Final Cleanup & Validation
- WP10: Database Manager Cleanup (1h)
- Final validation and testing (0.5h)
- Documentation update
- Final commit and tag `codebase-refactor-complete`

---

## Emergency Procedures

### If Tests Start Failing

```bash
# 1. Check which tests failed
python3 -m pytest tests/ -v --tb=short

# 2. Check what changed
git diff HEAD~1

# 3. Revert if unclear
git revert HEAD

# 4. Re-run tests to confirm they pass
python3 -m pytest tests/ -v
```

### If Behavior Changed Unexpectedly

```bash
# 1. Document the change
# 2. Determine if acceptable or bug
# 3. If bug, revert immediately
git revert HEAD

# 4. Debug offline and fix
```

---

## Post-Completion Tasks

### 1. Update Documentation

- [ ] Update CHANGELOG.md with improvements
- [ ] Update README.md if needed
- [ ] Update developer documentation

### 2. Code Review

- [ ] Review all changes as a whole
- [ ] Verify consistency across files
- [ ] Check for any missed opportunities

### 3. Performance Check

- [ ] Benchmark app startup time
- [ ] Verify no performance regressions
- [ ] Check database query counts

### 4. Knowledge Share

- [ ] Document lessons learned
- [ ] Share refactoring patterns
- [ ] Update coding standards if needed

---

## Excluded Items

The following improvements are intentionally excluded due to risk or scope:

### ❌ Printer Service Refactoring
**Why excluded**:
- Peripheral feature
- Complex hardware interaction
- Low priority
- Better addressed in dedicated printer improvement project

### ❌ Extract UI Components to Smaller Widgets
**Why excluded**:
- Would require changing component interfaces
- Risk of breaking existing layout
- Better as separate architectural improvement

### ❌ Migrate to Async Context Managers Everywhere
**Why excluded**:
- Current pattern works well
- Changes would be pervasive
- Risk/reward ratio not favorable

---

## Questions for Review

Before proceeding, please confirm:

1. **Priority**: Are there specific files/areas you want prioritized?
2. **Timeline**: Is the 3-4 day estimate acceptable?
3. **Scope**: Any modules you want added/removed from the plan?
4. **Testing**: Any specific test scenarios you want emphasized?
5. **Style**: Any coding style preferences not covered in the plan?

---

*End of Action Plan*
