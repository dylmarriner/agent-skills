---
name: android-setup
category: mobile-development
description: Complete Android development environment setup for Linux
---

# Android Development Environment Setup

Automate setup of complete Android Studio development environment including Android Studio, ADB, SDK tools, cmdline-tools, and SDK system images on Linux systems.

## Triggers

Use this skill when:
- Installing Android development environment on a new machine
- Setting up Android Studio development tools
- Needing to configure Android SDK and ADB from scratch
- Creating Android Virtual Devices (AVDs) for testing
- Troubleshooting Android Studio command-line tools

## Workflow

### Step 1: Download Android Studio

**Preferred method:** Download from official Google download URL

```bash
# Check latest version at: https://developer.android.com/studio#downloads
# Common working URL pattern (may vary by version):
curl -L -o /tmp/android-studio.zip \
  "https://edgedl.me.gvt1.com/android/studio/ide-zips/{VERSION}/android-studio-linux.tar.gz"
```

**Version patterns that work:**
- `2024.2.1.22` - Stable version (common)
- `2025.3.4.6` - Latest IDE packages
- Use exact version from developer.android.com if 404 errors occur

**⚠️ Common pitfall:** Versioned URLs like `2024.1.1.22` may return 404. Try newer versions or download page to get current URL.

### Step 2: Extract Android Studio

```bash
# Extract to user home or /opt
mkdir -p /home/kubuntux/android-studio
tar -xzf android-studio-*.tar.gz -C /home/kubuntux/android-studio --strip-components 1

# Verify extractor
ls /home/kubuntux/android-studio/bin/studio.sh
chmod +x /home/kubuntux/android-studio/bin/studio.sh
```

### Step 3: Install ADB and Platform Tools

**Download platform-tools (ADB, fastboot, etc.):**

```bash
cd $HOME/android-studio/sdk
mkdir -p platform-tools
cd platform-tools
wget -O platform-tools.zip \
  "https://dl.google.com/android/repository/platform-tools-latest-linux.zip"

unzip platform-tools.zip
# ⚠️ WORKAROUND: The zip creates nested directory structure

# Extract contents to correct location
mv platform-tools/platform-tools/* ./
rmdir platform-tools/platform-tools
rm platform-tools.zip

chmod +x adb fastboot
```

**Verify ADB:**
```bash
./adb version
```

### Step 4: Install Command Line Tools

```bash
cd $HOME/android-studio/sdk
mkdir -p cmdline-tools
cd cmdline-tools
wget -O cmdline-tools.zip \
  "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"

unzip cmdline-tools.zip
mv cmdline-tools latest

chmod +x bin/sdkmanager
chmod +x bin/avdmanager
```

### Step 5: Install Java JDK 17+

Android SDK tools require Java 17 or later:

```bash
# Install OpenJDK 17
sudo apt update
sudo apt install -y openjdk-17-jdk

# Verify installation
java -version

# Find Java home
readlink -f $(which java)
```

### Step 6: Configure Environment Variables

Add to `~/.bashrc`:

```bash
# Android Development Environment
export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"
export ANDROID_HOME="$HOME/android-studio/sdk"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export PATH="$PATH:$ANDROID_HOME/cmdline-tools/latest/bin"
export PATH="$PATH:$ANDROID_HOME/platform-tools"
```

Apply changes:
```bash
source ~/.bashrc
```

### Step 7: Set Up SDK

```bash
# Accept SDK licenses
sdkmanager --licenses

# Install platform tools and system images
sdkmanager "platform-tools"
sdkmanager "build-tools;34.0.0"
sdkmanager "platforms;android-34"
sdkmanager "system-images;android-34;google_apis;x86_64"
```

### Step 8: Create Android Virtual Device (AVD)

```bash
# List available devices
avdmanager list device

# Create AVD
avdmanager create avd \
  -n Pixel_7_API_34 \
  -d pixel_7 \
  -k "system-images;android-34;google_apis;x86_64" \
  --force

# List created AVDs
avdmanager list avd
```

### Step 9: Launch Android Studio

```bash
$HOME/android-studio/bin/studio.sh &
```

## Reference Files

### scripts/android-verify.sh
Run to verify setup:

```bash
#!/bin/bash
set -e
echo "=== Android Setup Verification ==="
echo "Java: $(java -version 2>&1 | head -1)"
echo "ADB: $(adb version | head -1)"
echo "SDK Manager: $(sdkmanager --version 2>&1)"
echo "Android Studio: ls /home/kubuntux/android-studio/bin/studio.sh && echo OK"
echo "AVDs: avdmanager list avd | grep -v "^$""
```

### references/android-download-urls.md
Known-working download URLs (update periodically):
- Android Studio: `https://edgedl.me.gvt1.com/android/studio/ide-zips/2025.3.4.6/android-studio-panda4-linux.tar.gz`
- Platform Tools: `https://dl.google.com/android/repository/platform-tools-latest-linux.zip`
- Command Line Tools: `https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip`

## Pitfalls

1. **Nested extraction directory:** Platform-tools and cmdline-tools zip files create nested structures. Always extract and move contents to parent directory.

2. **Java version requirement:** Android SDK tools require Java 17+. Java 11 or older will fail with "ERROR: JAVA_HOME is set to an invalid directory".

3. **Versioned download URLs:** Not all .android.com URLs are stable. If version `2024.1.1.22` returns 404, try `2024.2.1.22` or `2025.3.4.6` or download from page.

4. **License acceptance:** `sdkmanager --licenses` must be run before installing other components. Answer "y" to all prompts.

5. **AVD creation order:** Must have system images installed BEFORE creating AVD, or AVD creation will fail.

## Verification Checklist

- [ ] Java 17+ installed and JAVA_HOME set
- [ ] Android Studio extracted with bin/studio.sh working
- [ ] ADB in platform-tools working (test with `adb version`)
- [ ] cmdline-tools/bin/sdkmanager working (test with `sdkmanager --version`)
- [ ] cmdline-tools/bin/avdmanager working (test with `avdmanager list`)
- [ ] SDK licenses accepted
- [ ] System images downloaded
- [ ] AVD created and listed in avdmanager list
- [ ] Environment variables in ~/.bashrc and sourced

## Usage

### Start Android Studio with GUI
```bash
$HOME/android-studio/bin/studio.sh
```

### Start emulator
```bash
emulator -avd Pixel_7_API_34
```

### Connect device via ADB
```bash
# Connect running phone
adb devices

# Install APK
adb install myapp.apk

# View logs
adb logcat
```

## Troubleshooting

### "ERROR: JAVA_HOME is set to an invalid directory"
- Ensure JAVA_HOME points to actual JDK installation (not JRE)
- Should contain `/lib` and `/bin/java`
- Verify with: `ls $JAVA_HOME/lib`

### "avdmanager not found"
- Ensure cmdline-tools/extracted correctly
- Check: `ls $HOME/android-studio/sdk/cmdline-tools/latest/bin/avdmanager`

### "platforms;android-34 not found"
- List available platforms: `sdkmanager --list`
- Download correct version for your needs

### ADB "device not found"
- Enable USB debugging on connected Android device
- Connect device via USB cable
- Run: `adb devices`