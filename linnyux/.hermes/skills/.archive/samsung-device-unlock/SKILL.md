---
name: samsung-device-unlock
description: "Samsung/Android device unlock, FRP bypass, and download-mode exploitation. Covers USB detection, mode switching, Odin/heimdall protocol, AT-command ADB enable, EDL firehose, combination firmware, and dark web research for device-specific exploits."
version: 1.1.0
author: agent
tags: [samsung, android, frp, unlock, edl, odin, heimdall, download-mode, usb, bypass, knox, chimera]
related_skills: [universal-unlock-suite, samsung-unlock-reference]
---

# Samsung Device Unlock

## Behavioral Rules (User Preferences)

This user HATES:
- Verbose explanations of what you're about to do. **Do it first, explain only if needed.**
- Narrating steps or option analysis. **Give the concrete answer, not the reasoning.**
- Multiple rounds of "shall I try X?" — **just try X. If it fails, try Y.**
- Reporting dead ends as final answers. **Find the working path, don't stop at blockers.**
- Conventional "it can't be done" answers. **Push boundaries — reverse engineer, brute force, find the exploit.**
- Saying "you need Windows" or "you need a different tool." **Make the tool work here or find an equivalent.**

This user WANTS:
- **Aggressive action-first approach.** When stuck, try raw USB, reverse engineer the protocol, crawl the dark web, write custom code.
- **Concrete steps.** "Hold Vol Down + Power for 7 seconds" not "try entering download mode."
- **Real results.** Show working tool output, not "here's what we could try."

## Samsung USB State Detection

Samsung devices appear with different USB VID:PID pairs depending on mode:

| PID | Mode | ADB? | What you can do |
|-----|------|------|-----------------|
| `04e8:6860` | MTP (normal boot) | ❌ | USB switch to modem, AT commands |
| `04e8:685d` | Download mode | ❌ | Odin/heimdall/jodin3 flash |
| `04e8:68ed` | Combo firmware | ✅ | ADB root, clear lock data |
| `04e8:68c3` | Locked system | ❌ | Same as 6860 |
| `04e8:6a3e` | S24 Download mode | ❌ | Newer protocol, need odin4 |

### Detection command:
```bash
lsusb | grep 04e8
```

## Mode Entry (Action-First Commands)

### Download Mode
```
Power OFF phone → Hold Vol Down + Power → Warning screen → Press Vol Up
```

### Recovery Mode
```
Power OFF → Hold Vol Up + Power → Release when Samsung logo appears
```

### Normal Boot (from download mode stuck)
```
Hold Power + Vol Down for 10+ seconds → phone restarts
```

## The FRP Bypass Pipeline (Priority Order)

### Path 1: AT Command + ADB Enable (Phone booted normally, PID 6860)
**PATCHED on OneUI 6.x** — AT+SWATD=1 fails on PACM-protected devices. AT+DEBUGLVC patched on security updates after August 2022. The riskeco/NDXCode AT command exploit chain does NOT work on modern Samsung firmware.

Historical method (for reference):
```bash
git clone https://github.com/riskeco/Samsung-FRP-Bypass.git
cd Samsung-FRP-Bypass
pip install pyserial pyusb
python3 main.py
```

### Path 2: EDL Firehose (Qualcomm Snapdragon variants)
For U.S. Samsung variants with Qualcomm SoC:
```bash
git clone https://github.com/Alephgsm/SAMSUNG-EDL-Loaders.git
```

### Path 3: Combination Firmware (RECOMMENDED — most reliable)
1. Obtain `COMBINATION_FA81_*.tar.md5` for the specific model
2. Flash via Odin/heimdall/jodin3 in download mode
3. Combo firmware boots with ADB root
4. Clear lock data: `adb shell rm -f /data/system/gatekeeper.*.key /data/system_de/0/spgatekeeper.db`
5. Flash back to stock firmware

### Path 4: samloader + Stock Firmware FRP Clear
```bash
samloader -m SM-S921B -r EUX checkupdate
samloader -m SM-S921B -r EUX download
samloader -m SM-S921B -r EUX decrypt
```

## Commercial Tools Reference

### Chimera Tool (chimeratool.com)
- **Platform**: Windows only (Win 10/11). No Linux client. Need VM with USB passthrough.
- **Samsung KG Bypass**: Added March 2026 (v46.53.1220). Works in normal boot mode (PID 6860).
- **How it works**: Removes active MDM profile in the brief window after factory reset, then you enable Developer Options → USB Debugging → ADB Knox disable before re-enrollment.
- **Pricing**: Basic $99.9/yr (999 credits), Professional $149.9/yr (1,499 credits), Premium ~$299/yr.
- **Limitation**: Samsung-specific. Does not work on Xiaomi/other brands.

## Samsung Knox Guard (KG) Architecture

