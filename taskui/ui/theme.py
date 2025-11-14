"""One Monokai color theme for TaskUI.

This module defines the One Monokai color scheme with level-specific accent colors
for the task hierarchy visualization.
"""

from rich.style import Style
from rich.theme import Theme


# One Monokai Base Colors
BACKGROUND = "#272822"
FOREGROUND = "#F8F8F2"
SELECTION = "#49483E"
COMMENT = "#75715E"
BORDER = "#3E3D32"

# Level-Specific Accent Colors
LEVEL_0_COLOR = "#66D9EF"  # Cyan/Blue - Top level
LEVEL_1_COLOR = "#A6E22E"  # Green - First nesting
LEVEL_2_COLOR = "#F92672"  # Pink/Red - Second nesting

# Additional UI Colors
YELLOW = "#E6DB74"
ORANGE = "#FD971F"
PURPLE = "#AE81FF"
WHITE = "#F8F8F2"

# Status Colors
COMPLETE_COLOR = "#75715E"  # Dimmed gray for completed tasks
ARCHIVE_COLOR = "#49483E"   # Even more dimmed for archived


# Rich Theme for Textual
ONE_MONOKAI_THEME = Theme({
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
})


def get_level_color(level: int) -> str:
    """Get the accent color for a specific nesting level.

    Args:
        level: The nesting level (0, 1, or 2)

    Returns:
        Hex color string for the level
    """
    colors = {
        0: LEVEL_0_COLOR,
        1: LEVEL_1_COLOR,
        2: LEVEL_2_COLOR,
    }
    return colors.get(level, FOREGROUND)


def get_level_style(level: int) -> Style:
    """Get a Rich Style object for a specific nesting level.

    Args:
        level: The nesting level (0, 1, or 2)

    Returns:
        Rich Style object with the appropriate color
    """
    return Style(color=get_level_color(level))
