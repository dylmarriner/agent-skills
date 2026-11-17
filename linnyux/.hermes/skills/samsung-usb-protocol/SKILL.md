---
name: samsung-usb-protocol
description: "Samsung USB protocol analysis for download mode, MTP, AT command, and ADB enable. Covers endpoint layouts, USB config switching, pyusb communication, and known limitations on Exynos devices with OneUI 6.x+."
version: 1.0.0
author: Hermes Agent
platforms: [linux]
metadata:
  hermes:
    tags: [samsung, usb, pyusb, odin, adb, download-mode, mdm]
    related_skills: [mobile-device-unlock, unlocking-samsung-devices]
---

# Samsung USB Protocol

**Trigger:** Working with Samsung devices over USB — download mode communication, AT command ADB enable, USB config switching, pyusb endpoint discovery.

## Samsung USB PIDs

| PID | Mode | What you can do |
|-----|------|-----------------|
| `04e8:6860` | MTP (normal boot, locked or unlocked) | USB config switch, AT commands, MTP file access |
| `04e8:685d` | Download mode | Odin/heimdall protocol (handshake works, PIT fails on post-2022) |
| `04e8:68ed` | Combo firmware | ADB root — full access |
| `04e8:68e3` | Locked OS, no ADB | Cannot touch |

USB descriptors LIE — all Samsung devices report as "Galaxy S II" regardless of model. Ignore the text, check PID.

## Download Mode USB Endpoint Layout

Post-2022 Samsung in download mode (PID 685d):

```
Interface 0: CDC ACM (Class=0x02, Sub=0x02, Proto=0x01)
  EP 0x82 IN  max=10  type=interrupt   (AT command / control)

Interface 1: CDC Data (Class=0x0a, Sub=0x00, Proto=0x00)
  EP 0x81 IN  max=512 type=bulk        (Odin protocol data)
  EP 0x01 OUT max=512 type=bulk        (Odin protocol data)
```

### Finding endpoints in pyusb — ALWAYS use Interface 1 for bulk:

```python
import usb.core, usb.util
dev = usb.core.find(idVendor=0x04E8, idProduct=0x685D)
cfg = dev.get_active_configuration()
intf = cfg[(1, 0)]                          # Interface 1 = CDC Data
ep_out = usb.util.find_descriptor(intf,
    custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
ep_in  = usb.util.find_descriptor(intf,
    custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)
```

Interface 0 only has an interrupt IN endpoint — using it for bulk writes returns None.

### Heimdall 1.4.2 behavior on post-2022 Samsung

Heimdall 1.4.2 handshakes successfully ("Protocol initialisation successful") but cannot complete partition operations:
- Sending old Odin command format `struct.pack('<II', cmd, flag)` + 504 zero bytes via bulk OUT succeeds (no USB error)
- Bulk IN read always times out (`LIBUSB_ERROR_TIMEOUT`)
- **libusb error -7** = `LIBUSB_ERROR_TIMEOUT`

This is NOT a code bug — the Samsung download protocol framing changed for OneUI 6.x / Android 14+ bootloaders. The new format is undocumented. No open-source tool implements it.

## USB Config Switching (MTP ↔ Modem)

When phone is in MTP mode (PID 6860) and you need the ACM serial port:

```python
import usb.core
from riskeco.Samsung-FRP-Bypass.usbswitcher import setUSBConfig

dev = usb.core.find(idVendor=0x04E8, idProduct=0x6860)
setUSBConfig(dev, 2)   # Modem mode → /dev/ttyACM0 appears if supported
# ... run AT commands ...
setUSBConfig(dev, 1)   # Back to MTP
```

**Model support:**
- **S24 Exynos (SM-S921B):** Only 1 config. `setUSBConfig(dev, 2)` silently fails. No ACM port ever.
- **A54 Exynos (SM-A546E):** Config 2 exists. `setUSBConfig(dev, 2)` succeeds. /dev/ttyACM0 appears.

