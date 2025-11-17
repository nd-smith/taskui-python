# Configuration-Driven Nesting - Quick Summary

## Overview

To make TaskUI's nesting fully configuration-driven (supporting any arbitrary depth), you need to modify **8 files** with approximately **270 lines of changes**.

---

## Files Requiring Changes

| # | File | Changes | Lines | Complexity |
|---|------|---------|-------|------------|
| 1 | `config.py` | Add nesting config methods | +60 | Medium |
| 2 | `nesting_rules.py` | Class → Instance, inject config | ~30 | High ⚠️ |
| 3 | `models.py` | Dynamic Pydantic validators | ~15 | Medium |
| 4 | `theme.py` | Dynamic color mapping | ~20 | Low |
| 5 | `task_item.py` | Dynamic CSS generation | ~25 | Medium |
| 6 | `task_service.py` | Inject config, update checks | ~10 | Low |
| 7 | `ui/app.py` | Pass config to services | ~10 | Low |
| 8 | `tests/*.py` | Update for config awareness | ~100 | Medium |
| | **TOTAL** | | **~270** | **Medium** |

---

## Key Changes at a Glance

### 1. Configuration (config.py)
```python
# NEW METHODS
def get_nesting_config() -> Dict[str, int]:
    """Returns {'max_depth_column1': 1, 'max_depth_column2': 5}"""

def get_level_colors(max_level: int) -> Dict[int, str]:
    """Returns {0: '#66D9EF', 1: '#A6E22E', ...}"""
```

### 2. Nesting Rules (nesting_rules.py)
```python
# BEFORE: Class methods with constants
class NestingRules:
    MAX_DEPTH_COLUMN2 = 2
    @classmethod
    def can_create_child(cls, task, column): ...

# AFTER: Instance methods with config
class NestingRules:
    def __init__(self, config: Config):
        self.max_depth_column2 = config.get_nesting_config()['max_depth_column2']
    def can_create_child(self, task, column): ...
```

### 3. Models (models.py)
```python
# BEFORE: Hardcoded
level: int = Field(default=0, ge=0, le=2)

# AFTER: Dynamic
_max_level = Config().get_nesting_config()['max_depth_column2']
level: int = Field(default=0, ge=0, le=_max_level)
```

### 4. Theme (theme.py)
```python
# BEFORE: Hardcoded dictionary
def get_level_color(level: int):
    colors = {0: LEVEL_0_COLOR, 1: LEVEL_1_COLOR, 2: LEVEL_2_COLOR}
    return colors.get(level, FOREGROUND)

# AFTER: Dynamic from config
_LEVEL_COLORS = Config().get_level_colors(max_level)
def get_level_color(level: int):
    return _LEVEL_COLORS.get(level, FOREGROUND)
```

### 5. Task Item (task_item.py)
```python
# BEFORE: Hardcoded CSS
DEFAULT_CSS = """
.level-0 { border: thick #66D9EF; }
.level-1 { border: thick #A6E22E; }
.level-2 { border: thick #F92672; }
"""

# AFTER: Generated CSS
def _generate_level_css():
    colors = Config().get_level_colors(max_level)
    return "\n".join([f".level-{i} {{ border: thick {c}; }}"
                     for i, c in colors.items()])
DEFAULT_CSS = _generate_level_css()
```

### 6. Task Service (task_service.py)
```python
# BEFORE: Hardcoded check
if new_level > 2:
    raise NestingLimitError(...)

# AFTER: Config-driven
max_depth = self._nesting_rules.get_max_depth(column)
if new_level > max_depth:
    raise NestingLimitError(...)
```

---

## Configuration Format

### config.ini (~/.taskui/config.ini)
```ini
[nesting]
max_depth_column1 = 1
max_depth_column2 = 5

[colors]
level_0_color = #66D9EF
level_1_color = #A6E22E
level_2_color = #F92672
level_3_color = #AE81FF
level_4_color = #E6DB74
level_5_color = #FD971F
level_default_color = #F8F8F2
```

### Environment Variables
```bash
export TASKUI_MAX_DEPTH_COLUMN1=2
export TASKUI_MAX_DEPTH_COLUMN2=10
export TASKUI_LEVEL_3_COLOR="#AE81FF"
```

---

## Breaking Changes

### ⚠️ NestingRules API
**Before**: Class methods
```python
NestingRules.can_create_child(task, column)
```

**After**: Instance methods
```python
rules = NestingRules(config)
rules.can_create_child(task, column)
```

**Mitigation**: Provide backwards-compatible class method wrappers with deprecation warnings.

### ⚠️ TaskService Constructor
**Before**: `TaskService(db_manager)`

**After**: `TaskService(db_manager, config)`

**Mitigation**: Make config parameter optional with default: `config: Optional[Config] = None`

---

## Implementation Phases

### Phase 1: Foundation ✅
- Add config methods
- Create example config.ini
- Unit tests for config

### Phase 2: Core Changes ⚠️ (Breaking)
- Update NestingRules to instance-based
- Update models.py validators
- Update all callers

### Phase 3: UI Updates
- Dynamic theme colors
- Dynamic CSS generation
- Visual testing

### Phase 4: Testing
- Update existing tests
- Parameterized tests for various depths
- Integration tests

### Phase 5: Documentation
- README updates
- Migration guide
- Example configs

---

## Recommended Approach: Hybrid

Keep both class and instance methods for backwards compatibility:

```python
class NestingRules:
    _default_instance = None

    def __init__(self, config: Optional[Config] = None):
        self._config = config or Config()
        # ... load from config

    def can_create_child(self, task: Task, column: Column) -> bool:
        # Instance method implementation
        pass

    @classmethod
    def can_create_child_default(cls, task: Task, column: Column) -> bool:
        """Backwards compatible class method."""
        if cls._default_instance is None:
            cls._default_instance = cls()
        return cls._default_instance.can_create_child(task, column)
```

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Breaking existing code | Backwards compat wrappers + deprecation warnings |
| Config loading failures | Robust fallbacks, comprehensive error handling |
| Performance overhead | Cache config values, lazy initialization |
| Test failures | Comprehensive test suite updates |
| CSS generation bugs | Unit tests for CSS gen, visual regression tests |

---

## Effort Estimate

**Time**: 2-3 days for experienced developer

**Breakdown**:
- Day 1: Config infrastructure + NestingRules refactor
- Day 2: Models, UI, service updates + testing
- Day 3: Documentation + migration guide + final testing

---

## Benefits vs. Drawbacks

### ✅ Benefits
- Support any arbitrary nesting depth
- User-configurable without code changes
- Easier to test different scenarios
- Better separation of concerns
- Follows existing config patterns

### ⚠️ Drawbacks
- Breaking API changes (mitigated)
- Increased initialization complexity
- More test cases to cover
- Slight performance overhead (negligible)

---

## Conclusion

**Is it worth it?**
- **YES** if you want flexibility and user customization
- **NO** if current hardcoded limits are sufficient

**Best approach**: Hybrid implementation with backwards compatibility

**Risk level**: **Medium** (breaking changes but well-contained)

**Recommended**: Proceed if nesting flexibility is a key requirement
