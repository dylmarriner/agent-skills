# Apizu Tool & Hydra Tool RE Findings

Discoveries from reverse engineering Apizu Tool V4.4.4 and Hydra Tool V7.0.

## Apizu Tool V4.4.4 ("Alien")

**Installer:** Smart Install Maker v5.04, 199MB password-protected PE32 stub.
**Password:** `1234` (cracked via brute-force through xvfb + xdotool)
**Platform:** .NET WinForms (MaterialSkin + Guna UI2 + Newtonsoft.Json)
**Purpose:** Samsung MDM bypass / FRP removal tool.

### File Manifest (embedded in SIM overlay)

| File | Size | Purpose |
|------|------|---------|
| `Apizu Tool.exe` | 6.6MB | Main .NET WinForms application |
| `exDownload.dll` | ~1MB | Custom Samsung Exynos download mode DLL |
| `adb.exe`, `fastboot.exe` | Standard | Android Debug Bridge tools |
| `adbsdm.exe` | Custom | Samsung Download Mode ADB variant |
| `AdbWinApi.dll`, `AdbWinUsbApi.dll` | Standard | Windows ADB bridge |
| 17 APK files (1.apk through terminal.apk) | Various | Side-loaded on devices for exploit |
| `frp.bin` | Firmware | FRP bypass payload |
| `dopher.img`, `pitiful.img` | Images | Device partition images |
| `driver.msi` | Driver | USB driver installer |
| `scrcpy.exe` + FFmpeg/SDL2 DLLs | ~10MB | Screen mirroring via scrcpy |

### SIM Overlay Analysis

The installer header at offset ~0x05a200 contains SIM v5.04 config:
- Password flag at field offset 26 (25 = enabled, 0 = disabled)
- Feature selection, EULA acceptance, and install path controls
- RAR5 archive after config contains the compressed files

## Hydra Tool V7.0

**Source:** RAR archive (1.9GB), extracted to 2.7GB SIM installer.
**Password:** `hydratool` (confirmed via separate Wine + xdotool test)
**Installer:** Smart Install Maker v5.04 (same as Apizu)
**Purpose:** Multi-platform mobile servicing tool — flashing, unlocking, FRP removal, IMEI repair for Qualcomm, MediaTek, Spreadtrum, and other chipsets.

### Key Features (from README/tool description)
- Unlock pattern, PIN, and network lock on supported devices
- Flash stock and custom ROMs across multiple chipsets
- Remove FRP lock and Google account verification
- Repair and write IMEI
- Read/write firmware and partitions
- GUI-based interface for technicians

### Analysis Status
Full SIM installer extracted but **unable to extract files** — Wine's `setupapi:do_file_copyW` blocks the file copy phase. The embedded file manifest was never extracted. A Windows VM (QEMU/KVM) is needed to install and capture the actual application files.

## Wine SIM Installer Bottleneck

Both Apizu and Hydra use Smart Install Maker v5.04. Under Wine:
1. **Password accepted** — Wine passes the password check dialog correctly
2. **UI renders** — The installer shows progress and file list
3. **File copy FAILS** — `setupapi:do_file_copyW` returns an error, none of the actual tool files are written to disk

This is a known Wine limitation. The `setupapi` DLL doesn't implement the SIM file copy handler. No known workaround exists — the tools must be installed inside a real Windows environment.

## Password Brute-Force via xvfb + xdotool

For SIM installers where the password is unknown:

```bash
export WINEPREFIX=$HOME/.wine_sim_bf
rm -rf $WINEPREFIX
wineboot -u 2>/dev/null
export DISPLAY=:99

# Start the installer
timeout 60 wine "/tmp/Hydra_Tool_Setup.exe" 2>/dev/null &
sleep 8

# Find the password dialog window
WIN=$(xdotool search --name "Password|Setup|Smart Install" 2>/dev/null | head -1)
if [ -n "$WIN" ]; then
    # Try password attempt
    xdotool type "hydratool"
    xdotool key Return
    sleep 3
fi

# Check if installer progressed (no error dialog)
```

**Known SIM passwords from experience:**
| Tool | Password |
|------|----------|
| Apizu Tool V4.4.4 | `1234` |
| Hydra Tool V7.0 | `hydratool` |
| (Other common ones to try) | `123`, `12345`, `admin`, `tool`, `unlock`, empty string |

## MITM + DLL Stubs Deploy Pattern

For deploying MITM infrastructure to capture tool-server communication inside a Windows VM:

```bash
# Host-side setup
# 1. Python MITM server on port 8443
# 2. DNS poison in /etc/hosts pointing *.toolserver.com to host IP
# 3. Forward host port to VM: -nic user,hostfwd=tcp::8443-:8443

# Deploy into VM via SMB or HTTP download from host
# Inside VM:
# 1. Place WinSCard.dll + libusb-1.0.dll stubs in tool directory
# 2. Edit C:\Windows\System32\drivers\etc\hosts
# 3. Run tool -> traffic hits host MITM server
```
