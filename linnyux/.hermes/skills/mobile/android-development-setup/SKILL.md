---
name: android-development-setup
category: mobile
description: Complete Android development environment setup from scratch on Linux
---

# android-development-setup

Complete Android development environment setup from scratch. This skill covers Android Studio installation, SDK configuration, ADB setup, environment variables, and Android Virtual Device (AVD) creation.

## When to use
- Setting up a new Linux machine for Android development
- Troubleshooting Android SDK/SDK Manager issues
- Configuring environment variables for Android development
- Creating Android Virtual Devices (AVDs)
- Installing or troubleshooting platform-tools (ADB, fastboot)

## Prerequisites
- Linux with at least 19 GB disk space
- Java 17+ installed (OpenJDK recommended)
- Internet connection for downloads (800 MB - 1.5 GB)
- Terminal access

## Setup Steps

### 1. Download Android Studio

```bash
download_dir="$HOME/Downloads"
mkdir -p "$download_dir"

cd "$download_dir"

# Try multiple download URLs in order (direct links expire)
urls=(
  "https://edgedl.me.gvt1.com/android/studio/ide-zips/2025.1.1.2/android-studio-2025.1.1.2-linux.tar.gz"
  "https://download.jetbrains.com/idea/android-studio-2024.2.1.22-linux.tar.gz"
)

for url in "${urls[@]}"; do
  wget -q -O android-studio.tar.gz "$url"
  if [ -f android-studio.tar.gz ] && [ "$(stat -c%s android-studio.tar.gz)" -gt 300000000 ]; then
    echo "Download successful"
    break
  fi
  rm -f android-studio.tar.gz
done
```

**Warning:** Direct download links often return 404. Try the official Android Studio download page if all URLs fail: https://developer.android.com/studio#downloads

### 2. Extract Android Studio

```bash
extract_dir="$HOME/android-studio"
mkdir -p "$extract_dir"

tar -xzf android-studio.tar.gz -C "$extract_dir" --strip-components=1

# Find and make executable
chmod +x "$HOME/android-studio/bin/studio.sh"
echo "Android Studio extracted to $HOME/android-studio"
```

### 3. Install Java JDK 17+ (Required)

```bash
# Verify Java is installed
java -version 2>/dev/null || echo "Java not found"

# If not installed
sudo apt update
sudo apt install -y openjdk-17-jdk openjdk-17-jre

# Verify
java -version
```

**Critical:** Java 17 is required for recent Android SDK tools. Version 11 may work but 17+ is recommended.

### 4. Download Android SDK Command-line Tools

```bash
sdk_dir="$HOME/android-studio/sdk"
cmdline_tools_dir="$sdk_dir/cmdline-tools"

mkdir -p "$cmdline_tools_dir"

cd "$cmdline_tools_dir"

wget -q -O cmdline-tools.zip "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"

unzip -q cmdline-tools.zip
mv cmdline-tools latest
rm cmdline-tools.zip

echo "Command-line tools installed"
```

### 5. Set Environment Variables

Add to `~/.bashrc`:

```bash
# Android Development Environment
export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"
export ANDROID_HOME="$HOME/android-studio/sdk"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export PATH="$PATH:$ANDROID_HOME/cmdline-tools/latest/bin"
export PATH="$PATH:$ANDROID_HOME/platform-tools"

# Reload
source ~/.bashrc
```

**Critical:** JAVA_HOME must be correctly set or sdkmanager will fail with "JAVA_HOME is set to an invalid directory".

### 6. Download Platform Tools and System Images

```bash
sdk_dir="$HOME/android-studio/sdk"
sdkmanager="$sdk_dir/cmdline-tools/latest/bin/sdkmanager"

# Accept licenses (press 'y' for all)
yes | $sdkmanager --licenses

# Download platform tools (ADB, fastboot)
$sdkmanager "platform-tools"

# Check for 64-bit system images
$sdkmanager --list | grep "system-images;android-34;google_apis;x86_64"

# Install system image (may take 5-10 minutes)
$sdkmanager "system-images;android-34;google_apis;x86_64"
```

## Build and deploy React Native / Expo debug APK via ADB

Use this workflow to build a debug APK from a React Native or Expo project and install it on a connected device.

### Prerequisites
- Android SDK installed and `ANDROID_HOME` set (see Setup Steps above)
- Device connected via ADB (`adb devices` shows it)
- Java 17+ available

### Workflow

```bash
# 1. Build the debug APK
cd path/to/project/apps/mobile/android
./gradlew assembleDebug

# 2. Find the APK output
# Usually at:
#   android/app/build/outputs/apk/debug/app-debug.apk
ls -lh app/build/outputs/apk/debug/app-debug.apk

# 3. Install on connected device (replaces existing install)
adb install -r app/build/outputs/apk/debug/app-debug.apk

# 4. Verify install
adb shell pm list packages | grep <your-package-name>
```

### Notes for monorepo projects
- The Gradle build runs from the `android/` directory inside the mobile app folder
- If the project uses Expo's managed workflow, run `npx expo prebuild` first to generate/update the `android/` project
- For Expo dev clients, use `npx expo run:android` instead of manual Gradle commands
- Setting `EXPO_NO_METRO_WATCH=1` can speed up builds inside Expo-managed projects

