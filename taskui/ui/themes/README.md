# TaskUI Theme Collection

Popular VS Code color themes adapted for TaskUI's task management interface.

## Available Themes

### 1. **One Monokai** (Default)
- **Location**: `taskui/ui/theme.py`
- **Style**: Dark with warm accents
- **Best for**: General use, warm color preferences
- **Colors**: Charcoal background, cyan/green/pink hierarchy
- **Inspiration**: Sublime Text's Monokai

### 2. **Dracula** 🧛
- **Location**: `taskui/ui/themes/dracula.py`
- **Style**: Bold, vibrant dark theme
- **Best for**: High contrast, reduced eye strain in low light
- **Colors**: Purple-gray background, vibrant accent colors
- **Inspiration**: https://draculatheme.com/
- **Popularity**: 10+ million installs on VS Code

**Color Preview:**
```
Background:  #282A36  ███  Dark purple-gray
Foreground:  #F8F8F2  ███  Off-white
Level 0:     #8BE9FD  ███  Cyan
Level 1:     #50FA7B  ███  Green
Level 2:     #FF79C6  ███  Pink
Yellow:      #F1FA8C  ███  Bright yellow
Orange:      #FFB86C  ███  Warm orange
Purple:      #BD93F9  ███  Lavender
Red:         #FF5555  ███  Bright red
```

### 3. **Tokyo Night** 🌃
- **Location**: `taskui/ui/themes/tokyo_night.py`
- **Style**: Deep blue night theme
- **Best for**: Night owls, blue color preferences
- **Colors**: Deep blue-black background, cool blue accents
- **Inspiration**: Downtown Tokyo's nighttime skyline
- **Popularity**: Trending theme on VS Code

**Color Preview:**
```
Background:  #1A1B26  ███  Deep blue-black
Foreground:  #A9B1D6  ███  Soft blue-white
Level 0:     #7AA2F7  ███  Primary blue
Level 1:     #73DACA  ███  Teal green
Level 2:     #BB9AF7  ███  Purple
Yellow:      #E0AF68  ███  Warm yellow
Orange:      #FF9E64  ███  Bright orange
Purple:      #9D7CD8  ███  Magenta
Red:         #F7768E  ███  Soft red
Cyan:        #7DCFFF  ███  Bright cyan
```

### 4. **Nord** ❄️
- **Location**: `taskui/ui/themes/nord.py`
- **Style**: Arctic, north-bluish theme
- **Best for**: Calm, focused atmosphere; reduced blue light
- **Colors**: Polar night background, frost blue accents
- **Inspiration**: Arctic landscapes, https://www.nordtheme.com/
- **Popularity**: 2+ million downloads

**Color Preview:**
```
Background:  #2E3440  ███  Dark polar night
Foreground:  #D8DEE9  ███  Snow storm white
Level 0:     #88C0D0  ███  Frost light blue
Level 1:     #A3BE8C  ███  Aurora green
Level 2:     #B48EAD  ███  Aurora purple
Yellow:      #EBCB8B  ███  Aurora yellow
Orange:      #D08770  ███  Aurora orange
Purple:      #B48EAD  ███  Aurora purple
Red:         #BF616A  ███  Aurora red
```

---

## How to Switch Themes

### Method 1: Replace theme.py (Recommended for permanent change)

1. **Backup current theme:**
   ```bash
   cd taskui/ui
   cp theme.py theme_backup.py
   ```

2. **Copy desired theme:**
   ```bash
   # For Dracula:
   cp themes/dracula.py theme.py

   # For Tokyo Night:
   cp themes/tokyo_night.py theme.py

   # For Nord:
   cp themes/nord.py theme.py
   ```

3. **Restart the application:**
   ```bash
   python -m taskui.ui.app
   ```

### Method 2: Import in theme.py (Quick testing)

Edit `taskui/ui/theme.py` and replace the color constants:

```python
# At the top of theme.py, replace all color definitions with:
from taskui.ui.themes.dracula import *

# OR
from taskui.ui.themes.tokyo_night import *

# OR
from taskui.ui.themes.nord import *
```

