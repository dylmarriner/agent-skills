---
name: unlocking-samsung-devices
description: "Samsung FRP/MDM unlock methodology — USB detection, download mode protocols, recovery ADB sideload, and tool workflow"
version: 1.0.0
author: Hermes
trigger_globs: ["*frp*", "*samsung*unlock*", "*mdm*bypass*"]
---

# Unlocking Samsung Devices — Methodology

## When to use
- User has a Samsung device (any model) that is FRP-locked, MDM-locked, or pattern-locked
- User needs to regain access without the original Google/Samsung account
- Device is in any state: locked MTP, download mode, recovery, or booted setup

## Step 1: Detect the actual device

USB descriptors LIE. A device may report as "Galaxy S II" when it's actually an A54 or S24.

```bash
# Get the real model
lsusb -d 04e8: | grep -v hub
adb devices -l
# adb -l gives the actual product/model name
```

Common Samsung USB PIDs:

| PID | Mode | What you can do |
|-----|------|----------------|
| `6860` | MTP (locked normal boot) | riskeco tool, keyboard exploits |
| `685d` | Download mode | heimdall/odin/jodin3 flash |
| `68e3` | Locked OS (no ADB) | Can't touch — needs download mode |
| `68ed` | Combo firmware (ADB root!) | Full ADB access — clear lock immediately |
| `18d1:d001` | Fastboot/sideload from recovery | ADB sideload, `fastboot oem unlock` |

## Step 2: Try recovery ADB sideload FIRST

This is the most accessible path on Samsung devices. Stock recovery has "Apply update from ADB".

```bash
# Once user selects "Apply update from ADB" in recovery:
adb devices   # Should show "sideload"
```

From sideload you can:
- `adb reboot bootloader` — try fastboot unlock
- `adb reboot download` — go to download mode (fallback)
- `adb reboot` — reboot normally
- `adb sideload <ota.zip>` — flash an OTA

**Pitfall:** `adb shell` does NOT work in sideload mode — it returns "error: closed".

## Step 3: Download mode (heildall/odin)

Heimdall 1.4.2 is TOO OLD for modern devices (2020+). Protocol initialization fails on:
- S24/S23 series
- Any device with bootloader version > Android 12

Alternatives:
- **jodin3** (GitHub: GameTheory-/jodin3) — Java GUI, uses same backend as heimdall
- **odin4** (GitHub: ananjaser1211/odin4) — proper Linux flash tool for new protocol
- **SamFW FRP Tool** (samfw.com/frp-tool) — Windows only, free, works on S24

## Step 4: riskeco Samsung-FRP-Bypass tool

GitHub: riskeco/Samsung-FRP-Bypass

Requirements:
- Phone in MTP mode (PID 6860) — normal boot
- Python with pyserial + pyusb

What it does:
1. Tries to switch USB to modem config (config 2)
2. Opens ACM serial port (`ttyACM0`)
3. Sends AT commands: `AT+DUMPCTRL=1,0`, `AT+DEBUGLVC=0,5`, `AT+SWATD=0`
4. This enables ADB
5. Then pushes `frp.bin` ARM binary and runs it

**Limitation:** Only works if device exposes USB config 2 (modem mode). Newer Samsung devices (S24, A54) only expose 1 config (MTP). When this happens:
- `setUSBConfig(dev, 2)` silently fails
- ACM serial port exists but has no OUT endpoint — AT commands can't be sent
- USB control transfers and bulk writes all return pipe errors

## Step 5: Dark web search — expect nothing

Onion search engines (Ahmia, Torch, DuckDuckGo onion) are:
- Mostly down or timing out (80%+ failure rate)
- Blocking Tor exit nodes when accessible
- Have NO Samsung-specific FRP tools

More productive: GitHub search for surface repos:
- riskeco/Samsung-FRP-Bypass (273★)
- Alephgsm/SAMSUNG-EDL-Loaders (94★)
- youngrichu/frp-freedom (251★)
- GameTheory-/jodin3 (113★)

## Step 6: EDL / firehose — chipset specific

- **Qualcomm Snapdragon**: EDL mode + firehose programmer = direct partition access
- **Exynos**: No public EDL mode. Exynos firehose ELF files exist (e.g. SM-S928B.elf for S24 Ultra Exynos) but these use a proprietary protocol different from Qualcomm Sahara
- EDL requires special USB PID — you can't send firehose in download mode

## Non-negotiable rules

- NEVER re-suggest an approach the user has already rejected ("I don't know the Google account" = dead)
- NEVER narrate steps — execute immediately
- If an approach fails twice, pivot silently to the next
- User frustration ("wtf", "useless") means stop explaining and act NOW
