# TaskUI Column 2 Nesting Implementation - Comprehensive Investigation

## Executive Summary

Column 2 (Subtasks) in TaskUI currently supports **3 levels of nesting** (levels 0, 1, 2) with **context-relative display**. The nesting logic is centralized in the `NestingRules` service class and validated at multiple layers (model validation, service layer, and UI layer).

---

## 1. CURRENT NESTING CAPABILITIES IN COLUMN 2

### Supported Levels
- **Maximum depth: 3 levels total** (Levels 0, 1, 2)
- **Level 0**: Root tasks (can have children)
- **Level 1**: First nesting level (can have children)  
- **Level 2**: Second nesting level (CANNOT have children - maximum leaf level)

### Data Model Constraints
**File**: `/home/user/taskui-python/taskui/models.py` (Lines 76-95)

```python
class Task(BaseModel):
    # ... 
    level: int = Field(default=0, ge=0, le=2, description="Nesting level (0-2)")
    parent_id: Optional[UUID] = Field(default=None, description="Parent task ID for nesting")
```

Key constraints:
- `level` field: **ge=0, le=2** (validates range 0-2)
- Field validator enforces: `0 <= level <= 2`
- Model validator ensures parent_id consistency:
  - Level 0 tasks MUST NOT have parent_id
  - Level 1+ tasks MUST have parent_id

### Column 2 Display Logic
Column 2 uses **context-relative levels** for display:
- When a Level 0 task is selected in Column 1, its children (Level 1) appear as Level 0 in Column 2
- When a Level 1 task is selected, its children (Level 2) appear as Level 0 in Column 2
- This creates a "virtual hierarchy" starting from 0 in Column 2

**File**: `/home/user/taskui-python/taskui/ui/app.py` (Lines 1202-1226)

```python
def _make_levels_context_relative(self, tasks: List[Task], parent_level: int) -> List[Task]:
    """Adjust task levels to be context-relative for Column 2 display."""
    level_offset = parent_level + 1
    adjusted_tasks = []
    for task in tasks:
        adjusted_task = task.model_copy(update={
            "level": task.level - level_offset
        })
        adjusted_tasks.append(adjusted_task)
    return adjusted_tasks
```

---

## 2. CONSTRAINTS AND RULES ENFORCED

### A. Maximum Nesting Rules
**File**: `/home/user/taskui-python/taskui/services/nesting_rules.py`

```python
class NestingRules:
    MAX_DEPTH_COLUMN1 = 1  # Levels 0-1 (2 levels total)
    MAX_DEPTH_COLUMN2 = 2  # Levels 0-2 (3 levels total)
```

### B. Child Creation Rules

**Column 1 (Tasks):**
- Level 0 can have children → children are Level 1
- Level 1 CANNOT have children (max depth reached)

**Column 2 (Subtasks):**
- Level 0 can have children → children are Level 1
- Level 1 can have children → children are Level 2
- Level 2 CANNOT have children (max depth reached)

**Method**: `NestingRules.can_create_child(task: Task, column: Column) -> bool`

```python
@classmethod
def can_create_child(cls, task: Task, column: Column) -> bool:
    if column == Column.COLUMN1:
        return task.level < cls.MAX_DEPTH_COLUMN1  # Only level 0
    elif column == Column.COLUMN2:
        return task.level < cls.MAX_DEPTH_COLUMN2  # Level 0 and 1
```

### C. Service Layer Validation
**File**: `/home/user/taskui-python/taskui/services/task_service.py` (Lines 339-412)

```python
async def create_child_task(
    self,
    parent_id: UUID,
    title: str,
    column: Column,
    notes: Optional[str] = None,
) -> Task:
    # ...
    if not NestingRules.can_create_child(parent_task, column):
        max_depth = NestingRules.get_max_depth(column)
        raise NestingLimitError(
            f"Cannot create child task. Parent task at level {parent_task.level} "
            f"has reached maximum nesting depth ({max_depth}) for {column.value}."
        )
```

### D. Database Level Constraints
**File**: `/home/user/taskui-python/taskui/database.py` (Lines 57-93)

```python
class TaskORM(Base):
    __tablename__ = "tasks"
    
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )
    level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
```

No database-level constraints enforcing max level, but application layer prevents invalid values.

---

## 3. WHERE NESTING LOGIC IS DEFINED AND ENFORCED

### A. Centralized Rules Engine
**Primary Location**: `/home/user/taskui-python/taskui/services/nesting_rules.py`

This is the **single source of truth** for all nesting rules. Methods:

