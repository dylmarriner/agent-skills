---
name: samsung-usb-protocol
description: "Samsung download mode and MTP mode USB protocol analysis — endpoint layout, CDC ACM init sequence, Odin protocol handshake, vendor control requests, AT command serial access, and USB rebind recovery. For reverse-engineering and low-level USB tool development."
version: 1.0.0
author: Hermes Agent
tags: [samsung, usb, pyusb, odin, heimdall, cdc-acm, download-mode, protocol]
---

# Samsung USB Protocol Analysis

**Trigger:** Reverse-engineering Samsung's USB protocol in download mode or MTP mode, fixing pyusb endpoint detection, or recovering from a stalled ACM serial port.

## Download Mode (PID 685d) — USB Endpoint Layout

Post-2022 Samsung (A54, S24) exposes two USB interfaces in download mode:

```
Interface 0 (CDC ACM Control):
  bInterfaceClass=0x02  bInterfaceSubClass=0x02  bInterfaceProtocol=0x01
  EP 0x82 IN  max=10  type=3 (Interrupt)
  — AT command / modem signaling channel

Interface 1 (CDC Data):
  bInterfaceClass=0x0a  bInterfaceSubClass=0x00  bInterfaceProtocol=0x00
  EP 0x81 IN  max=512  type=2 (Bulk)
  EP 0x01 OUT max=512  type=2 (Bulk)
  — Odin protocol data transfer
```

### Correct pyusb endpoint detection

```python
import usb.core, usb.util

dev = usb.core.find(idVendor=0x04E8, idProduct=0x685D)

# Detach kernel drivers
for iface in [0, 1]:
    try:
        if dev.is_kernel_driver_active(iface):
            dev.detach_kernel_driver(iface)
    except: pass

try:
    dev.set_configuration()
except: pass

cfg = dev.get_active_configuration()

# Interface 0 — interrupt endpoint (for AT commands)
intf0 = cfg[(0, 0)]
ep_int = usb.util.find_descriptor(
    intf0, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
)

# Interface 1 — bulk endpoints (for Odin protocol)
intf1 = cfg[(1, 0)]
ep_out = usb.util.find_descriptor(
    intf1, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
)
ep_in = usb.util.find_descriptor(
    intf1, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
)
```

**COMMON BUG:** Using `cfg[(0, 0)]` for bulk endpoints — interface 0 has no bulk OUT endpoint.
Always use `cfg[(1, 0)]` for the CDC Data interface.

### CDC ACM Init Sequence

Before bulk transfers work in download mode, initialize the CDC ACM interface:

```python
import struct

# SET_LINE_CODING (115200 8N1)
line_coding = struct.pack('<IBBBB', 115200, 0, 0, 8, 0)
dev.ctrl_transfer(0x21, 0x20, 0, 0, line_coding, timeout=5000)

# SET_CONTROL_LINE_STATE (assert DTR+RTS)
dev.ctrl_transfer(0x21, 0x22, 0x3, 0, None, timeout=5000)
```

After CDC init, the device may accept Odin protocol commands on bulk endpoints.
However, on OneUI 6.x+ devices, heimdall 1.4.2 "Protocol initialisation" succeeds
but bulk reads still timeout — the Odin command packet format changed.

## Known Protocol Behavior

### Heimdall 1.4.2 on S24/A54

```
Protocol initialisation successful.    ← CDC init works
Beginning session...                    ← Bulk write succeeds
ERROR: libusb error -7 / timeout       ← Bulk read times out
```

The bulk write succeeds (no USB error) but the device never responds. This means:
- The packet format sent by heimdall is NOT what the new bootloader expects
- The new format hasn't been publicly reverse-engineered
- Possible changes: different header magic, different command values, encrypted packets

### Raw USB Probe Results

Sending 512-byte packets with various command headers (0x01, 0x03, 0x64):
- Bulk OUT write: succeeds (no error)
- Bulk IN read: always times out (no response)
- Interrupt endpoint read: also times out

## MTP Mode (PID 6860) — ADB Enable Attempts

### Vendor Control Transfer Brute Force

All tested Samsung vendor requests succeed as USB transfers (return OK) but None
actually enable ADB on A54 Exynos 1380 OneUI 6.x:

```python
for bm in [0x42, 0x41]:
    for req in range(0x64, 0x69):
        for val in [0, 1, 2, 5, 0x1000, 0x1001, 0x7]:
            for idx in [0, 1, 2, 4]:
                dev.ctrl_transfer(bm, req, val, idx, data, timeout=2000)
```

All return OK but ADB stays off. The OS controls USB debugging authorization —
no USB-level command can bypass it.

### AT Command Serial (ttyACM0)

The riskeco tool detects `/dev/ttyACM0` on A54 even without USB config switching.
AT command responses:

| Command | Response | Meaning |
|---------|----------|---------|
| `AT` | `OK` | Modem responsive |
| `AT+SWATD=1` | `+CME Error:PACM(AP),PROTECTED_NO_TOK` | ADB enable refused by protocol access control module |
| `AT+SWATD=1` | `[DR]: CHANGE TO ATD` | Attempt processed but failed silently |
| `AT+ADBENABLE=1` | `+CME Error:PACM(AP),UNREGISTED` | Feature not registered |
| `AT+USBADB=1` | `+CME Error:PACM(AP),UNREGISTED` | Feature not registered |

The PACM (Protocol Access Control Module) on Exynos 1380 latest firmware
prevents ADB enable via AT commands.

## USB Rebind Recovery

After a failed pyusb or heimdall session leaves the ACM serial port stalled:

```bash
# Find the USB bus address
lsusb -d 04e8:
# Example: Bus 001 Device 010 → "1-1" (bus 1, port 1)

# Unbind and rebind
echo "1-1" | sudo tee /sys/bus/usb/drivers/usb/unbind
sleep 3
echo "1-1" | sudo tee /sys/bus/usb/drivers/usb/bind
sleep 5
```

After rebind, the device re-enumerates at a new address (same PID).
The ttyACM0 port will also be recreated.

## Working ADB Enable Path (Phone Booted + Unlocked)

No USB-level or AT-command method works on A54/S24 OneUI 6.x+.
The ONLY path is:
1. Phone screen: Settings → About Phone → Software Information → tap Build Number 7x
2. Settings → Developer Options → USB Debugging → ON
3. Accept RSA fingerprint prompt on phone screen

## Tools Reference

- `github.com/riskeco/Samsung-FRP-Bypass` — Python AT command ADB enabler (works on older Samsung)
- `github.com/GameTheory-/jodin3` — Java Odin for Linux/Mac (wraps heimdall protocol)
- `heimdall 1.4.2` — Partial handshake OK on S24/A54, PIT/flash fail
