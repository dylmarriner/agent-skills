---
name: android-adb-1-0-0
description: Control Android devices via ADB with support for UI layout analysis (uiautomator) and visual feedback (screencap). Use when you need to interact with Android apps, perform UI automation, take screenshots, or run complex ADB command sequences.
---

# Android Automation

Control and automate Android devices using ADB, uiautomator, and screencap.

## Installation

### Debian/Ubuntu
```bash
sudo apt install adb
```

### macOS
```bash
brew install android-platform-tools
```

### Verify
```bash
adb version
```

## Connecting Devices

### USB Connection
1. Enable **Developer Options** and **USB Debugging** on the device.
2. Connect via USB and verify with `adb devices`.
3. If `adb devices` shows the device with `no permissions` — you need udev rules (see Connection Troubleshooting below).
4. If it shows `unauthorized` — the user needs to tap **Allow** on the phone's RSA prompt (see Connection Troubleshooting below).

### Wireless Connection (Android 11+)
1. Enable **Wireless Debugging** in Developer Options.
2. **Pairing** (first-time only): Tap "Pair device with pairing code" — a popup appears with an IP:port and 6-digit pairing code. This port is DIFFERENT from the connection port on the main screen.
   `adb pair <ip>:<pairing_port> <pairing_code>`
3. **Connecting**: Use the IP and port shown on the main Wireless Debugging screen (NOT the popup port).
   `adb connect <ip>:<connection_port>`
4. Verify with `adb devices`.

**⚠️ Key wireless gotcha:** The pairing port and connection port are ALWAYS different. The popup gives you a pairing port (for `adb pair`), the main screen gives you a connection port (for `adb connect`). Confusing them produces `protocol fault (couldn't read status message)` errors.

## Device Optimization

Use ADB to improve Android device performance, free RAM, and reclaim storage. Run diagnostics first to identify bottlenecks, then apply targeted optimizations.

### Diagnostics — Baseline
```bash
# Device identity info
adb shell getprop ro.product.model
adb shell getprop ro.build.version.release

# Memory pressure
adb shell cat /proc/meminfo | grep -E "MemTotal|MemFree|MemAvailable|Cached"

# Top RAM consumers
adb shell dumpsys meminfo | grep -A 50 "Total RSS by process:" | head -30

# Storage
adb shell df -h /data

# Animation settings (1.0 = default)
adb shell settings get global window_animation_scale
adb shell settings get global transition_animation_scale
adb shell settings get global animator_duration_scale

# Running processes overview
adb shell top -b -n 1 -d 1 | head -20

# Battery stats
adb shell dumpsys battery | grep -E "status|level|power|temperature"

# Swap pressure
adb shell cat /proc/meminfo | grep Swap
```

### Optimizations

#### 1. Speed up animations (instant snappiness)
Setting animations to **0.5x** makes the phone feel significantly faster with minimal visual difference.
```bash
adb shell settings put global window_animation_scale 0.5
adb shell settings put global transition_animation_scale 0.5
adb shell settings put global animator_duration_scale 0.5
```
To revert to defaults: replace `0.5` with `1.0`, or disable entirely with `0`.

#### 2. Clear app caches (free storage + reduce cruft)
The universal trim command clears cache for all apps at once:
```bash
adb shell pm trim-caches 999G
```
To target specific heavy apps individually:
```bash
adb shell pm clear --cache-only <package_name>
```
Common cache hogs: `com.google.android.youtube`, `com.facebook.orca`, `com.google.android.apps.photos`, `com.heytap.market`.

#### 3. Force-stop heavy background apps (free RAM)
Identify RAM hogs from diagnostics, then force-stop them. They'll restart when opened, so this is safe:
```bash
adb shell am force-stop com.facebook.orca
adb shell am force-stop com.facebook.katana  # Facebook main app
adb shell am force-stop com.google.android.youtube
adb shell am force-stop com.heytap.market     # OPPO market
```
Meta/Facebook background services (`com.facebook.appmanager`, `com.facebook.services`) are particularly aggressive RAM consumers.

#### 4. Disable background assistant services (save ~100MB+ RAM)
The Google App hotword detection service (`com.google.android.googlequicksearchbox`) continuously listens for "Hey Google" and consumes significant RAM. Disabling it reclaims that:
```bash
adb shell pm disable-user --user 0 com.google.android.googlequicksearchbox
```
Re-enable if needed: `adb shell pm enable com.google.android.googlequicksearchbox`

**⚠️ Note:** This disables Google Assistant. Confirm the user doesn't actively use "Hey Google" before doing this.

#### 5. Trim storage (fstrim)
On some kernels, this optimizes flash storage write performance:
```bash
adb shell fstrim -v /data
```
Not available on all kernels — skip if it errors.

#### 6. Check for OPPO/OnePlus/Xiaomi bloatware
List third-party packages that are likely OEM bloat:
```bash
adb shell pm list packages -3 | grep -iE "facebook|market|weather|heytap|coloros|miui"
```
Disable unwanted packages (same `pm disable-user` pattern as above).

