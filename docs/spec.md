# TaskUI - Python TUI Implementation Specification

## PROJECT OVERVIEW

Build a beautiful terminal-based task management system with nested hierarchy, using Python and modern TUI frameworks. Priority on exceptional UX, visual design, and frictionless interaction.

## TECHNOLOGY STACK

```yaml
language: Python 3.10+
ui_framework: Textual 6.6.0+ (CSS-like styling, reactive, modern)
database: SQLite3 with JSON export/backup
theme: One Monokai color scheme
printing: Network printing to Raspberry Pi print server
testing: pytest, textual-dev
packaging: pip/poetry, single executable with PyInstaller
```

## VERSION NOTES & COMPATIBILITY

### Latest Stable Versions (November 2025):
- **Textual**: 6.6.0 - Major improvements from 0.45.x series
- **Rich**: 14.1.0 - Stable, mature library
- **Pydantic**: 2.12.x - V2 is significantly faster than V1
- **aiosqlite**: 0.21.0 - Python 3.8+ required

### Important Changes:
1. **Textual 6.x**: Breaking changes from earlier versions
   - New widget API
   - Improved CSS system
   - Better async support
   
2. **Pydantic V2**: Complete rewrite, ~17x faster
   - New validation API
   - Better type hints
   - Use `BaseModel` from `pydantic` directly

3. **Python 3.10+**: Required for modern type hints
   - Union types with `|` operator
   - Better async/await support
   - Structural pattern matching available

## CORE DEPENDENCIES

```python
# pyproject.toml / requirements.txt
textual>=6.6.0       # TUI framework (latest: 6.6.0 as of Nov 2025)
rich>=14.1.0         # Pretty printing/formatting (latest: 14.1.0)
sqlite3              # Built-in
aiosqlite>=0.21.0    # Async SQLite operations (latest: 0.21.0)
pydantic>=2.12       # Data validation (latest: 2.12.x)
pydantic-settings>=2.0  # Settings management (separate in V2)
python-dateutil      # Timestamp handling
aiofiles             # Async file operations
requests             # Network printer communication
typer                # CLI arguments
pytest>=7.0          # Testing
textual-dev>=0.0.2   # Development tools (latest release)
```

## DATA MODELS

```python
# models.py

import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum

class TaskStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class Task(BaseModel):
    """Core task model with nesting constraints."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    notes: Optional[str] = None
    status: TaskStatus = TaskStatus.ACTIVE
    
    # Hierarchy
    parent_id: Optional[str] = None
    list_id: str
    level: int = 0  # 0-1 in Column1, 0-2 in Column2
    position: int = 0  # Order within parent
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    modified_at: datetime = Field(default_factory=datetime.now)
    
    # Computed fields
    child_count: int = 0
    completed_child_count: int = 0
    
    def progress_string(self) -> str:
        """Return progress like '2/5' for display."""
        if self.child_count > 0:
            return f"{self.completed_child_count}/{self.child_count}"
        return ""

class TaskList(BaseModel):
    """Task list container."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    position: int  # 1, 2, or 3
    task_count: int = 0
    completed_count: int = 0
    archived_count: int = 0
    
    def completion_percentage(self) -> int:
        """Calculate completion percentage."""
        if self.task_count == 0:
            return 0
        return int((self.completed_count / self.task_count) * 100)
```

## DATABASE SCHEMA

```sql
-- schema.sql

CREATE TABLE IF NOT EXISTS lists (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    position INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    notes TEXT,
    status TEXT DEFAULT 'active',
    parent_id TEXT REFERENCES tasks(id),
    list_id TEXT NOT NULL REFERENCES lists(id),
    level INTEGER DEFAULT 0,
    position INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    archived_at TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tasks_parent ON tasks(parent_id);
CREATE INDEX idx_tasks_list ON tasks(list_id);
CREATE INDEX idx_tasks_status ON tasks(status);

-- Trigger to update modified_at
CREATE TRIGGER update_task_modified 
AFTER UPDATE ON tasks
BEGIN
    UPDATE tasks SET modified_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
```

