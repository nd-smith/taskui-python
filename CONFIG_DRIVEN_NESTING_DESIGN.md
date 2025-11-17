# Configuration-Driven Nesting Design

## Executive Summary

This document outlines the architectural changes needed to make TaskUI's nesting system fully configuration-driven, allowing any arbitrary depth value without code changes.

**Current State**: Nesting levels are hardcoded across 8+ files with maximum depth of 2 (3 levels: 0, 1, 2).

**Target State**: All nesting constraints loaded from configuration with dynamic validation, styling, and UI generation.

---

## Architecture Overview

### Configuration Layer

The existing `Config` class (`taskui/config.py`) will be extended to support nesting configuration:

```python
# New method in Config class
def get_nesting_config(self) -> Dict[str, int]:
    """
    Get nesting configuration with environment overrides.

    Environment variables take precedence:
    - TASKUI_MAX_DEPTH_COLUMN1
    - TASKUI_MAX_DEPTH_COLUMN2

    Returns:
        Dictionary with max_depth_column1 and max_depth_column2
    """
    config = {
        'max_depth_column1': int(os.getenv('TASKUI_MAX_DEPTH_COLUMN1') or
                                self._config.get('nesting', 'max_depth_column1',
                                               fallback='1')),
        'max_depth_column2': int(os.getenv('TASKUI_MAX_DEPTH_COLUMN2') or
                                self._config.get('nesting', 'max_depth_column2',
                                               fallback='2')),
    }
    return config
```

### Configuration File Format

`~/.taskui/config.ini`:
```ini
[nesting]
max_depth_column1 = 1
max_depth_column2 = 5

[colors]
# Dynamic level colors (can define as many as needed)
level_0_color = #66D9EF
level_1_color = #A6E22E
level_2_color = #F92672
level_3_color = #AE81FF
level_4_color = #E6DB74
level_5_color = #FD971F
# Fallback color for undefined levels
level_default_color = #F8F8F2
```

### Environment Variable Overrides

```bash
export TASKUI_MAX_DEPTH_COLUMN1=2
export TASKUI_MAX_DEPTH_COLUMN2=10
export TASKUI_LEVEL_0_COLOR="#FF0000"
export TASKUI_LEVEL_DEFAULT_COLOR="#FFFFFF"
```

---

## Required Changes by File

### 1. **taskui/config.py** (NEW FUNCTIONALITY)

**Changes**: Add nesting and color configuration methods

```python
def get_nesting_config(self) -> Dict[str, int]:
    """Get nesting depth configuration."""
    return {
        'max_depth_column1': int(os.getenv('TASKUI_MAX_DEPTH_COLUMN1') or
                                self._config.get('nesting', 'max_depth_column1',
                                               fallback='1')),
        'max_depth_column2': int(os.getenv('TASKUI_MAX_DEPTH_COLUMN2') or
                                self._config.get('nesting', 'max_depth_column2',
                                               fallback='2')),
    }

def get_level_colors(self, max_level: int) -> Dict[int, str]:
    """
    Get color mapping for all levels up to max_level.

    Args:
        max_level: Maximum level to generate colors for

    Returns:
        Dictionary mapping level (int) to hex color (str)
    """
    colors = {}
    default_colors = [
        "#66D9EF",  # Cyan
        "#A6E22E",  # Green
        "#F92672",  # Pink
        "#AE81FF",  # Purple
        "#E6DB74",  # Yellow
        "#FD971F",  # Orange
    ]

    default_color = os.getenv('TASKUI_LEVEL_DEFAULT_COLOR') or \
                   self._config.get('colors', 'level_default_color',
                                   fallback='#F8F8F2')

    for level in range(max_level + 1):
        env_var = f'TASKUI_LEVEL_{level}_COLOR'
        config_key = f'level_{level}_color'

        # Check env var, then config, then defaults array, then fallback
        color = os.getenv(env_var) or \
               self._config.get('colors', config_key, fallback=None) or \
               (default_colors[level] if level < len(default_colors) else default_color)

        colors[level] = color

    return colors
```

**Lines Changed**: ~60 new lines

---

### 2. **taskui/services/nesting_rules.py** (CORE CHANGES)

**Changes**: Replace constants with config lookups, make class instance-based

**Before**:
```python
class NestingRules:
    MAX_DEPTH_COLUMN1 = 1
    MAX_DEPTH_COLUMN2 = 2

    @classmethod
    def can_create_child(cls, task: Task, column: Column) -> bool:
        if column == Column.COLUMN1:
            return task.level < cls.MAX_DEPTH_COLUMN1
        # ...
```

