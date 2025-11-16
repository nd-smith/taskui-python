# Printer Integration Implementation Tasks

**Project:** TaskUI Network Printer Support (Task 4.1)
**Hardware:** Epson TM-T20III @ 192.168.50.99:9100
**Paper:** 80mm thermal receipt paper (70 character width)
**Goal:** Print physical kanban cards for real-world task boards

---

## Implementation Strategy

Each story is sized for approximately one Claude Code context window session.
Focus: **Incremental validation** - prove each layer works before building on it.

**Key Principles:**
- Test hardware connectivity FIRST before app integration
- Validate ESC/POS commands work with our specific printer model
- Build formatting iteratively (minimal → standard → full)
- Keep stories independent where possible

---

## STORY 1: Basic Printer Connectivity & Hello World ⚡ [STANDALONE]

**Size:** Small | **Time:** 30 mins | **Dependencies:** None

**Goal:** Prove we can connect to the printer and print basic text.

### Objectives
1. Install `python-escpos` dependency
2. Create standalone test script that connects to printer
3. Successfully print "Hello World" test page
4. Validate auto-cut functionality works
5. Document any connectivity issues and solutions

### Deliverables

**Files to create:**
- `scripts/test_printer_connection.py` - Standalone test script
- `docs/PRINTER_TROUBLESHOOTING.md` - Connection issues and solutions

**Files to update:**
- `requirements.txt` - Add python-escpos dependency
- `pyproject.toml` - Add python-escpos to dependencies (if used)

### Test Script Requirements

```python
# scripts/test_printer_connection.py
"""
Standalone printer connectivity test.
Tests basic connection and printing without app integration.
"""

from escpos.printer import Network
import sys

def test_connection():
    """Test basic connection to printer."""
    try:
        printer = Network("192.168.50.99", port=9100, timeout=10)
        print("✓ Connected to printer")
        return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

def test_print_hello():
    """Print simple hello world test."""
    try:
        printer = Network("192.168.50.99", port=9100, timeout=10)

        # Test text printing
        printer.text("Hello World from TaskUI\n")
        printer.text("Test print successful!\n")
        printer.text("\n")

        # Test auto-cut
        printer.cut()

        print("✓ Test print successful")
        return True
    except Exception as e:
        print(f"✗ Print failed: {e}")
        return False

def test_formatted_text():
    """Test text formatting capabilities."""
    try:
        printer = Network("192.168.50.99", port=9100, timeout=10)

        # Test formatting
        printer.set(align='center', bold=True, double_height=True)
        printer.text("TASKUI\n")

        printer.set(align='left', bold=False, double_height=False)
        printer.text("Normal text\n")

        printer.set(bold=True)
        printer.text("Bold text\n")

        printer.set(underline=True, bold=False)
        printer.text("Underlined text\n")

        printer.text("\n")
        printer.cut()

        print("✓ Formatting test successful")
        return True
    except Exception as e:
        print(f"✗ Formatting test failed: {e}")
        return False

if __name__ == "__main__":
    print("TaskUI Printer Connectivity Test")
    print("=" * 40)

    tests = [
        ("Connection", test_connection),
        ("Hello World", test_print_hello),
        ("Text Formatting", test_formatted_text),
    ]

    results = []
    for name, test_func in tests:
        print(f"\nRunning: {name}")
        result = test_func()
        results.append((name, result))

    print("\n" + "=" * 40)
    print("Test Results:")
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status} - {name}")

    all_passed = all(result for _, result in results)
    sys.exit(0 if all_passed else 1)
```

### Success Criteria
- [ ] python-escpos installed successfully
- [ ] Script connects to printer at 192.168.50.99
- [ ] "Hello World" prints on thermal paper
- [ ] Auto-cut works correctly
- [ ] Formatting commands (bold, underline, align) work
- [ ] All connection issues documented in troubleshooting guide

### Common Issues to Document
- Network timeouts (firewall, wrong IP, printer offline)
- Port 9100 blocked or unavailable
- Printer in wrong mode (need raw printing mode)
- Paper jams or out of paper
- ESC/POS command compatibility

