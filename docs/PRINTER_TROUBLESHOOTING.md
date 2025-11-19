# Printer Troubleshooting Guide

**Hardware:** Epson TM-T20III @ 192.168.1.100
**Last Updated:** 2025-11-16

---

## Issue 1: Port 9100 Connection Refused

**Symptom:**
```
✗ Print failed: Device not found (Could not open socket for 192.168.1.100:
[Errno 111] Connection refused)
```

**Root Cause:**
The Raspberry Pi is configured as a CUPS print server, not for raw socket printing.

**Port Scan Results:**
- ✓ Port 80 (HTTP) - OPEN - Web interface available
- ✓ Port 631 (IPP/CUPS) - OPEN - CUPS print server
- ✗ Port 9100 (Raw printing) - CLOSED

**Analysis:**
The printer is accessible via CUPS (Internet Printing Protocol) on port 631, but raw ESC/POS socket printing on port 9100 is not enabled.

### Solution Options

#### Option A: Enable Raw Printing on Port 9100 (Recommended for Direct Control)

**Pros:**
- Direct ESC/POS control
- Faster printing
- No CUPS middleware
- Simpler architecture

**Steps:**
1. SSH into Raspberry Pi: `ssh pi@192.168.1.100`
2. Install `cups-backend-bjnp` or configure raw printing
3. Set up port 9100 forwarding to printer
4. Restart CUPS: `sudo systemctl restart cups`

**Alternative - Use `socat` for port forwarding:**
```bash
# On Raspberry Pi
sudo apt-get install socat
socat TCP-LISTEN:9100,fork,reuseaddr TCP:localhost:631
```

#### Option B: Use CUPS Printing via python-escpos (Current Architecture)

**Pros:**
- Works with current setup
- Standard print server architecture
- Queue management built-in
- Easy to configure

**Cons:**
- Requires CUPS printer name
- Slight performance overhead
- Less direct ESC/POS control

**Implementation:**
```python
from escpos.printer import CupsPrinter

# Instead of:
# printer = Network("192.168.1.100", port=9100)

# Use:
printer = CupsPrinter("TM-T20III")  # or actual CUPS printer name
```

**Steps to find printer name:**
1. Access CUPS web interface: http://192.168.1.100:631
2. Go to Printers tab
3. Note the printer name (e.g., "TM-T20III", "EPSON_TM_T20III", etc.)
4. Use that name in CupsPrinter()

#### Option C: Use IPP (Internet Printing Protocol) URL

**Implementation:**
```python
from escpos.printer import File

# Print via IPP URL
printer_url = "ipp://192.168.1.100:631/printers/TM-T20III"
# Configure python-escpos to use IPP
```

---

## Issue 2: CUPS Printer Name Unknown

**Symptom:**
Cannot use `CupsPrinter()` without knowing the printer name.

**Solution:**
Access CUPS web interface to discover printer name:

```bash
# Option 1: Web browser
open http://192.168.1.100:631

# Option 2: Command line (if you have SSH access)
ssh pi@192.168.1.100 'lpstat -p'
```

---

## Issue 3: Network Connectivity

**Symptoms:**
- Connection timeout
- No route to host
- Network unreachable

**Diagnostic Steps:**

1. **Check network connectivity:**
```bash
ping 192.168.1.100
```

2. **Check port availability:**
```bash
nc -zv 192.168.1.100 631
nc -zv 192.168.1.100 9100
```

3. **Check from Raspberry Pi side (SSH in):**
```bash
ssh pi@192.168.1.100
sudo systemctl status cups
lpstat -p
```

---

## Issue 4: Python Library Import Errors

**Symptom:**
```
ModuleNotFoundError: No module named 'escpos'
```

**Solution:**
```bash
pip install python-escpos Pillow
```

**Verify installation:**
```bash
python3 -c "from escpos.printer import Network; print('✓ python-escpos installed')"
```

---

## Diagnostic Checklist

Use this checklist when troubleshooting printer issues:

- [ ] Raspberry Pi is powered on and accessible
- [ ] Printer is powered on
- [ ] Network connectivity verified (`ping 192.168.1.100`)
- [ ] Port 631 (CUPS) is accessible (`nc -zv 192.168.1.100 631`)
- [ ] python-escpos is installed
- [ ] CUPS printer name is known
- [ ] Thermal paper is loaded
- [ ] No paper jams or errors on printer

---

## Next Steps for Story 1

**Current Status:** Port 9100 raw printing is not available.

**Recommendation:** Proceed with Option B (CUPS printing) for now:
1. Access http://192.168.1.100:631 to find printer name
2. Update test script to use `CupsPrinter` instead of `Network`
3. Test printing via CUPS
4. Consider enabling port 9100 in future if direct ESC/POS needed

**Decision Point for User:**
- **Quick path:** Use CUPS (update test script now)
- **Full control path:** Configure port 9100 on Raspberry Pi (requires SSH access)

---

## Reference Commands

