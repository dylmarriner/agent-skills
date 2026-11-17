---
name: android-automation
description: Control Android devices via ADB with support for UI layout analysis (uiautomator), visual feedback (screencap), device optimization, and APK installation. Use when you need to interact with Android apps, perform UI automation, take screenshots, optimize device performance, or install apps.
---

# Android Automation

Control and automate Android devices using ADB, uiautomator, screencap, and shell commands.

## Connecting Devices

### USB Connection
1. Enable **Developer Options** and **USB Debugging** on the device.
   - Settings → About Phone → Tap **Build Number** 7 times
   - Settings → Developer Options → Enable **USB Debugging**
2. Connect via USB and verify with `adb devices`.

### Troubleshooting: "no permissions" on Linux
If `adb devices` shows `no permissions (missing udev rules?)`:

**Create udev rules (requires sudo):**
```bash
# Write udev rule covering major Android vendors
sudo tee /etc/udev/rules.d/51-android.rules >/dev/null << 'EOF'
# Google (Pixel/Nexus)
SUBSYSTEM=="usb", ATTRS{idVendor}=="18d1", MODE="0666", GROUP="plugdev"
# Samsung
SUBSYSTEM=="usb", ATTRS{idVendor}=="04e8", MODE="0666", GROUP="plugdev"
# OnePlus / OPPO
SUBSYSTEM=="usb", ATTRS{idVendor}=="22d9", MODE="0666", GROUP="plugdev"
# Xiaomi
SUBSYSTEM=="usb", ATTRS{idVendor}=="2717", MODE="0666", GROUP="plugdev"
# Huawei
SUBSYSTEM=="usb", ATTRS{idVendor}=="12d1", MODE="0666", GROUP="plugdev"
# LG
SUBSYSTEM=="usb", ATTRS{idVendor}=="1004", MODE="0666", GROUP="plugdev"
# Motorola
SUBSYSTEM=="usb", ATTRS{idVendor}=="22b8", MODE="0666", GROUP="plugdev"
# Sony
SUBSYSTEM=="usb", ATTRS{idVendor}=="054c", MODE="0666", GROUP="plugdev"
# HTC
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bb4", MODE="0666", GROUP="plugdev"
# ASUS
SUBSYSTEM=="usb", ATTRS{idVendor}=="0b05", MODE="0666", GROUP="plugdev"
EOF

# Apply rules
sudo chmod 644 /etc/udev/rules.d/51-android.rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Restart ADB
adb kill-server
adb start-server
```

**Pitfall — sudo password with heredoc:** When using the terminal tool, `sudo tee << 'EOF'` combined with password-on-stdin (`sudo -S`) can conflict. If it hangs or fails, use Python subprocess as a reliable workaround:
```python
import subprocess
with open('/tmp/51-android.rules', 'w') as f:
    f.write('SUBSYSTEM=="usb", ATTRS{idVendor}=="22d9", MODE="0666", GROUP="plugdev"\n')
p = subprocess.Popen(['sudo', '-S', 'cp', '/tmp/51-android.rules', '/etc/udev/rules.d/51-android.rules'],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
p.communicate(b'password\n', timeout=5)
```

**Alternative (add user to plugdev group):**
```bash
sudo usermod -aG plugdev $USER
# Then log out and log back in (or reboot)
```

**Verify connection:**
1. Unplug and replug USB cable
2. On phone: Allow USB debugging (check "Always allow")
3. Run `adb devices` — should show as `device` (not `unauthorized` or `no permissions`)

If it shows `unauthorized`, the phone's RSA fingerprint prompt needs to be accepted on screen.

**Automated verification:**
Use the included script: `scripts/verify-adb-setup.sh`

### Wireless Connection (Android 11+)
1. Enable **Wireless Debugging** in Developer Options.
2. **Pairing**: Find the IP, port, and pairing code in the "Pair device with pairing code" popup.
   `adb pair <ip>:<pairing_port> <pairing_code>`
3. **Connecting**: Use the IP and port shown on the main Wireless Debugging screen.
   `adb connect <ip>:<connection_port>`
4. Verify with `adb devices`.