## UI COMPONENTS (TEXTUAL)

```python
# ui/components.py

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Static, Header, Footer, Tree, TextArea
from textual.reactive import reactive

class TaskItem(Static):
    """Single task widget with nesting support."""
    
    DEFAULT_CSS = """
    TaskItem {
        padding: 0 1;
        height: 1;
    }
    
    TaskItem.level-0 {
        padding-left: 0;
        border-left: heavy $primary;
    }
    
    TaskItem.level-1 {
        padding-left: 3;
        border-left: medium $success;
    }
    
    TaskItem.level-2 {
        padding-left: 6;
        border-left: medium $accent;
    }
    
    TaskItem.selected {
        background: $surface;
        text-style: bold;
    }
    
    TaskItem.completed {
        text-style: strike;
        opacity: 0.6;
    }
    
    TaskItem.archived {
        opacity: 0.4;
        text-style: italic;
    }
    """

class Column(Vertical):
    """Column container with header and scrollable content."""
    
    title = reactive("Column")
    is_active = reactive(False)
    
    DEFAULT_CSS = """
    Column {
        width: 1fr;
        border: solid $primary;
        margin: 1;
    }
    
    Column.active {
        border: thick $accent;
        background: $surface;
    }
    
    Column > .column-header {
        height: 3;
        padding: 1;
        background: $panel;
        text-style: bold;
    }
    """

class TaskCreationModal(Container):
    """Modal for creating/editing tasks with notes."""
    
    DEFAULT_CSS = """
    TaskCreationModal {
        align: center middle;
        background: $background 80%;
        layer: modal;
    }
    
    TaskCreationModal > Container {
        width: 60;
        height: 20;
        background: $panel;
        border: thick $accent;
        padding: 2;
    }
    """

class MainApp(App):
    """Main application with three-column layout."""
    
    CSS = """
    /* One Monokai Theme Variables */
    $primary: #61afef;      /* Blue */
    $success: #98c379;      /* Green */  
    $accent: #c678dd;       /* Purple */
    $warning: #e5c07b;      /* Yellow */
    $error: #e06c75;        /* Red */
    $background: #282c34;   /* Dark background */
    $surface: #2c313c;      /* Slightly lighter */
    $panel: #3e4451;        /* Panel background */
    $text: #abb2bf;         /* Main text */
    $text-muted: #5c6370;   /* Muted text */
    """
```

## FILE STRUCTURE

```
taskui/
├── taskui.py               # Main entry point
├── config.py               # Configuration settings
├── models.py               # Data models
├── database.py             # SQLite operations
├── backup.py              # JSON export/import
├── printer.py             # Network printing
├── ui/
│   ├── __init__.py
│   ├── app.py            # Main Textual app
│   ├── components.py     # UI components
│   ├── modals.py         # Modal dialogs
│   ├── keybindings.py    # Keyboard handling
│   └── theme.py          # One Monokai theme
├── services/
│   ├── __init__.py
│   ├── task_service.py   # Task operations
│   └── list_service.py   # List operations
├── utils/
│   ├── __init__.py
│   └── formatting.py     # Text formatting
├── tests/
│   ├── test_models.py
│   ├── test_database.py
│   └── test_ui.py
└── data/
    ├── taskui.db         # SQLite database
    └── backups/          # JSON backups
```

## KEY IMPLEMENTATION DETAILS

### 1. NESTING CONSTRAINTS

```python
class NestingRules:
    """Enforce nesting constraints."""
    
    COLUMN1_MAX_LEVEL = 1  # Level 0 and 1 only
    COLUMN2_MAX_LEVEL = 2  # Level 0, 1, and 2
    
    @staticmethod
    def can_create_child(task: Task, in_column: int) -> bool:
        if in_column == 1:
            return task.level < NestingRules.COLUMN1_MAX_LEVEL
        elif in_column == 2:
            # Context-relative: check depth from Column1 parent
            return get_depth_from_column1_parent(task) < NestingRules.COLUMN2_MAX_LEVEL
        return False
```

