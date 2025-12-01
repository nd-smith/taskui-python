# TaskUI Codebase Cleanup Recommendations

This document tracks identified opportunities to clean up the TaskUI codebase, including dead code removal, readability improvements, and refactoring suggestions for clearer separation of concerns.

---

## Executive Summary

The TaskUI codebase is well-structured with good test coverage and comprehensive documentation. However, there are several areas that could benefit from cleanup:

| Category | Items Found | Priority |
|----------|-------------|----------|
| Dead Code | 3 files/modules | High |
| Unused Imports | 4 instances | Medium |
| Large Files | 2 files >1000 lines | Medium |
| Code Duplication | 3 patterns | Medium |
| Separation of Concerns | 2 areas | Low |

---

## 1. Dead Code

### 1.1 `sync_queue.py` - Legacy Sync Implementation (HIGH PRIORITY)

**Location:** `taskui/services/sync_queue.py` (298 lines)

**Issue:** This file implements a legacy per-operation sync queue (V1) that has been superseded by `sync_v2.py` (full-state JSON sync). The `SyncQueue` class is only imported by its test file (`tests/test_sync_queue.py`), not by the main application.

**Evidence:**
```bash
$ grep -r "from taskui.services.sync_queue" .
tests/test_sync_queue.py:13:from taskui.services.sync_queue import SyncQueue
```

**Recommendation:**
- Remove `taskui/services/sync_queue.py`
- Remove `tests/test_sync_queue.py`
- Update any documentation referencing V1 sync

**Impact:** ~300 lines removed

---

### 1.2 `sync_client.py` - Unused SyncClient Class (HIGH PRIORITY)

**Location:** `taskui/services/sync_client.py` (35 lines)

**Issue:** The `SyncClient` class that manages client IDs is not imported anywhere in the codebase. Client ID management appears to be handled directly in `sync_v2.py` and configured via `config.py`.

**Evidence:**
```bash
$ grep -r "sync_client\|SyncClient" taskui/
taskui/services/sync_client.py:9:class SyncClient:
# No other imports found
```

**Recommendation:**
- Remove `taskui/services/sync_client.py`
- Verify client ID management is working correctly in the current implementation

**Impact:** ~35 lines removed

---

### 1.3 `if __name__ == "__main__"` Example Blocks

**Locations:**
- `taskui/services/sync_queue.py:242-298` (56 lines)
- `taskui/services/printer_service.py:283-340` (57 lines)
- `taskui/services/cloud_print_queue.py:362-408` (46 lines)
- `taskui/config.py:286-305` (19 lines)

**Issue:** Multiple files contain `if __name__ == "__main__":` blocks with example usage code. While useful during development, these add maintenance burden and increase file sizes.

**Recommendation:**
- Move example code to dedicated script files in `scripts/` or `examples/` directory
- Or document these examples in docstrings/comments instead
- Consider keeping only in files that are genuinely runnable utilities

**Impact:** ~180 lines could be moved to dedicated example files

---

## 2. Unused Imports

### 2.1 `cloud_print_queue.py` Unused Imports (MEDIUM PRIORITY)

**Location:** `taskui/services/cloud_print_queue.py:9-14`

**Unused imports:**
- `import json` - Line 9 (no `json.` usage found)
- `import base64` - Line 10 (no `base64.` usage found)
- `import logging` - Line 14 (uses `get_logger` instead)

**Recommendation:** Remove these three unused imports

---

### 2.2 `printer_service.py` Unused Import

**Location:** `taskui/services/printer_service.py:12`

**Unused import:**
- `from pathlib import Path` - Used in `PrinterConfig.from_config_file()` signature but `Path` is never actually used in the method body

**Recommendation:** Verify usage; remove if truly unused

---

## 3. Code Duplication

### 3.1 SQS Connection Code (MEDIUM PRIORITY)

**Locations:**
- `taskui/services/sync_v2.py:68-113` (`connect()` method)
- `taskui/services/cloud_print_queue.py:121-170` (`connect()` method)
- `taskui/services/sync_queue.py:46-95` (`connect()` method)

**Issue:** Nearly identical SQS connection logic is duplicated across three files:
- boto3 import and SSL warning suppression
- Client kwargs building with credentials
- Connection testing via `get_queue_attributes`
- Error handling pattern

**Recommendation:** Extract common SQS connection logic into a shared base class or utility:

```python
# taskui/services/sqs_base.py
class SQSConnectionMixin:
    """Shared SQS connection handling."""

    def _create_sqs_client(self, config):
        """Create and test SQS client connection."""
        # Common boto3 setup, SSL handling, credential passing
        ...
```

**Impact:** Reduces duplication by ~100 lines and centralizes SQS configuration

---

### 3.2 Encryption Initialization Pattern

**Locations:**
- `taskui/services/sync_v2.py:64`
- `taskui/services/cloud_print_queue.py:112-117`
- `taskui/services/sync_queue.py:38-42`

**Issue:** Same pattern of initializing `MessageEncryption` and logging encryption status

**Recommendation:** Could be part of the SQS base class mentioned above

