# TaskUI Requirements

## Core Purpose
**Frictionless workflow: thought → task → physical kanban card in 2 seconds**

The app exists to support a physical bulletin board workflow with thermal printer output.

## Essential Features

### 1. Task Management
- **Hierarchy**: Max 4 levels of nesting
- **Fields**: Title, notes, completion status
- **Operations**: Create, edit, delete, complete/uncomplete, restore deleted

### 2. Two-Column Display
- **Column 1**: High-level view (shows shallow tasks for mental clarity)
- **Column 2**: Drill-down view (shows all descendants of selected task)
- **Purpose**: Mental model - broad overview → focused details

### 3. Multiple Lists
- **Use case**: Separate projects, work/personal, etc.
- **Constraint**: Lists are independent containers, no special per-list rules
- **Justification**: Useful organization, low complexity cost

### 4. Thermal Printing (CORE FEATURE)
- **Printer**: ESC/POS thermal printer
- **Transport**: AWS SQS (workaround for VPN-blocked direct network access)
- **Security**: AES-256-GCM encryption (corporate environment requirement)
- **Workflow**: Select task → press P → physical card prints
- **Print content**: Task + all children as single kanban card with auto-cut

### 5. Deleted Task Recovery
- **Current**: Archive system
- **Desired**: Simpler "trash/restore" functionality
- **Requirement**: UI to browse and restore deleted tasks

### 6. Theming
- **Current**: 3 pre-built themes (Dracula, Nord, Tokyo Night)
- **Desired**: Easy CSS system for creating themes, remove pre-builts
- **Requirement**: Simple way to customize colors/appearance

## Future Features (Design Considerations)

### Phase 2
- **Additional task fields**: URLs, Outlook email links
- **Diary/Status updates**: Quick friction-less status notes on tasks
  - Example: "waiting for Jeff to email back"
  - Must be fast to add
- **Notepad**: Scratch space for notes during calls
  - May link to tasks later
  - Needs to be instantly accessible

## Non-Requirements

### Explicitly NOT Needed
- Theoretical deep nesting (10+ levels)
- Column-specific data validation rules
- Multiple pre-built themes
- Separate archive vs delete workflows

## Constraints

### Technical
- Python 3.10+
- Textual TUI framework
- SQLite async database
- VPN environment (requires cloud queue for printer)

### User Experience
- **Speed is critical**: 2-second target from thought to action
- **Keyboard-driven**: No mouse required
- **Visual clarity**: Physical kanban metaphor