### 2. COLUMN 2 DYNAMIC BEHAVIOR

```python
class Column2:
    """Column 2 shows children of Column 1 selection."""
    
    def update_from_column1_selection(self, task: Task):
        # Update header
        self.header = f"{task.title} Subtasks"
        
        # Load all descendants
        children = get_all_descendants(task.id)
        
        # Reset levels relative to this parent (start at 0)
        for child in children:
            child.display_level = calculate_relative_level(child, task)
```

### 3. KEYBOARD HANDLING

```python
KEYBINDINGS = {
    "n": "create_sibling",      # Same level as selected
    "c": "create_child",        # Child of selected
    "space": "toggle_complete", # Complete/uncomplete
    "a": "archive_task",        # Archive completed
    "p": "print_column",        # Print to thermal
    "tab": "next_column",       # Focus next column
    "shift+tab": "prev_column", # Focus previous column
    "up": "select_prev",        # Navigate up
    "down": "select_next",      # Navigate down
    "1-3": "switch_list",       # Switch lists
    "escape": "cancel",         # Cancel modal
    "enter": "confirm",         # Confirm modal
    "q": "quit",               # Quit application
}
```

### 4. JSON BACKUP SYSTEM

```python
# backup.py

async def export_to_json(db_path: str, output_path: str):
    """Export entire database to JSON with hierarchy preserved."""
    data = {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "lists": [],
        "tasks": []
    }
    
    # Export maintaining parent-child relationships
    async with aiosqlite.connect(db_path) as db:
        # ... export logic
        
async def import_from_json(json_path: str, db_path: str):
    """Import from JSON, recreating hierarchy."""
    # ... import logic

async def auto_backup(db_path: str, backup_dir: str):
    """Auto-backup on significant operations."""
    # Triggered on: complete task, archive, create, delete
```

### 5. NETWORK PRINTING

```python
# printer.py

class NetworkPrinter:
    """Handle network printing to Raspberry Pi print server."""
    
    def __init__(self, server_url: str, printer_name: str = "Epson_TM-T20III"):
        self.server_url = server_url
        self.printer_name = printer_name
    
    async def print_column(self, tasks: List[Task], column_name: str):
        """Format and send tasks to network printer."""
        
        # Format for 80mm thermal printer
        receipt = self.format_receipt(tasks, column_name)
        
        # Send to print server (IPP/CUPS or custom API)
        await self.send_to_printer(receipt)
    
    def format_receipt(self, tasks: List[Task], column_name: str) -> str:
        """Format tasks for thermal printer with proper escaping."""
        lines = []
        lines.append("=" * 32)
        lines.append(f"TASKUI - {column_name}")
        lines.append(datetime.now().strftime("%Y-%m-%d %H:%M"))
        lines.append("=" * 32)
        
        for task in tasks:
            indent = "  " * task.display_level
            status = "[✓]" if task.status == TaskStatus.COMPLETED else "[ ]"
            progress = f" ({task.progress_string()})" if task.child_count > 0 else ""
            lines.append(f"{indent}{status} {task.title}{progress}")
        
        lines.append("-" * 32)
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        lines.append(f"Total: {len(tasks)} | Done: {completed}")
        
        return "\n".join(lines)
```

## IMPLEMENTATION PHASES

### Phase 1: Core Foundation (MVP)
1. Set up project structure with Poetry/pip
2. Implement data models and SQLite database
3. Create basic three-column Textual UI
4. Implement task creation with nesting rules
5. Add keyboard navigation

### Phase 2: Task Management
1. Implement task completion toggle
2. Add progress indicators for parent tasks
3. Create task creation modal with notes
4. Implement Column 2 dynamic headers
5. Add archive functionality

### Phase 3: Polish & Persistence
1. Apply One Monokai theme completely
2. Add JSON backup/restore
3. Implement auto-save
4. Add list switching (1-3 keys)
5. Performance optimization

