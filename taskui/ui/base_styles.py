"""Shared CSS styles for TaskUI components.

This module provides reusable CSS definitions for common UI patterns like
modals, buttons, and form elements. All styles use theme constants from theme.py
to ensure consistency and maintainability.

Overview
--------
Base styles are pre-configured CSS strings that can be imported and used by
components to maintain visual consistency across the application. Instead of
duplicating button or modal styling in every component, import the relevant
base style and extend it with component-specific styles.

Available Style Categories
--------------------------
1. **MODAL_BASE_CSS**: Complete modal dialog styling
   - Semi-transparent overlay
   - Centered container with border
   - Header, inputs, buttons
   - Empty state messages

2. **BUTTON_BASE_CSS**: Button states and variants
   - Default, hover, disabled states
   - Success variant (green) for confirmations
   - Error variant (pink) for cancellations

3. **SEMANTIC_TEXT_CSS**: Text color classes by meaning
   - .text-success (green)
   - .text-warning (pink)
   - .text-info (cyan)
   - .text-dimmed (gray)

4. **BACKGROUND_STATE_CSS**: Background interaction states
   - .bg-hover (semi-transparent overlay)
   - .bg-selected (selection background)
   - .bg-transparent

5. **BASE_STYLES**: All of the above combined

Usage Examples
--------------
### Example 1: Using modal base styles

    from taskui.ui.base_styles import MODAL_BASE_CSS
    from taskui.ui.theme import LEVEL_1_COLOR

    class MyModal(ModalScreen):
        # Start with base modal styles, then add custom styles
        DEFAULT_CSS = MODAL_BASE_CSS + f'''
        MyModal .custom-element {{
            color: {LEVEL_1_COLOR};
            padding: 1;
        }}
        '''

### Example 2: Using button base styles

    from taskui.ui.base_styles import BUTTON_BASE_CSS

    class MyWidget(Widget):
        DEFAULT_CSS = BUTTON_BASE_CSS + '''
        MyWidget {
            layout: vertical;
        }
        '''

        def compose(self) -> ComposeResult:
            yield Button("Save", classes="success")  # Green button
            yield Button("Cancel", classes="error")  # Pink button

### Example 3: Using semantic text classes

    from taskui.ui.base_styles import SEMANTIC_TEXT_CSS

    class StatusPanel(Widget):
        DEFAULT_CSS = SEMANTIC_TEXT_CSS + '''
        StatusPanel {
            padding: 1;
        }
        '''

        def render(self) -> RenderableType:
            return Static("[.text-success]✓ Complete[/]", classes="text-success")

### Example 4: Combining multiple base styles

    from taskui.ui.base_styles import BASE_STYLES

    class ComplexWidget(Widget):
        # Get all base styles at once
        DEFAULT_CSS = BASE_STYLES + '''
        ComplexWidget {
            border: solid;
        }
        '''

Design Philosophy
-----------------
- **DRY Principle**: Don't repeat styling across components
- **Consistency**: All modals/buttons look the same
- **Theme Integration**: All colors from theme.py constants
- **Extensibility**: Easy to add component-specific styles

See Also
--------
- theme.py: Color constants and theme documentation
- README.md: Complete theming guide with examples
"""

from .theme import (
    BACKGROUND,
    FOREGROUND,
    BORDER,
    SELECTION,
    COMMENT,
    LEVEL_0_COLOR,
    LEVEL_1_COLOR,
    LEVEL_2_COLOR,
    MODAL_OVERLAY_BG,
    HOVER_OPACITY,
    with_alpha,
)


