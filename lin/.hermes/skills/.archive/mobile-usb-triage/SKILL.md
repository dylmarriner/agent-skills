---
name: mobile-usb-triage
description: "USB-level triage for locked Android devices — identify chipset, probe ADB/fastboot, attempt mode switching via control transfers, sysfs operations, and SCSI commands. Covers Samsung, Spreadtrum/Unisoc (TCL/Alcatel), MediaTek, and Qualcomm chipsets."
version: 1.0.0
author: Hermes Agent
---

# Mobile USB Triage

**Trigger:** User wants to factory reset, unlock, or mode-switch a phone connected via USB that isn't responding to ADB/fastboot.

## First — Identify Chipset

```bash
lsusb              # find VID:PID
lsusb -t -d V:P    # check interface classes and driver
lsusb -v -d V:P    # check number of USB configurations
adb devices        # ADB reachable?
fastboot devices   # fastboot reachable?
ls /dev/ttyACM* /dev/ttyUSB*  # modem/serial available?
```

| VID | Chipset | OEMs | Configs | Mode Switchable? |
|-----|---------|------|---------|-----------------|
| 0x04e8 | Samsung Exynos/QC | Samsung | 1-2 (MTP+modem) | Partial — AT commands via built-in ACM serial (SWATD=0 DDEXE) |
| 0x1782 | Spreadtrum/Unisoc | TCL, Alcatel | 1 (MTP only) | **No** — USB dead end |
| 0x0e8d | MediaTek | Xiaomi, Oppo, Realme | 1-2 | Preloader via UART |
| 0x05c6 | Qualcomm | Various | 1 | EDL (9008) via test point |
| 0x12d1 | HiSilicon Kirin | Huawei | 1 | Fastboot only |

## Samsung — MTP Mode (PID 6860) — Has Built-in CDC ACM Serial

Post-2022 Samsung (A54/S24) expose **1 USB config** in MTP mode, but still include a CDC ACM serial across interfaces 1+2. The serial is **always accessible as `/dev/ttyACM0`** — no config switching needed.

**Interface layout in MTP mode (A54 Exynos 1380):**
```
Interface 0 (MTP/PTP):     bulk 0x81 IN, 0x01 OUT, interrupt 0x82 IN
Interface 1 (CDC Control): interrupt 0x84 IN  (AT command signaling)
Interface 2 (CDC Data):    bulk 0x83 IN, 0x02 OUT (modem data channel)
```

The serial talks to the **modem CPU** (CP), NOT the application processor (AP). The AP proxies all traffic through PACM.

### AT Command Probing

```python
import serial, time
ser = serial.Serial('/dev/ttyACM0', 115200, timeout=2)
time.sleep(0.3)
ser.reset_input_buffer()
ser.write(b'AT\r\n')
time.sleep(1)
data = ser.read(1024)
```

**Modem-level commands (work — bypass PACM):**
| Command | Response | Meaning |
|---------|----------|---------|
| `AT` | `OK` | Modem alive |
| `AT+SWATD=0` | `[DR]: CHANGE TO DDEXE` / `[ATD]: CHANGE TO DDEXE` | Switch modem to download/debug mode (internal only) |
| `AT+SWATD=1` | `[DR]: CHANGE TO ATD` / `[ATD]: CHANGE TO ATD` | Switch modem to AT data mode |
| `AT+SWATD=2` | `[DR]: ATD` + `ERROR` | Already in ATD mode |

The SWATD command is handled **entirely by the modem CPU** — it changes the modem's internal USB personality but does NOT affect the AP-side USB gadget, so the PC sees no PID/interface change. The AP must also be told to switch, which requires PACM-registered commands.

**AP-gated commands (blocked by PACM):**
| Command | Response | Meaning |
|---------|----------|---------|
| `AT+SWAT=1` | `+CME Error:PACM(AP),UNREGISTED` | Feature not registered on AP side |
| `AT+ADBENABLE=1` | `+CME Error:PACM(AP),UNREGISTED` | Same |
| `AT+USBADB=1` | `+CME Error:PACM(AP),UNREGISTED` | Same |
| `AT+SSW=2` | `+CME Error:PACM(AP),UNREGISTED` | Same |
| `AT+DEBUGLVC=0,5` | `+CME Error:PACM(AP),PROTECTED_NO_TOK` | Needs auth token |
| `AT+CGSN` | `+CME Error:PACM(AP),NOT_ALLOWED_CRO` | Cross-operation blocked |

