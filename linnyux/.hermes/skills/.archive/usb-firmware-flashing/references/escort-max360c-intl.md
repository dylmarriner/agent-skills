# ESCORT MAX 360c INTL Firmware Flashing

## Device Identification

- **USB:** `VID 22e3:PID 0049` — ESCORT Inc. MAX 360c INTL
- **Serial:** 1G205159
- **Protocol:** Vendor-specific class (0xFF), bulk endpoints (0x81 IN, 0x02 OUT), 64-byte packets
- **Driver model (Windows):** WinUSB (`escortboot.inf`)
- **Driver interface GUID:** `{b35924d6-3e16-4a9e-9782-5524a4b79bac}`
- **Device class GUID:** `{78A1C341-4539-11d3-B88D-00C04FAD5171}`
- **No standard serial port** — NOT a CDC ACM device. No `/dev/ttyUSB*` or `/dev/ttyACM*` appears

## Official Update Tool

**Detector Tools Pro v2.3.5.4** (Windows/macOS only)

| Platform | Download |
|----------|----------|
| Windows  | `https://cedarelectronics.s3.amazonaws.com/tools/DetectorToolsProSetup_v2.3.5.4.exe` |
| macOS    | `https://cedarelectronics.s3.us-east-1.amazonaws.com/tools/ESCORTDetectorTools_v2_5_18_1.dmg` |

Installed (via Wine): `~/.wine/drive_c/Program Files (x86)/Escort/Detector Tools Pro/`

## Firmware Source

- **NOT embedded in the installer** — firmware is downloaded at runtime
- **Web service:** `https://tools.drivealert.io/DetectorToolsWS/DTInterim.asmx`
- **SOAP methods used:** GetDistributedSoftwareVersionsByType, GetDatabaseFirmwareVersionsByType, GetDatabaseFile, GetRamCodeFiles
- **Storage:** Amazon S3 (pre-signed URLs from the SOAP API)
- **Auth:** All endpoints return 401 without valid credentials
- **S3 bucket `cedarelectronics`:** Contains `tools/` and `firmware/` prefixes but NO MAX 360c firmware — it's delivered via dynamically generated pre-signed URLs

## Key Files in the Installer

| File | Purpose |
|------|---------|
| `Detector Tools Pro.exe` | .NET WPF app (main UI) |
| `escortusb.exe` / `escortusb_x64.exe` | USB device finder (uses Windows SetupAPI) |
| `libbulkusb.dll` | Native USB communication library (wraps libusb/WinUSB) |
| `DriverInstall.exe` | Driver installer |
| `escortboot.inf` | WinUSB driver INF for normal mode |
| `escort_virtual_serial.inf` | Serial driver for bootloader mode (older models) |

## App Behavior Under Wine

- Wine 11.0.0 (winehq-stable) can run the app via Xvfb
- The app detects devices through Windows SetupAPI — Wine doesn't implement WinUSB kernel driver, so the detector is never found ("No Detector Connected")
- Network connections observed: `ec2-18-216-103-8.us-east-2.compute.amazonaws.com` (web service) and `s3-1-w.amazonaws.com` (S3) — but only AFTER device detection
- Registry entries for the device don't help because SetupAPI depends on kernel-level WinUSB support

## Alternative Update Path

The MAX 360c has WiFi/Bluetooth. The **Drive Smarter** mobile app (iOS/Android) can update firmware over-the-air — this is the recommended path for users who just want the firmware updated without the Windows tooling hassle.

## Protocol Notes (libusb accessible)

- pyusb confirmed working — device enumerated, bulk endpoints 0x81/0x02 accessible
- Sending null 64-byte packets gets no response (protocol is proprietary)
- Device does NOT re-enumerate during normal operation — different PIDs for bootloader mode aren't confirmed for the INTL variant
- Full reverse engineering would require capturing USB traffic from a Windows machine running Detector Tools Pro

## See also

- `https://www.escortradar.com/pages/update-your-device` — official update page
- INF files at `~/.wine/drive_c/windows/inf/escortboot.inf` and `escort_virtual_serial.inf`
