# Android Development Setup Troubleshooting

## Quick Reference

### ADB Version Command
```bash
adb version
# Expected output: Android Debug Bridge version 1.0.41
```

### Environment Variable Check
```bash
echo $JAVA_HOME
echo $ANDROID_HOME
echo $PATH | grep android
```

### Verify Installation
```bash
adb version
which sdkmanager
which avdmanager
ls -la $ANDROID_HOME/emulator/
```

## Detailed Troubleshooting

### 1. JAVA_HOME Issues

**Symptom:** `Error: JAVA_HOME is set to an invalid directory`

**Diagnosis:**
```bash
echo $JAVA_HOME  # Check value
ls -la $JAVA_HOME  # Verify directory exists
ls -la $JAVA_HOME/bin/java  # Verify java binary exists
```

**Fix:**
```bash
# Find actual Java installation
sudo update-alternatives --list java
# Note the path from output

# Set JAVA_HOME correctly (example for Ubuntu)
export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"

# Make permanent
echo "export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64" | tee -a ~/.bashrc
source ~/.bashrc
```

### 2. Platform-tools Extraction Issue

**Symptom:** `adb: command not found` after download

**Diagnosis:**
```bash
ls -la $ANDROID_HOME/platform-tools/
# Should show: adb, fastboot, etc.
# Wrong: nested platform-tools/ directory
```

**Fix:**
```bash
# Move files from nested directory
mv $ANDROID_HOME/platform-tools/platform-tools/* $ANDROID_HOME/platform-tools/
rmdir $ANDROID_HOME/platform-tools/platform-tools

# Verify
ls $ANDROID_HOME/platform-tools/adb
```

### 3. ADB Device Not Found

**Symptom:** `error: device not found` or `device offline`

**Diagnosis:**
```bash
adb devices
adb kill-server && adb start-server
adb devices
```

**Fixes:**

#### Option A: Enable USB Debugging
1. On Android device: Settings → About phone → Tap "Build number" 7 times
2. Go to Settings → Developer options
3. Enable "USB debugging"
4. Reconnect device
5. On computer: `adb devices`
6. Accept USB debugging authorization on device

#### Option B: Use ADB over Network
```bash
# On device (via adb wifi or ADB app)
adb tcpip 5555

# Connect via IP
adb connect 192.168.1.100:5555

# Verify
adb devices
```

#### Option C: Install Google USB Driver
```bash
# Linux
sudo apt install android-tools-adb

# Or download from: https://developer.android.com/studio/run/win32.html#usb
```

### 4. SDK Manager License Errors

**Symptom:** `Licenses for packages not accepted`

**Fix:**
```bash
# Accept all licenses
yes | $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager --licenses

# Or individually
sdkmanager "licenses"
```

### 5. System Image Download Failure

**Symptom:** `Error: Package path is not valid` or download hangs

**Diagnosis:**
```bash
# Check for .installer flag (indicates incomplete install)
ls $ANDROID_HOME/system-images/android-34/google_apis/x86_64/.installer

# Check disk space
df -h $ANDROID_HOME

# Check for corrupted downloads
ls -lh $ANDROID_HOME/system-images/android-34/google_apis/x86_64/boot.img
```

**Fix:**
```bash
# Remove incomplete installation
rm -rf $ANDROID_HOME/system-images/android-34/google_apis/x86_64

# Redownload
$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager "system-images;android-34;google_apis;x86_64"

# If that fails, try older version
$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager "system-images;android-33;google_apis;x86_64"
```

### 6. AVD Creation Fails

**Symptom:** `avdmanager create avd` fails with errors

**Diagnosis:**
```bash
# Check available avdmanager
$ANDROID_HOME/cmdline-tools/latest/bin/avdmanager list

# Check available devices
$ANDROID_HOME/cmdline-tools/latest/bin/avdmanager list device

# Verify system image exists
ls $ANDROID_HOME/system-images/android-34/google_apis/x86_64/
```

**Fix:**
```bash
# Create with simpler parameters first
$ANDROID_HOME/cmdline-tools/latest/bin/avdmanager create avd \
  -n TestAVD \
  -d pixel_2 \
  -k "system-images;android-33;default;x86_64"

# Once working, create your preferred config
$ANDROID_HOME/cmdline-tools/latest/bin/avdmanager create avd \
  -n Pixel_7_API_34 \
  -d pixel_7 \
  -k "system-images;android-34;google_apis;x86_64"
```

### 7. Emulator Won't Start

**Symptom:** `emulator: ERROR: Cannot start emulator`

**Diagnosis:**
```bash
# Check KVM/VT-x support
grep -E '(vmx|svm)' /proc/cpuinfo

# Check if VT-x is enabled in BIOS
sudo dmidecode -s bios-version

# Check emulator logs
$ANDROID_HOME/emulator/emulator -avd Pixel_7_API_34 -verbose
```

**Fix:**
```bash
# Enable virtualization in BIOS
# Restart and enable Intel VT-x or AMD-V

# Verify KVM modules loaded
lsmod | grep kvm

# Add user to kvm group
sudo usermod -a -G $USER $USER

# Reconnect USB if needed
sudo udevadm control --reload-rules
sudo udevadm trigger

# Try with headless mode
$ANDROID_HOME/emulator/emulator -avd Pixel_7_API_34 -no-window
```

### 8. Slow ADB Connection

**Symptom:** `adb` commands take 10+ seconds

**Fix:**
```bash
# Kill server and restart
adb kill-server
adb start-server

# Check USB connection
dmesg | tail

# Try different USB port
# (prefer USB 3.0+ blue ports)
```

## Automated Verification Script

Create `~/android-setup-check.sh`:

```bash
#!/bin/bash
echo "=== Android Setup Verification ==="
echo ""

# Check Java
echo -n "Java: "
java -version 2>&1 | head -1

# Check ADB
echo -n "ADB: "
adb version | head -1

# Check SDK Manager
echo -n "SDK Manager: "
if command -v sdkmanager &> /dev/null; then
  echo "Found"
else
  echo "Not found"
fi

# Check AVD Manager
echo -n "AVD Manager: "
if command -v avdmanager &> /dev/null; then
  echo "Found"
else
  echo "Not found"
fi

# Check Emulator
echo -n "Emulator: "
if command -v emulator &> /dev/null; then
  echo "Found"
else
  echo "Not found"
fi

# Check Android Studio
echo -n "Android Studio: "
if [ -f $HOME/android-studio/bin/studio.sh ]; then
  echo "Found"
else
  echo "Not found"
fi
```

Make executable: `chmod +x ~/android-setup-check.sh`

## Common Error Codes

| Error Code | Meaning | Fix |
|------------|---------|-----|
| 1 | General error | Check logs |
| 2 | Invalid arguments | Check command syntax |
| 3 | Connection timeout | Check network |
| 4 | Device not available | Check USB connection |
| 5 | Invalid AVD | Check AVD exists |

## Getting Help

- Android Studio logs: `Help → Show Log`
- ADB logs: `adb logcat -d > adb-logs.txt`
- Emulator logs: `adb logcat -d > emulator-logs.txt`
- Official docs: https://developer.android.com/studio/run/managing-avds