### Pitfalls
- **Build fails with "JAVA_HOME not set"**: ensure `JAVA_HOME` points to a JDK 17+ installation
- **Build fails with "SDK location not found"**: check `local.properties` has `sdk.dir=/path/to/Android/Sdk`
- **adb install fails with "INSTALL_FAILED_UPDATE_INCOMPATIBLE"**: use `adb uninstall <package>` then install
- **adb install fails with "INSTALL_FAILED_NO_MATCHING_ABIS"**: the APK targets a different CPU architecture; add `splits { abi { enable true reset() include 'arm64-v8a', 'armeabi-v7a' universalApk false } }` to `app/build.gradle` or use `abiFilters`
- **adb: device offline**: re-plug or restart ADB server (`adb kill-server && adb start-server`)
- **Gradle takes very long on first build**: normal for fresh projects; subsequent builds use cached artifacts
## Verification

```bash
# Confirm device is connected
adb devices

# After install, launch the app
adb shell monkey -p <your.package.name> 1
```

## Native Android (Kotlin/Gradle) Builds

For building native Android apps (Kotlin, Compose, WebRTC) from the CLI:

### Common Build Issues

See `references/native-android-build-troubleshooting.md` for detailed fixes, but the most frequent patterns are:

1. **Missing SDK platform**: `compileSdk = 35` requires `platforms;android-35` installed via sdkmanager
2. **WebRTC dependency**: `org.webrtc:google-webrtc` is deprecated. Use `com.dafruits:webrtc:123.0.0` instead (same import paths)
3. **Gradle wrapper missing**: Create manually by downloading gradle-wrapper.jar and generating wrapper properties
4. **kotlinx.serialization 1.7.x API**: `putJsonObject`/`putJsonArray` removed — use `put(key, buildJsonObject { ... })` and `put(key, buildJsonArray { ... })` with explicit `JsonPrimitive()` wrappers
5. **Missing mipmap resources**: If `AndroidManifest.xml` references `@mipmap/ic_launcher` but no launcher icons exist, reference an existing drawable instead

### Build Command

```bash
export ANDROID_HOME=/path/to/sdk
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

cd project/
./gradlew assembleDebug 2>&1 | grep '^e:'    # Filter to just errors
```

### APK Output

Debug APK location: `app/build/outputs/apk/debug/app-debug.apk`

Install on device:
```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

### Pitfalls

- **WebRTC .so stripping warning**: The warning "Unable to strip the following libraries" for `.so` files is normal — packaging proceeds fine
- **First build is slow**: Gradle downloads dependencies; subsequent builds are faster
- **JAVA_HOME must be JDK 17+**: Android Gradle Plugin 8.x requires it
- **Kotlin compiler only shows errors with `^e:` prefix**: Warnings start with `w:` and are not errors

## Pitfalls & Troubleshooting

### Platform-tools extraction issue
**Symptom:** `adb` not found after download
**Cause:** Files extracted in nested `platform-tools/platform-tools/` directory
**Fix:**
```bash
mv "$ANDROID_HOME/platform-tools/platform-tools/"* "$ANDROID_HOME/platform-tools/"
rmdir "$ANDROID_HOME/platform-tools/platform-tools"
```

### JAVA_HOME issue
**Symptom:** "Error: JAVA_HOME is set to an invalid directory" when running sdkmanager
**Fix:** Verify JAVA_HOME points to actual JDK installation:
```bash
echo $JAVA_HOME
ls -la $JAVA_HOME

# Find actual Java location
readlink -f $(which java)
ls -la $(dirname $(dirname $(readlink -f $(which java)))))
```

### ADB connection errors
**Symptom:** "error: device not found" or "device offline"
**Possible causes:**
- Android device not in Developer Mode
- USB debugging not enabled
- USB cable incompatible (try a different cable)
- Device not authorized for ADB
**Fix:** Enable USB debugging in Developer options and authorize computer.

### AVD creation fails
**Symptom:** Error: "Package path is not valid"
**Causes:**
1. System image not fully downloaded (check `.installer` flag)
2. System image path incorrect
**Fix:**
```bash
# Remove installation flag if present
rm -rf $ANDROID_HOME/system-images/android-34/google_apis/x86_64/.installer

# Verify boot.img exists
ls -lh $ANDROID_HOME/system-images/android-34/google_apis/x86_64/boot.img
```

### Command-line tools not working
**Symptom:** `sdkmanager` or `avdmanager` not found
**Fix:** Ensure environment variables are sourced:
```bash
source ~/.bashrc
which sdkmanager
which avdmanager
```

## Alternative Installation Methods

### Snap (if available)
```bash
sudo snap install android-studio --classic
```

### Flatpak (if available)
```bash
flatpak install flathub org.jetbrains.androidstudio
```

## Next Steps After Setup

1. Create an Android Virtual Device via AVD Manager:
   ```bash
   $ANDROID_HOME/cmdline-tools/latest/bin/avdmanager create avd \
     -n Pixel_7_API_34 \
     -d pixel_7 \
     -k "system-images;android-34;google_apis;x86_64"
   ```

2. Launch Android Studio:
   ```bash
   $HOME/android-studio/bin/studio.sh
   ```

3. Test emulator:
   ```bash
   $ANDROID_HOME/emulator/emulator -avd Pixel_7_API_34
   ```

## Support Files

- `scripts/android-env-check.sh` - One-line verification script
- `references/download-urls.md` - Current Android Studio download URLs
- `references/troubleshooting.md` - Extended troubleshooting scenarios
- `references/native-android-build-troubleshooting.md` - Native Kotlin/Gradle build issues (WebRTC, serialization API, missing resources, Gradle wrapper creation)