| Method | Purpose | Column 1 | Column 2 |
|--------|---------|----------|----------|
| `can_create_child()` | Can task have children? | L0 only | L0, L1 |
| `get_max_depth()` | Max depth for column | 1 | 2 |
| `validate_nesting_depth()` | Is level valid? | ≤1 | ≤2 |
| `get_allowed_child_level()` | What level are children? | L0→L1 | L0→L1, L1→L2 |

### B. Model Validation Layer
**File**: `/home/user/taskui-python/taskui/models.py` (Lines 127-165)

```python
@field_validator("level")
@classmethod
def validate_level(cls, v: int) -> int:
    if v < 0 or v > 2:
        raise ValueError("Task level must be between 0 and 2")
    return v

@model_validator(mode='after')
def validate_parent_level_consistency(self) -> 'Task':
    if self.level == 0 and self.parent_id is not None:
        raise ValueError("Level 0 tasks cannot have a parent_id")
    if self.level > 0 and self.parent_id is None:
        raise ValueError(f"Level {self.level} tasks must have a parent_id")
```

### C. Service Layer Enforcement
**File**: `/home/user/taskui-python/taskui/services/task_service.py`

- `create_child_task()`: Validates before creating
- `move_task()`: Validates nesting on move (Lines 846-1003)
- `_update_descendant_levels()`: Recursive level update with bounds checking

### D. UI Layer Display Logic
**File**: `/home/user/taskui-python/taskui/ui/app.py` (Lines 1167-1226)

- Column 2 header shows selected task name: `"{selected_task.title} Subtasks"`
- Context-relative level adjustment happens before rendering
- TaskColumn displays with tree lines (└─, ├─) based on level

### E. Component Rendering
**File**: `/home/user/taskui-python/taskui/ui/components/task_item.py` (Lines 135-249)

- TaskItem applies CSS classes based on level: `level-0`, `level-1`, `level-2`
- Tree visualization with indentation based on level
- Level-specific colors from theme

---

## 4. DATA MODEL STRUCTURE

### Task Hierarchy Model

```
Task (Pydantic model)
├── id: UUID
├── title: str
├── parent_id: Optional[UUID]  ← Establishes parent-child link
├── level: int                 ← Depth indicator (0-2)
├── position: int              ← Order among siblings
├── list_id: UUID              ← Belongs to this list
├── is_completed: bool
├── is_archived: bool
└── Computed Properties:
    ├── progress_string: "X/Y" (if has children)
    ├── completion_percentage: 0-100 (of children)
    ├── has_children: bool
    ├── can_have_children_in_column1: bool (L0 only)
    └── can_have_children_in_column2: bool (L0, L1)
```

### Parent-Child Relationships

**Column 1 Hierarchy:**
```
Level 0 (Root)
  └─ Level 1 (max nesting here)
```

**Column 2 Hierarchy (absolute levels):**
```
Level 0 (Root)
  └─ Level 1 (first nesting)
    └─ Level 2 (max nesting here)
```

**Column 2 Hierarchy (context-relative display):**
```
When Level 0 task selected:
Level 0 → shows as Level 0
  └─ Level 1 → shows as Level 0 in Column 2
    └─ Level 2 → shows as Level 1 in Column 2

When Level 1 task selected:
Level 1 → shows as Level 0
  └─ Level 2 → shows as Level 0 in Column 2
```

---

## 5. UI RENDERING OF NESTING LEVELS

### CSS Classes by Level
**File**: `/home/user/taskui-python/taskui/ui/components/task_item.py` (Lines 50-77)

```css
TaskItem.level-0 { border-left: thick #66D9EF; }  /* Cyan */
TaskItem.level-1 { border-left: thick #A6E22E; }  /* Green */
TaskItem.level-2 { border-left: thick #F92672; }  /* Pink */
```

### Visual Indicators

1. **Tree Lines** (Lines 225-249):
   - `└─` for last child
   - `├─` for non-last children
   - Indentation: 2 spaces per level

2. **Colors** (from `/home/user/taskui-python/taskui/ui/theme.py`):
   - **LEVEL_0_COLOR**: `#66D9EF` (Cyan)
   - **LEVEL_1_COLOR**: `#A6E22E` (Green)
   - **LEVEL_2_COLOR**: `#F92672` (Pink)

3. **Progress Display**:
   - Format: "(X/Y)" where X=completed children, Y=total children
   - Only shown if task has_children
   - Dimmed foreground color

### Example Render for Level 2 Task
```
  ├─ [ ] Session management (1/2)
    └─ [ ] Redis setup
```

---

## 6. VALIDATION AND BUSINESS LOGIC

### Validation Layers (Defense in Depth)

