"""One Monokai color theme for TaskUI.

This module defines the One Monokai color scheme with level-specific accent colors
for task hierarchy visualization. All UI components reference these constants via
f-string interpolation in their CSS definitions, providing a single source of truth
for the application's visual styling.

Theme Architecture
------------------
The theme system follows these design principles:

1. **Centralization**: All color constants defined in one module
2. **Dynamic CSS**: Components use f-string interpolation to reference constants
3. **Consistency**: Standardized interaction states (hover, focus, disabled)
4. **Semantic naming**: Colors named by purpose, not appearance
5. **Hierarchy support**: Three distinct accent colors for visual nesting

Color Categories
----------------
- **Base colors**: Background, foreground, selection, borders
- **Hierarchy colors**: Level-specific accent colors (cyan, green, pink)
- **Status colors**: Completion and archive states
- **Interactive states**: Modal overlays, hover effects, focus indicators
- **Additional colors**: Warnings, highlights, informational text

Usage in Components
-------------------
Components import theme constants and use them in CSS via f-strings:

    from taskui.ui.theme import BACKGROUND, LEVEL_0_COLOR, with_alpha

    class MyWidget(Widget):
        DEFAULT_CSS = f'''
        MyWidget {{
            background: {BACKGROUND};
            border: thick {LEVEL_0_COLOR};
        }}
        MyWidget:hover {{
            background: {with_alpha(SELECTION, HOVER_OPACITY)};
        }}
        '''

Customization
-------------
To create a custom theme:

1. Modify the color constants in this file
2. Run the application to see changes immediately
3. All components update automatically via f-string interpolation

Example - Creating a light theme:
    BACKGROUND = "#FFFFFF"
    FOREGROUND = "#000000"
    LEVEL_0_COLOR = "#0066CC"  # Blue
    LEVEL_1_COLOR = "#00AA00"  # Green
    LEVEL_2_COLOR = "#CC0066"  # Magenta

See Also
--------
- base_styles.py: Reusable CSS patterns using these theme constants
- README.md: Complete theming documentation and examples
"""

from rich.style import Style
from rich.theme import Theme


# ============================================================================
# BASE COLORS
# ============================================================================
# Core colors used throughout the application for backgrounds, text, and UI
# elements. These form the foundation of the One Monokai color scheme.

BACKGROUND = "#272822"  # Main application background (dark charcoal)
FOREGROUND = "#F8F8F2"  # Primary text color (off-white)
SELECTION = "#49483E"   # Selected item background (medium gray)
COMMENT = "#75715E"     # Secondary/dimmed text (muted brown-gray)
BORDER = "#3E3D32"      # Borders and dividers (dark gray-green)


# ============================================================================
# HIERARCHY COLORS
# ============================================================================
# Level-specific accent colors for visual task hierarchy. Each nesting level
# has a distinct color to make the structure clear at a glance.

LEVEL_0_COLOR = "#66D9EF"  # Cyan/Blue - Top-level tasks (primary)
LEVEL_1_COLOR = "#A6E22E"  # Green - First nesting level (secondary)
LEVEL_2_COLOR = "#F92672"  # Pink/Red - Second nesting level (tertiary)


# ============================================================================
# ADDITIONAL UI COLORS
# ============================================================================
# Supplementary colors for warnings, highlights, and informational elements.

YELLOW = "#E6DB74"   # Highlights and incomplete percentages
ORANGE = "#FD971F"   # Warnings and archive indicators
RED = "#F92672"      # Errors and critical warnings (matches LEVEL_2_COLOR)
PURPLE = "#AE81FF"   # Informational text
WHITE = "#F8F8F2"    # Pure white (same as FOREGROUND)


# ============================================================================
# STATUS COLORS
# ============================================================================
# Colors indicating task completion and archive states.

COMPLETE_COLOR = "#75715E"  # Dimmed gray for completed tasks (matches COMMENT)
ARCHIVE_COLOR = "#49483E"   # Dimmed background for archived tasks (matches SELECTION)


# ============================================================================
# INTERACTION STATES
# ============================================================================
# Colors and opacity values for interactive UI elements (modals, hovers, focus).

MODAL_OVERLAY_BG = "#27282280"  # Semi-transparent dark overlay (50% opacity)
HOVER_OPACITY = "20"            # Hover effect transparency (hex: ~12% opacity)
FOCUS_COLOR = LEVEL_0_COLOR     # Focus indicator color (cyan, matches level 0)
DISABLED_OPACITY = "0.5"        # Disabled button opacity (50%)


