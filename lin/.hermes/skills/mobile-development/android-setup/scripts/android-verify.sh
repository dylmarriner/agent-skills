#!/bin/bash
# Android Development Environment Verification Script
# Run this after initial setup to verify everything is working

set -e

echo "=========================================="
echo "Android Setup Verification"
echo "=========================================="
echo ""

ANDROID_HOME="${ANDROID_HOME:-$HOME/android-studio/sdk}"

# Check Java
echo "1. Java Installation"
echo "--------------------"
if command -v java &> /dev/null; then
    java_version=$(java -version 2>&1 | head -1)
    echo "✓ Java found: $java_version"
    
    # Check if Java 17+
    java_major=$(java -version 2>&1 | grep -oP 'version "\K[0-9]+')
    if [[ $java_major -ge 17 ]]; then
        echo "✓ Java version $java_major (17+ required)"
    else
        echo "⚠ Java $java_major (Java 17+ recommended)"
    fi
else
    echo "✗ Java not found"
    exit 1
fi
echo ""

# Check ADB
echo "2. ADB (Android Debug Bridge)"
echo "----------------------------"
ADB_BIN="$ANDROID_HOME/platform-tools/adb"
if [ -f "$ADB_BIN" ]; then
    echo "✓ ADB found: $ADB_BIN"
    adb_version=$(adb version 2>&1 | head -1)
    echo "  $adb_version"
else
    echo "✗ ADB not found at $ADB_BIN"
    exit 1
fi
echo ""

# Check SDK Manager
echo "3. SDK Manager"
echo "-------------"
SDKMANAGER_BIN="$HOME/android-studio/sdk/cmdline-tools/latest/bin/sdkmanager"
if [ -f "$SDKMANAGER_BIN" ]; then
    echo "✓ SDK Manager found: $SDKMANAGER_BIN"
    sdk_version=$($SDKMANAGER_BIN --version 2>&1)
    echo "  $sdk_version"
else
    echo "✗ SDK Manager not found"
    exit 1
fi
echo ""

# Check AVD Manager
echo "4. AVD Manager"
echo "-------------"
AVDMANAGER_BIN="$HOME/android-studio/sdk/cmdline-tools/latest/bin/avdmanager"
if [ -f "$AVDMANAGER_BIN" ]; then
    echo "✓ AVD Manager found: $AVDMANAGER_BIN"
else
    echo "✗ AVD Manager not found"
    exit 1
fi
echo ""

# Check Android Studio
echo "5. Android Studio"
echo "----------------"
STUDIO_SCRIPT="$HOME/android-studio/bin/studio.sh"
if [ -f "$STUDIO_SCRIPT" ]; then
    echo "✓ Android Studio launcher found"
    ls -lh $STUDIO_SCRIPT
else
    echo "✗ Android Studio not found"
    exit 1
fi
echo ""

# Check Environment Variables
echo "6. Environment Variables"
echo "------------------------"
echo "ANDROID_HOME: $ANDROID_HOME"
echo "  Exists: $([ -d "$ANDROID_HOME" ] && echo "Yes ✓" || echo "No ✗")"

if [ -n "$JAVA_HOME" ]; then
    echo "JAVA_HOME: $JAVA_HOME"
    echo "  Exists: $([ -d "$JAVA_HOME" ] && echo "Yes ✓" || echo "No ✗")"
else
    echo "JAVA_HOME: Not set ⚠"
fi

if [[ ":$PATH:" == *":$ANDROID_HOME/platform-tools:"* ]]; then
    echo "platform-tools in PATH: Yes ✓"
else
    echo "platform-tools in PATH: No ⚠ (add to ~/.bashrc)"
fi

if [[ ":$PATH:" == *":$ANDROID_HOME/cmdline-tools/latest/bin:"* ]]; then
    echo "cmdline-tools in PATH: Yes ✓"
else
    echo "cmdline-tools in PATH: No ⚠ (add to ~/.bashrc)"
fi
echo ""

# Check AVDs
echo "7. Android Virtual Devices"
echo "--------------------------"
AVD_LIST=$($AVDMANAGER_BIN list avd 2>/dev/null | grep -v "^$" || echo "No AVDs found")
if [ "$AVD_LIST" != "No AVDs found" ]; then
    echo "✓ AVDs found:"
    echo "$AVD_LIST"
else
    echo "⚠ No AVDs created yet"
fi
echo ""

# Check Emulator
echo "8. Emulator"
echo "----------"
EMULATOR_BIN="$ANDROID_HOME/emulator/emulator"
if [ -f "$EMULATOR_BIN" ]; then
    echo "✓ Emulator found: $EMULATOR_BIN"
else
    echo "⚠ Emulator not found (may need system images)"
fi
echo ""

echo "=========================================="
echo "Verification Complete"
echo "=========================================="