```
1. Model Layer (Pydantic)
   ├─ @field_validator("level"): 0 ≤ level ≤ 2
   └─ @model_validator: parent_id consistency checks

2. Service Layer (TaskService)
   ├─ create_child_task(): Uses NestingRules.can_create_child()
   ├─ move_task(): Validates new_level ≤ 2
   └─ _update_descendant_levels(): Enforces bounds

3. Rules Engine (NestingRules)
   ├─ can_create_child(): Column-specific rules
   ├─ validate_nesting_depth(): Is level valid?
   └─ get_allowed_child_level(): What level for children?

4. UI Layer (TaskUI App & TaskColumn)
   ├─ Prevents creation if validation fails
   └─ Displays error messages to user
```

### Key Error Cases Handled

1. **Creating child of Level 2 task in Column 2**:
   - `NestingRules.can_create_child(level_2_task, COLUMN2)` → `False`
   - Raises: `NestingLimitError`

2. **Moving task to invalid depth**:
   - `move_task()` validates: `new_level > 2` → raises `NestingLimitError`

3. **Invalid model data**:
   - Pydantic validator raises `ValueError`
   - Prevents bad data from entering system

---

## 7. KEY FILES AND FUNCTIONS INVOLVED IN NESTING

### Data & Models
| File | Key Components |
|------|-----------------|
| `/taskui/models.py` | `Task` class with level/parent_id validation |
| `/taskui/database.py` | `TaskORM` class with parent_id FK |

### Business Logic
| File | Key Functions |
|------|---|
| `/taskui/services/nesting_rules.py` | `NestingRules` class - rules engine |
| `/taskui/services/task_service.py` | `create_child_task()`, `move_task()`, `_update_descendant_levels()` |
| `/taskui/services/list_service.py` | `ListService` - works with TaskService |

### UI Display
| File | Key Components |
|------|---|
| `/taskui/ui/app.py` | `_update_column2_for_selection()`, `_make_levels_context_relative()` |
| `/taskui/ui/components/column.py` | `TaskColumn` - displays task list with hierarchy |
| `/taskui/ui/components/task_item.py` | `TaskItem` - renders individual task with level styling |
| `/taskui/ui/theme.py` | Color constants: `LEVEL_0/1/2_COLOR` |

### Configuration & Constants
| File | Key Items |
|------|---|
| `/taskui/ui/constants.py` | UI constants (notification timeouts, etc.) |
| `/taskui/ui/keybindings.py` | Column IDs: `COLUMN_1_ID`, `COLUMN_2_ID`, `COLUMN_3_ID` |

### Tests
| File | Coverage |
|------|----------|
| `/tests/test_nesting_rules.py` | Complete NestingRules test suite (407 lines) |
| `/tests/test_column2_updates.py` | Column 2 context-relative display |
| `/tests/test_task_service.py` | Service layer nesting validation |

---

## 8. CHANGES NEEDED FOR ADDITIONAL NESTING LEVEL (Level 3)

### To add a 4th level (Level 3) to Column 2, these changes are REQUIRED:

#### A. Update Constants
**File**: `/taskui/services/nesting_rules.py`

```python
# CHANGE THIS:
MAX_DEPTH_COLUMN2 = 2  # Levels 0-2 (3 levels total)

# TO THIS:
MAX_DEPTH_COLUMN2 = 3  # Levels 0-3 (4 levels total)
```

#### B. Update Model Validation
**File**: `/taskui/models.py`

```python
# CHANGE THIS:
level: int = Field(default=0, ge=0, le=2, description="Nesting level (0-2)")

# TO THIS:
level: int = Field(default=0, ge=0, le=3, description="Nesting level (0-3)")

# AND THIS:
@field_validator("level")
@classmethod
def validate_level(cls, v: int) -> int:
    if v < 0 or v > 2:  # ← Change to: v > 3
        raise ValueError("Task level must be between 0 and 3")  # ← Update message
    return v
```

#### C. Add Level 3 Color to Theme
**File**: `/taskui/ui/theme.py`

```python
# ADD THIS (after LEVEL_2_COLOR):
LEVEL_3_COLOR = "#E6DB74"  # Yellow (or choose another distinct color)

# UPDATE THIS:
def get_level_color(level: int) -> str:
    colors = {
        0: LEVEL_0_COLOR,
        1: LEVEL_1_COLOR,
        2: LEVEL_2_COLOR,
        3: LEVEL_3_COLOR,  # ← ADD THIS LINE
    }
    return colors.get(level, FOREGROUND)
```

#### D. Add CSS Class for Level 3
**File**: `/taskui/ui/components/task_item.py`

```python
# In DEFAULT_CSS, ADD:
TaskItem.level-3 {{
    border-left: thick {LEVEL_3_COLOR};
}}

# Also import LEVEL_3_COLOR from theme
```

#### E. Add Level 3 to Rich Theme
**File**: `/taskui/ui/theme.py`