# ============================================================================
# RICH THEME OBJECT
# ============================================================================
# Pre-configured Rich theme for use with Textual's rich text rendering.
# These named styles can be used in Rich markup throughout the application.
#
# Usage in Rich markup:
#     text.append("Task", style="level_0")  # Uses LEVEL_0_COLOR
#     text.append("Warning!", style="warning")  # Uses ORANGE

ONE_MONOKAI_THEME = Theme({
    "background": f"on {BACKGROUND}",  # Background color style
    "foreground": FOREGROUND,           # Default text color
    "selection": f"on {SELECTION}",     # Selection background
    "border": BORDER,                   # Border color
    "level_0": LEVEL_0_COLOR,           # Top-level task color (cyan)
    "level_1": LEVEL_1_COLOR,           # Nested task color (green)
    "level_2": LEVEL_2_COLOR,           # Deep nested color (pink)
    "complete": COMPLETE_COLOR,         # Completed task color
    "archive": ARCHIVE_COLOR,           # Archived task color
    "highlight": YELLOW,                # Highlight color
    "warning": ORANGE,                  # Warning color
    "info": PURPLE,                     # Info color
})


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_level_color(level: int) -> str:
    """Get the accent color for a specific task nesting level.

    This function maps task nesting levels to their corresponding accent colors,
    providing visual distinction for task hierarchy. Levels outside the defined
    range (0-2) fall back to the default FOREGROUND color.

    Args:
        level: The task nesting level (0, 1, or 2)
            - Level 0: Top-level tasks (cyan)
            - Level 1: First nesting (green)
            - Level 2: Second nesting (pink)

    Returns:
        Hex color string for the specified level. Returns FOREGROUND for
        undefined levels (graceful degradation).

    Examples:
        >>> get_level_color(0)
        '#66D9EF'  # Cyan
        >>> get_level_color(1)
        '#A6E22E'  # Green
        >>> get_level_color(99)
        '#F8F8F2'  # FOREGROUND (fallback)

    Usage in components:
        level_color = get_level_color(task.level)
        text.append(task.title, style=level_color)
    """
    colors = {
        0: LEVEL_0_COLOR,
        1: LEVEL_1_COLOR,
        2: LEVEL_2_COLOR,
    }
    return colors.get(level, FOREGROUND)


def get_level_style(level: int) -> Style:
    """Get a Rich Style object for a specific task nesting level.

    Convenience function that wraps get_level_color() in a Rich Style object,
    making it easy to apply level-specific colors in Rich text rendering.

    Args:
        level: The task nesting level (0, 1, or 2)

    Returns:
        Rich Style object with the appropriate color for the level.

    Examples:
        >>> style = get_level_style(0)
        >>> text.append("Top-level task", style=style)

    See Also:
        get_level_color(): For getting just the hex color string
    """
    return Style(color=get_level_color(level))


def with_alpha(color: str, alpha: str) -> str:
    """Add alpha transparency to a hex color.

    Appends an alpha channel to a hex color code, enabling semi-transparent
    colors for hover effects, overlays, and other UI states. The alpha value
    is provided as a hex string (00-FF).

    Args:
        color: Base hex color string (e.g., '#272822')
        alpha: Alpha value as 2-digit hex string:
            - '00': Fully transparent (0%)
            - '20': Subtle transparency (~12%)
            - '80': Half transparent (50%)
            - 'FF': Fully opaque (100%)

    Returns:
        Color with alpha channel appended (8-digit hex color code).

    Examples:
        >>> with_alpha(SELECTION, HOVER_OPACITY)
        '#49483E20'  # Selection color with 20% opacity

        >>> with_alpha(BACKGROUND, '80')
        '#27282280'  # Background at 50% opacity

        >>> with_alpha(LEVEL_0_COLOR, 'FF')
        '#66D9EFFF'  # Level 0 color fully opaque

    Usage in CSS:
        DEFAULT_CSS = f'''
        MyWidget:hover {{
            background: {with_alpha(SELECTION, HOVER_OPACITY)};
        }}
        '''

    Note:
        The alpha value is in hexadecimal (00-FF), not decimal (0-255).
        Common values: 20 (~12%), 40 (~25%), 80 (50%), CC (~80%), FF (100%)
    """
    return f"{color}{alpha}"
