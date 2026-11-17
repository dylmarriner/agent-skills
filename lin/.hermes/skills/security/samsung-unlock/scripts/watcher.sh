#!/bin/bash
# Samsung Device Watcher — detects USB state and suggests next action
# v2 — no heimdall (fails on S23+/A54), monitors all relevant PIDs
echo "Samsung Device Watcher — monitoring USB for unmount 04e8"
echo ""
while true; do
    if lsusb | grep -q "04e8:685d"; then
        echo "$(date): DOWNLOAD MODE (04e8:685d)"
        echo "  → heimdall FAILS on S23+/A54. Use jodin3 or Odin3 (Windows)."
        echo "  → Check ~/.samsung_firmware/ for combo firmware"
        ls ~/.samsung_firmware/COMBINATION*.tar* 2>/dev/null && echo "  → COMBO FIRMWARE FOUND" || echo "  → No combo firmware"
        exit 0
    fi
    if lsusb | grep -q "04e8:6860"; then
        echo "$(date): MTP MODE (04e8:6860) — booted normally"
        echo "  → Run riskeco Samsung-FRP-Bypass tool"
        echo "  cd /tmp/Samsung-FRP-Bypass && python3 main.py"
        exit 0
    fi
    if lsusb | grep -q "18d1:d001"; then
        echo "$(date): RECOVERY/FASTBOOT MODE (18d1:d001)"
        adb devices -l 2>/dev/null | grep -q sideload && echo "  → ADB SIDELOAD ACTIVE: can flash OTA or reboot to different mode"
        echo "  → Use: adb reboot recovery (stay in recovery)"
        echo "  → Use: adb reboot download (go to download mode)"
        echo "  → Use: adb reboot (boot normally)"
        exit 0
    fi
    sleep 2
done
