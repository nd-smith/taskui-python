# Column Refactor - Configuration Changes

## Configuration Files Affected

### Files to DELETE:
1. `taskui/config/nesting_config.py` (119 lines)
2. `nesting.toml` (if exists in project root)
3. Any `config/nesting.toml` (if exists)

### Files to MODIFY:
1. `README.md` - Remove nesting configuration documentation
2. `taskui/ui/app.py` - Remove nesting config loading

---

## Current Configuration System

### 1. `taskui/config/nesting_config.py`
**Purpose:** Load and validate nesting configuration from TOML file
**Size:** 119 lines
**Used by:**
- `taskui/services/nesting_rules.py`
- `taskui/ui/app.py` (loads config on startup)

**Status:** ❌ **DELETE** - No longer needed

---

### 2. `nesting.toml` (Example Config)
**Purpose:** User-facing nesting configuration file
**Location:** Project root or `~/.taskui/nesting.toml`

**Current structure:**
```toml
[nesting]
enabled = true
num_columns = 2

[nesting.column1]
max_depth = 1
display_name = "Tasks"
level_colors = ["#66D9EF", "#A6E22E"]

[nesting.column2]
max_depth = 2
display_name = "Subtasks"
level_colors = ["#66D9EF", "#A6E22E", "#F92672"]
context_relative = true

[nesting.validation]
strict_validation = true
warn_at_max_depth = true

[nesting.ui]
show_level_indicators = true
indent_per_level = 2
tree_line_enabled = true
tree_line_last_child = "└─"
tree_line_middle_child = "├─"
```

**Status:** ❌ **DELETE** - Replaced with hardcoded constant

---

## New Configuration (Simplified)

### Single Constant in Code
```python
# taskui/services/nesting_validation.py
MAX_NESTING_DEPTH = 4  # Global maximum task depth

# Display constants (UI layer)
COLUMN1_MAX_DISPLAY_LEVEL = 1  # Only show shallow tasks in Column 1
```

**Benefits:**
- No config file to manage
- No TOML parsing
- No validation needed
- Simpler mental model
- Users can't misconfigure nesting

**Trade-off:**
- Users can't customize nesting depth
- Must change code to adjust limits

**Justification:**
- User said "4 levels is sufficient"
- Column 1 showing "shallow" is UI preference, not customizable feature
- Simpler is better for this use case

---

## Migration Path

### User Impact:
**Before refactor:**
- Users with `~/.taskui/nesting.toml` → Config loaded and used
- Users without config → Defaults used (max_depth 1/2)

**After refactor:**
- All users → Global max depth 4, Column 1 shows level 0-1
- Existing `nesting.toml` files → Ignored (no error, just unused)

### Migration Notice:
Add to README.md:
```markdown
## Configuration Changes (v0.2.0)

**Nesting configuration has been simplified:**
- `nesting.toml` is no longer used (safe to delete)
- Global max depth is now 4 levels (hardcoded)
- Column 1 shows tasks at level 0-1
- Column 2 shows all descendants

This change reduces complexity while supporting all practical use cases.
```

---

## README.md Changes

### Section to REMOVE:
**Lines to delete:** ~300 lines of nesting configuration docs

**Sections:**
1. "Nesting Configuration" (full section)
2. "Setting Up Configuration"
3. "Example Configuration"
4. "Configuration Options Explained"
5. "Nesting Depths"
6. "Column Behavior"
7. "Colors"
8. "Backward Compatibility"
9. "Use Cases"
10. "Complete Example"

### Section to ADD (Brief):
```markdown
## Task Hierarchy

TaskUI supports up to 4 levels of task nesting:

**Column 1 (Tasks):**
- Shows high-level tasks (levels 0-1)
- Use for main projects and phases

**Column 2 (Subtasks):**
- Shows all descendants of selected task
- Use for detailed breakdown

**Example:**
```
Build App (Level 0)
├─ Build UI (Level 1)
│  ├─ Design components (Level 2)
│  │  └─ Button styles (Level 3)
│  └─ Implement forms (Level 2)
└─ Build API (Level 1)
   └─ Auth endpoints (Level 2)
       └─ JWT tokens (Level 3)
