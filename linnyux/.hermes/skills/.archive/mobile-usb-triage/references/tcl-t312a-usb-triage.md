# TCL OneTouch T312A (Alcatel) — USB Triage Session Log

**Date:** 2026-07-07
**Model:** TCL OneTouch T312A (Alcatel 4042S)
**Chipset:** Spreadtrum/Unisoc SC9832E
**VID/PID:** 0x1782:0x4d01
**USB Mode:** MTP only (single configuration, mass storage class)

## Initial State

- `lsusb` → Bus 001 Device 035: ID 1782:4d01
- `lsusb -t | grep 1782` → Port 004, If 0, Class=Mass Storage, Driver=usb-storage, 480M
- `lsusb -v` → 1 configuration, 1 interface (Mass Storage, SCSI, Bulk-Only), EP 0x89 IN / 0x0a OUT
- `adb devices` → empty; `fastboot devices` → empty; `/dev/ttyACM* /dev/ttyUSB*` → none

## USB Control Transfer Results

### Standard Android vendor requests (bRequest=0x34)
- wValue=0 (reboot): timed out
- wValue=1 (fastboot): accepted, ignored
- wValue=2 (recovery): accepted, ignored
- wValue=3 (download): accepted, ignored

### Spreadtrum vendor requests (0x40)
- 0xA0 (wValues 0-3), 0xB0, 0xC0, 0xD0: all timed out

### Other attempts
- AOA protocol: timed out (not supported)
- SCSI `sg_raw`: DID_TIME_OUT
- sysfs unbind: device disappears, **cannot reattach without physical replug**
- sysfs deauthorize/reauthorize: no mode change
- Brute force (21 sequences): none triggered mode switch

## Critical Findings

1. **Spreadtrum locked-MTP is a USB dead end.** Unlike Samsung (config-switchable), Spreadtrum has **exactly 1 USB config with 1 mass-storage interface**.
2. **Control transfers accepted but inert.** Return 0 bytes at USB protocol level but never reach Android framework.
3. **No known USB method** triggers reboot, mode switch, or factory reset on locked TCL/Alcatel Spreadtrum from MTP.
4. **Physical key combo is the only reliable method.** Vol UP + Power (release Power at TCL logo, keep Vol UP). Alternative: Vol DOWN+Power or both Volume buttons + Power.
5. **sysfs unbind is dangerous** — disconnects until physical replug. Kernel storage driver won't reattach via bind after pyusb detach.