### Phase 4: Printing & Advanced
1. Network printer integration
2. Receipt formatting
3. Print preview in modal
4. Error handling and recovery
5. Configuration file support

## TESTING APPROACH

```python
# tests/test_nesting.py

import pytest
from unittest.mock import Mock, AsyncMock
from taskui.models import Task, TaskStatus
from taskui.services.nesting_rules import NestingRules

@pytest.mark.asyncio
async def test_column1_max_nesting():
    """Column 1 should only allow 2 levels."""
    task_l0 = create_task(level=0)
    task_l1 = create_task(level=1, parent_id=task_l0.id)
    
    # Should not allow creating child of level-1 in Column 1
    assert not NestingRules.can_create_child(task_l1, in_column=1)
    assert NestingRules.can_create_child(task_l0, in_column=1)

@pytest.mark.asyncio  
async def test_column2_context_relative():
    """Column 2 levels should be relative to Column 1 selection."""
    # Create hierarchy
    task_api = create_task(title="API Development", level=0)
    task_auth = create_task(title="Auth endpoints", level=1, parent_id=task_api.id)
    task_jwt = create_task(title="JWT", level=0, parent_id=task_auth.id)  # Level 0 in Column 2 context
    
    # When Auth endpoints is selected, JWT should appear as level 0 in Column 2
    assert calculate_relative_level(task_jwt, task_auth) == 0
```

## COMPREHENSIVE TESTING STRATEGY

### 1. TEST DEPENDENCIES

```python
# requirements-test.txt
pytest>=7.4.0
pytest-asyncio>=0.21.0      # Async test support
pytest-mock>=3.11.0         # Enhanced mocking
pytest-cov>=4.1.0           # Coverage reporting
pytest-textual-snapshot>=0.4.0  # Textual snapshot testing
pytest-timeout>=2.1.0       # Test timeouts
pytest-xdist>=3.3.0         # Parallel test execution
hypothesis>=6.0.0           # Property-based testing
faker>=19.0.0              # Fake data generation
freezegun>=1.2.0          # Time mocking
```

### 2. TESTING TEXTUAL UI

```python
# tests/test_ui.py

import pytest
from textual.pilot import Pilot
from taskui.ui.app import TaskUI

class TestTaskUI:
    """Test the main Textual application."""
    
    @pytest.mark.asyncio
    async def test_app_startup(self):
        """Test that app starts correctly."""
        app = TaskUI()
        async with app.run_test() as pilot:
            # Check that all three columns are present
            assert app.query_one("#column1")
            assert app.query_one("#column2")
            assert app.query_one("#column3")
            
            # Check list bar
            assert app.query_one(".list-bar")
    
    @pytest.mark.asyncio
    async def test_keyboard_navigation(self):
        """Test keyboard shortcuts."""
        app = TaskUI()
        async with app.run_test() as pilot:
            # Create a new task with 'N'
            await pilot.press("n")
            assert app.query_one(".modal")  # Modal should appear
            
            # Type task name
            await pilot.type("Test Task")
            await pilot.press("enter")
            
            # Verify task was created
            tasks = app.query(".task-item")
            assert len(tasks) == 1
            assert "Test Task" in tasks[0].text
    
    @pytest.mark.asyncio
    async def test_task_completion(self):
        """Test marking tasks complete."""
        app = TaskUI()
        async with app.run_test(size=(120, 30)) as pilot:
            # Create and select a task
            await create_test_task(pilot, "Complete me")
            
            # Press space to complete
            await pilot.press("space")
            
            # Check task is marked complete
            task = app.query_one(".task-item")
            assert "completed" in task.classes
    
    @pytest.mark.asyncio
    async def test_column_switching(self):
        """Test Tab navigation between columns."""
        app = TaskUI()
        async with app.run_test() as pilot:
            # Start in column 1
            assert app.focused_column == 1
            
            # Tab to column 2
            await pilot.press("tab")
            assert app.focused_column == 2
            
            # Tab to column 3
            await pilot.press("tab")
            assert app.focused_column == 3
            
            # Shift+Tab back
            await pilot.press("shift+tab")
            assert app.focused_column == 2

# Snapshot Testing for Visual Regression
def test_app_snapshot(snap_compare):
    """Test visual appearance hasn't changed."""
    assert snap_compare("taskui/ui/app.py", 
                        terminal_size=(120, 30),
                        press=["n", "escape"])  # Test with modal

# Test helper functions
async def create_test_task(pilot: Pilot, title: str, notes: str = ""):
    """Helper to create a task via UI."""
    await pilot.press("n")
    await pilot.type(title)
    await pilot.press("tab")  # Move to notes field
    await pilot.type(notes)
    await pilot.press("enter")
```