---

## STORY 2: Kanban Card Formatting ⚡ [DEPENDS ON: Story 1]

**Size:** Medium | **Time:** 40 mins | **Dependencies:** Story 1

**Goal:** Create properly formatted kanban cards with box borders and test with real printer.

### Objectives
1. Implement box drawing characters for card borders
2. Test 70-character width on actual 80mm paper
3. Validate line spacing and padding looks good physically
4. Ensure auto-cut creates clean separations
5. Print test cards with sample task data

### Deliverables

**Files to create:**
- `scripts/test_card_format.py` - Card formatting test script

**Files to update:**
- `taskui/services/printer_service.py` - Refine _format_minimal() based on real hardware

### Test Script Requirements

```python
# scripts/test_card_format.py
"""
Test kanban card formatting on real printer.
Print sample cards with various scenarios.
"""

def print_minimal_card():
    """Test minimal format card."""
    # Test basic card with borders and padding
    pass

def print_card_with_children():
    """Test card with multiple children."""
    # Test with 1, 3, 5 children to see spacing
    pass

def print_long_title_card():
    """Test card with long title that might wrap."""
    # Test truncation/wrapping behavior
    pass

def print_edge_cases():
    """Test edge cases."""
    # No children, many children (10+), very long titles
    pass
```

### Test Cases to Print
1. Simple card: parent task, no children
2. Card with 3 children (1 completed)
3. Card with long title (>50 chars)
4. Card with 10 children (test vertical space)
5. Completed parent task card
6. Card with special characters in title

### Success Criteria
- [ ] Box borders render correctly on thermal paper
- [ ] 70-character width fits perfectly on 80mm paper
- [ ] Padding provides enough white space for readability
- [ ] Cards are easy to handle physically
- [ ] Auto-cut creates clean edges
- [ ] Text is readable on physical card
- [ ] Special characters print correctly

### Measurements to Validate
- Card height with 0, 3, 5, 10 children
- Minimum padding for physical handling
- Font size readability from arm's length
- Whether to use single or double-width borders

---

## STORY 3: PrinterService Integration ⚡ [DEPENDS ON: Story 2]

**Size:** Medium | **Time:** 40 mins | **Dependencies:** Story 2

**Goal:** Complete PrinterService implementation with real Network printer.

### Objectives
1. Implement actual printer connection logic
2. Add connection validation and error handling
3. Implement all three detail levels (minimal, standard, full)
4. Add comprehensive logging
5. Create unit tests with mock printer

### Deliverables

**Files to update:**
- `taskui/services/printer_service.py` - Complete implementation
  - `connect()` method with real Network printer
  - `_format_standard()` implementation
  - `_format_full()` implementation
  - Error handling and logging

**Files to create:**
- `tests/test_printer_service.py` - Unit tests with mocks
- `scripts/test_detail_levels.py` - Test all three format levels

### Implementation Details

**connect() method:**
```python
def connect(self) -> bool:
    """Connect to thermal printer."""
    logger.debug(f"Connecting to printer at {self.config.host}:{self.config.port}")

    try:
        self.printer = Network(
            self.config.host,
            port=self.config.port,
            timeout=self.config.timeout
        )

        # Test connection with simple command
        self.printer.text("")  # Send empty text to test

        self._connected = True
        logger.info(f"Successfully connected to printer at {self.config.host}")
        return True

    except Exception as e:
        logger.error(f"Failed to connect to printer: {e}", exc_info=True)
        self._connected = False
        raise ConnectionError(
            f"Cannot connect to printer at {self.config.host}:{self.config.port}"
        ) from e
```

**_format_standard() requirements:**
- Add list name
- Add completion percentage
- Add created/modified timestamps
- Add child task dates if available

**_format_full() requirements:**
- All standard fields
- Task notes (word-wrapped)
- Child task notes
- Print timestamp
- Column/level information

### Success Criteria
- [ ] connect() works with real printer
- [ ] disconnect() cleans up properly
- [ ] is_connected() accurate
- [ ] All three format levels implemented
- [ ] Logging at appropriate levels
- [ ] Unit tests pass with mock printer
- [ ] Manual test script validates all formats on real printer

