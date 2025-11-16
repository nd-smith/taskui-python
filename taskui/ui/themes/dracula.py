"""Dracula color theme for TaskUI.

Official Dracula theme adapted for TaskUI's task management interface.
Based on the Dracula color scheme: https://draculatheme.com/

This theme features bold, vibrant colors with high contrast on a dark
background, optimized for reduced eye strain in low-light conditions.

Theme Philosophy:
- Bold purples and pinks for keywords and important elements
- Vibrant cyan for primary hierarchy
- Green for success/completion states
- Red/orange for errors and warnings
- Dark background with high-contrast text

To use this theme:
1. Rename this file to 'theme.py' (backing up the current theme.py first)
2. Restart the application
OR
3. Import colors from this module in your theme.py

Example:
    from taskui.ui.themes.dracula import *
"""

from rich.style import Style
from rich.theme import Theme


# ============================================================================
# BASE COLORS (Dracula Official Palette)
# ============================================================================
# Core colors from the official Dracula specification

BACKGROUND = "#282A36"  # Dark purple-gray background
FOREGROUND = "#F8F8F2"  # Off-white text (same as One Monokai for consistency)
SELECTION = "#44475A"   # Medium gray-purple for selections
COMMENT = "#6272A4"     # Blue-gray for comments and secondary text
BORDER = "#44475A"      # Same as selection for subtle borders


# ============================================================================
# HIERARCHY COLORS
# ============================================================================
# Mapped to Dracula's vibrant accent colors for visual task hierarchy
# Following the cyan/green/pink pattern for consistency with One Monokai

LEVEL_0_COLOR = "#8BE9FD"  # Cyan - Top-level tasks (primary)
LEVEL_1_COLOR = "#50FA7B"  # Green - First nesting level (secondary)
LEVEL_2_COLOR = "#FF79C6"  # Pink - Second nesting level (tertiary)


# ============================================================================
# ADDITIONAL UI COLORS
# ============================================================================
# Dracula's full palette for warnings, highlights, and special states

YELLOW = "#F1FA8C"   # Bright yellow for highlights and incomplete states
ORANGE = "#FFB86C"   # Warm orange for warnings and moderate alerts
PURPLE = "#BD93F9"   # Lavender purple for metadata and informational text
RED = "#FF5555"      # Bright red for errors and critical warnings
WHITE = FOREGROUND   # Alias for consistency


# ============================================================================
# STATUS COLORS
# ============================================================================
# Task completion and archive states using Dracula semantics

COMPLETE_COLOR = LEVEL_1_COLOR  # Green indicates success/completion
ARCHIVE_COLOR = COMMENT         # Dimmed blue-gray for archived tasks


# ============================================================================
# INTERACTION STATES
# ============================================================================
# Modal overlays, hover effects, and focus indicators

MODAL_OVERLAY_BG = "#282A3680"  # Semi-transparent background overlay (50% opacity)
HOVER_OPACITY = "20"            # Hover effect transparency (~12% opacity)
FOCUS_COLOR = LEVEL_0_COLOR     # Cyan focus indicator (matches level 0)
DISABLED_OPACITY = "0.5"        # Disabled button opacity (50%)


# ============================================================================
# RICH THEME OBJECT
# ============================================================================
# Pre-configured Rich theme for Textual's text rendering

DRACULA_THEME = Theme({
    "background": f"on {BACKGROUND}",
    "foreground": FOREGROUND,
    "selection": f"on {SELECTION}",
    "border": BORDER,
    "level_0": LEVEL_0_COLOR,
    "level_1": LEVEL_1_COLOR,
    "level_2": LEVEL_2_COLOR,
    "complete": COMPLETE_COLOR,
    "archive": ARCHIVE_COLOR,
    "highlight": YELLOW,
    "warning": ORANGE,
    "info": PURPLE,
    "error": RED,
})


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_level_color(level: int) -> str:
    """Get the accent color for a specific task nesting level.

    Args:
        level: The task nesting level (0, 1, or 2)

    Returns:
        Hex color string for the specified level
    """
    colors = {
        0: LEVEL_0_COLOR,
        1: LEVEL_1_COLOR,
        2: LEVEL_2_COLOR,
    }
    return colors.get(level, FOREGROUND)


def get_level_style(level: int) -> Style:
    """Get a Rich Style object for a specific task nesting level.

    Args:
        level: The task nesting level (0, 1, or 2)

    Returns:
        Rich Style object with the appropriate color
    """
    return Style(color=get_level_color(level))


def with_alpha(color: str, alpha: str) -> str:
    """Add alpha transparency to a hex color.

    Args:
        color: Base hex color string (e.g., '#282A36')
        alpha: Alpha value as 2-digit hex string (e.g., '20' for ~12%)

    Returns:
        Color with alpha channel appended (e.g., '#282A3620')
    """
    return f"{color}{alpha}"