### 3. DATABASE TESTING

```python
# tests/conftest.py

import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from taskui.database import Base
from taskui.models import Task, TaskList

@pytest.fixture(scope="function")
async def in_memory_db():
    """Create in-memory SQLite database for testing."""
    # Use in-memory SQLite for fast, isolated tests
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    # Cleanup
    await engine.dispose()

@pytest.fixture
async def sample_tasks(in_memory_db):
    """Create sample task hierarchy."""
    session = in_memory_db
    
    # Create lists
    work_list = TaskList(name="Work", position=1)
    session.add(work_list)
    
    # Create task hierarchy
    task1 = Task(title="Sprint Planning", list_id=work_list.id, level=0)
    task2 = Task(title="Review backlog", parent_id=task1.id, level=1)
    
    session.add_all([task1, task2])
    await session.commit()
    
    return {"list": work_list, "tasks": [task1, task2]}

# tests/test_database.py

@pytest.mark.asyncio
async def test_task_creation(in_memory_db):
    """Test creating tasks in database."""
    session = in_memory_db
    
    task = Task(
        title="Test Task",
        notes="Test notes",
        list_id="test-list"
    )
    session.add(task)
    await session.commit()
    
    # Query back
    result = await session.execute(
        select(Task).where(Task.title == "Test Task")
    )
    saved_task = result.scalar_one()
    
    assert saved_task.title == "Test Task"
    assert saved_task.notes == "Test notes"
    assert saved_task.status == TaskStatus.ACTIVE

@pytest.mark.asyncio
async def test_cascade_operations(in_memory_db, sample_tasks):
    """Test parent-child relationships."""
    session = in_memory_db
    parent = sample_tasks["tasks"][0]
    
    # Add more children
    child2 = Task(title="Team sync", parent_id=parent.id, level=1)
    session.add(child2)
    await session.commit()
    
    # Query children
    result = await session.execute(
        select(Task).where(Task.parent_id == parent.id)
    )
    children = result.scalars().all()
    
    assert len(children) == 2
```

### 4. SERVICE LAYER TESTING

```python
# tests/test_services.py

import pytest
from unittest.mock import Mock, AsyncMock, patch
from taskui.services.task_service import TaskService
from taskui.services.printer_service import NetworkPrinter

class TestTaskService:
    """Test task business logic."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session
    
    @pytest.mark.asyncio
    async def test_create_task_with_nesting_check(self, mock_db_session):
        """Test task creation respects nesting limits."""
        service = TaskService(mock_db_session)
        
        # Mock parent at level 1 in Column 1
        parent = Mock(level=1, id="parent-id")
        mock_db_session.execute.return_value.scalar_one.return_value = parent
        
        # Should fail to create child in Column 1
        with pytest.raises(NestingLimitError):
            await service.create_child_task(
                parent_id="parent-id",
                title="Child",
                column=1
            )
    
    @pytest.mark.asyncio
    async def test_calculate_progress(self, mock_db_session):
        """Test parent progress calculation."""
        service = TaskService(mock_db_session)
        
        # Mock children: 2 complete, 1 active
        children = [
            Mock(status=TaskStatus.COMPLETED),
            Mock(status=TaskStatus.COMPLETED),
            Mock(status=TaskStatus.ACTIVE),
        ]
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = children
        
        progress = await service.calculate_progress("parent-id")
        assert progress == {"completed": 2, "total": 3, "percentage": 66}

class TestPrinterService:
    """Test thermal printer integration."""
    
    @pytest.mark.asyncio
    @patch('requests.post')
    async def test_print_receipt(self, mock_post):
        """Test receipt formatting and sending."""
        printer = NetworkPrinter("http://raspberrypi.local:631")
        
        tasks = [
            Mock(title="Task 1", level=0, status=TaskStatus.ACTIVE),
            Mock(title="Task 2", level=1, status=TaskStatus.COMPLETED),
        ]
        
        await printer.print_column(tasks, "Work Tasks")
        
        # Check that printer was called
        mock_post.assert_called_once()
        
        # Check receipt format
        call_args = mock_post.call_args
        receipt_data = call_args.kwargs.get('data', '')
        assert "Work Tasks" in receipt_data
        assert "[ ] Task 1" in receipt_data
        assert "  [✓] Task 2" in receipt_data
```