---

## STORY 4: Configuration Management ⚡ [DEPENDS ON: Story 3]

**Size:** Small | **Time:** 25 mins | **Dependencies:** Story 3

**Goal:** Implement config.ini parsing and printer configuration.

### Objectives
1. Create config.ini schema and example
2. Implement configuration file parsing
3. Add fallback to defaults if config missing
4. Support environment variable overrides
5. Add configuration validation

### Deliverables

**Files to create:**
- `.taskui/config.ini.example` - Example configuration file
- `taskui/config.py` - Configuration management module
- `tests/test_config.py` - Configuration parsing tests

**Files to update:**
- `taskui/services/printer_service.py` - Use config module

### Configuration Schema

**~/.taskui/config.ini:**
```ini
[printer]
# Printer network configuration
host = 192.168.50.99
port = 9100
timeout = 60

# Print format options
detail_level = minimal  # minimal | standard | full

# Print behavior
auto_cut = true
enable_logging = true
```

### Config Module Requirements

```python
# taskui/config.py
"""
Configuration management for TaskUI.
Loads settings from config.ini with environment variable overrides.
"""

import configparser
from pathlib import Path
from typing import Optional
import os

class Config:
    """Application configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self._default_config_path()
        self._config = configparser.ConfigParser()
        self._load()

    def _default_config_path(self) -> Path:
        """Get default config path."""
        return Path.home() / ".taskui" / "config.ini"

    def _load(self):
        """Load configuration from file."""
        if self.config_path.exists():
            self._config.read(self.config_path)

    def get_printer_config(self) -> dict:
        """Get printer configuration with environment overrides."""
        return {
            'host': os.getenv('TASKUI_PRINTER_HOST') or
                   self._config.get('printer', 'host', fallback='192.168.50.99'),
            'port': int(os.getenv('TASKUI_PRINTER_PORT') or
                       self._config.get('printer', 'port', fallback='9100')),
            'timeout': int(self._config.get('printer', 'timeout', fallback='60')),
            'detail_level': self._config.get('printer', 'detail_level',
                                            fallback='minimal'),
        }
```

### Success Criteria
- [ ] Config.ini example created
- [ ] Config module parses config.ini correctly
- [ ] Environment variables override config file
- [ ] Defaults work if config missing
- [ ] Invalid config values handled gracefully
- [ ] Unit tests cover all config scenarios

---

## STORY 5: UI Integration - 'P' Key Handler ⚡ [DEPENDS ON: Stories 3, 4]

**Size:** Medium | **Time:** 35 mins | **Dependencies:** Stories 3, 4

**Goal:** Integrate printer into TaskUI app with 'P' key handler.

### Objectives
1. Add 'P' key handler to app keybindings
2. Retrieve selected task + children from UI state
3. Initialize printer service on app startup
4. Show printing status feedback to user
5. Handle printer errors gracefully in UI

### Deliverables

**Files to update:**
- `taskui/ui/app.py` - Add printer service initialization and 'P' key handler
- `taskui/ui/keybindings.py` - Add 'P' key binding
- `docs/tasks.md` - Mark task 4.1 as complete

**Files to create:**
- `taskui/ui/components/printer_status_modal.py` - Status/error modal
- `tests/test_printer_integration.py` - Integration tests

### UI Integration Requirements

**App initialization:**
```python
# taskui/ui/app.py
from taskui.services.printer_service import PrinterService, PrinterConfig
from taskui.config import Config

class TaskUIApp(App):
    def on_mount(self):
        # Load config
        config = Config()
        printer_config = PrinterConfig(**config.get_printer_config())

        # Initialize printer service
        self.printer_service = PrinterService(printer_config)

        # Try to connect (don't fail if printer offline)
        try:
            self.printer_service.connect()
            logger.info("Printer connected and ready")
        except ConnectionError:
            logger.warning("Printer not available at startup")
```

