# Column Refactor - Test Changes

## Test Files Affected: 14 files

### Critical Changes (Must Update)

#### 1. `tests/test_nesting_rules.py` ⚠️ REWRITE NEEDED
**Current:** Tests Column.COLUMN1 vs Column.COLUMN2 validation
**After:** Test global depth validation only

**Changes:**
```python
# BEFORE
from taskui.services.nesting_rules import NestingRules, Column

def test_column1_allows_one_child():
    task_l0 = Task(level=0, ...)
    assert NestingRules.can_create_child(task_l0, Column.COLUMN1) == True

    task_l1 = Task(level=1, ...)
    assert NestingRules.can_create_child(task_l1, Column.COLUMN1) == False  # Max depth 1

def test_column2_allows_two_children():
    task_l1 = Task(level=1, ...)
    assert NestingRules.can_create_child(task_l1, Column.COLUMN2) == True  # Max depth 2

# AFTER
from taskui.services.nesting_validation import can_create_child, MAX_NESTING_DEPTH

def test_can_create_child_within_limit():
    assert can_create_child(level=0) == True
    assert can_create_child(level=1) == True
    assert can_create_child(level=2) == True
    assert can_create_child(level=3) == True
    assert can_create_child(level=4) == False  # At max depth

def test_validate_task_depth():
    validate_task_depth(0)  # OK
    validate_task_depth(4)  # OK

    with pytest.raises(NestingLimitError):
        validate_task_depth(5)  # Exceeds max
```

**Tests to remove:**
- All column-specific tests
- Context-relative level tests
- Column enum tests

**Tests to add:**
- Global depth validation
- Simple can_create_child() tests

**Estimated effort:** 1 hour (complete rewrite)

---

#### 2. `tests/test_task_service.py` ⚠️ HIGH IMPACT
**Current:** All `create_child_task()` calls pass `column` parameter
**After:** Remove `column` parameter from all calls

**Changes:**
```python
# BEFORE
await task_service.create_child_task(
    parent_id=parent.id,
    title="Child Task",
    column=Column.COLUMN1,
    notes="..."
)

# AFTER
await task_service.create_child_task(
    parent_id=parent.id,
    title="Child Task",
    notes="..."
)
```

**Find/replace pattern:**
- Find: `column=Column\.(COLUMN1|COLUMN2),?\s*`
- Replace: (empty)

**Assertions to update:**
```python
# BEFORE
with pytest.raises(NestingLimitError, match="column1"):
    await task_service.create_child_task(..., column=Column.COLUMN1)

# AFTER
with pytest.raises(NestingLimitError, match="max depth 4"):
    # Create 5 levels deep
    await task_service.create_child_task(...)
```

**Estimated effort:** 45 minutes

---

#### 3. `tests/test_task_modal.py` ⚠️ MODERATE IMPACT
**Current:** TaskCreationModal tests with column parameter
**After:** Remove column parameter, update validation tests

**Changes:**
```python
# BEFORE
modal = TaskCreationModal(
    mode="create_child",
    parent_task=parent,
    column=Column.COLUMN2
)

# AFTER
modal = TaskCreationModal(
    mode="create_child",
    parent_task=parent
)
```

**Validation tests to update:**
```python
# BEFORE
def test_validation_error_at_max_depth_column1():
    parent = Task(level=1, ...)  # Max for Column 1
    modal = TaskCreationModal(
        mode="create_child",
        parent_task=parent,
        column=Column.COLUMN1
    )
    assert modal.validation_error is not None

# AFTER
def test_validation_error_at_max_depth():
    parent = Task(level=4, ...)  # At global max
    modal = TaskCreationModal(
        mode="create_child",
        parent_task=parent
    )
    assert modal.validation_error is not None
```

**Estimated effort:** 30 minutes

---

#### 4. `tests/test_integration_mvp.py` ⚠️ MODERATE IMPACT
**Current:** Uses Column enum for integration tests
**After:** Remove column references

**Changes:**
```python
# BEFORE
from taskui.services.nesting_rules import Column as NestingColumn

# Create child in column 2
child = await task_service.create_child_task(
    parent_id=parent.id,
    title="Child",
    column=NestingColumn.COLUMN2
)

# AFTER
# (remove import)

# Create child (no column needed)
child = await task_service.create_child_task(
    parent_id=parent.id,
    title="Child"
)
```

**Estimated effort:** 20 minutes

---

### Minor Changes (Low Impact)

#### 5. `tests/test_config.py` ⚠️ UPDATE OR DELETE
**Current:** Tests `nesting_config.py` loading
**After:** Delete nesting config tests (config file removed)

**Changes:**
- Delete all `ColumnNestingConfig` tests
- Delete all `NestingConfig` tests
- Keep other config tests (printer, etc.)

**Estimated effort:** 10 minutes

---

