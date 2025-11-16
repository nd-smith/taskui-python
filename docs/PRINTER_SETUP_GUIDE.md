# Thermal Printer Setup Guide

Complete guide for setting up and using the thermal printer feature in TaskUI.

## Overview

TaskUI can print physical kanban cards to a thermal receipt printer, creating tangible task cards for your physical board. Press **'P'** on any task to print it with all its children as a clean, readable card.

**Hardware:** Epson TM-T20III (or compatible ESC/POS thermal printer)
**Paper:** 80mm thermal receipt paper
**Connection:** Network (IP address)

---

## Hardware Requirements

### Supported Printers
- **Epson TM-T20III** (tested and validated)
- **Any ESC/POS compatible thermal printer** (80mm)

### Network Setup
- Printer must be accessible via IP address
- Port 9100 (raw printing protocol)
- Network connectivity from your computer to printer

---

## Installation

### 1. Install Dependencies

TaskUI requires the `python-escpos` library for thermal printing:

```bash
pip install python-escpos Pillow
```

Or if using the project:
```bash
pip install -r requirements.txt
```

### 2. Verify Printer Network Connection

Test that you can reach the printer:

```bash
ping 192.168.50.99  # Replace with your printer's IP
```

If the printer is connected via USB and you need to forward it to a network port (e.g., on a Raspberry Pi):

```bash
# Forward USB printer to network port 9100
socat TCP-LISTEN:9100,fork,reuseaddr GOPEN:/dev/usb/lp0,noctty
```

---

## Configuration

### 3. Create Configuration File

Create `~/.taskui/config.ini`:

```bash
mkdir -p ~/.taskui
cp .taskui/config.ini.example ~/.taskui/config.ini
```

### 4. Edit Configuration

Edit `~/.taskui/config.ini`:

```ini
[printer]
# Your printer's IP address
host = 192.168.50.99

# Port (usually 9100 for raw printing)
port = 9100

# Connection timeout in seconds
timeout = 60

# Print detail level (currently only 'minimal' supported)
detail_level = minimal

# Auto-cut after printing
auto_cut = true

# Enable logging for printer operations
enable_logging = true
```

### 5. Environment Variable Overrides (Optional)

You can override config values with environment variables:

```bash
export TASKUI_PRINTER_HOST=192.168.1.100
export TASKUI_PRINTER_PORT=9100
export TASKUI_PRINTER_TIMEOUT=30
```

---

## Validation

### 6. Test Printer Connection

Run the hardware validation script:

```bash
python3 scripts/validate_printer.py
```

This will:
1. Test printer connection
2. Print several test cards
3. Validate all printing features
4. Confirm everything works correctly

Expected output:
```
✓ PASS - Connection
✓ PASS - Test Print
✓ PASS - Task with Children
✓ PASS - Task with Notes
✓ PASS - Edge Cases

✓ ALL VALIDATIONS PASSED
```