---

### 3.3 Queue Depth Retrieval

**Locations:**
- `taskui/services/sync_v2.py:381-399`
- `taskui/services/cloud_print_queue.py:273-291`
- `taskui/services/sync_queue.py:221-239`

**Issue:** Identical `get_queue_depth()` implementations

**Recommendation:** Part of SQS base class refactoring

---

## 4. Large Files - Separation of Concerns

### 4.1 `app.py` - Monolithic Application Class (MEDIUM PRIORITY)

**Location:** `taskui/ui/app.py` (1,912 lines)

**Issue:** The main `TaskUI` class handles too many responsibilities:
- Application lifecycle
- Database session management
- Command palette provider
- All task operations (create, edit, delete, move)
- List operations
- Printing operations
- Sync operations
- Diary entry operations
- UI state management

**Recommendation:** Consider extracting handlers into separate classes/modules:

1. **TaskOperationsHandler** - Task CRUD operations
2. **ListOperationsHandler** - List management
3. **SyncHandler** - Sync push/pull operations
4. **PrintHandler** - Print queue management

Example structure:
```python
# taskui/ui/handlers/task_operations.py
class TaskOperationsHandler:
    def __init__(self, app: "TaskUI"):
        self.app = app

    async def create_task(self, ...): ...
    async def edit_task(self, ...): ...
    async def delete_task(self, ...): ...
```

**Impact:** Better testability, clearer responsibilities, easier navigation

---

### 4.2 `task_service.py` - Large Service File (LOW PRIORITY)

**Location:** `taskui/services/task_service.py` (1,072 lines)

**Issue:** While appropriately scoped to task operations, this file is large. The complexity is justified by the business logic involved (hierarchical tasks, position management, bulk operations).

**Recommendation:** Consider splitting into:
- `task_crud.py` - Basic CRUD operations
- `task_hierarchy.py` - Parent/child operations, level management
- `task_bulk.py` - Bulk operations (migrate, reorder)

**Priority:** Low - current organization is acceptable

---

## 5. Empty/Minimal Files

### 5.1 `services/__init__.py`

**Location:** `taskui/services/__init__.py`

**Current content:**
```python
"""TaskUI services - Business logic and data operations."""

__all__ = []
```

**Issue:** Empty `__all__` exports nothing useful

**Recommendation:** Either:
- Remove the file (Python 3 doesn't require `__init__.py`)
- Or export commonly used services for cleaner imports:
```python
__all__ = [
    "TaskService",
    "ListService",
    "DiaryService",
    "PrinterService",
]
```

---

## 6. Minor Cleanup Opportunities

### 6.1 Consistent Logger Usage

**Issue:** Most files use `from taskui.logging_config import get_logger`, but `cloud_print_queue.py` also imports unused `import logging`

**Recommendation:** Ensure consistent pattern across all files

---

### 6.2 Type Hints Consistency

**Issue:** Some older functions lack type hints while newer code has comprehensive typing

**Examples:**
- `task_modal.py:186-210` - `__init__` has `diary_service_getter=None` without type hint

**Recommendation:** Add missing type hints during other refactoring work

---

### 6.3 Docstring Format Consistency

**Issue:** Mix of docstring styles - some use Google style (Args/Returns sections), others use simpler formats

**Recommendation:** Standardize on Google-style docstrings project-wide (already dominant pattern)

---

## 7. Refactoring Suggestions (Future)

### 7.1 Modal Base Class

**Issue:** Multiple modals (`TaskCreationModal`, `ListManagementModal`, `ListDeleteModal`, `DiaryEntryModal`) share similar patterns for:
- CSS styling base
- Button handling
- Escape/Enter key bindings
- Dismiss behavior

**Recommendation:** Create `BaseModal` class with shared functionality

---

### 7.2 Configuration Validation

**Issue:** Configuration validation is scattered across multiple `from_config_file()` methods

**Recommendation:** Centralize config validation in `Config` class with schema validation (potentially using Pydantic)

---

## Prioritized Action Plan

### Phase 1: Quick Wins (High Impact, Low Effort)
1. Remove `sync_queue.py` and its test file
2. Remove `sync_client.py`
3. Remove unused imports in `cloud_print_queue.py`

### Phase 2: Code Quality (Medium Impact, Medium Effort)
4. Extract SQS connection logic into shared base class
5. Move `if __name__ == "__main__"` blocks to examples directory

### Phase 3: Architecture (Medium Impact, Higher Effort)
6. Split `app.py` into handler classes
7. Populate `services/__init__.py` with useful exports

### Phase 4: Polish (Lower Priority)
8. Add missing type hints
9. Standardize docstring format
10. Consider modal base class

---

## Metrics

| Metric | Current | After Cleanup |
|--------|---------|---------------|
| Total Python files | 38 | 36 |
| Total lines (approx) | 13,000+ | ~12,500 |
| Files >500 lines | 5 | 4 |
| Dead code files | 2 | 0 |

---

*Document created: 2025-12-01*
*Review status: Initial analysis complete*