### PACM Gatekeeper (Protocol Access Control Module)
The AP intercepts all modem AT commands and checks against a registered service table:
- `UNREGISTED` = AP hasn't registered this feature (common on consumer firmware)
- `PROTECTED_NO_TOK` = needs an authorization token the AP hasn't issued
- `NOT_ALLOWED_CRO` = cross-operation restricted

On stock Samsung OneUI 6.x firmware, most engineering/debug features are unregistered. Only basic modem diagnostics (`AT`, `AT+SWATD`, `AT+DUMPCTRL`) pass through.

**S24 (Exynos 2400) MTP-mode AT is unreliable — don't expect a clean channel.** On the S24 in normal MTP mode (`04e8:6860`), an AT probe against `/dev/ttyACM0` (open at 115200 raw, `AT`/`ATI`/`AT+CGSN`/`AT+GMM`) **hung and timed out** — no `OK`, no response at all. This matches the AP holding the modem (AP-control-mode restriction, same failure seen over Windows COM8). So on the S24 specifically, the MTP-mode ACM port is NOT a usable AT path; treat any read that never returns as the expected outcome and don't block the session on it. The actionable path is download mode (`04e8:685d`) — see `exynos-download-mode`.

### MTP App Data Directory Access for MDM Investigation

Even in MTP mode, `Android/data/` directories for installed apps are often readable:

```bash
# Mount phone via MTP
go-mtpfs /tmp/mtp_mount
ls /tmp/mtp_mount/Android/data/

# Find MDM-related app data
find /tmp/mtp_mount/Android/data/ -maxdepth 3 -type d | grep -iE "mdm|miradore|provision|knox"

# Read Miradore MDM logs (typically contains server URL, enrollment key)
cat /tmp/mtp_mount/Android/data/com.miradore.client.v2/files/miradore.log.0
```

**What the Miradore log tells you:**
- Client version and build (e.g. v2.18.8 build 468)
- Enrollment status — `"Not Work Profile or Fully Managed"` = pre-enrollment
- MDM server URL (typically `gateway.miradore.com`)
- Enrollment key / auth ID (UUID format)
- Knox/SAFE support version
- Registration failure reasons (`NETWORK_ERROR` = WiFi off)

**Useful MTP app data directories to check:**
- `com.android.managedprovisioning/files/download_cache/` — MDM provisioning cache
- `com.miradore.client.v2/files/` — MDM agent logs and config
- `com.google.android.gms/` — Google Play Services (device policy)

### ADB Enable — No USB/AT Bypass Works (Confirmed)

On A54/S24 OneUI 6.x+, NO USB-level or AT-command method enables ADB. The ONLY path is on-device: Settings → Developer Options → USB Debugging. This is blocked if MDM policy has locked Developer Options via DevicePolicyManager.

**If Developer Options is MDM-blocked, the practical options are:**
1. Keep WiFi OFF permanently — MDM can't register without internet (Miradore fails with NETWORK_ERROR)
2. Block DNS to `gateway.miradore.com` at the router level
3. Enter Download Mode via key combo (Vol Down + Vol Up + USB) and use ODIN protocol
4. Physical testpoint method for EUB mode (hardware-level, soldering required)

### USB Rebind Recovery

After a failed pyusb session leaves the ACM serial stalled:

```bash
# Find device path
ls /sys/bus/usb/devices/ | grep "^1-"
# Unbind interface-level driver
echo "1-2:1.1" | sudo tee /sys/bus/usb/drivers/cdc_acm/unbind
echo "1-2:1.1" | sudo tee /sys/bus/usb/drivers/cdc_acm/bind
# Or device-level (more aggressive):
echo "1-2" | sudo tee /sys/bus/usb/drivers/usb/unbind
sleep 3
echo "1-2" | sudo tee /sys/bus/usb/drivers/usb/bind
```

The interface-level unbind/bind is preferred — it only affects the CDC ACM driver, leaving MTP access intact.

## Spreadtrum/Unisoc (TCL, Alcatel) — USB Dead End

Confirmed via extensive testing on TCL OneTouch T312A (0x1782:0x4d01):

