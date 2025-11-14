# Feature Specification: MVP Core - Nested Hierarchy Task System (Updated)

**Feature Branch**: `001-mvp-core`
**Created**: 2025-11-12
**Status**: Updated with Clarified Nesting
**Last Modified**: 2025-11-14

## Nesting Behavior Clarification

### Column 1 - Tasks
- **Maximum nesting**: 2 levels (Level 0 → Level 1)
- **Example**: Sprint Planning (Level 0) → Review backlog (Level 1)
- **Restriction**: Cannot create children for Level 1 tasks in Column 1

### Column 2 - Subtasks
- **Dynamic header**: Shows "[Parent Task] Subtasks" based on Column 1 selection
- **Maximum visible nesting**: 3 levels (Level 0 → Level 1 → Level 2)
- **Context-relative display**: Children of selected Column 1 task appear starting at Level 0 in Column 2
- **Example**: When "API Development" (Level 0) is selected in Column 1:
  - Column 2 shows: Auth endpoints (Level 0) → Session management (Level 1) → Redis setup (Level 2)
- **Example**: When "Auth endpoints" (Level 1) is selected in Column 1:
  - Column 2 shows: Session management (Level 0) → Redis setup (Level 1) → Cache config (Level 2)

## Updated Requirements

### Functional Requirements

- **FR-001**: System MUST display three distinct columns: Tasks (Column 1), Subtasks (Column 2), Details (Column 3)
- **FR-002**: Column 1 MUST support maximum 2 levels of nesting (Level 0 and Level 1 only)
- **FR-003**: Column 2 MUST support maximum 3 levels of visible nesting (Level 0, Level 1, Level 2)
- **FR-004**: Column 2 header MUST dynamically show "[Parent Task Name] Subtasks"
- **FR-005**: System MUST allow task creation via 'N' key (creates sibling at same level)
- **FR-006**: System MUST allow child task creation via 'C' key when any task is selected
- **FR-007**: System MUST enforce maximum nesting depth (2 levels in Column 1, 3 levels in Column 2)
- **FR-008**: Column 2 MUST show children of selected Column 1 task with context-relative levels
- **FR-009**: Task creation modal MUST include optional notes field
- **FR-010**: System MUST support archive functionality via 'A' key
- **FR-011**: Column 3 MUST display detailed information for the currently selected task
- **FR-012**: Users MUST be able to navigate within columns using Up/Down arrow keys
- **FR-013**: Users MUST be able to navigate between columns using Tab (forward) and Shift+Tab (backward)
- **FR-014**: Users MUST be able to toggle task completion status using Space key
- **FR-015**: System MUST support multiple lists switchable via number keys 1-3
- **FR-016**: System MUST display list tabs in list bar with active/inactive states
- **FR-017**: System MUST show completion percentage and archive count in trash icon
- **FR-018**: System MUST persist all task data to SQLite database with auto-save
- **FR-019**: System MUST use One Monokai color theme with level-specific accent colors
- **FR-020**: System MUST respond to all user inputs within 100 milliseconds
- **FR-021**: System MUST display visual hierarchy using tree lines, indentation, and border colors
- **FR-022**: System MUST show obvious focus states with column highlighting and border emphasis
- **FR-023**: System MUST support printing current column to Epson TM-T20III thermal printer via 'P' key
- **FR-024**: Column 3 detail panel MUST show complete hierarchy from root task
- **FR-025**: Parent tasks MUST show progress indicators without auto-completion

### Key Entities

- **Task**: Represents a single actionable item with properties:
  - Unique identifier
  - Title (text content)
  - Completion status (complete/incomplete)
  - Archived status (active/archived)
  - Parent task reference (optional, for nesting)
  - Nesting level (Column 1: 0-1, Column 2: 0-2)
  - Position/order within parent
  - Creation timestamp
  - Completion timestamp (optional)
  - Archive timestamp (optional)
  - Notes/description text
  - List reference (which list it belongs to)

### Updated Keyboard Shortcuts

- **N**: Create new sibling task at same level
- **C**: Create new child task (disabled at max nesting)
- **Space**: Toggle task completion
- **A**: Archive completed task
- **P**: Print current column to thermal printer
- **Tab**: Navigate forward between columns
- **Shift+Tab**: Navigate backward between columns
- **↑/↓**: Navigate within column
- **1-3**: Switch between lists
- **Esc**: Cancel modal/operation
- **Enter**: Confirm modal/operation

### User Story Updates

**Task Creation Modal Enhancement**:
- Modal includes task name field (required)
- Modal includes notes field (optional)
- Modal displays context (creating sibling vs child, current level)

**Archive Functionality**:
- Users can press 'A' to archive completed tasks
- Archived tasks show with 📦 icon and reduced opacity
- Trash icon displays completion percentage and archive count
- Archived tasks remain visible but de-emphasized

**Column 2 Dynamic Headers**:
- Header updates to show "[Parent] Subtasks" based on Column 1 selection
- Provides clear context for what's displayed in Column 2
- Examples: "Sprint Planning Subtasks", "Auth endpoints Subtasks"

### Success Criteria

- **SC-001**: Users understand Column 1 max 2-level and Column 2 max 3-level nesting without documentation
- **SC-002**: Column 2 header clearly indicates which parent's children are displayed
- **SC-003**: Task creation modal with notes field improves task context capture
- **SC-004**: Archive functionality reduces visual clutter while preserving task history
- **SC-005**: All keyboard shortcuts respond within 100 milliseconds
- **SC-006**: Visual hierarchy is immediately clear through indentation and tree lines
- **SC-007**: Parent task progress indicators provide completion visibility without auto-completion