### 5. INTEGRATION TESTING

```python
# tests/test_integration.py

import pytest
from taskui.ui.app import TaskUI
from taskui.database import init_db

class TestFullWorkflow:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_task_workflow(self, tmp_path):
        """Test full create-complete-archive workflow."""
        # Use temporary database
        db_path = tmp_path / "test.db"
        await init_db(str(db_path))
        
        app = TaskUI(db_path=str(db_path))
        async with app.run_test(size=(120, 30)) as pilot:
            # Create parent task
            await pilot.press("n")
            await pilot.type("Sprint Planning")
            await pilot.press("enter")
            
            # Create child task
            await pilot.press("c")
            await pilot.type("Review backlog")
            await pilot.press("enter")
            
            # Navigate to child
            await pilot.press("down")
            
            # Complete child
            await pilot.press("space")
            
            # Archive completed
            await pilot.press("a")
            
            # Verify archive
            tasks = app.query(".task-item.archived")
            assert len(tasks) == 1
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_performance_with_many_tasks(self, in_memory_db):
        """Test performance with 1000+ tasks."""
        import time
        
        # Create many tasks
        tasks = []
        for i in range(1000):
            task = Task(title=f"Task {i}", list_id="test-list")
            tasks.append(task)
        
        in_memory_db.add_all(tasks)
        await in_memory_db.commit()
        
        # Test query performance
        start = time.time()
        result = await in_memory_db.execute(
            select(Task).where(Task.list_id == "test-list")
        )
        all_tasks = result.scalars().all()
        elapsed = time.time() - start
        
        assert len(all_tasks) == 1000
        assert elapsed < 0.2  # Should complete in < 200ms
```

### 6. PROPERTY-BASED TESTING

```python
# tests/test_properties.py

from hypothesis import given, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant

class TaskStateMachine(RuleBasedStateMachine):
    """Property-based testing for task operations."""
    
    def __init__(self):
        super().__init__()
        self.tasks = {}
        self.next_id = 1
    
    @rule(title=st.text(min_size=1, max_size=200))
    def create_task(self, title):
        """Create a task with valid title."""
        task_id = str(self.next_id)
        self.tasks[task_id] = {
            "title": title,
            "level": 0,
            "children": []
        }
        self.next_id += 1
        return task_id
    
    @rule(
        parent_id=st.sampled_from(lambda self: list(self.tasks.keys()) if self.tasks else [None]),
    )
    def create_child(self, parent_id):
        """Create child respecting nesting limits."""
        if parent_id and self.tasks[parent_id]["level"] < 2:
            child_id = self.create_task("Child")
            self.tasks[child_id]["level"] = self.tasks[parent_id]["level"] + 1
            self.tasks[parent_id]["children"].append(child_id)
    
    @invariant()
    def check_nesting_depth(self):
        """Verify no task exceeds max nesting."""
        for task in self.tasks.values():
            assert task["level"] <= 2

# Run with: pytest tests/test_properties.py --hypothesis-show-statistics
```