# Base Modal Styles
# Used by TaskCreationModal, ArchiveModal, and other modal dialogs
MODAL_BASE_CSS = f"""
/* Modal overlay - dark background behind modal */
ModalScreen {{
    align: center middle;
    background: {MODAL_OVERLAY_BG};
}}

/* Modal container - the actual modal box */
ModalScreen > Container {{
    background: {BACKGROUND};
    border: thick {LEVEL_0_COLOR};
    padding: 1 2;
}}

/* Modal header styling */
ModalScreen .modal-header {{
    color: {LEVEL_0_COLOR};
    border-bottom: solid {BORDER};
    text-style: bold;
    padding: 0 0 1 0;
}}

/* Field labels in forms */
ModalScreen .field-label {{
    color: {FOREGROUND};
    padding: 1 0 0 0;
}}

/* Input fields */
ModalScreen Input {{
    background: {BORDER};
    color: {FOREGROUND};
    border: solid {SELECTION};
    padding: 0 1;
}}

ModalScreen Input:focus {{
    border: solid {LEVEL_0_COLOR};
}}

/* Text areas */
ModalScreen TextArea {{
    background: {BORDER};
    color: {FOREGROUND};
    border: solid {SELECTION};
    padding: 0 1;
}}

ModalScreen TextArea:focus {{
    border: solid {LEVEL_0_COLOR};
}}

/* Empty state messages */
ModalScreen .empty-message {{
    color: {COMMENT};
    text-style: italic;
    text-align: center;
    padding: 2;
}}

/* Informational text */
ModalScreen .info-text {{
    color: {COMMENT};
    text-align: center;
    padding: 0 0 1 0;
}}
"""


# Base Button Styles
# Provides consistent button styling across all components
BUTTON_BASE_CSS = f"""
/* Default button styling */
Button {{
    background: {SELECTION};
    color: {FOREGROUND};
    border: solid {BORDER};
    margin: 0 1;
    min-width: 15;
    height: 3;
}}

/* Button hover state */
Button:hover {{
    background: {BORDER};
    border: solid {LEVEL_0_COLOR};
}}

/* Success variant (green) - used for save, create, confirm actions */
Button.success {{
    border: solid {LEVEL_1_COLOR};
}}

Button.success:hover {{
    background: {LEVEL_1_COLOR};
    color: {BACKGROUND};
}}

/* Error/Cancel variant (pink) - used for cancel, delete, close actions */
Button.error {{
    border: solid {LEVEL_2_COLOR};
}}

Button.error:hover {{
    background: {LEVEL_2_COLOR};
    color: {BACKGROUND};
}}

/* Disabled button state */
Button:disabled {{
    opacity: 0.5;
    border: solid {BORDER};
}}
"""


# Semantic Text Color Classes
# Use these for consistent text coloring based on meaning
SEMANTIC_TEXT_CSS = f"""
/* Success messages and positive indicators */
.text-success {{
    color: {LEVEL_1_COLOR};
}}

/* Warning messages */
.text-warning {{
    color: {LEVEL_2_COLOR};
}}

/* Informational text */
.text-info {{
    color: {LEVEL_0_COLOR};
}}

/* Dimmed/secondary text */
.text-dimmed {{
    color: {COMMENT};
}}

/* Emphasized text */
.text-emphasis {{
    color: {FOREGROUND};
    text-style: bold;
}}
"""


# Background State Classes
# Common background states for interactive elements
BACKGROUND_STATE_CSS = f"""
/* Hover background overlay */
.bg-hover {{
    background: {with_alpha(SELECTION, HOVER_OPACITY)};
}}

/* Selected background */
.bg-selected {{
    background: {SELECTION};
}}

/* Transparent background */
.bg-transparent {{
    background: transparent;
}}
"""


# ============================================================================
# COMBINED EXPORT
# ============================================================================
# All base styles combined into a single string for convenience.
# Import this when a component needs multiple style categories.
#
# Usage:
#     from taskui.ui.base_styles import BASE_STYLES
#
#     class MyWidget(Widget):
#         DEFAULT_CSS = BASE_STYLES + '''
#         MyWidget { layout: vertical; }
#         '''

BASE_STYLES = MODAL_BASE_CSS + BUTTON_BASE_CSS + SEMANTIC_TEXT_CSS + BACKGROUND_STATE_CSS
