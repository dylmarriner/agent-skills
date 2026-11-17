#!/bin/bash
# ADB Setup Verification Script
# Checks if ADB is properly configured and device is connected
# Usage: ./scripts/verify-adb-setup.sh

ADB_PATH=/home/kubuntux/android-studio/sdk/platform-tools/adb

echo "=== ADB Setup Verification ==="
echo ""

# Check ADB exists
if [ -x "$ADB_PATH/adb" ]; then
    echo "✅ ADB binary found at: $ADB_PATH/adb"
else
    echo "❌ ADB binary not found. Expected: $ADB_PATH/adb"
    echo "   Install URL: https://developer.android.com/studio/releases/platform-tools"
    exit 1
fi

# Check devices
echo ""
echo "Connected Devices:"
$ADB_PATH/adb devices

# Check for common issues
echo ""
echo "Common Issues Check:"
echo "1. Udev rules for ADB?"
if [ -f /etc/udev/rules.d/51-android.rules ]; then
    echo "   ✅ Rules file exists"
else
    echo "   ⚠️  Rules file missing"
    echo "   Create with: sudo tee /etc/udev/rules.d/51-android.rules << 'EOF'"
    echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="18d1", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTRS{idVendor}=="04e8", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTRS{idVendor}=="2a70", GROUP="plugdev"'
    echo "EOF"
    echo "   Then: sudo udevadm control --reload-rules && sudo udevadm trigger"
fi

echo ""
echo "=== Verification Complete ==="