### Before/After Verification
Run the diagnostics again after optimizations to demonstrate improvement:
- **MemFree** and **MemAvailable** should increase
- **Free RAM** (from `dumpsys meminfo | grep "Free RAM"`) should rise
- **Storage** should show freed space (e.g., "32G used" vs "33G used" before cache clearing)

For a full worked example, see `references/device-optimization-session.md`.

## Connection Troubleshooting

### USB: "no permissions" / missing udev rules (Linux)
If `adb devices` shows the device but says `no permissions`:
1. Find the vendor ID: `lsusb | grep -i "android\|google\|samsung\|oneplus\|xiaomi\|oppo"`
   Example output: `Bus 001 Device 009: ID 22d9:2769 OPPO Electronics Corp.`
   Vendor ID is the first hex pair (`22d9`), product ID is the second (`2769`).
2. Create a udev rule (requires sudo).
   
   **If you can pass sudo non-interactively** (e.g. terminal tool has access to the password), write the rule to a temp file first then use Python subprocess — this reliably handles the stdin conflict between heredocs and `sudo -S`:
   ```python
   import subprocess
   with open('/tmp/51-android.rules', 'w') as f:
       f.write('SUBSYSTEM=="usb", ATTR{idVendor}=="22d9", ATTR{idProduct}=="2769", MODE="0666", GROUP="plugdev"\n')
   p = subprocess.Popen(['sudo', '-S', 'cp', '/tmp/51-android.rules', '/etc/udev/rules.d/51-android.rules'],
       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
   out, err = p.communicate(b'<password>\n', timeout=5)
   ```
   
   **If you can run sudo interactively**, use tee directly:
   ```bash
   echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="22d9", ATTR{idProduct}=="2769", MODE="0666", GROUP="plugdev"' | sudo tee /etc/udev/rules.d/51-android.rules
   ```
   
   **Pitfall:** Piping `echo` content into `sudo -S tee` while also using a heredoc (`<<<`) causes stdin conflicts where the password is consumed before the content arrives. The temp-file + Python subprocess approach avoids this entirely.
3. Reload: `sudo udevadm control --reload-rules && sudo udevadm trigger`
4. **Restart ADB** (critical — ADB caches permissions, restarting it without killing the server first won't pick up the new rules):
   ```bash
   adb kill-server && sleep 1 && adb start-server && adb devices
   ```
5. If sudo isn't available, fall back to wireless connection.

### USB: "unauthorized" after fixing permissions
After udev rules fix, the device may show as `unauthorized` instead of `no permissions`:
- **Cause:** The phone is waiting for the user to accept the RSA key fingerprint on-screen.
- **Fix:** Tell the user to look at their phone — a prompt "Allow USB debugging?" with the RSA fingerprint should be visible. They need to tap **OK** / **Allow**, and optionally check "Always allow from this computer".
- After approval, run `adb devices` again — it should show as `device` (not `unauthorized`).

### Wireless: "protocol fault" on adb pair
- **Cause:** You're using the connection port (from main Wireless Debugging screen) instead of the pairing port (from the popup).
- **Fix:** Tap "Pair device with pairing code" on the phone — that popup shows a DIFFERENT port. Use that one for `adb pair`.
- After pairing succeeds, use the original port from the main screen for `adb connect` — NOT the popup port.

### Wireless: "failed to connect" after pairing succeeds
- The device may have reconnected to a different WiFi network.
- The device may have gone to sleep — unlock it and check Wireless Debugging is still enabled.
- The connection port on the main screen may have changed — recheck it.
- Try re-pairing: `adb pair <ip>:<new_pairing_port> <code>` then `adb connect <ip>:<connection_port>`.
- **Fallback:** If wireless keeps failing, offer USB as an alternative (which avoids all port confusion).

## Common Workflows

### Launching an App
Use the monkey tool to launch apps by package name:
`adb shell monkey -p <package_name> -c android.intent.category.LAUNCHER 1`

### Analyzing the UI
Dump and pull the UI hierarchy to find coordinates:
`adb shell uiautomator dump /sdcard/view.xml && adb pull /sdcard/view.xml ./view.xml`

Then grep for text or resource IDs to find `bounds="[x1,y1][x2,y2]"`.

### Interacting with Elements
- **Tap**: `adb shell input tap <x> <y>`
- **Text**: `adb shell input text "<text>"` (Note: Use `%\s` for spaces in some environments or handle quoting carefully)
- **Keyevent**: `adb shell input keyevent <keycode>` (Home: 3, Back: 4, Power: 26, Search: 84, Enter: 66)
- **Swipe**: `adb shell input swipe <x1> <y1> <x2> <y2> <duration_ms>`

### Visual Verification
Take a screenshot to verify the state:
`adb shell screencap -p /sdcard/screen.png && adb pull /sdcard/screen.png ./screen.png`

## Tips
- **Search**: Use `input keyevent 84` to trigger search in many apps.
- **Wait**: Use `sleep <seconds>` between commands to allow the UI to update.
- **Coordinates**: Calculate the center of `[x1,y1][x2,y2]` for reliable taps.