- **Only 1 USB configuration** in MTP mode (no modem/ACM)
- **No ADB** (USB debugging off)
- **No fastboot** (bootloader not accessible from MTP)
- **No serial port** (no CDC ACM / ttyUSB endpoints)

### Control Transfers — accepted but inert

```python
# These requests complete (return 0 bytes) but the device ignores them
dev.ctrl_transfer(0x40, 0x34, 1, 0, b'')  # fastboot — accepted, ignored
dev.ctrl_transfer(0x40, 0x34, 2, 0, b'')  # recovery — accepted, ignored
dev.ctrl_transfer(0x40, 0x34, 3, 0, b'')  # download — accepted, ignored
```

Spreadtrum vendor requests (0xA0, 0xB0, 0xC0, 0xD0) all time out. AOA protocol not supported.

### sysfs operations — dangerous

```bash
echo "bus-port" | tee /sys/bus/usb/drivers/usb/unbind  # DEVICE DISAPPEARS
echo "bus-port" | tee /sys/bus/usb/drivers/usb/bind    # won't reattach without physical replug
```

**Once the kernel usb-storage driver is detached via pyusb, it CANNOT be reattached.** Only physical unplug/replug restores the connection.

### The Only Reliable Method

Physical key combo into recovery, then `Wipe data/factory reset`:

- **Vol UP + Power**: Recovery (release Power at OEM logo)
- **Vol DOWN + Power**: Fastboot (some models)
- **Both Volume + Power**: Emergency download

## MediaTek — Preloader Mode

Not fully covered here — see references.

## Qualcomm — EDL Mode (9008)

Not fully covered here — see references.

## Pitfalls

- **Do NOT detach kernel driver via pyusb on Spreadtrum MTP-only devices** — you lose USB access until physical replug
- **Do NOT assume control transfers that return 0 actually did something** — they're accepted at USB protocol level but don't reach the Android framework
- **Do NOT assume Samsung methods generalize** — AT commands, config switching, and Odin are Samsung-specific. Spreadtrum, MediaTek, and Qualcomm each require their own approach
- **sysfs device-level unbind** (`echo bus-port | tee unbind`) removes the entire device — interface-level unbind (`echo bus-port:1.0 | tee unbind`) only removes the driver, which also can prevent reattachment

## Samsung — Download Mode (ODIN Protocol)

Samsung Exynos devices in download mode present at PID `0x685D` with:
- Interface 0: CDC Communications class 0x02 (interrupt endpoint for control)
- Interface 1: CDC Data class 0x0A (bulk endpoints IN/OUT — Odin protocol)

The Odin protocol: send `ODIN` → expect `LOKE` reply over bulk transfers.
Confirmed working on Exynos 2400 (S24 SM-S921B). See `exynos-download-mode` skill.

**PIT read now WORKS on Exynos 2400 (verified live 2026-08-30).** The earlier
"PIT read fails" result was missing the modern-bootloader **ZLP (empty-send)**
after each request, plus the correct PIT sub-commands (0x01 dump / 0x02 part /
0x03 end) and the **132-byte PIT entry layout** (not the classic 128). Full
technique, wire framing, and the live 49-partition S24 table:
see `references/s24-live-pit-read.md`.

**Critical:** state machine gets stuck after partial session. Only physical
unplug + power cycle clears it. USB reset has no effect on Exynos 2400.

## References

See `references/tcl-t312a-usb-triage.md` for the full session log with control transfer details, descriptors, and brute-force results.
See `references/samsung-boot-mode-monitor.md` for the full boot-mode VID:PID table covering Samsung (Odin 04e8:685d/6601/68c3/68ef/4eee/4eef, EUB/BROM 04e8:1234/1100), Qualcomm EDL (05c6:9008/900e/901d/9006), AND MediaTek (0e8d:2000/2001 BROM, 0e8d:0003 preloader), plus the ready-made udev rule for instant (no-polling) detection when a phone enters EDL/BROM/EUB/Odin mode over USB. Also carries the **chipset-verification lesson**: never assume the SoC from the model name — the Redmi Note 13 5G (Dimensity 6080/MT6833V) was wrongly coded as Snapdragon in the suite's `RedmiNote13Forcer`; always confirm VID:PID + `ro.board.platform` before writing device-specific code.