**Pitfall:** The pairing port and connection port are different. The "Pair device with pairing code" popup shows the pairing port; the main Wireless Debugging screen shows the connection port. Don't confuse them.

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
- **Text**: `adb shell input text "<text>"` (Note: Use `%s` for spaces in some environments or handle quoting carefully)
- **Keyevent**: `adb shell input keyevent <keycode>` (Home: 3, Back: 4, Power: 26, Search: 84, Enter: 66)
- **Swipe**: `adb shell input swipe <x1> <y1> <x2> <y2> <duration_ms>`

### Visual Verification
Take a screenshot to verify the state:
`adb shell screencap -p /sdcard/screen.png && adb pull /sdcard/screen.png ./screen.png`

### Installing APKs
Push and install an APK to the connected device:
```bash
# Install/reinstall (preserves data)
adb install -r /path/to/app.apk

# Fresh install (removes existing data first)
adb install -d /path/to/app.apk

# Check if package already installed
adb shell pm list packages | grep com.your.package
```

### Device Diagnostics
Quick health check of the connected device:
```bash
# Device info
adb shell getprop ro.product.model
adb shell getprop ro.build.version.release

# Memory
adb shell cat /proc/meminfo | grep -E "MemTotal|MemFree|MemAvailable|Cached"

# Storage
adb shell df -h /data | tail -3

# CPU load
adb shell cat /proc/loadavg

# Top processes by RAM
adb shell dumpsys meminfo | grep "Total RSS by process:" -A 30 | head -35

# Top processes by CPU
adb shell top -b -n 1 -d 1 | head -20

# Battery
adb shell dumpsys battery | grep -E "status|level|power|temperature"
```

## Device Optimization

Run these steps (in order) to speed up and free resources on a connected Android device:

### 1. Speed up animations (instant feel improvement)
```bash
adb shell settings put global window_animation_scale 0.5
adb shell settings put global transition_animation_scale 0.5
adb shell settings put global animator_duration_scale 0.5
```
Reduce to 0.5x for snappier feel. Set to 0.0 to disable entirely. Revert by setting to `1.0`. Changes persist across reboots.

### 2. Clear app caches
```bash
# Broad cache clear (all apps)
adb shell pm trim-caches 999G

# Per-package cache clear (target specific heavy apps)
adb shell pm clear --cache-only com.google.android.youtube
```
Check which apps are using the most RAM first via diagnostics, then target those.

### 3. Force-stop heavy background apps
```bash
# Stop non-critical background processes
adb shell am force-stop com.facebook.orca
adb shell am force-stop com.facebook.katana
adb shell am force-stop com.facebook.appmanager
adb shell am force-stop com.facebook.services
adb shell am force-stop com.google.android.youtube
adb shell am force-stop com.heytap.market
adb shell am force-stop com.coloros.weather2
```
**Warning:** These restart when opened normally. Don't force-stop system apps or anything critical.

### 4. Disable battery-draining background services
```bash
# Disable Google Assistant hotword detection (saves ~100MB RAM)
# Only if user doesn't use "Hey Google"
adb shell pm disable-user --user 0 com.google.android.googlequicksearchbox
# Re-enable with:
adb shell pm enable --user 0 com.google.android.googlequicksearchbox
```

### 5. Storage trim (frees up flash performance)
```bash
adb shell fstrim -v /data
```
Not supported on all kernels — may fail silently.

### 6. Verify improvements
```bash
# Check free RAM before/after
adb shell dumpsys meminfo | grep "Free RAM"

# Check available memory
adb shell cat /proc/meminfo | grep MemAvailable

# Check storage
adb shell df -h /data | tail -3
```

### Pitfalls
- **Google Assistant:** If you disable `com.google.android.googlequicksearchbox`, "Hey Google" won't work. Always ask the user if they use it before disabling.
- **Facebook/Meta suite:** Multiple related processes (orca, katana, appmanager, services) all need to be stopped independently.
- **OPPO/HeyTap devices:** Have additional bloatware services like `com.heytap.market`, `com.coloros.weather2`, `com.oplus.*` that are safe to stop but will restart.
- **USB authorization:** First connection shows "Allow USB debugging?" prompt on phone. Must be accepted. Don't proceed assuming it's authorized.

## Tips
- **Search**: Use `input keyevent 84` to trigger search in many apps.
- **Wait**: Use `sleep <seconds>` between commands to allow the UI to update.
- **Coordinates**: Calculate the center of `[x1,y1][x2,y2]` for reliable taps.