### 7. TEST CONFIGURATION

```python
# pytest.ini

[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto

# Markers
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    ui: marks tests that require UI
    
# Coverage
addopts = 
    --cov=taskui
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
    -v

# Timeouts
timeout = 10
timeout_method = thread

# Parallel execution
workers = auto

# pyproject.toml

[tool.coverage.run]
source = ["taskui"]
omit = [
    "*/tests/*",
    "*/test_*.py",
    "*/__init__.py",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]

# tox.ini

[tox]
envlist = py310, py311, py312, lint, type

[testenv]
deps = 
    -r requirements.txt
    -r requirements-test.txt
commands = 
    pytest {posargs}

[testenv:lint]
deps = 
    black
    flake8
    isort
commands = 
    black --check taskui tests
    flake8 taskui tests
    isort --check taskui tests

[testenv:type]
deps = 
    mypy
    types-aiofiles
commands = 
    mypy taskui
```

### 8. TESTING BEST PRACTICES

```python
# tests/factories.py

"""Test data factories for consistent test data."""

import factory
from factory import Faker, SubFactory, LazyAttribute
from taskui.models import Task, TaskList

class TaskListFactory(factory.Factory):
    """Factory for creating test lists."""
    class Meta:
        model = TaskList
    
    id = factory.Sequence(lambda n: f"list-{n}")
    name = Faker("word")
    position = factory.Sequence(lambda n: n)

class TaskFactory(factory.Factory):
    """Factory for creating test tasks."""
    class Meta:
        model = Task
    
    id = factory.Sequence(lambda n: f"task-{n}")
    title = Faker("sentence", nb_words=4)
    notes = Faker("text", max_nb_chars=200)
    list_id = LazyAttribute(lambda obj: TaskListFactory().id)
    level = 0
    position = factory.Sequence(lambda n: n)

# Usage in tests:
def test_with_factory():
    task = TaskFactory(title="Custom Title", level=1)
    assert task.title == "Custom Title"
    assert task.level == 1
```

### 9. PERFORMANCE & MONITORING

```python
# tests/test_performance.py

import pytest
import time
from memory_profiler import profile

class TestPerformance:
    """Performance and resource usage tests."""
    
    @pytest.mark.benchmark
    def test_navigation_speed(self, benchmark):
        """Benchmark navigation operations."""
        app = TaskUI()
        
        def navigate():
            app.move_cursor_down()
            app.move_cursor_up()
        
        # Should complete in < 50ms
        result = benchmark(navigate)
        assert result.stats.median < 0.05
    
    @pytest.mark.memory
    @profile
    def test_memory_usage_with_large_dataset(self):
        """Test memory doesn't leak with many tasks."""
        tasks = []
        for i in range(10000):
            task = Task(title=f"Task {i}")
            tasks.append(task)
        
        # Process tasks
        for task in tasks:
            task.progress_string()
        
        # Memory should stay under 50MB
        # (checked by memory_profiler decorator)
```

### 10. CONTINUOUS TESTING

```yaml
# .github/workflows/test.yml

name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run tests
      run: |
        pytest --cov=taskui --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## DEVELOPMENT COMMANDS

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt  # Testing dependencies

# Run all tests
pytest

# Run with coverage
pytest --cov=taskui --cov-report=html

# Run specific test categories
pytest -m "not slow"           # Skip slow tests
pytest -m unit                  # Only unit tests
pytest -m integration           # Only integration tests
pytest tests/test_ui.py         # Specific test file

# Run tests in parallel
pytest -n auto                  # Use all CPU cores

# Run with verbose output
pytest -vv

# Run Textual UI tests with snapshot update
pytest --snapshot-update

# Watch mode for development
ptw -- --testmon               # Rerun tests on file changes

# Run in development mode with hot reload
textual run --dev taskui.py

# Run with textual console for debugging
textual console  # In one terminal
textual run --dev taskui.py  # In another terminal

# Serve as web app (new in Textual 6.x)
textual serve taskui.py

# Run tests with tox (multiple Python versions)
tox

# Run specific tox environment
tox -e py311                   # Python 3.11
tox -e lint                    # Linting only
tox -e type                    # Type checking

# Build executable
pyinstaller --onefile --name taskui taskui.py

# Create backup
python -m taskui backup --output backups/

# Restore from backup
python -m taskui restore --input backups/backup.json
```

