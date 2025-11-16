"""Nord color theme for TaskUI.

Nord theme adapted for TaskUI's task management interface.
Based on the official Nord palette: https://www.nordtheme.com/

An arctic, north-bluish color palette featuring carefully selected,
dimmed pastel colors optimized for snow-like ambiance and reduced
blue light for comfortable extended use.

Theme Philosophy:
- Cool arctic blues for calm, focused atmosphere
- Frost palette for primary interactive elements
- Aurora colors for accents and status indicators
- Polar Night for dark backgrounds
- Snow Storm for text (adapted for dark theme)

To use this theme:
1. Rename this file to 'theme.py' (backing up the current theme.py first)
2. Restart the application
OR
3. Import colors from this module in your theme.py

Example:
    from taskui.ui.themes.nord import *
"""

from rich.style import Style
from rich.theme import Theme


# ============================================================================
# OFFICIAL NORD PALETTE (16 colors)
# ============================================================================
# Four component palettes: Polar Night, Snow Storm, Frost, and Aurora

# Polar Night (Dark colors - nord0-nord3)
NORD0 = "#2E3440"  # Darkest - base background
NORD1 = "#3B4252"  # Dark - elevated surfaces
NORD2 = "#434C5E"  # Medium dark - selection
NORD3 = "#4C566A"  # Light dark - comments

# Snow Storm (Bright colors - nord4-nord6)
NORD4 = "#D8DEE9"  # Off-white text
NORD5 = "#E5E9F0"  # White text
NORD6 = "#ECEFF4"  # Bright white highlights

# Frost (Bluish colors - nord7-nord10)
NORD7 = "#8FBCBB"   # Frost cyan - calm and smooth
NORD8 = "#88C0D0"   # Frost light blue - calm and smooth
NORD9 = "#81A1C1"   # Frost blue - colorful and lively
NORD10 = "#5E81AC"  # Frost dark blue - deep and harmonious

# Aurora (Colorful accents - nord11-nord15)
NORD11 = "#BF616A"  # Aurora red - errors and warnings
NORD12 = "#D08770"  # Aurora orange - special annotations
NORD13 = "#EBCB8B"  # Aurora yellow - highlights and search
NORD14 = "#A3BE8C"  # Aurora green - success and additions
NORD15 = "#B48EAD"  # Aurora purple - rare and special


# ============================================================================
# BASE COLORS
# ============================================================================
# Mapped to TaskUI's color system using Nord palette

BACKGROUND = NORD0   # Darkest polar night for main background
FOREGROUND = NORD4   # Snow storm off-white for text
SELECTION = NORD2    # Medium polar night for selections
COMMENT = NORD3      # Light polar night for secondary text
BORDER = NORD1       # Dark polar night for subtle borders


# ============================================================================
# HIERARCHY COLORS
# ============================================================================
# Using Frost palette for cohesive bluish hierarchy

LEVEL_0_COLOR = NORD8   # Frost light blue (cyan) - Top-level tasks
LEVEL_1_COLOR = NORD14  # Aurora green - First nesting level
LEVEL_2_COLOR = NORD15  # Aurora purple - Second nesting level


# ============================================================================
# ADDITIONAL UI COLORS
# ============================================================================
# Aurora colors for warnings, highlights, and special states

YELLOW = NORD13  # Aurora yellow for highlights and incomplete states
ORANGE = NORD12  # Aurora orange for warnings
PURPLE = NORD15  # Aurora purple for metadata and informational text
RED = NORD11     # Aurora red for errors
CYAN = NORD7     # Frost calm cyan for special highlights
WHITE = NORD6    # Bright snow storm for high-emphasis text


# ============================================================================
# STATUS COLORS
# ============================================================================
# Task completion and archive states using Nord semantics

COMPLETE_COLOR = NORD14  # Aurora green indicates success/completion
ARCHIVE_COLOR = NORD3    # Dimmed polar night for archived tasks


# ============================================================================
# INTERACTION STATES
# ============================================================================
# Modal overlays, hover effects, and focus indicators

MODAL_OVERLAY_BG = f"{NORD0}80"  # Semi-transparent background overlay (50% opacity)
HOVER_OPACITY = "20"              # Hover effect transparency (~12% opacity)
FOCUS_COLOR = LEVEL_0_COLOR       # Frost blue focus indicator (matches level 0)
DISABLED_OPACITY = "0.5"          # Disabled button opacity (50%)


# ============================================================================
# RICH THEME OBJECT
# ============================================================================
# Pre-configured Rich theme for Textual's text rendering

NORD_THEME = Theme({
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
    "cyan": CYAN,
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
        color: Base hex color string (e.g., '#2E3440')
        alpha: Alpha value as 2-digit hex string (e.g., '20' for ~12%)

    Returns:
        Color with alpha channel appended (e.g., '#2E344020')
    """
    return f"{color}{alpha}"
