# Samsung Unlock Skill

## When to use
When the user asks about unlocking a Samsung phone, bypassing FRP, removing MDM, or bypassing lock screens.

## How to use
1. Run `unlock-detect scan` to detect connected devices
2. Run `unlock-detect method-list` to see available bypass methods
3. Run `unlock-detect unlock --all` to attempt auto-unlock

## Method Chain (priority order)
1. ADB Bypass — if USB debugging is enabled
2. Heimdall Combination Firmware — flash engineering firmware via download mode
3. TalkBack Exploit — screen reader navigation in setup wizard
4. Download Mode — manual combo firmware flash

## Research Docs
- ~/Documents/universal-unlock-suite/docs/FRP_BYPASS_METHODS_RESEARCH.md
- ~/Documents/universal-unlock-suite/docs/SAMSUNG_FRP_DARKWEB_CRAWL.md
- ~/Documents/universal-unlock-suite/docs/2026_SAMSUNG_UNLOCK_METHODS.md

## Connected Devices Info
Always check `lsusb` and `adb devices -l` first.

## Warning
Do NOT proceed with unlock methods on devices the user doesn't own.
