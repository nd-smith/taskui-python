# Architecture Overview

## Project Structure
```
taskui-python/
├── taskui/              # Main application package
│   ├── __main__.py      # Application entry point
│   ├── models.py        # Pydantic data models
│   ├── database.py      # SQLAlchemy database layer
│   ├── services/        # Business logic
│   │   ├── task_service.py
│   │   ├── list_service.py
│   │   └── nesting_rules.py
│   └── ui/              # Textual UI components
│       ├── app.py       # Main application
│       ├── theme.py     # One Monokai theme
│       ├── keybindings.py # Keyboard shortcuts
│       └── components/  # UI widgets
│           ├── task_item.py
│           ├── column.py
│           ├── detail_panel.py
│           ├── task_modal.py
│           └── list_bar.py
├── tests/               # Test suite
└── docs/                # Documentation
```

## Key Components

### Data Layer
- **models.py**: Pydantic models for data validation
- **database.py**: SQLAlchemy ORM for SQLite database
- **schema.sql**: Database schema

### Business Logic Layer
- **services/task_service.py**: Task CRUD operations
- **services/list_service.py**: List management
- **services/nesting_rules.py**: Hierarchical nesting validation

### UI Layer
- **ui/app.py**: Main Textual application
- **ui/theme.py**: One Monokai color scheme
- **ui/keybindings.py**: Keyboard shortcut definitions
- **ui/components/**: Reusable UI widgets

### UI Components
- **column.py**: Three-column layout implementation
- **task_item.py**: Individual task rendering
- **detail_panel.py**: Task details display
- **task_modal.py**: Modal dialogs for task creation/editing
- **list_bar.py**: List selection bar

## Data Flow
1. User input → UI components
2. UI components → Services (business logic)
3. Services → Database layer
4. Database → Services → UI (refresh)

## Nesting Rules
- **Column 1**: Max 2 levels (Level 0 → Level 1)
- **Column 2**: Max 3 levels (Level 0 → Level 1 → Level 2)
- Context-relative levels in Column 2
