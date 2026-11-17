# ADB Device Optimization — Worked Session

This captures a real session optimizing an **OPPO A40 (CPH2669)** running **Android 15**.

## Baseline State

| Metric | Before |
|--------|--------|
| MemFree | ~128 MB |
| MemAvailable | ~1.7 GB (estimated) |
| Free RAM (dumpsys) | ~2.5 GB cached |
| Storage | 33 GB used / 103 GB |
| Animations | 1.0x (default) |
| Swap used | 1.4 GB / 5.2 GB |

## Key RAM Hogs Identified

- `system_server` — 637 MB
- `com.android.systemui` — 333 MB
- `com.google.android.gms` — 314 MB (×2 processes)
- `com.google.android.youtube` — 242 MB
- `com.facebook.orca` — 234 MB
- `com.android.vending` — 220 MB
- `com.google.android.apps.photos` — 169 MB
- `org.telegram.messenger` — 166 MB
- `io.homeassistant.companion.android` — 164 MB
- `com.heytap.market` (OPPO bloat) — 156 MB
- `com.google.android.googlequicksearchbox` (hotword detection) — 106 MB

## Commands Run

### Diagnostics
```bash
adb shell dumpsys meminfo
adb shell df -h /data
adb shell cat /proc/meminfo | grep -E "MemTotal|MemFree|MemAvailable|Cached"
adb shell top -b -n 1 -d 1 | head -20
adb shell settings get global window_animation_scale
adb shell settings get global transition_animation_scale
adb shell settings get global animator_duration_scale
adb shell getprop ro.product.model  # CPH2669
adb shell getprop ro.build.version.release  # 15
```

### Optimizations

```bash
# 1. Animation speed-up
adb shell settings put global window_animation_scale 0.5
adb shell settings put global transition_animation_scale 0.5
adb shell settings put global animator_duration_scale 0.5

# 2. Clear all app caches
adb shell pm trim-caches 999G

# 3. Force-stop heavy background apps
adb shell am force-stop com.facebook.orca
adb shell am force-stop com.facebook.katana
adb shell am force-stop com.facebook.appmanager
adb shell am force-stop com.facebook.services
adb shell am force-stop com.google.android.youtube
adb shell am force-stop com.heytap.market
adb shell am force-stop com.coloros.weather2
adb shell am force-stop com.coloros.weather.service
adb shell am force-stop com.google.android.apps.photos

# 4. Disable Google Assistant hotword (reclaim ~100MB)
adb shell pm disable-user --user 0 com.google.android.googlequicksearchbox
# Re-enable if needed:
adb shell pm enable --user 0 com.google.android.googlequicksearchbox
```

### After State

| Metric | After |
|--------|-------|
| MemFree | ~200 MB |
| MemAvailable | ~2.6 GB |
| Free RAM (dumpsys) | ~2.5 GB |
| Storage | 32 GB used (freed ~1 GB) |
| Animations | 0.5x |

## Lesson: Google Assistant Trade-off

The user said "yes I use hey google" after Google App was disabled. The fix was immediate re-enable with `adb shell pm enable --user 0 ...`. This is a critical user-communication step — **always confirm the user doesn't need Assistant before disabling its background service**, since it frees ~100 MB of RAM at the cost of losing voice activation.

## Udev Rules Setup (OPPO-specific)

```python
import subprocess
with open('/tmp/51-android.rules', 'w') as f:
    f.write('SUBSYSTEM=="usb", ATTR{idVendor}=="22d9", ATTR{idProduct}=="2769", MODE="0666", GROUP="plugdev"\n')
p = subprocess.Popen(['sudo', '-S', 'cp', '/tmp/51-android.rules', '/etc/udev/rules.d/51-android.rules'],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
out, err = p.communicate(b'<password>\n', timeout=5)
```

Then:
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
adb kill-server && sleep 1 && adb start-server
```

## APK Install Pattern (Expo/React Native)

The Mealify app was an Expo 50 project at `/media/kubuntux/DEVELOPMENT1/Mealify/apps/mobile/`.

Build:
```bash
cd apps/mobile/android && ./gradlew clean assembleDebug
```

Replace old APK:
```bash
adb uninstall com.dylanmarriner.mealify
adb install app/build/outputs/apk/debug/app-debug.apk
adb shell monkey -p com.dylanmarriner.mealify -c android.intent.category.LAUNCHER 1
```

**Common pitfall:** Debug APKs try to connect to Metro bundler (`ws://localhost:8081`). If Metro isn't running, the app shows a red error screen. The build must export the JS bundle first (`npx expo export --platform android`) or build a release variant (`assembleRelease`).
