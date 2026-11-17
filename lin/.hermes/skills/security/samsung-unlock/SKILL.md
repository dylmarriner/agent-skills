---
name: samsung-unlock
description: Unlock pattern/PIN/password-locked Samsung Android devices via download mode → heimdall → ADB → lock data clear. Covers S2 through S24 series, USB detection, AT command channel, and known pitfalls.
version: 1.1.0
---

# Samsung Device Unlock

Three distinct classes of lock. Identify which one FAST:

| Lock Type | Phone State | USB Mode | Approach |
|-----------|------------|----------|----------|
| **FRP lock** (Factory Reset Protection) | Boots to setup wizard, stuck at WiFi/Google screen | MTP (0x6860) | AT command method (best) or setup wizard exploit |
| **Screen lock** (pattern/PIN/password) | Normal OS boots, lock screen appears | MTP or nothing | Download mode → combination firmware → ADB root |
| **FRP + locked download** | FRP at setup, heimdall fails on S23+ | 0x685d (proto mismatch) | Riskeco AT method (booted) or jodin3 (download) |
| **MDM lock** (Mobile Device Management) | Boots to setup, auto-enrolls to company, re-locks after reset | MTP (0x6860) or recovery sideload | Recovery sideload → Knox packages disable, or Samsung OKTA/Intune removal |
| **FRP + MDM** | Setup screen, needs both cleared | MTP (0x6860) | Recovery → wipe data, then ADB sideload → clear both |

**CRITICAL:** Ask FIRST if the phone boots normally to setup or shows a lock screen. These are completely different flows. Also check the PID — `0x685d` is shared across many generations (S2 descriptor text but often a much newer device like A54).

**USER PREFERENCE — DO NOT VIOLATE:**
- Do NOT repeat questions the user has already answered. If they told you once they don't know the Google account, move on immediately. Never circle back.
- Do NOT explain what you are about to do. Just do it. Send the command, report the result.
- Do NOT present options or ask which path they prefer. Pick one and execute. Tell them what happened.
- Do NOT apologize or narrate the difficulty. Results only.
- When a method fails, switch to the next one immediately with no gap explanation.

## Trigger Conditions

- User mentions locked Samsung, pattern/PIN lock, FRP lock
- User asks to unlock a phone over USB
- **STYLE: Aggressive action, not explanation. Try a method immediately. If it fails, try the next. No walls of text, no option-presenting. The user will tell you when they want options.**
- **PROTOCOL: Once the user has the phone in a particular mode (MTP, download, recovery sideload), STOP rebooting it. Work from that mode. Each reboot destroys progress and frustrates the user.**

---

## Flow A — AT Command Method (PREFERRED for FRP on S20–S24)

The most reliable Linux-compatible FRP bypass. Uses Samsung's Exynos modem processor — it responds to AT commands independently of Android, even when the OS is locked at the setup screen.

**Requires:** Phone booted normally (0x6860 MTP mode at WiFi screen). NOT download mode.

### Steps

```bash
# 1. Clone
git clone https://github.com/riskeco/Samsung-FRP-Bypass.git
cd Samsung-FRP-Bypass

# 2. Install deps
pip install pyserial pyusb

# 3. Run (auto: USB switch → AT commands → ADB → FRP clear)
python3 main.py
```

### What it does internally

1. **USB switch:** Finds Samsung at `0x6860`, resets USB, sets configuration 2 (modem mode). This changes the USB interface from MTP to CDC ACM serial. May need two passes (USB re-enumeration).

2. **AT commands:** Opens the new serial port (`/dev/ttyACM*`), sends:
   - `AT+SWATD=1` — Enable ADB
   - `AT+DEBUGLVC=0,5` — Max debug level
   - `AT+DUMPCTRL=1,0` — Enable dump control

3. **ADB clear:** Pushes `frp.bin` payload, sets `setup_wizard_has_run=1`, `user_setup_complete=1`, `DEVICE_PROVISIONED=1`

### Debugging

```bash
# Watch for new serial port after USB switch
ls /dev/ttyACM* /dev/ttyUSB*
dmesg | tail -20 | grep -i "acm\|usb\|serial"

# If no serial port appears:
sudo modprobe cdc_acm usbserial
```

### Manual fallback (after ADB connects)
```bash
adb shell settings put global setup_wizard_has_run 1
adb shell settings put secure user_setup_complete 1
adb shell content insert --uri content://settings/secure --bind name:s:DEVICE_PROVISIONED --bind value:i:1
adb shell am start -n com.android.settings/.Settings
```

**Key insight:** The AT method works because Samsung's Exynos modem co-processor runs independently. It accepts AT commands even when Android is locked. Qualcomm Snapdragon variants may not expose this interface the same way.

---

## Flow B — Setup Wizard Exploits (fallback if AT method fails)

Try these rapidly, one after another. Don't explain — just guide:

1. **Keyboard → Settings:** WiFi screen → tap name field → keyboard opens → gear icon → "About Samsung Keyboard" → "Open Source Licenses" → browser → download FRP APK
2. **Emergency dialer:** "Emergency Call" → `*#0*#` → hardware test → Back may dump to Settings
3. **TalkBack + Chrome:** Enable TalkBack (double-tap hold) → navigate with gestures → Chrome → download APK
4. **Google Assistant:** "Hey Google, open Chrome" / "open Settings"
5. **QR Scan:** On SIM/QR screen → scan any QR → gallery access → may reach browser

---

## Flow C — Screen Lock (download mode path)

### Device Identification
PID 0x685d is shared across generations. Don't trust lsusb text labels.

