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

| # | Package Name | Risk | Effort | Target Files | Lines Changed |
|---|--------------|------|--------|--------------|---------------|
| 1 | Extract Column Widget Helpers | 🟡 | 2h | column.py | ~80 |
| 2 | Simplify Archive Modal Logic | 🟡 | 1.5h | archive_modal.py | ~40 |
| 3 | Extract List Bar Tab Creation | 🟡 | 1h | list_bar.py | ~30 |
| 4 | Add Service Layer Type Hints | 🟢 | 1h | task_service.py, list_service.py | ~50 |
| 5 | Extract Task Service Query Patterns | 🟡 | 2.5h | task_service.py | ~100 |
| 6 | Consolidate List Service ORM Conversion | 🟡 | 1.5h | list_service.py | ~60 |
| 7 | Improve Task Service Organization | 🟡 | 2h | task_service.py | ~500 |
| 8 | Extract Task Modal Context Logic | 🟢 | 1h | task_modal.py | ~30 |
| 9 | Add Component Documentation | 🟢 | 2h | All UI components | ~100 |
| 10 | Database Manager Cleanup | 🟡 | 1h | database.py | ~20 |

**Total Estimated Time**: 15-17 hours
**Total Risk**: Mostly LOW-MEDIUM (no HIGH risk items in this plan)

---

## Phase 1: UI Component Improvements (7 hours)

These changes focus on eliminating duplication and improving readability in UI components.

---

### WP1: Extract Column Widget Helpers

**Risk**: 🟡 MEDIUM
**Effort**: 2 hours
**Dependencies**: None
**Target**: `taskui/ui/components/column.py`

#### Objective
Eliminate duplicate code blocks in `_render_tasks()` and extract complex retry logic.

#### Issues Identified

1. **Duplicate Widget Mounting Code** (lines 210-282):
   - Nearly identical code blocks for mounting widgets
   - One inside `mount_widgets()` callback, one inline
   - ~70 lines duplicated

2. **Complex Retry Logic** (lines 378-413):
   - Nested function with mutable list for retry counter
   - Could be extracted to separate method

3. **Parent Grouping Logic Duplicated** (lines 213-219, 251-257):
   - Same parent grouping code appears twice

#### Changes

**Extract parent grouping helper:**
```python
def _group_tasks_by_parent(self, tasks: List[Task]) -> dict:
    """Group tasks by parent ID for hierarchy visualization.

    Args:
        tasks: List of tasks to group

    Returns:
        Dictionary mapping parent_id to list of children
    """
    parent_groups = {}
    for task in tasks:
        parent_id = task.parent_id or "root"
        if parent_id not in parent_groups:
            parent_groups[parent_id] = []
        parent_groups[parent_id].append(task)
    return parent_groups
```

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

**Simplify _render_tasks():**
```python
def _render_tasks(self) -> None:
    """Render the task list with TaskItem widgets."""
    logger.debug(f"{self.column_id}: _render_tasks() called with {len(self._tasks)} tasks")

    content_container = self.query_one(f"#{self.column_id}-content", VerticalScroll)
    empty_message = self.query_one(f"#{self.column_id}-empty", Static)

    # Handle empty state
    if not self._tasks:
        self._clear_task_items(content_container)
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
- [ ] No duplicate code blocks in _render_tasks()
- [ ] Task rendering works correctly
- [ ] Selection state preserved across re-renders
- [ ] Lines of code reduced by ~60 lines

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

### WP9: Add Component Documentation

**Risk**: 🟢 LOW
**Effort**: 2 hours
**Dependencies**: WP1-3, WP8
**Target**: All UI component files

#### Objective
Add comprehensive module and method docstrings to UI components where missing.

#### Changes

1. **Ensure all methods have docstrings**
2. **Add Args/Returns sections where missing**
3. **Document non-obvious behavior**
4. **Add examples for complex methods**

#### Focus Areas

**column.py:**
- Document retry mechanism in ensure_selection
- Add docstrings to extracted helpers (from WP1)

**archive_modal.py:**
- Document search filtering logic
- Add docstrings to extracted helpers (from WP2)

**list_bar.py:**
- Document tab creation and switching
- Add docstrings to extracted helpers (from WP3)

**task_modal.py:**
- Document validation logic
- Add docstrings to extracted helpers (from WP8)

**task_item.py:**
- Add more detailed render() docstring
- Document color selection logic

**detail_panel.py:**
- Already well-documented, minor additions only

#### Files Modified
- All 6 UI component files

#### Testing
```bash
# Verify docstrings parse correctly
python3 -m pydoc taskui.ui.components.column
python3 -m pydoc taskui.ui.components.archive_modal
python3 -m pydoc taskui.ui.components.list_bar
python3 -m pydoc taskui.ui.components.task_modal