**After**:
```python
class NestingRules:
    """Enforces nesting rules based on runtime configuration."""

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize nesting rules with configuration.

        Args:
            config: Config instance. If None, creates default config.
        """
        self._config = config or Config()
        nesting_config = self._config.get_nesting_config()
        self.max_depth_column1 = nesting_config['max_depth_column1']
        self.max_depth_column2 = nesting_config['max_depth_column2']

        logger.info(f"NestingRules initialized: Column1 max={self.max_depth_column1}, "
                   f"Column2 max={self.max_depth_column2}")

    def can_create_child(self, task: Task, column: Column) -> bool:
        """Determine if a child can be created."""
        if column == Column.COLUMN1:
            return task.level < self.max_depth_column1
        elif column == Column.COLUMN2:
            return task.level < self.max_depth_column2
        return False

    def get_max_depth(self, column: Column) -> int:
        """Get maximum depth for column."""
        if column == Column.COLUMN1:
            return self.max_depth_column1
        elif column == Column.COLUMN2:
            return self.max_depth_column2
        return 0

    # ... update all other methods to use self.max_depth_column1/2
```

**Impact**: Change from class methods to instance methods. All callers must be updated.

**Lines Changed**: ~30 lines modified, add `__init__` method

---

### 3. **taskui/models.py** (DYNAMIC VALIDATION)

**Changes**: Replace hardcoded `le=2` with dynamic validator

**Before**:
```python
level: int = Field(default=0, ge=0, le=2, description="Nesting level (0-2)")

@field_validator("level")
@classmethod
def validate_level(cls, v: int) -> int:
    if v < 0 or v > 2:
        raise ValueError("Task level must be between 0 and 2")
    return v
```

**After**:
```python
from taskui.config import Config

# Module-level config for validators
_config = Config()
_nesting_config = _config.get_nesting_config()
_max_level = max(_nesting_config['max_depth_column1'],
                _nesting_config['max_depth_column2'])

level: int = Field(default=0, ge=0, le=_max_level,
                  description=f"Nesting level (0-{_max_level})")

@field_validator("level")
@classmethod
def validate_level(cls, v: int) -> int:
    if v < 0 or v > _max_level:
        raise ValueError(f"Task level must be between 0 and {_max_level}")
    return v
```

**Alternatively** (cleaner approach):
```python
# Remove le constraint from Field, let validator handle it
level: int = Field(default=0, ge=0, description="Nesting level")

@field_validator("level")
@classmethod
def validate_level(cls, v: int) -> int:
    config = Config()
    nesting_config = config.get_nesting_config()
    max_level = max(nesting_config['max_depth_column1'],
                   nesting_config['max_depth_column2'])

    if v < 0 or v > max_level:
        raise ValueError(f"Task level must be between 0 and {max_level}")
    return v
```

**Also update computed properties**:
```python
@computed_field
@property
def can_have_children_in_column2(self) -> bool:
    config = Config()
    max_depth = config.get_nesting_config()['max_depth_column2']
    return self.level < max_depth
```

**Lines Changed**: ~15 lines modified

---

### 4. **taskui/ui/theme.py** (DYNAMIC COLORS)

**Changes**: Make color mapping dynamic based on configuration

**Before**:
```python
LEVEL_0_COLOR = "#66D9EF"
LEVEL_1_COLOR = "#A6E22E"
LEVEL_2_COLOR = "#F92672"

def get_level_color(level: int) -> str:
    colors = {
        0: LEVEL_0_COLOR,
        1: LEVEL_1_COLOR,
        2: LEVEL_2_COLOR,
    }
    return colors.get(level, FOREGROUND)
```

**After**:
```python
from taskui.config import Config

# Module-level config
_config = Config()
_nesting_config = _config.get_nesting_config()
_max_level = max(_nesting_config['max_depth_column1'],
                _nesting_config['max_depth_column2'])

# Load dynamic colors
_LEVEL_COLORS = _config.get_level_colors(_max_level)

# Keep constants for backwards compatibility and common cases
LEVEL_0_COLOR = _LEVEL_COLORS.get(0, "#66D9EF")
LEVEL_1_COLOR = _LEVEL_COLORS.get(1, "#A6E22E")
LEVEL_2_COLOR = _LEVEL_COLORS.get(2, "#F92672")

def get_level_color(level: int) -> str:
    """Get color for any level, dynamically loaded from config."""
    return _LEVEL_COLORS.get(level, FOREGROUND)
```

**Lines Changed**: ~20 lines modified/added

---

### 5. **taskui/ui/components/task_item.py** (DYNAMIC CSS)

**Changes**: Generate CSS classes dynamically for all possible levels

**Before**:
```python
DEFAULT_CSS = f"""
TaskItem.level-0 {{
    border-left: thick {LEVEL_0_COLOR};
}}
TaskItem.level-1 {{
    border-left: thick {LEVEL_1_COLOR};
}}
TaskItem.level-2 {{
    border-left: thick {LEVEL_2_COLOR};
}}
"""
```

