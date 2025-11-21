# Column Refactor Plan

## Goal
Simplify the codebase by removing column-specific nesting validation. Replace with global max depth and UI-layer filtering.

## Current State vs Target State

### Current (Complex)
```python
# Data layer knows about UI columns
await task_service.create_child_task(
    parent_id=parent.id,
    title="Build UI",
    column=Column.COLUMN2,  # Database validates column-specific rules
)

# Validation:
# - Column 1: max depth 1 (levels 0-1)
# - Column 2: max depth 2 (levels 0-2)
# - Context-relative level adjustment for display
```

### Target (Simple)
```python
# Data layer only validates global depth
await task_service.create_child_task(
    parent_id=parent.id,
    title="Build UI",
    # No column parameter!
)

# Validation:
# - Global: max depth 4 (levels 0-4)
# - UI filters tasks by level for display
# - No context-relative adjustment needed
```

## What Changes

### Remove (659 lines):
1. **`services/nesting_rules.py`** (540 lines)
   - Remove `Column` enum
   - Remove column-specific validation
   - Simplify to single `validate_depth(task)` function

2. **`config/nesting_config.py`** (119 lines)
   - Delete entirely (no config needed)
   - Global max depth is hardcoded constant

### Simplify:
3. **`services/task_service.py`**
   - Remove `column` parameter from `create_child_task()`
   - Remove column-specific validation logic
   - Keep level tracking (needed for styling)
   - ~200 lines simplified

4. **`ui/app.py`**
   - Remove `Column` imports
   - Remove context-relative adjustment (~25 lines)
   - Add simple level filtering for Column 1 display
   - ~50 lines changed

5. **`ui/components/task_modal.py`**
   - Remove `column` parameter
   - Simplify validation (just check global depth)
   - ~100 lines simplified

6. **`models.py`**
   - Keep `level` field (needed for styling)
   - Simplify validation (single max_level)
   - ~30 lines simplified

## What Stays the Same

### UI Behavior (Unchanged):
- ✅ Column 1 shows high-level tasks (filter: level <= 1)
- ✅ Column 2 shows descendants of selected task
- ✅ Selecting task in Column 1 filters Column 2
- ✅ Styling based on task level
- ✅ Visual hierarchy indicators

### Data Layer (Unchanged):
- ✅ Tasks have `level` field
- ✅ Tasks have `parent_id` field
- ✅ Parent-child relationships
- ✅ Position ordering
- ✅ Database schema (no migration needed)

## Implementation Steps

### Phase 1: Simplify Nesting Rules (Low Risk)

**Step 1.1: Create simplified nesting validation**
```python
# taskui/services/nesting_validation.py (NEW, ~50 lines)
MAX_NESTING_DEPTH = 4

def validate_task_depth(task_level: int) -> None:
    """Validate task doesn't exceed max depth."""
    if task_level > MAX_NESTING_DEPTH:
        raise NestingLimitError(
            f"Task depth cannot exceed {MAX_NESTING_DEPTH}. Got {task_level}."
        )

def can_create_child(parent_level: int) -> bool:
    """Check if child can be created under parent."""
    return parent_level < MAX_NESTING_DEPTH
```

**Step 1.2: Update task_service.py**
- Change `create_child_task()` signature (remove `column` param)
- Replace `nesting_rules.can_create_child(task, column)` with `can_create_child(task.level)`
- Update all callers

**Step 1.3: Update UI layer**
- Remove `Column` imports from `app.py`
- Update task creation to not pass column
- Add level filtering for Column 1 display:
  ```python
  # Show only shallow tasks in Column 1
  shallow_tasks = [t for t in tasks if t.level <= 1]
  ```

**Step 1.4: Update task_modal.py**
- Remove `column` parameter
- Simplify validation to use global depth
- Remove column-specific error messages

**Tests affected:**
- `tests/test_nesting_rules.py` - rewrite for simplified validation
- `tests/test_task_service.py` - remove column parameters
- `tests/test_integration_mvp.py` - remove column parameters
- `tests/test_task_modal.py` - remove column parameters

### Phase 2: Remove Old Code (Safe After Phase 1)