```python
# In ONE_MONOKAI_THEME dict, ADD:
"level_3": LEVEL_3_COLOR,  # Deep nested color (yellow)
```

#### F. Update Tests
**File**: `/tests/test_nesting_rules.py`

Add tests for Level 3:
```python
def test_level2_can_have_children(self):
    """Level 2 tasks can have children in Column 2 (new)."""
    task = Task(title="Task", level=2, parent_id=uuid4(), list_id=uuid4())
    assert NestingRules.can_create_child(task, Column.COLUMN2) is True

def test_level3_cannot_have_children(self):
    """Level 3 tasks cannot have children in Column 2."""
    task = Task(title="Task", level=3, parent_id=uuid4(), list_id=uuid4())
    assert NestingRules.can_create_child(task, Column.COLUMN2) is False

def test_level3_depth_validation(self):
    """Level 3 tasks are valid in Column 2."""
    task = Task(title="Task", level=3, parent_id=uuid4(), list_id=uuid4())
    assert NestingRules.validate_nesting_depth(task, Column.COLUMN2) is True
```

#### G. Documentation Updates
- Update docstrings in models.py mentioning "0-2" → "0-3"
- Update docstrings in nesting_rules.py
- Update README.md and docs

#### H. Database Schema (Optional but Recommended)
While existing database will work (no explicit constraint), consider:
- No migration needed (level is just an INT column)
- Existing data with levels 0-2 will continue working

---

## 9. SUMMARY TABLE: CHANGES REQUIRED

| Component | File | Change | Lines |
|-----------|------|--------|-------|
| **Rules Engine** | `nesting_rules.py` | `MAX_DEPTH_COLUMN2 = 3` | 39 |
| **Model Validation** | `models.py` | Update `le=3`, validator to `v > 3` | 95, 142 |
| **Theme** | `theme.py` | Add `LEVEL_3_COLOR` | ~90, 187 |
| **CSS** | `task_item.py` | Add `.level-3` class | ~77 |
| **Imports** | `task_item.py` | Import `LEVEL_3_COLOR` | 29 |
| **Rich Theme** | `theme.py` | Add to dict | 141 |
| **Tests** | `test_nesting_rules.py` | Add 3+ test cases | +20 lines |
| **Docs** | Various | Update examples | Multiple |

---

## 10. CRITICAL IMPLEMENTATION NOTES

### What WILL Work Automatically
- Service layer validation (uses MAX_DEPTH_COLUMN2)
- Move operations with bounds checking
- Database storage (int column)
- Parent-child relationships
- Child count and progress calculation

### What REQUIRES Manual Changes
- Model validation (the `le=` constraint)
- Field validator logic
- Color theme
- CSS styling
- Tests
- Documentation

### Testing Recommendations
```python
# Before adding Level 3:
pytest tests/test_nesting_rules.py  # All pass

# After adding Level 3:
pytest tests/test_nesting_rules.py  # Should still pass
pytest tests/test_models.py          # Add Level 3 validation tests
pytest tests/test_task_service.py    # Ensure service handles Level 3
```

### Risk Assessment
**Risk Level**: LOW
- Changes are localized
- No breaking changes to existing data
- All constraints enforced at application layer
- Existing levels 0-2 unaffected
- Can be rolled back easily

---

## 11. REFERENCES TO KEY CODE

### NestingRules Core Logic
- `/home/user/taskui-python/taskui/services/nesting_rules.py` (219 lines)
  - All nesting rules in one place
  - Clear, well-documented methods
  - Used by all layers

### Task Model
- `/home/user/taskui-python/taskui/models.py` (Lines 76-267)
  - Pydantic model with computed properties
  - Full validation with clear error messages

### Service Layer
- `/home/user/taskui-python/taskui/services/task_service.py` (1044 lines)
  - `create_child_task()`: Lines 339-412
  - `move_task()`: Lines 846-971
  - `_update_descendant_levels()`: Lines 973-1003

### UI App Layer
- `/home/user/taskui-python/taskui/ui/app.py` (1500+ lines)
  - `_update_column2_for_selection()`: Lines 1167-1186
  - `_make_levels_context_relative()`: Lines 1202-1226

### Theme & Colors
- `/home/user/taskui-python/taskui/ui/theme.py` (252 lines)
  - Level colors: Lines 87-89
  - Color helper: `get_level_color()`: Lines 153-187

---

## Conclusion

Column 2's nesting implementation is **clean, well-structured, and extensible**. The use of a centralized `NestingRules` class makes it easy to understand and modify nesting constraints. Adding a Level 3 would require changes in approximately 6-8 files but would be straightforward with low risk of breaking existing functionality.
