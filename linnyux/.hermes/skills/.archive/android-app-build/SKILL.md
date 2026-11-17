---
name: android-app-build
description: "Build Android apps from source — cloning, Gradle setup, Android SDK, ADB install/debug, Tailscale tunnel, and build troubleshooting."
version: 1.0.0
author: Hermes Agent
tags: [android, gradle, adb, build, mobile, app-development, kotlin, jetpack-compose]
---

# Android App Build

Build and deploy Android apps from source repositories. Covers the full lifecycle:
cloning, SDK setup, Gradle build, ADB installation, USB debugging, and wireless
deployment.

## Prerequisites

```bash
export ANDROID_HOME=~/Android/Sdk    # or wherever the SDK lives
```

Required SDK components (verify):

```bash
ls $ANDROID_HOME/platforms/          # android-34, android-35, android-36, etc.
ls $ANDROID_HOME/build-tools/        # 34.0.0, 35.0.0, 36.0.0, 37.0.0, etc.
ls $ANDROID_HOME/platform-tools/     # adb binary lives here
```

Java 17+ is required (AGP 8.x+ mandates it). Check with:

```bash
java -version
```

## Build Flow

### 1. Clone

```bash
git clone --depth 1 <repo-url>
cd <repo>/apps/android      # most projects keep Android under apps/
```

### 2. Inspect Build Config

```bash
cat build.gradle.kts          # root build file
cat app/build.gradle.kts      # app module — check compileSdk, minSdk, targetSdk
cat gradle/libs.versions.toml # version catalog
cat gradle.properties         # JVM args, flags
```

Key things to check:
- **compileSdk** matches installed SDK platforms
- **minSdk** — older minSdk values (21+) build fine on newer SDKs
- **Flavor dimensions** — release builds may need keystore signing config
- **Shared resources** — some projects reference sibling directories (`../../shared/`)

### 3. Build Debug APK

```bash
./gradlew assembleDebug
```

For projects with product flavors:

```bash
./gradlew assemblePlayDebug     # Google Play flavor
./gradlew assembleThirdPartyDebug  # Third-party store flavor
```

**Common pitfalls:**
- **Out of memory:** `org.gradle.jvmargs=-Xmx3g` in `gradle.properties`
- **Kotlin version mismatch:** Check `kotlin` version in `libs.versions.toml` matches installed
- **Missing SDK platform:** Install with `sdkmanager "platforms;android-XX"`
- **AGP version too new for JDK:** AGP 9.x needs JDK 21+
- **Build cache corruption:** `./gradlew clean` or `rm -rf ~/.gradle/caches/`
- **Shared resources path broken:** The `sourceSets` block may reference `../../shared/` — verify the path exists relative to the app module

### 4. Find APK Output

```bash
find app/build/outputs/apk -name "*.apk"
```

Typical paths:
- `app/build/outputs/apk/debug/app-debug.apk`
- `app/build/outputs/apk/play/debug/<name>-play-debug.apk`
- `app/build/outputs/apk/thirdParty/debug/<name>-thirdParty-debug.apk`

### 5. Install via ADB

```bash
# Check device
adb devices -l

# Install
adb install <path-to-apk>

# Or use gradle's built-in install task (if available)
./gradlew installDebug
```

## ADB Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `unauthorized` | Device not trusted on this host | Unplug, re-plug, accept RSA fingerprint prompt on device |
| `no devices/emulators found` | USB debugging disabled or driver issue | Check Developer Options → USB Debugging; try `adb kill-server && adb start-server` |
| `INSTALL_FAILED_UPDATE_INCOMPATIBLE` | Existing install with different signature | `adb uninstall <package>` then re-install |
| `INSTALL_FAILED_INSUFFICIENT_STORAGE` | Device full | Free space on device |
| `Error: INSTALL_PARSE_FAILED_NO_CERTIFICATES` | APK not signed | Debug builds are auto-signed; use `assembleDebug` not `assembleRelease` |

## USB Tunneling (No WiFi Needed)

When the app needs to talk to a service on the build machine (e.g., a gateway at port
18789), use ADB reverse port forwarding:

```bash
# On the build machine
adb reverse tcp:18789 tcp:18789

# Verify
adb reverse --list
# → 127.0.0.1:18789 tcp:18789 tcp:18789
```

Then in the app, connect to `ws://127.0.0.1:18789` (or whatever protocol) as if it were
running locally on the device.

## Remote Access via Tailscale (Global / WiFi)

When the app connects to a gateway or API server that shouldn't be bound to `0.0.0.0`,
use Tailscale Serve:

```bash
# 1. Start the service on loopback only
openclaw gateway --port 18789 --bind loopback    # for OpenClaw
# or
hermes gateway run      # for Hermes (ports 8642 for API, 18789 for gateway)

# 2. Expose via Tailscale Serve
sudo tailscale serve --bg --https=443 <port>

# 3. Generate pairing QR code
openclaw qr --public-url "https://<hostname>.tail<XXXX>.ts.net"
```

Then in the app: **Connect → Manual** → host `<hostname>.tail<XXXX>.ts.net`, port `443`, TLS on.

## Release Builds (Signing)

Release builds need a keystore. Required Gradle properties (set in
`~/.gradle/gradle.properties`):

```properties
OPENCLAW_ANDROID_STORE_FILE=/path/to/keystore.jks
OPENCLAW_ANDROID_STORE_PASSWORD=password
OPENCLAW_ANDROID_KEY_ALIAS=alias
OPENCLAW_ANDROID_KEY_PASSWORD=password
```

(Property names vary per project — check `app/build.gradle.kts` for `providers.gradleProperty(...)` calls.)

Generate a debug keystore if none exists:

```bash
keytool -genkey -v -keystore ~/.android/debug.keystore -alias androiddebugkey \
  -storepass android -keypass android -keyalg RSA -keysize 2048 -validity 10000 \
  -dname "CN=Android Debug, OU=Development, O=Unknown, L=Unknown, ST=Unknown, C=US"
```

## Multiple Devices

When multiple Android devices are connected, target by serial:

```bash
adb devices -l
adb -s RF8NC1JVY8H install app-debug.apk
```

## Pitfalls

- **Do NOT** use `&` to background Gradle builds — they detach and lose log output. Use
  `terminal(background=true)` with Hermes tools instead.
- **Gradle wrapper version** is pinned in `gradle/wrapper/gradle-wrapper.properties`.
  If it's too old for the AGP version, update it with `./gradlew wrapper --gradle-version 8.12`
  (or whatever version matches the AGP).
- **Version catalogs** (`libs.versions.toml`) are the modern way to manage deps. Don't edit
  `build.gradle.kts` dependency blocks directly unless there's no catalog.
- **Build output naming** is often customized via `androidComponents.onVariants { }` or
  `applicationVariants.all { }` — the APK may have a different name than `app-debug.apk`.
  Always check `find ... -name "*.apk"` or look at the build output for the `outputFileName`.