```

Select "Build UI" in Column 1 → Column 2 shows all its descendants
```

**Estimated reduction:** ~270 lines removed from README.md

---

## Code Changes

### 1. Remove from `taskui/ui/app.py`

**DELETE these lines:**
```python
from taskui.config.nesting_config import NestingConfig

# In __init__:
try:
    nesting_config = NestingConfig.from_toml_file()
    self._nesting_rules = NestingRules(nesting_config)
    logger.info(
        f"Nesting config loaded: column1.max_depth={nesting_config.column1.max_depth}, "
        f"column2.max_depth={nesting_config.column2.max_depth}"
    )
except Exception as e:
    logger.warning(f"Failed to load nesting config, using defaults: {e}")
    self._nesting_rules = NestingRules()  # Uses default config
```

**REPLACE with:**
```python
# No nesting_rules needed - validation is simple
# Global max depth enforced at service layer
```

---

### 2. Remove from `taskui/config/__init__.py`

**DELETE import:**
```python
from taskui.config.nesting_config import ColumnNestingConfig, NestingConfig
```

**Note:** Check if this makes `__init__.py` empty. If so, can leave it (Python package marker) or add:
```python
"""Configuration package for TaskUI."""
```

---

## Testing Configuration Changes

### 1. Config Loading Tests
**File:** `tests/test_config.py`

**DELETE:**
- All `ColumnNestingConfig` tests
- All `NestingConfig.from_toml_file()` tests
- TOML validation tests

**Estimated:** ~100 lines of test code deleted

### 2. App Initialization Tests
**File:** `tests/test_app.py`

**UPDATE:**
- Remove tests that verify nesting config loading
- Keep other app initialization tests

---

## Backward Compatibility

### For Users:
✅ **No breaking changes for users**
- App continues to work
- Existing nesting.toml silently ignored
- No error messages about missing config

### For Developers:
⚠️ **Breaking API change**
- `NestingConfig` class removed
- `nesting_config.py` module deleted
- Code importing these will break

### Migration for Developers:
```python
# BEFORE
from taskui.config.nesting_config import NestingConfig
config = NestingConfig.from_toml_file()
max_depth = config.column1.max_depth

# AFTER
from taskui.services.nesting_validation import MAX_NESTING_DEPTH
max_depth = MAX_NESTING_DEPTH  # Simple constant
```

---

## Files Modified Summary

### Deleted (119+ lines):
- ❌ `taskui/config/nesting_config.py` (119 lines)
- ❌ `nesting.toml` (if exists)
- ❌ `config/nesting.toml` (if exists)

### Modified:
- ✏️ `README.md` (~270 lines removed, ~30 added)
- ✏️ `taskui/ui/app.py` (~15 lines removed)
- ✏️ `taskui/config/__init__.py` (~1 line removed)
- ✏️ `tests/test_config.py` (~100 lines removed)

### Net Change:
**~474 lines removed, ~30 lines added = 444 line reduction**

---

## Rollback Plan

If issues arise:
1. Restore `nesting_config.py` from git
2. Restore config loading in `app.py`
3. Restore README.md documentation
4. Users' `nesting.toml` files still work

**Risk:** LOW - Config is loaded but not critical to app function

---

## Timeline

| Task | Time |
|------|------|
| Delete config files | 5 min |
| Update README.md | 20 min |
| Remove config loading from app | 10 min |
| Update tests | 15 min |
| Verification | 10 min |
| **Total** | **1 hour** |

---

## Success Criteria

✅ `nesting_config.py` deleted
✅ Config loading removed from app
✅ README.md simplified
✅ Tests updated
✅ App starts without config file
✅ No errors about missing config
✅ Users can still manage tasks normally