# Run tests
python3 -m pytest tests/ -v
```

#### Success Criteria
- [ ] All tests pass
- [ ] All public methods have docstrings
- [ ] All docstrings include Args/Returns
- [ ] pydoc output is readable

#### Rollback
```bash
git revert HEAD
```

---

## Phase 2: Service Layer Improvements (7.5 hours)

These changes focus on reducing duplication and improving organization in service classes.

---

### WP4: Add Service Layer Type Hints

**Risk**: 🟢 LOW
**Effort**: 1 hour
**Dependencies**: None
**Target**: `taskui/services/task_service.py`, `taskui/services/list_service.py`

#### Objective
Add missing return type hints to all service methods for better IDE support and type checking.

#### Issues Identified

1. **Missing return types on some methods**
2. **Some parameters lack type hints**

#### Changes

Add complete type hints to all methods in:
- `TaskService`
- `ListService`

Ensure all methods follow this pattern:
```python
async def method_name(self, param: Type) -> ReturnType:
    """Docstring."""
    ...
```

#### Files Modified
- `taskui/services/task_service.py`
- `taskui/services/list_service.py`

#### Testing
```bash
# Run type checker
python3 -m mypy taskui/services/ --ignore-missing-imports

# Run service tests
python3 -m pytest tests/test_task_service.py tests/test_list_service.py -v
```

#### Success Criteria
- [ ] All tests pass
- [ ] All methods have return type hints
- [ ] All parameters have type hints
- [ ] Mypy runs without errors (if used)

#### Rollback
```bash
git revert HEAD
```

---

### WP5: Extract Task Service Query Patterns

**Risk**: 🟡 MEDIUM
**Effort**: 2.5 hours
**Dependencies**: WP4
**Target**: `taskui/services/task_service.py`

#### Objective
Eliminate repetitive database query patterns by extracting common operations.

#### Issues Identified

1. **Repetitive task fetching with child counts** (appears 8+ times):
```python
# Pattern repeated throughout:
result = await self.session.execute(
    select(TaskORM).where(TaskORM.id == str(task_id))
)
task_orm = result.scalar_one_or_none()
task = self._orm_to_pydantic(task_orm)
child_count = await self._count_children(task.id)
completed_child_count = await self._count_completed_children(task.id)
task.update_child_counts(child_count, completed_child_count)
```

2. **Repetitive list filtering queries**:
   - Active (non-archived) tasks
   - Top-level tasks
   - Tasks by parent

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

**Extract common query builders:**
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

**Refactor methods to use helpers:**

Update methods like `get_tasks_for_list()`, `get_task_children()`, etc. to use these helpers.

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
# Verify child counts display correctly
```

#### Success Criteria
- [ ] All tests pass
- [ ] Query patterns consolidated
- [ ] No behavioral changes
- [ ] Code is more DRY
- [ ] Lines of code reduced by ~80 lines

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

### WP7: Improve Task Service Organization

**Risk**: 🟡 MEDIUM
**Effort**: 2 hours
**Dependencies**: WP5
**Target**: `taskui/services/task_service.py`

#### Objective
Reorganize task service methods into logical sections for better navigation.

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

# Verify no logic changes
python3 -m taskui
```

#### Success Criteria
- [ ] All tests pass
- [ ] Methods organized in logical sections
- [ ] Section markers clearly visible
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
- [ ] All tests pass
- [ ] Deprecation warnings in place
- [ ] Documentation updated
- [ ] No new usage of deprecated methods

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

**Assuming dedicated work, ~3-4 days total:**

**Day 1 (7 hours)**: Phase 1 - UI Component Improvements
- WP1: Extract Column Widget Helpers (2h)
- WP2: Simplify Archive Modal Logic (1.5h)
- WP3: Extract List Bar Tab Creation (1h)
- WP8: Extract Task Modal Context Logic (1h)
- WP9: Add Component Documentation (2h)
- Checkpoint: Commit and tag `phase-1-ui-complete`

**Day 2 (4 hours)**: Phase 2 Part 1 - Service Layer Foundation
- WP4: Add Service Layer Type Hints (1h)
- WP5: Extract Task Service Query Patterns (2.5h)
- Checkpoint: Commit and tag `phase-2a-services-foundation`

**Day 3 (3.5 hours)**: Phase 2 Part 2 - Service Layer Organization
- WP6: Consolidate List Service ORM Conversion (1.5h)
- WP7: Improve Task Service Organization (2h)
- Checkpoint: Commit and tag `phase-2b-services-complete`

**Day 4 (1.5 hours)**: Phase 3 - Final Cleanup & Validation
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
