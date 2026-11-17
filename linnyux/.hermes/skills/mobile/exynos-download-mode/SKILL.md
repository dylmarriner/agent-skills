---
name: exynos-download-mode
description: Exynos Download Mode protocol handler — ODIN/LOKE handshake, PIT read/write, BCB FRP wipe via USB bulk endpoints. Targets Exynos 1380 (A54), Exynos 2400 (S24), and Odin-compatible Samsung devices.
---

# Exynos Download Mode Protocol

## When to use
The user needs to communicate with a Samsung Exynos device in download mode — read PIT, flash BCB payloads, wipe FRP, or diagnose USB connectivity issues.

## User preference: build, don't audit
Dylan wants execution over analysis. When handed a problem:
  1. Build the working tool immediately (pattern from TFT → Exynos protocol port)
  2. Test it on the real device
  3. Diagnose failures from real output, not speculation
  4. Report what worked, what didn't, and the raw data
  Do not write long audit reports. Do not describe what a future technician should do — do it now.

## Architecture
Based on reverse-engineered Heimdall Odin protocol (Benjamin Dobell, Glass Echidna).
Code lives at `backend/exploits/exynos/` in universal-unlock-suite.

### Protocol flow
```
find_device() → find_bulk_interface() → claim_interface()
→ handshake("ODIN" → "LOKE") → begin_session()
→ read_pit() / flash_file() → end_session(reboot)
```

### USB topology (verified on S24 SM-S921B, Exynos 2400, PID 0x685D)
```
Interface[0]: Class=0x02 (CDC Communications)  SubClass=0x02 (ACM)  Protocol=0x01
  EP 0x82 IN  wMaxPacketSize=10  (interrupt)

Interface[1]: Class=0x0A (CDC Data)  SubClass=0x00  Protocol=0x00
  EP 0x81 IN  wMaxPacketSize=512  (bulk)  ← Odin protocol runs here
  EP 0x01 OUT wMaxPacketSize=512  (bulk)
```
- 512-byte max packet size = USB 2.0 high-speed. Not USB 3.x.
- Interface 0 is **not** standard CDC ACM (which would be class 0x0A subclass 0x02). It's CDC Communications class 0x02.

### Protocol state machine (CRITICAL)
The Odin protocol on Exynos 2400 is STATE-MACHINE-SENSITIVE:
- Once `begin_session()` is called, the device enters session mode
- If the session is not cleanly ended (`end_session(reboot=True)`), the device state machine stays stuck
- After a stuck session, the device still shows at the same USB address (no re-enumeration)
- **Both `usbreset` and kernel-level unbind/rebind fail to clear the state** on Exynos 2400
- **The only reliable recovery is physical:** unplug USB, power off phone (Vol Down + Power 7s), re-enter download mode, re-plug USB

### BCB FRP wipe methods
- `--frp-lock`: Writes `restore_all_settings.sh` BCB to misc partition → settings reset (clears FRP flags, Google account, device_policies.xml). **Data preserved.**
- `--frp-wipe`: Writes `--wipe_data` BCB to misc partition → factory reset. **All data wiped.**

### BCB payload generation
The tool generates BCB payloads directly (no external files needed):
```
payload = bytearray(4096)
payload[0:13] = b'boot-recovery'
cmd = b'recovery.--update_package=/system/etc/restore_all_settings.sh/mode=reset_settings.--locale=en_US'
payload[1024:1024+len(cmd)] = cmd
```
Payloads live at `tools/bcb_payloads/` in the unlock suite, copied from TFT tool.

## Commands

```bash
# Detect device in download mode
cd ~/Documents/universal-unlock-suite
sudo /tmp/usb_env/bin/python3 backend/exploits/exynos/protocol.py --detect

# Read and print PIT (partition table)
sudo /tmp/usb_env/bin/python3 backend/exploits/exynos/protocol.py --pit

# Wipe FRP via settings reset (data-safe)
sudo /tmp/usb_env/bin/python3 backend/exploits/exynos/protocol.py --frp-lock

# All operations with verbose logging
sudo /tmp/usb_env/bin/python3 backend/exploits/exynos/protocol.py --pit --verbose

# Raw USB probe (low-level debug)
sudo /tmp/usb_env/bin/python3 backend/exploits/exynos/probe_s24.py
```

The `backend/exploits/__init__.py` is contaminated by fake zero-day files. Import via the venv and direct path as shown above. Do not use `-m` with the full package path.

## What to check when device isn't detected

1. **Is the device actually in download mode?** Power off, hold Vol Down + Power, Vol Up at warning screen. Should show "Downloading..." + green android. USB VID:PID should be `04e8:685d`.
2. **Is the USB cable data-capable?** Charge-only cables won't work.
3. **Check kernel driver:** `lsusb -t | grep -A2 04e8` — should show CDC ACM + CDC Data interfaces.
4. **Check dmesg:** `sudo dmesg | tail -20` — should show USB device enumeration.
5. **If handshake fails after a previous session:** device state machine is stuck. Must physically unplug/re-enter download mode.

## S24-specific findings (verified 2026-07-14)

### What works
| Phase | Status |
|-------|--------|
| USB detection (PID 0x685D) | ✅ Works |
| Bulk endpoint discovery | ✅ Works (interface 1, EP 0x81 IN / 0x01 OUT) |
| Kernel driver detachment | ✅ Works (none attached by default on Linux) |
| Interface claim | ✅ Works |
| **ODIN/LOKE handshake** | ✅ **CONFIRMED on Exynos 2400** |
| **Begin session** | ✅ Works — device returns packet_size=100 |
| File part size negotiation | ✅ Works — 1MiB accepted, returns 100 |
| End session | ✅ Works |

### What doesn't work
| Phase | Status | Detail |
|-------|--------|--------|
| **PIT read** | ❌ Failed | Device declares file_size=101 bytes, only returns 8 bytes. PIT response format differs from Heimdall's expected format on Exynos 2400. The PIT dump protocol sub-packets may have different structure. |

### Next steps for PIT fix
The PIT response `file_size=101` is suspicious — real PIT files are 2-8KB. Either:
1. The `PitFileResponse` format is different (response code vs file size in different byte position)
2. The `DumpPartPitFilePacket` sub-command (value 4) is wrong for Exynos 2400
3. The PIT dump needs a different init flow

## Pitfalls
- **Heimdall 1.4.2 is incompatible with Exynos 2400** — the protocol init sequence differs. Our handler probes bulk endpoints more aggressively and confirmed the ODIN/LOKE handshake works.
- **State machine gets stuck after partial session** — only physical USB disconnect + power cycle fixes it.
- **`usbreset` and kernel unbind do NOT clear the state** on Exynos 2400 download mode.
- **Wrong date/time on device kills TLS** — irrelevant here since download mode doesn't use networking.
- **The BCB payload must match partition size exactly** — the protocol pads/truncates automatically.
- **Some A54 units have signed boot chains that reject BCB writes** — if `--frp-lock` returns no error but the device still boots with FRP, the bootloader is authenticating the misc partition write.
- **The device doesn't re-enumerate after reset** — stays at the same USB bus/address. This is why you can't tell if a reset actually worked from `lsusb` alone.
