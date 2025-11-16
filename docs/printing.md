# TaskUI Printer Integration Research

**Session:** 2025-11-16
**Target Hardware:** Epson TM-T20III via Raspberry Pi (Network Printing)
**Status:** Research & Planning Phase

---

## Executive Summary

This document outlines the research, architecture, and implementation plan for integrating thermal receipt printing into TaskUI. The goal is to enable users to **print individual task cards** via the 'P' key for use in a **physical kanban board**. Each task (with its children) is printed as a separate card with auto-cut, creating physical artifacts that can be moved around on a real board.

**Print Server:** Raspberry Pi at `192.168.50.99`
**Hardware:** Epson TM-T20III thermal printer

---

## Hardware Specifications

### Epson TM-T20III
- **Type:** Thermal receipt printer
- **Command Set:** ESC/POS (Epson Standard Code for POS)
- **Print Speed:** Up to 250 mm/second
- **Paper Width:** **80mm** thermal receipt paper
- **Character Width:** ~64-72 characters (depending on font selection)
- **Connectivity:** Multiple models available:
  - USB + Serial
  - **Ethernet** (our configuration)
- **Network Specs:**
  - Standard TCP/IP socket printing
  - Default port: **9100** (raw printing)
  - DHCP support for automatic IP assignment
  - mPOS/tablet support via ePOS SDK

### Raspberry Pi Print Server
- Acts as network print server
- Bridges TaskUI application to thermal printer
- Could handle print queue management
- Potential for future multi-printer support

---

## Python Libraries Research

### 1. python-escpos (RECOMMENDED)
**Repository:** https://github.com/python-escpos/python-escpos
**Documentation:** https://python-escpos.readthedocs.io/

**Strengths:**
- Most popular and actively maintained ESC/POS library
- Well-documented with comprehensive API
- Built-in `Network` class for TCP/IP printing
- Supports all ESC/POS features:
  - Text formatting (bold, underline, font sizes)
  - Alignment (left, center, right)
  - Barcodes and QR codes
  - Images (logo printing)
  - Receipt cutting
- Multiple printer interfaces: USB, Serial, Network, CUPS
- Mock printer for testing without hardware

**Network Printing Example:**
```python
from escpos.printer import Network

# Connect to printer via IP and port
printer = Network("192.168.1.100", port=9100, timeout=60)

# Print text
printer.text("Hello World\n")
printer.cut()
```

**Installation:**
```bash
pip install python-escpos
```

**Dependencies:**
- `Pillow` (for image printing)
- `pyusb` (only for USB, not needed for network)
- `pyserial` (only for Serial, not needed for network)

### 2. PyESCPOS (Alternative)
**PyPI:** https://pypi.org/project/PyESCPOS/

**Notes:**
- Less maintained than python-escpos
- Simpler API but fewer features
- May be sufficient for basic text printing
- Not recommended unless python-escpos has issues

### 3. python-epson-printer
**Repository:** https://github.com/benoitguigal/python-epson-printer

**Notes:**
- Specifically for Epson printers
- Tested with TM-T20 (older model, but similar to TM-T20III)
- Less active development
- More limited than python-escpos
- Not recommended as primary choice

---

## Architecture Options

### Option A: Direct Network Connection
```
TaskUI (Python) → TCP Socket → Raspberry Pi → Epson TM-T20III
                  (port 9100)
```

**Pros:**
- Simple, direct communication
- No middleware complexity
- Fast printing
- Easy to implement with python-escpos Network class

**Cons:**
- Requires printer IP address configuration
- No print queue management
- Single point of failure
- No print job tracking

**Implementation:**
```python
from escpos.printer import Network

class PrinterService:
    def __init__(self, printer_ip: str, port: int = 9100):
        self.printer = Network(printer_ip, port=port)

    def print_column(self, tasks: list):
        # Format and print tasks
        self.printer.text("=== Task List ===\n")
        for task in tasks:
            self.printer.text(f"- {task.title}\n")
        self.printer.cut()
```

### Option B: CUPS Print Server
```
TaskUI → CUPS on Raspberry Pi → Epson TM-T20III
         (network print server)
```

**Pros:**
- Standard print server architecture
- Built-in queue management
- Multiple application support
- Print job history and status

**Cons:**
- More complex setup on Raspberry Pi
- Additional CUPS configuration needed
- May introduce latency
- Overkill for single-application use case