**After**:
```python
from taskui.config import Config

def _generate_level_css() -> str:
    """Generate CSS for all configured nesting levels."""
    config = Config()
    nesting_config = config.get_nesting_config()
    max_level = max(nesting_config['max_depth_column1'],
                   nesting_config['max_depth_column2'])

    level_colors = config.get_level_colors(max_level)

    css_parts = []
    for level, color in level_colors.items():
        css_parts.append(f"""
    TaskItem.level-{level} {{
        border-left: thick {color};
    }}""")

    return "\n".join(css_parts)

# Generate CSS dynamically
_LEVEL_CSS = _generate_level_css()

DEFAULT_CSS = f"""
TaskItem {{
    height: 1;
    width: 100%;
    background: transparent;
    opacity: 0;
}}

TaskItem:hover {{
    background: {with_alpha(SELECTION, HOVER_OPACITY)};
}}

TaskItem.selected {{
    background: {SELECTION};
}}

{_LEVEL_CSS}
"""
```

**Lines Changed**: ~25 lines modified/added

---

### 6. **taskui/services/task_service.py** (INJECT CONFIG)

**Changes**: Replace hardcoded checks with NestingRules instance

**Before**:
```python
# Hardcoded check
if new_level > 2:
    raise NestingLimitError(
        f"Cannot move task. New level ({new_level}) would exceed maximum (2)"
    )
```

**After**:
```python
class TaskService:
    def __init__(self, db_manager: DatabaseManager, config: Optional[Config] = None):
        self.db_manager = db_manager
        self._config = config or Config()
        self._nesting_rules = NestingRules(self._config)
        # ...

    async def move_task(self, ...):
        # ...
        # Use nesting rules for validation
        max_depth = self._nesting_rules.get_max_depth(Column.COLUMN2)
        if new_level > max_depth:
            raise NestingLimitError(
                f"Cannot move task. New level ({new_level}) would exceed maximum ({max_depth})"
            )
```

**Lines Changed**: ~10 lines modified, update constructor

---

### 7. **taskui/database.py** (NO CHANGES NEEDED)

**Status**: ✅ No changes required

The database stores `level` as an integer with no constraints. SQLAlchemy ORM doesn't enforce max values.

---

### 8. **tests/** (PARAMETERIZED TESTS)

**Changes**: Make tests configuration-aware or parameterized

**Option 1**: Test with default config
```python
def test_with_default_config():
    config = Config()  # Uses defaults
    rules = NestingRules(config)
    assert rules.max_depth_column2 == 2
```

**Option 2**: Test with custom config
```python
def test_with_custom_config():
    # Create in-memory config
    config = Config()
    config._config = configparser.ConfigParser()
    config._config.add_section('nesting')
    config._config.set('nesting', 'max_depth_column2', '5')

    rules = NestingRules(config)
    assert rules.max_depth_column2 == 5
```

**Option 3**: Parameterized tests
```python
@pytest.mark.parametrize("max_depth", [2, 5, 10, 20])
def test_dynamic_nesting(max_depth):
    config = create_config_with_max_depth(max_depth)
    rules = NestingRules(config)

    # Test that max_depth is enforced
    task = Task(level=max_depth - 1, ...)
    assert rules.can_create_child(task, Column.COLUMN2) == True

    task = Task(level=max_depth, ...)
    assert rules.can_create_child(task, Column.COLUMN2) == False
```

**Lines Changed**: ~50-100 lines modified/added

---

## Summary of Changes

| File | Lines Changed | Complexity | Breaking Changes |
|------|---------------|------------|------------------|
| `config.py` | +60 | Medium | No (additive) |
| `nesting_rules.py` | ~30 | High | **Yes** (class → instance) |
| `models.py` | ~15 | Medium | No (internal only) |
| `theme.py` | ~20 | Low | No (backwards compatible) |
| `task_item.py` | ~25 | Medium | No |
| `task_service.py` | ~10 | Low | **Yes** (constructor change) |
| `ui/app.py` | ~10 | Low | **Yes** (inject NestingRules) |
| `tests/*.py` | ~100 | Medium | **Yes** (many test updates) |
| **TOTAL** | **~270** | **Medium** | **Breaking** |

---

## Implementation Strategy

### Phase 1: Foundation (Low Risk)
1. Add `get_nesting_config()` to `Config` class
2. Add `get_level_colors()` to `Config` class
3. Create example `config.ini` in docs
4. Add unit tests for config methods

### Phase 2: Core Changes (High Risk)
1. Update `NestingRules` to instance-based with config injection
2. Update all `NestingRules` usage sites
3. Update `models.py` validators
4. Run all tests, fix failures

### Phase 3: UI Updates (Medium Risk)
1. Update `theme.py` with dynamic color mapping
2. Update `task_item.py` with dynamic CSS generation
3. Update any other UI components
4. Visual testing