```bash
# Network diagnostics
ping 192.168.1.100
nc -zv 192.168.1.100 631
nc -zv 192.168.1.100 9100

# CUPS web interface
open http://192.168.1.100:631

# SSH to Raspberry Pi
ssh pi@192.168.1.100

# Check CUPS status
systemctl status cups
lpstat -p -d

# Install python-escpos
pip install python-escpos Pillow

# Test import
python3 -c "from escpos.printer import Network, CupsPrinter; print('OK')"
```

---

## ✅ SOLUTION IMPLEMENTED: Port 9100 Raw Printing Enabled

**Date:** 2025-11-16
**Status:** ✓ Working

### What We Did

Enabled raw ESC/POS printing on port 9100 using `socat` to forward TCP connections directly to the USB printer device.

**Setup Commands (on Raspberry Pi):**
```bash
# Install socat
sudo apt-get install -y socat

# Create systemd service for automatic startup
sudo tee /etc/systemd/system/printer-raw.service << 'EOF'
[Unit]
Description=Raw Printer Access on Port 9100
After=cups.service

[Service]
Type=simple
ExecStart=/usr/bin/socat TCP-LISTEN:9100,fork,reuseaddr FILE:/dev/usb/lp0,raw
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable printer-raw.service
sudo systemctl start printer-raw.service
```

**Test Results:**
- ✓ Port 9100 accessible
- ✓ Connection successful
- ✓ Hello World printed
- ✓ Text formatting works (bold, underline, center)
- ✓ Auto-cut functional

### Architecture Finalized

**Network Path:**
```
TaskUI → TCP Socket (port 9100) → Raspberry Pi → socat → /dev/usb/lp0 → Epson TM-T20III
```

**Python Implementation:**
```python
from escpos.printer import Network
printer = Network("192.168.1.100", port=9100, timeout=60)
printer.text("Hello World\n")
printer.cut()
```

---

**Status:** ✅ Story 1 Complete - Raw printing on port 9100 fully functional

---

## Final Solution Summary

**Working Configuration:**
- **Library:** python-escpos (Network class)
- **Connection:** Direct TCP socket to 192.168.1.100:9100
- **Transport:** socat forwarding (GOPEN:/dev/usb/lp0,noctty)
- **Cut behavior:** Partial cut (perforated edge, intentional for kanban cards)

**Key Learnings:**
1. Must call `printer.close()` after `printer.cut()` to flush cut command
2. Partial cut is normal and desirable for receipt printers
3. python-escpos handles Epson-specific commands better than raw ESC/POS
4. Buffer clearing via `ESC @` prevents leftover text from previous jobs

**Tested and Working:**
- ✅ Text printing
- ✅ Bold formatting
- ✅ Underline formatting
- ✅ Center alignment
- ✅ Double-height text
- ✅ Auto-cut (partial perforation)

**Final Test Script:** `scripts/test_printer_connection.py`

---

## Common User Issues

### Issue: "Printer not connected" in TaskUI

**Symptom:** Warning message "Printer not connected" when pressing 'P'

**Solutions:**
1. Check printer is powered on
2. Verify printer IP in `~/.taskui/config.ini`
3. Test connection: `ping <printer_ip>`
4. Run validation: `python3 scripts/validate_printer.py`
5. Restart TaskUI to reconnect

### Issue: TaskUI starts but printer doesn't initialize

**Symptom:** No error, but printer doesn't work

**Check logs:**
```bash
# Look for printer warnings in TaskUI output
taskui 2>&1 | grep -i printer
```

**Common causes:**
- Config file not found (`~/.taskui/config.ini` missing)
- Wrong IP address in config
- Firewall blocking port 9100

### Issue: Printed cards are blank

**Symptom:** Printer cuts paper but nothing prints

**Solutions:**
1. Check thermal paper is loaded correctly (thermal side down)
2. Test if paper is thermal: scratch it with fingernail (should turn black)
3. Replace paper if old/faded
4. Run hardware validation to test printer

### Issue: Text is cut off or wraps incorrectly

**Symptom:** Task titles or notes don't display properly

**Solutions:**
- This should not happen with current implementation
- Report as bug with task title/notes content
- Maximum recommended title length: ~200 characters

### Issue: Printer jams or paper feed problems

**Solutions:**
1. Power off printer
2. Remove paper roll
3. Clear any jammed paper
4. Check for debris in paper path
5. Reload paper correctly
6. Power on and test

### Issue: socat service stops working

**Symptom:** Printing worked before, now fails with connection error

**Check service status:**
```bash
ssh pi@192.168.1.100
sudo systemctl status printer-raw.service
```

**Restart service:**
```bash
sudo systemctl restart printer-raw.service
```

**Check logs:**
```bash
sudo journalctl -u printer-raw.service -n 50
```

---

## Getting Help

1. **Check logs** - Look for error messages in TaskUI output
2. **Run validation** - `python3 scripts/validate_printer.py`
3. **Review this guide** - Most issues are covered above
4. **Check printer manual** - For hardware-specific issues
5. **GitHub issues** - Report bugs or ask for help