## TESTING QUICK REFERENCE

### Essential Test Commands

```bash
# Quick test during development
pytest tests/test_models.py::TestTask::test_creation -vv

# Test with debugging
pytest --pdb  # Drop into debugger on failure

# Generate test coverage report
pytest --cov=taskui --cov-report=html
open htmlcov/index.html  # View in browser

# Profile test performance
pytest --profile --profile-svg
```

### Testing Tips for TaskUI

1. **Use in-memory SQLite for speed**: Tests run 10x faster
2. **Mock network calls**: Don't actually hit the printer server in tests
3. **Use factories for test data**: Consistent, maintainable test data
4. **Test keyboard shortcuts thoroughly**: Core UX feature
5. **Snapshot test the UI**: Catch visual regressions early
6. **Test nesting rules extensively**: Core business logic
7. **Use async fixtures**: Match the async nature of Textual
8. **Test with different terminal sizes**: Ensure responsive layout

## CONFIGURATION

```python
# config.py

from pydantic_settings import BaseSettings  # Note: pydantic_settings for V2

class Settings(BaseSettings):
    # Database
    db_path: str = "data/taskui.db"
    auto_backup: bool = True
    backup_dir: str = "data/backups"
    
    # UI
    theme: str = "one_monokai"
    min_terminal_width: int = 120
    min_terminal_height: int = 30
    
    # Printer
    printer_server_url: str = "http://raspberrypi.local:631"
    printer_name: str = "Epson_TM-T20III"
    printer_enabled: bool = True
    
    # Behavior
    auto_save_delay_ms: int = 500
    max_title_length: int = 200
    
    model_config = {  # Pydantic V2 config
        "env_file": ".env",
        "env_prefix": "TASKUI_",
        "case_sensitive": False
    }
```

## ERROR HANDLING

```python
class TaskUIError(Exception):
    """Base exception for TaskUI."""
    pass

class NestingLimitError(TaskUIError):
    """Raised when max nesting depth exceeded."""
    def __init__(self, level: int, column: int):
        super().__init__(
            f"Maximum nesting level {level} reached in Column {column}. "
            f"Cannot create children for this task."
        )

class PrinterError(TaskUIError):
    """Raised when printing fails."""
    pass
```

## PERFORMANCE REQUIREMENTS

- Task navigation: < 50ms response time
- Task creation: < 100ms including database write
- Column switching: < 30ms
- List switching: < 200ms (includes data load)
- Startup time: < 500ms to interactive
- Memory usage: < 50MB for 1000 tasks

## DESIGN INSPIRATION NOTES

Based on awesome-tuis examples, prioritize:
1. **Clear visual hierarchy** - Like lazygit's tree view
2. **Smooth animations** - Like btop's transitions  
3. **Intuitive keybinds** - Like vim/helix patterns
4. **Rich formatting** - Like glow's markdown rendering
5. **Responsive layout** - Like k9s adaptive columns

## CRITICAL IMPLEMENTATION NOTES

1. **Column 2 is context-dependent** - Always shows children of Column 1 selection
2. **Nesting levels are relative** - Column 2 Level 0 = children of Column 1 selection
3. **Progress indicators don't auto-complete parents** - Manual completion only
4. **Archive vs Delete** - Archive keeps history, no delete in MVP
5. **Print formatting** - Must handle tree lines in plain text for thermal printer

---

This specification is optimized for AI-assisted development. Each section provides concrete implementation details without ambiguity. Start with Phase 1 and iterate.