#### 6. `tests/test_models.py` ⚠️ MINOR CHANGES
**Current:** Tests Task model level validation
**After:** Update max level validation

**Changes:**
```python
# BEFORE
def test_task_level_validation():
    # Level must be <= 2 (or whatever Column.COLUMN2 max is)
    Task(level=2, ...)  # OK
    with pytest.raises(ValidationError):
        Task(level=3, ...)  # Fails

# AFTER
def test_task_level_validation():
    # Level must be <= 4 (global max)
    Task(level=4, ...)  # OK
    with pytest.raises(ValidationError):
        Task(level=5, ...)  # Fails
```

**Estimated effort:** 15 minutes

---

#### 7. `tests/test_app.py` ⚠️ MINOR CHANGES
**Current:** May reference Column enum in app tests
**After:** Remove column references

**Changes:**
- Remove `Column` imports if present
- Update any column-specific app behavior tests

**Estimated effort:** 20 minutes

---

### No Changes Needed (UI/Display Tests)

#### 8. `tests/test_column.py` ✅ NO CHANGES
**Reason:** Tests TaskColumn widget (UI component), not Column enum

#### 9. `tests/test_column2_updates.py` ✅ NO CHANGES
**Reason:** Tests Column 2 display updates (UI behavior)

#### 10. `tests/test_keyboard_navigation.py` ✅ NO CHANGES
**Reason:** Tests keyboard nav between columns (UI behavior)

#### 11. `tests/test_persistence.py` ✅ MINOR VERIFICATION
**Reason:** Tests database persistence of tasks
**Change:** Verify level field still persists correctly

#### 12. `tests/test_refresh_helper.py` ✅ NO CHANGES
**Reason:** Tests UI refresh logic

#### 13. `tests/test_task_editing.py` ✅ NO CHANGES
**Reason:** Tests task editing modal (no column parameter)

#### 14. `tests/test_ui_components.py` ✅ NO CHANGES
**Reason:** Tests UI components rendering

---

## Test Changes Summary

### Must Update (7 files):
1. `test_nesting_rules.py` - **REWRITE** (1 hour)
2. `test_task_service.py` - Remove column params (45 min)
3. `test_task_modal.py` - Update validation (30 min)
4. `test_integration_mvp.py` - Remove column refs (20 min)
5. `test_config.py` - Delete nesting tests (10 min)
6. `test_models.py` - Update max level (15 min)
7. `test_app.py` - Remove column refs (20 min)

### Verify Only (2 files):
8. `test_persistence.py` - Verify level persists (5 min)
9. `test_column.py` - Quick smoke test (5 min)

### No Changes (5 files):
10. `test_column2_updates.py`
11. `test_keyboard_navigation.py`
12. `test_refresh_helper.py`
13. `test_task_editing.py`
14. `test_ui_components.py`

---

## Testing Strategy

### Phase 1: Update Unit Tests
**Order of execution:**
1. `test_nesting_rules.py` - Rewrite first (new foundation)
2. `test_models.py` - Update validation
3. `test_task_service.py` - Remove column params
4. `test_task_modal.py` - Update modal tests
5. `test_config.py` - Delete nesting config tests

**After each:** Run tests to verify changes work

### Phase 2: Update Integration Tests
1. `test_integration_mvp.py` - Remove column references
2. `test_app.py` - Update app-level tests
3. Run full integration suite

### Phase 3: Regression Testing
1. Run all tests: `pytest`
2. Check coverage: `pytest --cov=taskui`
3. Manual smoke tests (see COLUMN_REFACTOR_PLAN.md)

---

## Test Coverage Target

**Before refactor:** 75% coverage
**After refactor:** 75%+ coverage (maintain or improve)

**Key areas to maintain coverage:**
- Task creation at all depths (0-4)
- Depth validation (reject level 5)
- Parent-child relationships
- Level-based display filtering
- UI column behavior

---

## Automated Test Updates

### Global Find/Replace (Safe):
```bash
# Remove column parameters from function calls
find tests -name "*.py" -exec sed -i 's/column=Column\.\(COLUMN1\|COLUMN2\),\? //g' {} \;

# Remove Column imports
find tests -name "*.py" -exec sed -i '/from.*nesting_rules import.*Column/d' {} \;
```

**⚠️ WARNING:** Review changes before committing!

### Manual Review Required:
- Assertions about error messages (changed wording)
- Test setup (max depth values)
- Validation test cases (different limits)

---

## Time Estimate

| Phase | Time |
|-------|------|
| Unit tests update | 2.5 hours |
| Integration tests | 40 minutes |
| Regression testing | 30 minutes |
| **Total** | **3.5-4 hours** |

---

## Success Criteria

✅ All 14 test files reviewed
✅ 7 test files updated successfully
✅ `pytest` passes all tests
✅ Coverage remains >= 75%
✅ No column-specific tests remain
✅ Global depth validation tested
