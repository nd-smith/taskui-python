# TaskUI Architecture Review

## Feature → Code Mapping

### ✅ Task Hierarchy (4 levels max)

**Essential:**
- `models.py`: `Task.level` field (line 105)
- `database.py`: `level` column in TaskORM
- `task_service.py`: Parent-child relationship management
- `ui/components/task_item.py`: Indent/tree visualization based on level

**Potentially Over-Engineered:**
- `services/nesting_rules.py`: **540 lines** - enforces column-specific depth limits
  - Column 1: max depth 1 (2 levels)
  - Column 2: max depth 2 (3 levels)
  - **Reality**: This is a UI display preference, not a data constraint
  - **Simpler**: Global max depth (4), UI filters by level

- `config/nesting_config.py`: **119 lines** - TOML config for column limits
  - **Reality**: User just wants "shallow in column 1, deep in column 2"
  - **Simpler**: Hardcode display filters, no config needed

**Line Count:**
- Essential: ~200 lines
- Over-engineered: ~659 lines (nesting_rules + nesting_config)
- **Bloat ratio: 3.3x**

---

### ✅ Two-Column Display

**Essential:**
- `ui/components/column.py`: 499 lines - TaskColumn widget
- `ui/app.py`: Column management, focus handling
- `ui/keybindings.py`: Tab/navigation between columns

**Potentially Over-Engineered:**
- Context-relative level adjustment (app.py:1474-1498)
  - Adjusts displayed level in Column 2 to start at 0
  - **Reality**: Could just display absolute level with appropriate styling
  - **Impact**: 25 lines + mental complexity

**Line Count:**
- Essential: ~500 lines
- Over-engineered: ~25 lines
- **Bloat ratio: minimal**

---

### ✅ Multiple Lists

**Essential:**
- `models.py`: TaskList model
- `database.py`: TaskListORM
- `services/list_service.py`: 560 lines - CRUD operations
- `ui/components/list_bar.py`: 454 lines - List switcher
- `ui/components/list_management_modal.py`: 298 lines - Create/edit lists
- `ui/components/list_delete_modal.py`: 405 lines - Delete confirmation

**Analysis:**
- List service seems reasonable for the feature
- Modals are verbose but typical for Textual
- **No significant bloat identified**

**Line Count:**
- Total: ~1,717 lines
- **Assessment: Proportional to feature**

---

### ✅ Thermal Printing (CORE FEATURE)

**Essential:**
- `services/printer_service.py`: 337 lines - ESC/POS printing
- `services/cloud_print_queue.py`: 394 lines - AWS SQS integration
- `services/encryption.py`: 176 lines - AES-256-GCM encryption
- `ui/app.py`: Print action handler (lines 782-834)
- `ui/keybindings.py`: 'P' key binding

**Missing Dependencies:**
- ⚠️ `boto3` - NOT in pyproject.toml
- ⚠️ `python-escpos` - NOT in pyproject.toml
- ⚠️ `cryptography` - NOT in pyproject.toml

**Analysis:**
- Feature is justified (core workflow)
- Implementation seems reasonable
- **CRITICAL BUG**: Missing dependencies will cause runtime failures

**Line Count:**
- Total: ~900 lines
- **Assessment: Justified for core feature, but BROKEN (missing deps)**

---

### ✅ Deleted Task Recovery

**Current Implementation:**
- Archive system with separate archive modal (578 lines)
- Archive vs delete distinction
- `task_service.py`: archive/unarchive methods (lines 831-1003)

**User Requirement:**
- Simple trash/restore UI
- No need for archive vs delete distinction

**Over-Engineering:**
- Archive is separate from delete
- Complex archive modal
- **Simpler**: Soft-delete with "is_deleted" flag, single restore UI

**Line Count:**
- Current: ~750 lines (archive modal + service methods)
- Needed: ~200 lines (simple trash UI)
- **Bloat: ~550 lines**

---

### ✅ Theming

**Current Implementation:**
- `ui/themes/theme.py`: 251 lines - Theme system
- `ui/themes/dracula.py`: 150 lines
- `ui/themes/nord.py`: 182 lines
- `ui/themes/tokyo_night.py`: 151 lines

**User Requirement:**
- Easy CSS for theming
- Don't need pre-built themes

**Analysis:**
- Theme system (251 lines) may be over-engineered
- Could use simple .tcss files instead
- **Remove**: 483 lines of pre-built themes

**Line Count:**
- Current: 734 lines
- Needed: ~50 lines (basic color variables)
- **Bloat: ~684 lines**

---

### ❌ Legacy Code

**Files:**
- `legacy_config.py`: 196 lines

**Analysis:**
- App is version 0.1.0
- Why does a brand new app have "legacy" code?
- **Bloat: 196 lines**

---

## Summary: Bloat Identification

### Confirmed Bloat

| Component | Lines | Reason |
|-----------|-------|--------|
| Column-specific nesting rules | 659 | UI preference treated as data constraint |
| Pre-built themes (3x) | 483 | User wants simple CSS, not pre-builts |
| Archive vs delete distinction | 550 | User wants simple trash/restore |
| Legacy config | 196 | v0.1.0 shouldn't have "legacy" |
| **TOTAL** | **1,888** | **17% of codebase** |

### Essential But Broken

| Component | Lines | Issue |
|-----------|-------|-------|
| Printing infrastructure | 900 | Missing dependencies in pyproject.toml |

### Essential And Good

| Component | Lines |
|-----------|-------|
| Task service | ~800 |
| List management | ~1,700 |
| UI components | ~2,000 |
| Database layer | ~300 |

---

## Architectural Issues

### 1. Leaky Abstractions
**Problem:** Data layer knows about UI concepts
- `task_service.create_child_task()` takes `column: Column` parameter
- Database validates UI display preferences
- **Fix:** Remove column concept from data layer

### 2. Inline CSS
**Problem:** 616 lines of CSS embedded in Python
- All UI components have `DEFAULT_CSS` strings
- Textual supports external .tcss files
- **Fix:** Move to consolidated .tcss files

### 3. Missing Dependencies
**Problem:** Core feature will fail at runtime
- Printer requires `boto3`, `python-escpos`, `cryptography`
- Not listed in pyproject.toml
- **Fix:** Add to dependencies

### 4. Inconsistent Deletion
**Problem:** Two deletion paths
- Soft delete (archive)
- Hard delete
- User wants simple trash/restore
- **Fix:** Single soft-delete with restore UI

---

## Recommended Refactoring Priority

### P0 (Blocking/Broken)
1. **Add missing dependencies** - printer feature is broken
2. **Fix import paths** - ensure app runs

### P1 (High-Value Simplification)
1. **Remove column-specific nesting** - 659 lines, simplifies mental model
2. **Unify delete/archive** - 550 lines, matches user needs
3. **Remove legacy_config.py** - 196 lines, makes no sense in v0.1.0

### P2 (Nice-to-Have)
1. **Remove pre-built themes** - 483 lines, keep theme system
2. **Move CSS to .tcss files** - 616 lines, best practice
3. **Simplify context-relative display** - 25 lines, minor complexity

### P3 (Future)
1. Prepare for diary/status updates feature
2. Prepare for notepad feature
3. Prepare for URL/Outlook fields

---

## Expected Outcome

**Current:** 11,159 lines
**After P0-P1:** ~8,754 lines (21% reduction)
**After P0-P2:** ~7,655 lines (31% reduction)

**Benefits:**
- Simpler mental model
- Easier to add future features
- Matches actual usage patterns
- Fixes broken printer feature
