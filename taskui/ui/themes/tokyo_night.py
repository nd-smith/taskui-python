"""Tokyo Night color theme for TaskUI.

Tokyo Night theme adapted for TaskUI's task management interface.
Based on the Tokyo Night VS Code theme: https://github.com/tokyo-night/tokyo-night-vscode-theme

This theme celebrates the lights of Downtown Tokyo at night with deep blues,
purples, and carefully balanced contrast for comfortable night coding.

Theme Philosophy:
- Deep blue-black background for reduced eye strain
- Cool blue and cyan for primary elements
- Warm accents (orange, yellow) for highlights
- Purple and magenta for special states
- Balanced contrast optimized for nighttime use

To use this theme:
1. Rename this file to 'theme.py' (backing up the current theme.py first)
2. Restart the application
OR
3. Import colors from this module in your theme.py

Example:
    from taskui.ui.themes.tokyo_night import *
"""

from rich.style import Style
from rich.theme import Theme


# ============================================================================
# BASE COLORS (Tokyo Night Official Palette)
# ============================================================================
# Core colors from the official Tokyo Night theme

BACKGROUND = "#1A1B26"  # Deep blue-black background
FOREGROUND = "#A9B1D6"  # Soft blue-white text
SELECTION = "#283457"   # Dark blue selection (derived from #515c7e4d made opaque)
COMMENT = "#565F89"     # Muted blue-gray for secondary text
BORDER = "#292E42"      # Subtle dark blue border


# ============================================================================
# HIERARCHY COLORS
# ============================================================================
# Using Tokyo Night's vibrant blues and greens for task hierarchy

LEVEL_0_COLOR = "#7AA2F7"  # Primary blue - Top-level tasks (primary)
LEVEL_1_COLOR = "#73DACA"  # Teal green - First nesting level (secondary)
LEVEL_2_COLOR = "#BB9AF7"  # Purple - Second nesting level (tertiary)


# ============================================================================
# ADDITIONAL UI COLORS
# ============================================================================
# Tokyo Night's full accent palette for enhanced visual communication

YELLOW = "#E0AF68"   # Warm yellow for highlights and incomplete states
ORANGE = "#FF9E64"   # Bright orange for warnings
PURPLE = "#9D7CD8"   # Magenta purple for metadata and informational text
RED = "#F7768E"      # Soft red for errors and critical warnings
CYAN = "#7DCFFF"     # Bright cyan for special highlights
WHITE = "#C0CAF5"    # Brighter white for high-emphasis text


# ============================================================================
# STATUS COLORS
# ============================================================================
# Task completion and archive states using Tokyo Night semantics

COMPLETE_COLOR = LEVEL_1_COLOR  # Teal green indicates success/completion
ARCHIVE_COLOR = COMMENT         # Dimmed blue-gray for archived tasks


# ============================================================================
# INTERACTION STATES
# ============================================================================
# Modal overlays, hover effects, and focus indicators

MODAL_OVERLAY_BG = "#1A1B2680"  # Semi-transparent background overlay (50% opacity)
HOVER_OPACITY = "20"            # Hover effect transparency (~12% opacity)
FOCUS_COLOR = LEVEL_0_COLOR     # Blue focus indicator (matches level 0)
DISABLED_OPACITY = "0.5"        # Disabled button opacity (50%)


# ============================================================================
# RICH THEME OBJECT
# ============================================================================
# Pre-configured Rich theme for Textual's text rendering

TOKYO_NIGHT_THEME = Theme({
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
        color: Base hex color string (e.g., '#1A1B26')
        alpha: Alpha value as 2-digit hex string (e.g., '20' for ~12%)

    Returns:
        Color with alpha channel appended (e.g., '#1A1B2620')
    """
    return f"{color}{alpha}"