Then restart the application.

### Method 3: Symbolic Link (Advanced)

Create a symbolic link for easy theme switching:

```bash
cd taskui/ui
ln -sf themes/dracula.py theme.py
```

To switch:
```bash
ln -sf themes/tokyo_night.py theme.py
ln -sf themes/nord.py theme.py
```

---

## Creating Your Own Theme

1. **Copy a template:**
   ```bash
   cp themes/dracula.py themes/my_theme.py
   ```

2. **Edit color constants:**
   - Modify `BACKGROUND`, `FOREGROUND`, `SELECTION`, etc.
   - Adjust `LEVEL_0_COLOR`, `LEVEL_1_COLOR`, `LEVEL_2_COLOR` for hierarchy
   - Update accent colors (`YELLOW`, `ORANGE`, `PURPLE`, etc.)

3. **Test your theme:**
   ```bash
   cp themes/my_theme.py theme.py
   python -m taskui.ui.app
   ```

4. **Share your theme:**
   - Submit a PR to add your theme to this collection!

---

## Theme Color Mappings

All themes follow this structure for consistency:

| Purpose | Variable | Usage |
|---------|----------|-------|
| **Base** | `BACKGROUND` | Main app background |
| | `FOREGROUND` | Primary text color |
| | `SELECTION` | Selected items background |
| | `COMMENT` | Secondary/dimmed text |
| | `BORDER` | Borders and dividers |
| **Hierarchy** | `LEVEL_0_COLOR` | Top-level tasks (cyan family) |
| | `LEVEL_1_COLOR` | First nesting (green family) |
| | `LEVEL_2_COLOR` | Second nesting (pink/purple family) |
| **Accents** | `YELLOW` | Incomplete status, highlights |
| | `ORANGE` | Warnings, errors |
| | `PURPLE` | Metadata, timestamps |
| | `RED` | Critical errors |
| **Status** | `COMPLETE_COLOR` | Completed tasks |
| | `ARCHIVE_COLOR` | Archived tasks |
| **Interactive** | `HOVER_OPACITY` | Hover transparency |
| | `FOCUS_COLOR` | Focus indicator |
| | `MODAL_OVERLAY_BG` | Modal overlay |

---

## Theme Comparison

| Feature | One Monokai | Dracula | Tokyo Night | Nord |
|---------|-------------|---------|-------------|------|
| **Vibe** | Warm, classic | Bold, vibrant | Cool, sleek | Calm, arctic |
| **Contrast** | Medium-high | High | Medium | Medium |
| **Best Time** | Any | Night | Night | Day/Night |
| **Eye Strain** | Low | Very low | Low | Very low |
| **Accent Style** | Balanced | Punchy | Balanced | Subtle |
| **Popularity** | High | Very high | High | High |

---

## Tips for Choosing a Theme

**Choose Dracula if you:**
- Want bold, high-contrast colors
- Code in low-light environments
- Prefer vibrant purples and pinks
- Like the classic Dracula aesthetic

**Choose Tokyo Night if you:**
- Prefer cool blue tones
- Work late nights frequently
- Want a modern, sleek appearance
- Like balanced contrast with personality

**Choose Nord if you:**
- Value calm, focused environments
- Want reduced blue light exposure
- Prefer subtle, muted colors
- Like arctic/Scandinavian aesthetics

**Stick with One Monokai if you:**
- Like warm, earthy tones
- Want the classic Sublime Text feel
- Prefer balanced, familiar colors
- It's working well for you!

---

## Contributing

Have a favorite VS Code theme you'd like to see in TaskUI?

1. Create a new theme file following the existing structure
2. Add comprehensive color mapping
3. Include color preview in this README
4. Test with all UI components
5. Submit a pull request!

**Popular themes to consider:**
- Atom One Dark
- Solarized Dark
- GitHub Dark
- Material Theme
- Ayu Dark
- Gruvbox
- Catppuccin
