---
name: openclaw-android
description: Build, install, and pair the official OpenClaw Android app with a desktop gateway. Covers source build, flavors, Bonjour auto-discovery, USB tunnel, and pairing.
category: mobile
---

# OpenClaw Android App

Build the official OpenClaw Android client from source and pair it with a desktop OpenClaw gateway.

## Source Location

The Android app lives inside the **official OpenClaw monorepo** at `apps/android/`:

```
git clone https://github.com/openclaw/openclaw.git
cd openclaw/apps/android
```

The shared OpenClawKit (from `apps/shared/OpenClawKit/`) is a Swift package for iOS/macOS. The Android build only consumes its `Resources/` directory (certificates, tool-display config).

## Prerequisites

- Android SDK with platform 31+ and build-tools 34+
- Java 17+ (Gradle handles compatibility via sourceCompatibility)
- `ANDROID_HOME` or `ANDROID_SDK_ROOT` pointing to your SDK
- Gradle wrapper included (`./gradlew`)

## Building

**Debug build** (unsigned, sideload-ready):

```bash
cd apps/android
export ANDROID_HOME=~/Android/Sdk
./gradlew assembleDebug
```

APK output paths:

- `app/build/outputs/apk/play/debug/openclaw-<version>-play-debug.apk` (Google Play flavor — reduced permissions)
- `app/build/outputs/apk/thirdParty/debug/openclaw-<version>-thirdParty-debug.apk` (full permissions — SMS, call log, photos)

**Release build** (signed AAB):

Set signing properties in `~/.gradle/gradle.properties`:

```
OPENCLAW_ANDROID_STORE_FILE=/path/to/keystore
OPENCLAW_ANDROID_STORE_PASSWORD=...
OPENCLAW_ANDROID_KEY_ALIAS=...
OPENCLAW_ANDROID_KEY_PASSWORD=...
```

Then:

```bash
./gradlew bundlePlayRelease    # or bundleThirdPartyRelease
```

The project's `build.gradle.kts` errors with a clear message if a release build is requested without signing properties set.

## Flavors

| Flavor | Permissions | Use Case |
|--------|-------------|----------|
| `play` | Removes SMS, call log, recent-photo access | Google Play Store |
| `thirdParty` | Full: SMS, call log, notifications, contacts, camera, location, photos | Sideload, F-Droid, APKPure |

## Architecture

The Android app is **not a standalone agent**. It is a **remote client** for a desktop OpenClaw gateway:

| Component | Runs On |
|-----------|---------|
| AI agent, inference, tool execution | Desktop |
| Camera, mic, SMS, contacts, location, notifications, motion sensors | Phone |
| Chat UI, voice input, canvas/screen | Phone |

Communication is over WebSocket to the gateway.

## Connecting

### Method 1: Bonjour Auto-Discovery (same WiFi)

1. Ensure desktop OpenClaw gateway is running (`openclaw gateway --port 18789`)
2. Phone and desktop on the same LAN
3. Open the app — it scans for `_openclaw-gw._tcp.` via Android NSD
4. Tap the discovered gateway — pairing request appears on desktop

### Method 2: USB Tunnel (adb reverse)

No WiFi dependency. Tunnels localhost to the phone:

```bash
# Terminal A — start gateway
openclaw gateway --port 18789 --verbose

# Terminal B — reverse tunnel
adb reverse tcp:18789 tcp:18789
```

In the app: **Connect → Manual** — host `127.0.0.1`, port `18789`, TLS off.

### Method 3: Manual IP

If your desktop's LAN IP is stable, enter it directly in the Manual connect screen.

## Pairing

The first connection attempt triggers a pairing request on the desktop:

```bash
# List pending requests
openclaw devices list

# Approve by ID
openclaw devices approve <requestId>
```

## Pitfalls

- **`mDNS` requires `ACCESS_FINE_LOCATION` on Android < 13 / API < 33.** The location permission is used only for network scanning — no GPS data is collected.
- **Splash screen takes ~5-10 seconds** on first launch as the app loads into Jetpack Compose.
- **Canvas commands need the Screen tab open** — the A2UI WebView only processes canvas commands when that tab is active.
- **The `play` flavor strips SMS and call log.** Use the `thirdParty` flavor if those capabilities are needed.
- **`adb reverse` connections break when the USB cable is disconnected.** Re-run the `adb reverse` command after reconnecting.