If any tests fail, see [Troubleshooting](#troubleshooting) below.

---

## Using the Printer

### In TaskUI Application

1. **Start TaskUI:**
   ```bash
   taskui
   ```

2. **Select a task** using arrow keys

3. **Press 'P'** to print the selected task

4. **Check the printer** for your physical card!

### Card Format

Cards are printed in a clean, minimal format:

```
[Big Bold Title]

[ ] Subtask 1
[ ] Subtask 2
[X] Subtask 3 (completed)

[auto-cut]
```

**Features:**
- **Title:** Large, bold, double-height text (very readable)
- **Children:** Checkboxes `[ ]` or `[X]` for completed tasks
- **Notes:** If task has no children, notes are printed instead
- **Spacing:** Extra spacing between children and after title for readability
- **Auto-cut:** Automatic cutting for easy separation

---

## Troubleshooting

### Printer Not Connected

**Symptom:** "Printer not connected" warning when pressing 'P'

**Solutions:**
1. Check printer is powered on
2. Verify network connection: `ping <printer_ip>`
3. Test port accessibility: `telnet <printer_ip> 9100`
4. Check config.ini has correct IP address
5. Restart TaskUI to reconnect

### Connection Timeout

**Symptom:** "Connection timeout" error

**Solutions:**
1. Increase timeout in config.ini: `timeout = 120`
2. Check firewall isn't blocking port 9100
3. Verify printer isn't busy with another job
4. Check network speed/stability

### Print Fails But Connection Works

**Symptom:** Connection succeeds but printing fails

**Solutions:**
1. Check paper is loaded
2. Verify printer isn't in error state (paper jam, etc.)
3. Try test print: `python3 scripts/validate_printer.py`
4. Check printer logs for errors
5. Power cycle the printer

### Partial Cut Only

**Symptom:** Cards have perforation but don't fully separate

**Behavior:** This is **normal** for many thermal printers

The printer creates a perforation line between cards that you can easily tear along. This is the expected behavior for the Epson TM-T20III and similar models.

### Text Wrapping Issues

**Symptom:** Text doesn't wrap properly or is cut off

**Solutions:**
1. This shouldn't happen with current implementation
2. Report issue with task title length and content
3. Check `PRINTER_TROUBLESHOOTING.md` for details

### USB Printer on Raspberry Pi

**Setup for USB printer:**

1. **Install socat:**
   ```bash
   sudo apt-get install socat
   ```

2. **Find USB device:**
   ```bash
   ls -l /dev/usb/lp*
   ```

3. **Forward USB to network port:**
   ```bash
   socat TCP-LISTEN:9100,fork,reuseaddr GOPEN:/dev/usb/lp0,noctty
   ```

4. **Make it permanent (systemd service):**

   Create `/etc/systemd/system/escpos-forward.service`:
   ```ini
   [Unit]
   Description=ESC/POS USB to Network Forwarder
   After=network.target

   [Service]
   Type=simple
   User=root
   ExecStart=/usr/bin/socat TCP-LISTEN:9100,fork,reuseaddr GOPEN:/dev/usb/lp0,noctty
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   Enable and start:
   ```bash
   sudo systemctl enable escpos-forward
   sudo systemctl start escpos-forward
   ```

---

## Advanced Configuration

### Multiple Printers

Currently, TaskUI supports one printer at a time. To switch printers:

1. Update `~/.taskui/config.ini` with new IP
2. Or set environment variable: `export TASKUI_PRINTER_HOST=<new_ip>`
3. Restart TaskUI

### Print Quality

For best quality:
- Use high-quality thermal paper
- Keep printer clean (printhead, rollers)
- Replace paper when it fades
- Store paper in cool, dry place

### Paper Loading

1. Open paper compartment
2. Load 80mm thermal paper roll
3. Feed paper through until it emerges
4. Close compartment
5. Test with validation script

---

## Paper and Supplies

### Recommended Paper
- **Size:** 80mm (3.15") thermal paper
- **Type:** BPA-free thermal receipt paper
- **Length:** 50m to 80m rolls
- **Brands:** Any quality thermal paper for POS systems

### Where to Buy
- Office supply stores
- Amazon/online retailers
- POS equipment suppliers
- Restaurant supply stores

### Storage
- Keep in sealed package until use
- Store in cool (<25°C), dry place
- Avoid direct sunlight
- Use within 1-2 years for best quality

---

## Quick Reference

### Key Bindings
- **P** - Print selected task card

### CLI Commands
```bash
# Run validation tests
python3 scripts/validate_printer.py

# Start TaskUI
taskui

# View config
cat ~/.taskui/config.ini
```

### Config Location
- **Linux/Mac:** `~/.taskui/config.ini`
- **Example:** `.taskui/config.ini.example`

### Logs
Check logs for printer operations:
```bash
# If using systemd logging
journalctl -u taskui -f

# Or check TaskUI logs directly
# (location depends on your logging setup)
```

---

## Support

### Documentation
- `PRINTER_TROUBLESHOOTING.md` - Detailed troubleshooting
- `PRINT_TASKS.md` - Implementation details
- `README.md` - General TaskUI documentation

### Hardware Issues
- Check printer manual
- Contact manufacturer support
- Verify printer is ESC/POS compatible

### Software Issues
- Check GitHub issues
- Review logs for error messages
- Run validation script for diagnostics

---

## Frequently Asked Questions

**Q: Can I use a different printer model?**
A: Yes, any ESC/POS compatible 80mm thermal printer should work.

**Q: Does it work with USB printers?**
A: Yes, but you need to forward USB to network port (see USB setup above).

**Q: Can I print in color?**
A: No, thermal printers are black and white only.

**Q: How do I print multiple cards at once?**
A: Press 'P' on each task individually. Bulk printing not currently supported.

**Q: Can I customize the card format?**
A: Currently only MINIMAL format is supported. Format customization may be added later.

**Q: Will the cards fade over time?**
A: Yes, thermal printing fades. Use BPA-free paper and proper storage for longer life (months to years depending on conditions).

---

## Example Workflow

1. **Morning:** Print today's high-priority tasks
2. **Physical Board:** Attach cards to kanban board with tape/magnets
3. **Work:** Mark progress on physical cards
4. **Evening:** Update TaskUI with completed items
5. **Archive:** Store completed cards or dispose

---

**Happy Printing! 🖨️**
