"""Shared CSS styles for TaskUI components.

This module provides reusable CSS definitions for common UI patterns like
modals, buttons, and form elements. All styles use theme constants from theme.py
to ensure consistency and maintainability.
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


# Combined base styles export
# Import this in components that use multiple base style patterns
BASE_STYLES = MODAL_BASE_CSS + BUTTON_BASE_CSS + SEMANTIC_TEXT_CSS + BACKGROUND_STATE_CSS