**Step 2.1: Delete files**
- Delete `services/nesting_rules.py` (540 lines)
- Delete `config/nesting_config.py` (119 lines)

**Step 2.2: Remove config loading**
- Remove nesting config from `app.py` initialization
- Remove `nesting.toml` from config directory

**Step 2.3: Clean up imports**
- Remove `from nesting_rules import Column` everywhere
- Remove `NestingRules` instances

### Phase 3: UI Enhancement (Optional)

**Step 3.1: Improve Column 1 filtering**
Currently shows level 0-1. After refactor, this becomes:
```python
# In app.py, when loading Column 1 tasks
COLUMN1_MAX_DISPLAY_LEVEL = 1  # Only show shallow tasks

async def _load_column1_tasks(self, list_id: UUID):
    all_tasks = await task_service.get_tasks_for_list(list_id)
    # Filter for display
    shallow_tasks = [t for t in all_tasks if t.level <= COLUMN1_MAX_DISPLAY_LEVEL]
    column1.update_tasks(shallow_tasks)
```

**Step 3.2: Remove context-relative adjustment**
```python
# DELETE THIS from app.py
def _make_levels_context_relative(self, tasks, parent_level):
    # Not needed - just display actual levels
    pass
```

## Testing Strategy

### Unit Tests
1. **test_nesting_validation.py** (new file)
   - Test global depth validation
   - Test can_create_child() logic
   - Test error messages

2. **Update existing tests**
   - Remove `column` parameters from all test calls
   - Update assertions for new error messages
   - Verify level-based filtering works

### Integration Tests
1. **test_task_creation_depth.py**
   - Create tasks at various depths (0-4)
   - Verify depth 5 fails with error
   - Test parent-child relationships maintained

2. **test_column_display_filtering.py**
   - Verify Column 1 shows only level 0-1
   - Verify Column 2 shows all descendants
   - Test selection filtering works

### Manual Testing Checklist
- [ ] Create top-level task in Column 1
- [ ] Create child (level 1) - should work
- [ ] Select child, create grandchild (level 2) in Column 2 - should work
- [ ] Create great-grandchild (level 3) - should work
- [ ] Create great-great-grandchild (level 4) - should work
- [ ] Try creating level 5 - should fail with clear error
- [ ] Verify Column 1 only shows level 0-1 tasks
- [ ] Verify Column 2 shows descendants of selected task
- [ ] Test printing (should still work)

## Rollback Plan

If issues arise:
1. Revert commits in reverse order
2. Phase 2 rollback: Restore deleted files
3. Phase 1 rollback: Restore column parameters
4. Database schema unchanged - no migration needed

## Risk Assessment

### Low Risk:
- ✅ No database migration needed
- ✅ Level field stays in database
- ✅ Parent-child relationships unchanged
- ✅ Can rollback easily

### Medium Risk:
- ⚠️ Many test files need updates
- ⚠️ User's existing nesting.toml becomes unused

### Mitigation:
- Update all tests before removing old code
- Add deprecation notice in config
- Keep backward compatibility in Phase 1

## Success Criteria

1. **Code reduction**: Remove 659+ lines
2. **Tests passing**: All tests green
3. **Functionality preserved**: UI behavior identical
4. **Performance**: Same or better (less validation)
5. **Maintainability**: Simpler mental model

## Timeline Estimate

- Phase 1: 2-3 hours (implementation + tests)
- Phase 2: 30 minutes (cleanup)
- Phase 3: 1 hour (UI polish)
- Testing: 1 hour (manual verification)

**Total: 4-5 hours**

## Files Modified Summary

### Deleted (778 lines):
- `services/nesting_rules.py` (540)
- `config/nesting_config.py` (119)
- Context-relative code in `app.py` (25)
- Column validation in `task_service.py` (94)

### Modified:
- `services/task_service.py` (~200 lines changed)
- `ui/app.py` (~50 lines changed)
- `ui/components/task_modal.py` (~100 lines changed)
- `models.py` (~30 lines changed)

### Created:
- `services/nesting_validation.py` (~50 lines)
- Test files updated (~15 files)

### Net Result:
**Remove ~1,400 lines, add ~50 lines = 1,350 line reduction**

(Higher than initial estimate due to test cleanup!)
