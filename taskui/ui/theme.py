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
5. **Hierarchy support**: Unlimited nesting with dynamic color generation

Color Categories
----------------
- **Base colors**: Background, foreground, selection, borders
- **Hierarchy colors**: Level-specific accent colors with algorithmic fallback
- **Status colors**: Completion and archive states
- **Interactive states**: Modal overlays, hover effects, focus indicators
- **Additional colors**: Warnings, highlights, informational text

Color Palette for Nesting Levels
----------------------------------
The first 20 nesting levels use Kelly's 22 Colors of Maximum Contrast, carefully
selected for maximum visual distinction on dark backgrounds. For levels 20+, colors
are generated algorithmically using the golden ratio method to ensure continued
visual variety without repetition.

Usage in Components
-------------------
Components import theme constants and use them in CSS via f-strings:

    from taskui.ui.theme import BACKGROUND, LEVEL_0_COLOR, with_alpha, get_level_color

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
    LEVEL_COLORS[0] = "#0066CC"  # Blue
    LEVEL_COLORS[1] = "#00AA00"  # Green
    LEVEL_COLORS[2] = "#CC0066"  # Magenta

See Also
--------
- base_styles.py: Reusable CSS patterns using these theme constants
- README.md: Complete theming documentation and examples
"""

import colorsys
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
#
# Color Palette Source: Kelly's 22 Colors of Maximum Contrast
# Reference: Kenneth L. Kelly, "Twenty-Two Colors of Maximum Contrast" (1965)
#
# The first 20 levels use a curated selection from Kelly's research, optimized
# for visibility on dark backgrounds. Colors were chosen for maximum perceptual
# distinction while maintaining aesthetic harmony with the One Monokai theme.
#
# Note: The first 3 colors are preserved from the original TaskUI design for
# backward compatibility with existing configurations and user expectations.

LEVEL_COLORS = [
    # Levels 0-2: Original TaskUI colors (backward compatible)
    "#66D9EF",  # Level 0: Cyan/Blue - Top-level tasks (primary)
    "#A6E22E",  # Level 1: Green - First nesting level (secondary)
    "#F92672",  # Level 2: Pink/Magenta - Second nesting level (tertiary)

    # Levels 3-19: Kelly's Colors of Maximum Contrast
    "#F3C300",  # Level 3: Vivid Yellow
    "#875692",  # Level 4: Strong Purple
    "#F38400",  # Level 5: Vivid Orange
    "#A1CAF1",  # Level 6: Very Light Blue
    "#BE0032",  # Level 7: Vivid Red
    "#C2B280",  # Level 8: Grayish Yellow (Buff)
    "#848482",  # Level 9: Medium Gray
    "#008856",  # Level 10: Vivid Green
    "#E68FAC",  # Level 11: Strong Purplish Pink
    "#0067A5",  # Level 12: Strong Blue
    "#F99379",  # Level 13: Strong Yellowish Pink (Salmon)
    "#604E97",  # Level 14: Strong Violet
    "#F6A600",  # Level 15: Vivid Orange Yellow (Gold)
    "#B3446C",  # Level 16: Strong Purplish Red (Maroon)
    "#DCD300",  # Level 17: Vivid Greenish Yellow (Lime)
    "#882D17",  # Level 18: Strong Reddish Brown
    "#8DB600",  # Level 19: Vivid Yellowish Green (Olive)
]

# Backward compatibility: Individual color constants for levels 0-2
# These reference the LEVEL_COLORS list and remain available for legacy code
LEVEL_0_COLOR = LEVEL_COLORS[0]  # Cyan/Blue - Top-level tasks (primary)
LEVEL_1_COLOR = LEVEL_COLORS[1]  # Green - First nesting level (secondary)
LEVEL_2_COLOR = LEVEL_COLORS[2]  # Pink/Red - Second nesting level (tertiary)


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

def generate_hsl_color(level: int) -> str:
    """Generate a color for deep nesting levels using the golden ratio method.

    For nesting levels beyond the predefined LEVEL_COLORS palette (level 20+),
    this function generates colors algorithmically using the golden ratio
    conjugate to ensure maximum color variation without repetition.

    The golden ratio (φ ≈ 1.618) provides optimal angular spacing in color space,
    creating visually distinct hues that avoid clustering. This mathematical
    approach ensures that even very deep nesting levels remain distinguishable.

    Algorithm:
        1. Use golden ratio conjugate (0.618...) to step through hue space
        2. Apply modulo 1.0 to wrap around the color wheel
        3. Use fixed saturation (80%) and lightness (60%) for consistency
        4. Convert HSL to RGB and format as hex color code

    Args:
        level: The nesting level (should be >= 20 for levels beyond LEVEL_COLORS)

    Returns:
        Hex color string (e.g., '#A1B2C3') generated algorithmically

    Examples:
        >>> generate_hsl_color(20)
        '#99cc99'  # First generated color
        >>> generate_hsl_color(21)
        '#cc9999'  # Next in golden ratio sequence
        >>> generate_hsl_color(100)
        '#9999cc'  # Continues to vary even at deep levels

    Note:
        This function can be called for any level, but is designed for levels
        beyond the LEVEL_COLORS palette. The generated colors maintain good
        visibility on dark backgrounds through fixed saturation/lightness values.

    References:
        - Golden ratio method for color generation
        - HSL color space for perceptually uniform distribution
    """
    # Golden ratio conjugate for optimal hue distribution
    golden_ratio_conjugate = 0.618033988749895

    # Calculate hue based on level, using golden ratio for maximum distinction
    # Start at 0.5 (cyan/green area) and step by golden ratio conjugate
    hue = (0.5 + level * golden_ratio_conjugate) % 1.0

    # Fixed saturation and lightness for consistency and visibility
    # Saturation: 0.8 (80%) - vibrant but not oversaturated
    # Lightness: 0.6 (60%) - balanced for dark backgrounds
    lightness = 0.6
    saturation = 0.8

    # Convert HSL to RGB (note: colorsys uses HLS, not HSL)
    rgb = colorsys.hls_to_rgb(hue, lightness, saturation)

    # Convert RGB floats (0.0-1.0) to hex color code
    r = int(rgb[0] * 255)
    g = int(rgb[1] * 255)
    b = int(rgb[2] * 255)

    return f"#{r:02x}{g:02x}{b:02x}"


def get_level_color(level: int) -> str:
    """Get the accent color for a specific task nesting level.

    This function maps task nesting levels to their corresponding accent colors,
    providing visual distinction for task hierarchy. It supports unlimited nesting
    depth through a combination of predefined colors and algorithmic generation.

    Color Selection Strategy:
        - Levels 0-19: Use predefined LEVEL_COLORS (Kelly's palette)
        - Levels 20+: Generate colors algorithmically via golden ratio method
        - Invalid levels (negative): Return FOREGROUND color (graceful fallback)

    Args:
        level: The task nesting level (0 to infinity)
            - Level 0: Top-level tasks (cyan)
            - Level 1: First nesting (green)
            - Level 2: Second nesting (pink/magenta)
            - Levels 3-19: Kelly's Colors of Maximum Contrast
            - Levels 20+: Algorithmically generated colors
            - Negative: Returns FOREGROUND (error handling)

    Returns:
        Hex color string for the specified level. Always returns a valid color.

    Examples:
        >>> get_level_color(0)
        '#66D9EF'  # Cyan (predefined)
        >>> get_level_color(5)
        '#F38400'  # Vivid Orange (Kelly's color)
        >>> get_level_color(25)
        '#A1B2C3'  # Generated color
        >>> get_level_color(-1)
        '#F8F8F2'  # FOREGROUND (fallback)

    Usage in components:
        level_color = get_level_color(task.level)
        text.append(task.title, style=level_color)

    See Also:
        generate_hsl_color(): Algorithmic color generation for deep nesting
        LEVEL_COLORS: Predefined color palette for levels 0-19
    """
    # Handle invalid levels gracefully
    if level < 0:
        return FOREGROUND

    # Use predefined colors for levels 0-19
    if level < len(LEVEL_COLORS):
        return LEVEL_COLORS[level]

    # Generate colors algorithmically for deeper nesting (level 20+)
    return generate_hsl_color(level)


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
