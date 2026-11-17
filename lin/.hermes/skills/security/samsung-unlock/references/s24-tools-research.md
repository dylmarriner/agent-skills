# SM-S921B FRP Bypass — Research Reference (June 2026)

## Dark Web Search Results
8+ minutes across 100+ onion sites, 9 search queries, Ahmia, DuckDuckGo Tor, SuprBay forum.
**Result:** Nothing. All onion search engines are down, block Tor, or have no S24 content.
"EUB" (Emergency USB Boot) term — searched extensively, no documentation found for Exynos 2400.

## Tools That Work

### riskeco/Samsung-FRP-Bypass (⭐273)
- **URL:** https://github.com/riskeco/Samsung-FRP-Bypass
- **Approach:** USB configuration switch (MTP→modem mode) → AT command serial → enable ADB → push FRP clear payload
- **Requires:** Phone booted normally (MTP mode, 0x6860), NOT download mode
- **Linux:** ✅ Python (pyserial, pyusb)
- **Steps:** `python3 main.py` — auto-detects Samsung, switches USB config, enables ADB, clears FRP
- **Blog:** https://blog-cyber.riskeco.com/en/analysis-of-samsung-frp-bypass/
- **Limitation:** Fails on S24/A54 — modern devices only expose 1 USB configuration (MTP mode). `set_configuration(2)` has no effect. ACM serial port doesn't accept AT commands without modem config.

### jodin3 (⭐113)
- **URL:** https://github.com/GameTheory-/jodin3
- **Approach:** Odin firmware flasher for Linux/macOS
- **Updated:** June 2026 — actively maintained
- **Use for:** Flashing combination firmware to enable ADB root

### Alephgsm/SAMSUNG-EDL-Loaders (⭐94)
- **URL:** https://github.com/Alephgsm/SAMSUNG-EDL-Loaders
- **Key file:** SM-S928B.elf (675KB) — EDL firehose for S24 Ultra Exynos 2400
- **Note:** SM-S921B (S24 base Exynos) has NO firehose in this repo. S928B firehose may work since both use Exynos 2400.

### SamFW FRP Tool
- **URL:** https://samfw.com/frp-tool
- **Platform:** Windows only
- **Approach:** Download mode → FRP clear via Samsung proprietary protocol
- **Free:** ✅
- **S24 support:** ✅

### HalabTech S921B Repair Firmware
- **URL:** https://support.halabtech.com/index.php?a=downloads&b=folder&id=182972
- **Files:** 4-file repair firmware packages (BL, AP, CP, CSC) for SM-S921B
- **Note:** Behind auth/paywall

### Other Resources
- **knoxium** (32★ GitHub) — Knox guard removal scripts, recommends SamFW first
- **NDXCode/Samsung-FRP-Bypass-WEB** (122★) — WebSerial/WebUSB browser-based version
- **prabhathgwp/SamsungFRP_TestPoint_MBN** — Test point MBN files for hardware bypass

## MDM Removal (Separate from FRP)

MDM (Mobile Device Management) profiles survive factory reset on Samsung Knox devices. The phone re-enrolls during setup.

### Recovery ADB Sideload Mode
- Samsung stock recovery supports `adb sideload` for OTA updates only
- `adb devices` shows the device as `sideload` with transport ID
- Commands available: `adb reboot`, `adb reboot recovery`, `adb reboot download`
- NO shell, push, or root access from sideload

### Knox MDM Packages to Disable
```bash
adb shell pm disable-user --user 0 com.samsung.android.kgclient
adb shell pm uninstall --user 0 com.samsung.android.kgclient
adb shell pm uninstall --user 0 com.samsung.android.mdm
adb shell pm disable-user --user 0 com.sec.enterprise.knox.cloudmdm.smdms
```
Requires full ADB (USB debugging enabled), not available from sideload.

### Safe Mode Bypass
After factory reset: Power on + hold Volume Down → "Safe mode" → MDM policies don't load from here, can access Settings → Developer Options → enable USB Debugging.

## Identified Dead Ends
- heimdall 1.4.2 → handshake fails on S24 (protocol version mismatch)
- odin4 Linux binary → no pre-built release available
- USB control transfers (0x40) → all pipe errors from download mode
- Python bulk protocol with ODIN/SBL1/DLMG magic → all timeouts
- riskeco AT method → S24/A54 only expose 1 USB config, modem switch fails
- "EUB" (Emergency USB Boot) → no documentation found for Exynos 2400

## Model Identification
PID 0x685d is shared across: Galaxy S2 → S9, A54 (SM-A546E), and possibly more.
lsusb text descriptors are unreliable — always confirm actual model via ADB product string.