**Implementation:**
```python
from escpos.printer import CupsPrinter

class PrinterService:
    def __init__(self, printer_name: str = "TM-T20III"):
        self.printer = CupsPrinter(printer_name)

    def print_column(self, tasks: list):
        # Same as above
        pass
```

### Option C: REST API on Raspberry Pi
```
TaskUI → HTTP POST → Flask/FastAPI on RPi → Epson TM-T20III
```

**Pros:**
- Decoupled architecture
- Easy to add web-based printing
- Could support multiple clients
- Centralized print logic on Pi

**Cons:**
- Adds network dependency
- More complex infrastructure
- Additional service to maintain
- May be overkill for MVP

---

## Recommended Architecture: **Option A (Direct Network)**

For MVP and initial implementation, **Option A** is recommended:

**Rationale:**
1. **Simplicity:** Minimal moving parts, easier to debug
2. **Performance:** Direct socket connection is fastest
3. **Dependencies:** Only requires python-escpos library
4. **Testing:** Easy to mock for development
5. **Evolution Path:** Can migrate to Option B or C later if needed

**Configuration Requirements:**
- Static IP for Raspberry Pi (or DHCP reservation)
- Printer IP address in TaskUI configuration
- Network connectivity validation

---

## Print Format Design

### Use Case: Physical Kanban Board Cards
Each printed task becomes a physical card that can be:
- Pinned to a corkboard
- Moved between columns (To Do → In Progress → Done)
- Annotated with physical marks
- Grouped and reorganized in real space

### Task Card Layout (Draft)

**MINIMAL Format** (default):
```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│  [ ] Design new feature                                            │
│                                                                    │
│      Progress: 3/5 subtasks                                        │
│                                                                    │
│      [ ] Write specs                                               │
│      [X] Create mockups                                            │
│      [ ] Review with team                                          │
│                                                                    │
│      Created: 2025-11-15                                           │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
[AUTO CUT HERE]
```

**STANDARD Format** (--detail=standard):
```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│  [ ] Design new feature                                            │
│                                                                    │
│  List: Work                                                        │
│  Progress: 3/5 subtasks complete (60%)                             │
│                                                                    │
│  Subtasks:                                                         │
│      [ ] Write specs                                               │
│          Due: 2025-11-20                                           │
│      [X] Create mockups                                            │
│          Completed: 2025-11-15                                     │
│      [ ] Review with team                                          │
│                                                                    │
│  Created: 2025-11-15 14:30                                         │
│  Modified: 2025-11-16 10:22                                        │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
[AUTO CUT HERE]
```

**FULL Format** (--detail=full):
```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│  [ ] Design new feature                                            │
│                                                                    │
│  List: Work                                                        │
│  Progress: 3/5 subtasks complete (60%)                             │
│  Column: Level 1                                                   │
│                                                                    │
│  Notes:                                                            │
│  This is a critical feature for Q4 release.                        │
│  Need to coordinate with design team.                              │
│                                                                    │
│  Subtasks:                                                         │
│      [ ] Write specs                                               │
│          Due: 2025-11-20                                           │
│          Notes: Include API examples                               │
│      [X] Create mockups                                            │
│          Completed: 2025-11-15                                     │
│      [ ] Review with team                                          │
│          Notes: Schedule 1hr meeting                               │
│                                                                    │
│  Created: 2025-11-15 14:30                                         │
│  Modified: 2025-11-16 10:22                                        │
│  Printed: 2025-11-16 15:45                                         │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
[AUTO CUT HERE]
```

**Design Considerations:**
- **70 characters wide** (80mm thermal paper, standard font)
- Heavy padding (blank lines) for readability and physical handling
- Box drawing for visual separation
- Auto-cut after each card
- Completion checkboxes [ ] / [X] for manual checking with pen
- Progress indicators for parent tasks
- Configurable detail levels
- Print timestamp for tracking when card was created
- Wider format allows for better readability on physical kanban board

---

## Implementation Plan

### Phase 1: Basic Infrastructure (This Session)
- [X] Research printer capabilities
- [X] Evaluate Python libraries
- [X] Choose architecture approach
- [ ] Design print format
- [ ] Create `printer_service.py` skeleton
- [ ] Implement mock printer for testing