| PID | Likely Device |
|-----|--------------|
| 0x685d | Galaxy S2–S7+, A54 (SM-A546E), some S8/S9, the descriptor lies |
| 0x6a3e | S24 (S921) |
| 0x6a44 | S24+ (S926) |
| 0x6a4a | S24 Ultra (S928) |

### Protocol
- **Pre-2020 (PID 0x685d):** heimdall 1.4.2 works. Reset USB before retry on failure.
- **S23+ (PID 0x685d but new protocol):** heimdall FAILS handshake. Need jodin3 (Linux) or Odin3 (Windows).
- **Raw Python USB:** Bulk endpoints on interface 1 (OUT 0x01, IN 0x81). ODIN/SBL1/DLMG magic → all timeouts on S24.

### USB reset before heimdall
```bash
python3 -c "
import usb.core, usb.util
dev = usb.core.find(idVendor=0x04e8)
if dev: dev.reset()
"
sudo heimdall print-pit --no-reboot
```

### If heimdall fails → switch to jodin3
```bash
git clone https://github.com/GameTheory-/jodin3.git
# Flash combination firmware or FRP partition clear
```

### Lock data clear (once ADB root from combo firmware)
```bash
adb shell rm -f \
  /data/system/gatekeeper.password.key \
  /data/system/gatekeeper.pattern.key \
  /data/system_de/0/spgatekeeper.db
adb reboot
```

---

## Flow D — jodin3 + EDL Firehose (advanced, Exynos 2400)

For S24 Exynos variants where heimdall fails. jodin3 is the maintained Odin alternative (updated June 2026).

EDL firehose programmers for Exynos 2400:
- SM-S928B (S24 Ultra) has a firehose ELF (675KB) at Alephgsm/SAMSUNG-EDL-Loaders
- SM-S921B (S24 base) currently has NO firehose — S928B's may work (same SoC)

---

## Auto-Watcher Script

A USB watcher daemon that auto-detects Samsung devices and runs the unlock pipeline:
- Monitors USB for VID 0x04e8
- On 0x685d (download mode) → prompts for combination firmware
- On 0x68ed (combo firmware) → auto-clears lock via ADB
- On 0x6860 (MTP) → suggests riskeco AT method

---

## Key Pitfalls

1. **lsusb lies** — "Galaxy S II" descriptor is reused across generations. PID 0x685d is shared by S2 through S9+.
2. **Heimdall handshake fail** — On S23+, the protocol changed. USB reset helps 50% of the time. If it still fails, switch to jodin3 immediately.
3. **USB control transfers pipe out** — Download mode (0x685d) doesn't accept vendor 0x40 transfers. Use bulk endpoints.
4. **ACM serial is dead in download mode** — Interface 0 (CDC ACM) exists but doesn't respond to AT commands. AT commands only work from MTP mode.
5. **Riskeco USB switch fails on S24/A54** — Modern Samsung devices only have 1 USB configuration (MTP). The tool tries `set_configuration(2)` which doesn't exist. ACM serial port won't accept AT commands without the modem config.
6. **Combination firmware is signed** — Must be flashed via Odin, not just written. Model-specific: `COMBINATION_FA81_S921B*.tar.md5` for S24.
6. **Don't fight heimdall endlessly** — Two retries max, then switch to jodin3 or riskeco.
7. **FRP vs Screen Lock** — Clarify immediately. FRP needs AT/exploit. Screen lock needs download mode.
8. **Rapid action > explanation** — User signals frustration? Stop talking, try the next method.

---

## Remote Unlock (no USB)

- **Samsung Find My Mobile:** https://findmymobile.samsung.com — needs Samsung account
- **Google Find My Device:** https://google.com/android/find — "Lock" → new PIN overrides current

---

## Tool Reference

See `references/s24-tools-research.md` for the full research dump (dark web crawl results, GitHub URLs, confirmed dead ends, 8-minute deep search across 100+ onion sites).

---

## Flow E — Recovery ADB Sideload (MDM devices)

If the phone is MDM-enrolled (auto-re-locks during setup), the standard FRP bypass won't work. The MDM profile survives factory reset and re-enrolls at setup.

### Access recovery
```bash
# From off: hold Volume Up + Power
# From download mode: hold Volume Up + Power (or Vol Down + Power to exit DM)
```

In recovery, select **"Apply update from ADB"** . The device shows as:
```
$ adb devices
R5CW90M2ZQH  sideload  product:a54xnsxx model:SM_A546E device:a54x
```

### What sideload mode allows
- `adb sideload <ota.zip>` — flash an OTA update
- `adb reboot` — reboot normally
- `adb reboot recovery` — reboot back to recovery
- `adb reboot download` — reboot to download mode
- NO `adb shell`, NO `adb push`, NO `adb root`

### MDM removal path
1. In sideload mode: `adb reboot recovery`
2. Wipe data/factory reset
3. Reboot to setup — MDM profile removed if Knox packages were previously disabled

For Samsung **Knox Guard / Knox Manage MDM**, you need full ADB access to run:
```bash
adb shell pm disable-user --user 0 com.samsung.android.kgclient
adb shell pm uninstall --user 0 com.samsung.android.kgclient
adb shell pm uninstall --user 0 com.samsung.android.mdm
adb shell pm disable-user --user 0 com.sec.enterprise.knox.cloudmdm.smdms
```
Get full ADB via: recovery wipe → setup → safe mode → Developer Options → USB Debugging.

### Safe mode (bypasses MDM auto-lock)
After factory reset, during first boot: **Power on + HOLD Volume Down**. Keep holding until "Safe mode" appears. MDM policies don't load. Use this to reach Settings → Developer Options → enable USB Debugging → then ADB shell to uninstall MDM packages.

---