**Key handler:**
```python
def action_print_task(self) -> None:
    """Handle 'P' key - print selected task card."""
    selected_task = self.get_selected_task()
    if not selected_task:
        self.show_error("No task selected")
        return

    # Get children
    children = self.task_service.get_children(selected_task.id)

    # Check printer connection
    if not self.printer_service.is_connected():
        self.show_printer_error("Printer not connected")
        return

    # Print card
    try:
        self.show_printing_status("Printing task card...")
        self.printer_service.print_task_card(selected_task, children)
        self.show_success("Task card printed!")
    except Exception as e:
        logger.error(f"Print failed: {e}", exc_info=True)
        self.show_printer_error(f"Print failed: {str(e)}")
```

### Status Modal Requirements

**PrinterStatusModal:**
- Show "Printing..." message
- Show success message briefly
- Show error message with retry option
- Don't block UI during printing

### Success Criteria
- [ ] 'P' key bound correctly
- [ ] Selected task retrieval works
- [ ] Children retrieved correctly
- [ ] Printer service initialized on app startup
- [ ] Status feedback shown to user
- [ ] Errors handled gracefully with clear messages
- [ ] Logging shows print operations
- [ ] Can print cards from running app
- [ ] App doesn't crash if printer offline

---

## STORY 6: Detail Levels & Configuration UI ⚡ [DEPENDS ON: Story 5]

**Size:** Small | **Time:** 30 mins | **Dependencies:** Story 5

**Goal:** Add UI for switching detail levels and printer settings.

### Objectives
1. Add keyboard shortcuts for detail level switching
2. Show current detail level in status bar
3. Add printer settings to help panel
4. Create printer configuration helper command

### Deliverables

**Files to update:**
- `taskui/ui/app.py` - Add detail level shortcuts (Shift+P cycles levels)
- `taskui/ui/components/help_panel.py` - Add printer help text
- `taskui/__main__.py` - Add --print-config CLI command

### Keybindings
- `p` - Print current task (existing)
- `shift+p` - Cycle detail level (minimal → standard → full → minimal)
- `ctrl+p` - Show printer settings

### CLI Commands
```bash
# Show current printer configuration
taskui --print-config

# Test printer connection
taskui --test-printer

# Print sample card
taskui --print-sample
```

### Success Criteria
- [ ] Can cycle detail levels with Shift+P
- [ ] Current level shown in UI
- [ ] Help panel documents printer keys
- [ ] CLI commands work
- [ ] Configuration displayed correctly

---

## STORY 7: Error Handling & Polish ⚡ [DEPENDS ON: Story 5]

**Size:** Medium | **Time:** 35 mins | **Dependencies:** Story 5

**Goal:** Comprehensive error handling and user experience polish.

### Objectives
1. Handle all printer error scenarios
2. Add retry logic for transient failures
3. Improve error messages
4. Add printer status indicator
5. Update logging for all operations

### Error Scenarios to Handle

**Connection Errors:**
- Printer offline/unreachable
- Network timeout
- Wrong IP address
- Port blocked by firewall

**Print Errors:**
- Paper jam
- Out of paper
- Printer busy
- Invalid ESC/POS command

**Configuration Errors:**
- Invalid config file
- Missing required fields
- Invalid detail level
- Invalid IP address format

### Deliverables

**Files to update:**
- `taskui/services/printer_service.py` - Enhanced error handling
- `taskui/ui/app.py` - Better error user feedback
- `docs/PRINTER_TROUBLESHOOTING.md` - Complete troubleshooting guide

**Files to create:**
- `taskui/exceptions.py` - Custom printer exceptions

### Custom Exceptions

```python
# taskui/exceptions.py
class PrinterError(Exception):
    """Base exception for printer errors."""
    pass

class PrinterConnectionError(PrinterError):
    """Printer connection failed."""
    pass

class PrinterOfflineError(PrinterError):
    """Printer is offline or unreachable."""
    pass

class PrinterBusyError(PrinterError):
    """Printer is busy with another job."""
    pass

class PrinterConfigError(PrinterError):
    """Invalid printer configuration."""
    pass
```