### Phase 2: Core Functionality
- [ ] Install python-escpos dependency
- [ ] Implement PrinterService class
- [ ] Create print formatting logic
- [ ] Add configuration for printer IP
- [ ] Implement 'P' key handler in UI
- [ ] Test with mock printer

### Phase 3: Integration & Testing
- [ ] Test with actual TM-T20III hardware
- [ ] Handle network errors gracefully
- [ ] Add printer offline detection
- [ ] Implement user feedback (printing status)
- [ ] Add logging for print operations
- [ ] Performance testing

### Phase 4: Polish
- [ ] Optimize print format for readability
- [ ] Add print preview option
- [ ] Support printing individual tasks vs columns
- [ ] Configuration UI for printer settings
- [ ] Documentation and help text

---

## Design Decisions (FINALIZED)

### 1. **Print Scope** ✅
   - **Decision:** Print selected task + all children
   - **Behavior:** Each task becomes a physical kanban card
   - **Auto-cut:** After each task card for easy separation

### 2. **Print Format Detail Level** ✅
   - **Decision:** Configurable via `~/.taskui/config.ini`
   - **Levels:**
     - `minimal` (default): Title, checkbox, basic progress
     - `standard`: Add dates, list name, completion %
     - `full`: Everything including notes
   - **Configuration Key:** `printer.detail_level`

### 3. **Configuration Approach** ✅
   - **Decision:** Config file at `~/.taskui/config.ini`
   - **Section:** `[printer]`
   - **Keys:**
     - `host = 192.168.50.99`
     - `port = 9100`
     - `detail_level = minimal`
     - `timeout = 60`

### 4. **Error Handling** ✅
   - **Decision:** Show error modal and abort
   - **Behavior:**
     - Clear error message if printer offline
     - No retry queue (keep it simple for MVP)
     - User can retry manually after fixing connection

### 5. **Testing Strategy** ✅
   - **Decision:** Test with real hardware
   - **Hardware Available:** Raspberry Pi at 192.168.50.99
   - **Fallback:** Mock printer class for unit tests

---

## Technical Risks & Mitigations

### Risk 1: Network Connectivity
**Risk:** Printer IP changes, network down, firewall issues
**Mitigation:**
- Static IP or DHCP reservation for printer
- Connection validation before printing
- Clear error messages with troubleshooting steps
- Fallback to file export if printing fails

### Risk 2: Printer Compatibility
**Risk:** TM-T20III may have quirks not documented
**Mitigation:**
- Use well-tested python-escpos library
- Reference Epson's ESC/POS command documentation
- Test incrementally with real hardware
- Maintain compatibility with standard ESC/POS

### Risk 3: Format Rendering
**Risk:** Complex task hierarchies may not render well on narrow receipt
**Mitigation:**
- Design with 48-character constraint from start
- Implement smart truncation/wrapping
- Test with various hierarchy depths
- Consider collapsing deeply nested tasks

### Risk 4: Dependencies
**Risk:** python-escpos may have conflicts with existing dependencies
**Mitigation:**
- Test in current environment early
- Minimal dependencies for network printing
- Consider dependency isolation if needed
- Document version requirements clearly

---

## Next Steps

**This Session:**
1. ✅ Complete research document
2. ✅ Discuss requirements with user
3. ✅ Finalize architecture decisions
4. ✅ Design print format for kanban cards
5. ⏳ Create skeleton `printer_service.py`
6. ⏳ Define configuration schema

**Follow-up Sessions:**
1. Implement PrinterService class with card formatting
2. Add configuration management (`~/.taskui/config.ini`)
3. Integrate 'P' key handler in UI
4. Test with real hardware at 192.168.50.99
5. Iterate on card format based on physical usage
6. Add detail level configuration options

---

## References

- [python-escpos Documentation](https://python-escpos.readthedocs.io/)
- [Epson TM-T20III Technical Reference](https://files.support.epson.com/pdf/pos/bulk/tm-t20iii_trg_en_reva.pdf)
- [ESC/POS Command Reference](https://download4.epson.biz/sec_pubs/pos/reference_en/escpos/tmt20iii.html)
- [python-escpos GitHub](https://github.com/python-escpos/python-escpos)

---

**Document Status:** ✅ Complete - Architecture finalized, ready for implementation
**Last Updated:** 2025-11-16
**Paper Specification:** 80mm thermal receipt paper (70 character width)
**Printer Location:** 192.168.50.99:9100