## AT Command ADB Enable

Once /dev/ttyACM0 is available, send AT commands:

```python
import serial
ser = serial.Serial("/dev/ttyACM0", 115200, timeout=3)
ser.write(b"AT+SWATD=1\r\n")
time.sleep(2)
resp = ser.read(1024)    # Read response
ser.close()
```

**Known AT commands tested on A54 (OneUI 6.x, A546EXXU5CXK3):**

| Command | Response | Meaning |
|---------|----------|---------|
| `AT` | `OK` | Basic handshake works |
| `AT+SWATD=1` | `+USB READY` | ADB was enabled (rare, may work on older fw) |
| `AT+SWATD=1` | `PACM(AP),PROTECTED_NO_TOK` | Blocked by modem firmware (OneUI 6.x) |
| `AT+SWATD=1` | Pure echo of command | Not executed — modem rejecting |
| `AT+ADBENABLE=1` | `PACM(AP),UNREGISTED` | Command unknown or blocked |
| `AT+USBADB=1` | `PACM(AP),UNREGISTED` | Command unknown or blocked |

**PACM (Protocol Access Control Module):** A Samsung modem firmware component that restricts AT commands based on device state. On OneUI 6.x+ with MDM enforcement, it blocks security-sensitive AT commands at the modem processor level — not a kernel toggle, not bypassable via USB control transfers.

## USB Reset for Stalled Endpoints

After failed pyusb/heimdall attempts, endpoints can stall (EPIPE = `[Errno 32] Pipe error`):

```bash
# Identify the USB port first
lsusb -t | grep -B2 04e8

# Reset (substitute correct port path)
echo "1-1" | sudo tee /sys/bus/usb/drivers/usb/unbind
sleep 3
echo "1-1" | sudo tee /sys/bus/usb/drivers/usb/bind
```

Note: This re-enumerates the device with a new address but does NOT clear a stalled endpoint state within the device controller. Physical replug is the only guaranteed reset.

## USB Control Transfer Brute-Force

Testing ADB enable via vendor-specific control requests on MTP-mode phone (PID 6860):

```python
params = []
for bm in [0x42, 0x41, 0xC0, 0x40]:      # request type
    for req in range(0x64, 0x69):           # bRequest
        for val in [0, 1, 2, 5, 0x1000, 0x1001, 0x7]:  # wValue
            for idx in [0, 1, 2, 4]:        # wIndex
                dev.ctrl_transfer(bm, req, val, idx, 64, timeout=2000)
```

On A54 with OneUI 6.x: all vendor requests accepted by USB controller but **none enable ADB**. ADB enablement requires OS-level userspace authorization — cannot be triggered by USB control transfers alone.

## MDM-Locked But Unlocked Phone

A phone can be fully booted, unlocked, and usable but still have MDM restrictions:
- Developer Options shows "Contact your administrator"
- USB debugging blocked at OS level
- AT command ADB enable blocked by PACM at modem level
- USB control transfers accepted but ADB never enabled
- Serial port (ttyACM0) echoes commands without executing

**Practical options to remove MDM when ADB is unavailable:**
1. Physical screen access: Settings → Device admin apps → uncheck MDM
2. Physical screen access: Settings → Accounts → remove work profile
3. Flash combination firmware (requires odin4 + combo files, from download mode)
4. Factory reset WITHOUT MDM policy (wipes data — last resort)

## Pitfalls

- **Do NOT** use Interface 0 for bulk USB operations — it only has an interrupt endpoint
- **Do NOT** assume `dev.reset()` clears all stall states — physical replug is more reliable
- **Do NOT** send Odin commands after a failed heimdall session without a USB reset first — device stays in a half-initialized state
- **Do NOT** claim A54 has no USB config 2 — it does; S24 Exynos does not
- **Do NOT** expect AT+SWATD to work on OneUI 6.x+ — PACM blocks it at the modem firmware level