### Success Criteria
- [ ] All error scenarios handled gracefully
- [ ] Clear, actionable error messages
- [ ] Retry logic for transient failures
- [ ] Printer status indicator in UI
- [ ] Comprehensive troubleshooting guide
- [ ] All error paths logged
- [ ] No crashes due to printer issues

---

## STORY 8: Testing & Documentation ⚡ [DEPENDS ON: Story 7]

**Size:** Medium | **Time:** 40 mins | **Dependencies:** Story 7

**Goal:** Complete test coverage and documentation.

### Objectives
1. Unit tests for all printer service methods
2. Integration tests for UI flow
3. Hardware validation tests
4. Update main documentation
5. Create user guide for printer setup

### Deliverables

**Files to create:**
- `tests/test_printer_service.py` - Complete unit tests
- `tests/test_printer_integration.py` - Integration tests
- `docs/PRINTER_SETUP_GUIDE.md` - User setup guide
- `scripts/validate_printer.py` - Hardware validation script

**Files to update:**
- `README.md` - Add printer feature documentation
- `docs/tasks.md` - Mark task 4.1 complete
- `docs/PRINTER_TROUBLESHOOTING.md` - Final polish

### Test Coverage Requirements

**Unit Tests (with mocks):**
- PrinterConfig creation and validation
- PrinterService connection/disconnection
- All three format levels
- Error handling
- Configuration parsing

**Integration Tests:**
- App startup with printer
- 'P' key handler flow
- Error modal display
- Status feedback
- Detail level switching

**Hardware Validation:**
- Physical printer connection
- All format levels print correctly
- Auto-cut works
- Cards are readable
- Edge cases handled

### Documentation Requirements

**PRINTER_SETUP_GUIDE.md:**
1. Hardware requirements
2. Network configuration
3. Software installation
4. Configuration file setup
5. Testing connectivity
6. Using printer from app
7. Troubleshooting

**README.md updates:**
- Add printer feature to features list
- Add printer setup to installation section
- Add printer keybindings to usage section

### Success Criteria
- [ ] >80% test coverage for printer code
- [ ] All integration tests pass
- [ ] Hardware validation script passes
- [ ] Setup guide is clear and complete
- [ ] README updated
- [ ] Task 4.1 marked complete
- [ ] All documentation accurate

---

## Implementation Schedule

**Recommended Order:**
1. **Story 1** - Basic connectivity (CRITICAL - must work first)
2. **Story 2** - Card formatting (validate physical output)
3. **Story 3** - PrinterService (complete core functionality)
4. **Story 4** - Configuration (infrastructure)
5. **Story 5** - UI Integration (user-facing feature)
6. **Story 6** - Detail Levels (enhancement)
7. **Story 7** - Error Handling (polish)
8. **Story 8** - Testing & Docs (completion)

**Total Estimated Time:** ~4-5 hours of focused development

---

## Success Metrics

**Technical:**
- [ ] Can connect to printer at 192.168.50.99
- [ ] Cards print correctly on 80mm paper
- [ ] All three detail levels work
- [ ] Configuration loaded from file
- [ ] Errors handled gracefully
- [ ] No app crashes due to printer

**User Experience:**
- [ ] 'P' key prints selected task
- [ ] Clear feedback during printing
- [ ] Useful error messages
- [ ] Easy to configure
- [ ] Cards are physically usable

**Quality:**
- [ ] >80% test coverage
- [ ] All tests pass
- [ ] Complete documentation
- [ ] Logging comprehensive
- [ ] No security issues

---

## Dependencies

**External:**
- python-escpos library
- Network access to 192.168.50.99:9100
- 80mm thermal paper loaded in printer

**Internal:**
- Task model (existing)
- Task service (existing)
- Configuration system (to be created)
- UI keybinding system (existing)

---

## Notes for Future Enhancements

**Not in current scope, but consider later:**
- Print preview in UI
- Print queue management
- Multiple printer support
- Print job history
- Custom templates
- QR codes on cards
- Barcode support
- Color coding (if supported)
- Print from CLI without UI

---

**Document Status:** Ready for implementation
**Last Updated:** 2025-11-16
**Next Action:** Start with Story 1 - Basic Connectivity
