# Column 2 Nesting - Quick Summary

## Current State

**Column 2 supports 3 nesting levels (0, 1, 2)**

- **Level 0**: Root tasks (can have children)
- **Level 1**: First nesting (can have children)
- **Level 2**: Leaf level (CANNOT have children)

## Key Architecture

### Validation Layers (Defense in Depth)
1. **Rules Engine** (`nesting_rules.py`): `MAX_DEPTH_COLUMN2 = 2`
2. **Model Validation** (`models.py`): `level: int = Field(..., le=2)`
3. **Service Layer** (`task_service.py`): `NestingLimitError` on violation
4. **UI Layer** (`app.py`): Prevents creation if rules violated

### Display Logic
- **Context-relative levels**: Children appear starting at level 0 in Column 2
- **Visual hierarchy**: Tree lines (├─, └─) + indentation + color coding
  - Level 0: Cyan (#66D9EF)
  - Level 1: Green (#A6E22E)
  - Level 2: Pink (#F92672)

## Core Files

| Purpose | File | Key Component |
|---------|------|---|
| **Rules** | `services/nesting_rules.py` | NestingRules class (219 lines) |
| **Model** | `models.py` | Task class with validators |
| **Service** | `services/task_service.py` | create_child_task, move_task |
| **UI App** | `ui/app.py` | _update_column2_for_selection |
| **Rendering** | `ui/components/task_item.py` | TaskItem widget |
| **Theme** | `ui/theme.py` | LEVEL_0/1/2_COLOR constants |
| **Tests** | `tests/test_nesting_rules.py` | 407 lines of tests |

## To Add Level 3 (4th level)

### Required Changes (6-8 files):

1. **nesting_rules.py**: `MAX_DEPTH_COLUMN2 = 3`
2. **models.py**: Change `le=2` to `le=3` and validator logic
3. **theme.py**: Add `LEVEL_3_COLOR` and update get_level_color()
4. **task_item.py**: Add `.level-3` CSS class and import color
5. **Tests**: Add 3+ test cases for Level 3
6. **Docs**: Update references to "0-2" → "0-3"

### Risk: LOW
- Changes are localized
- No breaking changes to existing data (levels 0-2 unaffected)
- All rules use the constants, so one change propagates automatically

## What Works Automatically After Changes

- Service validation (uses the constant)
- Move operations
- Database storage
- Parent-child relationships
- Child counts and progress
- All tier validations

---

For detailed implementation guide, see **NESTING_INVESTIGATION.md**