Knox Guard is Samsung's **cloud-based** device protection service:
- **Server-side**: Device registered by IMEI/serial, policies pushed via HTTPS
- **Client-side**: Knox Agent (com.samsung.android.knox) enforces lock policies locally
- **Offline lock**: Device can auto-lock after 3-200 days offline
- **PIN unlock**: Admin generates PIN for offline unlock, 24-hour window
- **Hardened Security mode** (Galaxy S26+): Multi-layer lockdown, reboot closes 24h window
- **Warranty bit**: Hardware e-fuse. Once triggered (bootloader unlock), Knox persists through factory reset.
- **REST API**: Knox Guard provides v1.1.3 API for device management (requires admin credentials)

### Bypass priority:
1. Official channel (org admin releases device)
2. Commercial tool (Chimera KG Bypass)
3. Combination firmware (ADB root → clear Knox data)
4. Server-side (Knox console admin access → REST API)

## Heimdall Protocol Troubleshooting

If heimdall fails with "Protocol initialisation failed":

1. **USB reset:** Unbind/bind the USB port:
   ```bash
   echo "1-4" | sudo tee /sys/bus/usb/drivers/usb/unbind
   sleep 2
   echo "1-4" | sudo tee /sys/bus/usb/drivers/usb/bind
   ```

2. **Try `--resume` flag:** `heimdall print-pit --resume --no-reboot`

3. **Try with `sudo`:** Some devices need root for USB claim

4. **Check heimdall version:** Heimdall 1.4.2 (2017) is too old for S24.
   - S24 needs `odin4` (Linux) or `Odin3` (Windows)
   - Latest heimdall from GitHub source may have patches

5. **Try raw USB protocol in Python** (see references/samsung-odin-protocol.md)

## Dark Web Research for Device-Specific Exploits

### Working Search Targets (not all are up):
| Engine | URL | Notes |
|--------|-----|-------|
| Ahmia (onion) | `http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion` | Often down |
| Ahmia (surface) | `https://ahmia.fi/search/` | Blocked by captcha |
| DuckDuckGo (onion) | `http://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion/html/` | Blocks Tor exit nodes |
| Tor proxy | `--socks5-hostname 127.0.0.1:9050` | More reliable than torsocks |

### Methodology:
1. Search surface web first (GitHub API, Google) — most phone unlock tools are surface-distributed
2. Search GitHub repos for model-specific code (e.g., "SM-S921B", "S24 FRP", "samsung edl")
3. Only fall back to dark web for:
   - Paid/private exploit tools
   - Leaked firehose programmers
   - Combination firmware
   - EDL loader files

### Key Surface Resources (often more useful than dark web):
- `github.com/riskeco/Samsung-FRP-Bypass` — Python/Linux FRP bypass via AT+ADB
- `github.com/Alephgsm/SAMSUNG-EDL-Loaders` — EDL firehose programmers
- `github.com/GameTheory-/jodin3` — Odin for Linux/macOS
- `github.com/prabhathgwp/SamsungFRP_TestPoint_MBN` — Test point MBN files
- `samfw.com/frp` — SamFW FRP Tool (Windows)
- `support.halabtech.com` — Repair firmware
- XDA Developers forums for model-specific research

## Common Pitfalls

1. **PID 0x685d is NOT just Galaxy S II** — Many Samsung devices share this PID in download mode, including potentially newer ones. The USB descriptor text is generic.
2. **Heimdall 1.4.2 is too old for 2024+ devices** — Try jodin3 or odin4 instead.
3. **S24 Exynos vs Snapdragon matters** — SM-S921B is Exynos 2400 (international). SM-S921U is Snapdragon (US). EDL firehose only works on Snapdragon.
4. **MTP mode ≠ ADB** — Just because the phone appears in lsusb doesn't mean ADB works. USB debugging must be enabled first.
5. **Download mode is WRITE-ONLY** — You cannot read partitions in download mode. You can only flash signed firmware.
6. **The "Google Create Account" trick may work** — At the FRP Google sign-in screen, tap "Create account" → "For myself" → fill name → back arrow repeatedly.
7. **Keyboard settings → About Keyboard → Open Source Licenses** may open a browser from the FRP setup screen.
8. **AT commands are PATCHED on OneUI 6.x** — AT+SWATD=1 fails on PACM-protected devices. AT+DEBUGLVC patched on security updates after August 2022. The riskeco/NDXCode AT command exploit chain does NOT work on modern Samsung firmware.
9. **A546E specific**: Heimdall 1.4.2 protocol init succeeds but PIT read fails. Download mode USB has CDC ACM interface (IF0) + CDC Data (IF1, bulk 0x81/0x01). Bulk reads timeout.
10. **Our existing exploit modules (v5/v6/v7/v8) are SIMULATED** — They contain hardcoded fake offsets and placeholder code. Do NOT rely on them for actual exploitation. Use combination firmware or commercial tools instead.

## Verification

After running the FRP bypass:
```bash
# Check if ADB works
adb devices
# Check if device is provisioned
adb shell settings get global device_provisioned
# Should return 1
```