### Phase 4: Testing (High Risk)
1. Update existing tests to use config
2. Add parameterized tests for various max depths
3. Add integration tests with custom configs
4. Add regression tests

### Phase 5: Documentation
1. Update README with configuration options
2. Add migration guide for existing users
3. Document environment variables
4. Add examples of custom nesting configs

---

## Migration Path for Existing Users

### Backwards Compatibility

**Default behavior remains unchanged**:
- Without any config file: Uses hardcoded defaults (Column1: 1, Column2: 2)
- Existing code continues to work

**Opt-in configuration**:
```bash
# Create config file
mkdir -p ~/.taskui
cat > ~/.taskui/config.ini << EOF
[nesting]
max_depth_column1 = 1
max_depth_column2 = 5
EOF

# Or use environment variables
export TASKUI_MAX_DEPTH_COLUMN2=5
```

---

## Breaking Changes Detail

### 1. NestingRules API Change

**Before**:
```python
from taskui.services.nesting_rules import NestingRules, Column

# Class methods
can_create = NestingRules.can_create_child(task, Column.COLUMN2)
max_depth = NestingRules.get_max_depth(Column.COLUMN2)
```

**After**:
```python
from taskui.services.nesting_rules import NestingRules, Column
from taskui.config import Config

# Instance methods
config = Config()
rules = NestingRules(config)
can_create = rules.can_create_child(task, Column.COLUMN2)
max_depth = rules.get_max_depth(Column.COLUMN2)
```

**Mitigation**: Provide singleton helper or keep class methods as deprecated wrappers

```python
# Backwards compatibility wrapper
_default_rules = None

@classmethod
def can_create_child(cls, task: Task, column: Column) -> bool:
    """Deprecated: Use instance method instead."""
    warnings.warn("Class method deprecated, use instance method", DeprecationWarning)
    global _default_rules
    if _default_rules is None:
        _default_rules = NestingRules()
    return _default_rules.can_create_child(task, column)
```

### 2. TaskService Constructor

**Before**:
```python
service = TaskService(db_manager)
```

**After**:
```python
config = Config()
service = TaskService(db_manager, config)
```

**Mitigation**: Make config optional with default

```python
def __init__(self, db_manager: DatabaseManager, config: Optional[Config] = None):
    self._config = config or Config()
    # ...
```

---

## Testing Strategy

### Unit Tests
- Test `Config.get_nesting_config()` with various inputs
- Test `Config.get_level_colors()` with edge cases
- Test `NestingRules` with different max depths
- Test dynamic validator in `models.py`

### Integration Tests
- Test full workflow with custom max depth
- Test config file loading
- Test environment variable overrides
- Test CSS generation for 10+ levels

### Regression Tests
- Ensure default behavior unchanged
- Ensure existing tests still pass
- Test backwards compatibility wrappers

### Performance Tests
- Measure config loading overhead
- Measure CSS generation time for large depths
- Ensure no performance regression

---

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking existing code | High | High | Backwards compat wrappers |
| Config loading errors | Medium | Low | Robust fallbacks, logging |
| Performance degradation | Low | Low | Cache config, lazy load |
| Test suite failures | Medium | High | Comprehensive test updates |
| CSS generation bugs | Medium | Medium | Unit tests, visual testing |
| Migration complexity | Medium | Medium | Clear docs, examples |

---

## Alternative Approaches

### Alternative 1: Keep Class Methods, Use Global Config
- Less intrusive changes
- Global state makes testing harder
- No dependency injection benefits

### Alternative 2: Compile-Time Configuration
- Use constants set at build/install time
- No runtime overhead
- Less flexible for users

### Alternative 3: Hybrid Approach (RECOMMENDED)
- Keep class method interface
- Add optional config parameter
- Internal instance with cached config
```python
@classmethod
def can_create_child(cls, task: Task, column: Column,
                    config: Optional[Config] = None) -> bool:
    if config is None:
        config = cls._get_default_config()
    rules = cls(config)
    return rules._can_create_child_impl(task, column)
```

---

## Conclusion

Making nesting fully configuration-driven requires **~270 lines of changes across 8 files**, with **medium complexity** and **some breaking changes**.

**Benefits**:
- ✅ Any arbitrary nesting depth without code changes
- ✅ User-configurable via config file or env vars
- ✅ Easier testing with different configs
- ✅ Better separation of concerns

**Drawbacks**:
- ⚠️ Breaking API changes (mitigated with wrappers)
- ⚠️ Increased complexity in initialization
- ⚠️ Potential performance overhead (minimal)
- ⚠️ More edge cases to test

**Recommendation**: Implement using **Hybrid Approach** (Alternative 3) to minimize breaking changes while gaining configuration flexibility.

**Estimated Effort**: 2-3 days for experienced developer (implementation + testing + docs)
