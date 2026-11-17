---
name: concord-security-firmware
description: Download, extract, and flash firmware for Concord Security NVRs (CNK8868PFA-V2 / QV5708) and cameras (CNC81BP-V2 / QC5728) from the Celum PIN-gated DAM system.
---

# Concord Security Firmware

Covers downloading firmware for Concord Security NVR/DVR and camera systems, particularly models sold through Jaycar Australia/New Zealand.

## Known Models

| Model | Cat.No. | Type |
|-------|---------|------|
| CNK8868PFA-V2 | QV5708 | 8CH 4K NVR Kit (4x PIR bullet + 2x floodlight IP cams) |
| CNC81BP-V2 | QC5728 | 4K bullet camera (included with kit) |
| CNK8845P-A, CNK8865P-A, CNK8848P-A, CNK8868PFA-A | QV5600/QV5602/QV5700/QV5702 | Older NVR models |

## Finding Firmware

Firmware pages are on the Electus Distribution help center or Concord Connect help center:
- https://help.electusdistribution.com.au/hc/en-us/sections/35680827871385-Firmware-Updates
- https://help.concordconnect.com.au/hc/en-us/

Each firmware has a unique download PIN. The PINs are listed on the help article pages.

## Downloading from Celum DAM

The firmware files are hosted on a Celum DAM system at `dam.jeg.systems` behind a PIN-gated download portal. The download requires a multi-step session flow:

### NVR firmware (PIN: ZNAKH6FD1SUI)
Latest file: `N8XXX_V221013V220921V220929V221123V221102V221102V221013V221013.sw` (~70 MB, July 2024)

### Camera firmware (PIN: WED8X7QU6GJP)
Latest file: `CH528N_F128M_SF_ENU_ELECTUS(CONCORD)_V27.45.8.2.3.4_230816_20737_W.sw` (~81 MB, August 2023)

### Download Procedure

Using curl with cookie persistence:

```bash
# Step 1: POST the PIN to authenticate
curl -L -c /tmp/cookies.txt -b /tmp/cookies.txt \
  --data "pin=ZNAKH6FD1SUI&pinlogin=true" \
  -o /tmp/step1.html \
  "https://dam.jeg.systems/pindownload/login.do"

# Step 2: Check step1.html for documentId (e.g., documentId=155166)
grep -o 'documentId=[0-9]*' /tmp/step1.html

# Step 3: Navigate to the download page to see format selection
curl -L -c /tmp/cookies.txt -b /tmp/cookies.txt \
  -o /tmp/step2.html \
  "https://dam.jeg.systems/pindownload/downloadpinobjects.do?documentId=155166"

# Step 4: POST the format selection (fulldownload,6 = "Original Format")
curl -L -c /tmp/cookies.txt -b /tmp/cookies.txt \
  --data "submit=fulldownload,6" \
  -o /tmp/step3.html \
  "https://dam.jeg.systems/pindownload/downloadpinobjects.do"

# Step 5: Extract the generated download URL from step3.html
grep -oP 'downloads/[^"]+' /tmp/step3.html
# e.g. downloads/1779469602897/CNK8868PFA-V2%20QV5708.zip

# Step 6: Download the actual ZIP
curl -L -c /tmp/cookies.txt -b /tmp/cookies.txt \
  -o /tmp/firmware.zip \
  "https://dam.jeg.systems/pindownload/downloads/1779469602897/CNK8868PFA-V2%20QV5708.zip"
```

**Pitfalls:**
- The session cookie is critical — each step must reuse the same cookie jar.
- The `.sw` filename may contain `%2520` (double-encoded spaces). Use `%20` instead.
- The download URL is time-limited (1,800 seconds per the server).
- Using `submit=fulldownload%2C6` (URL-encoded comma) may fail — use a bare comma `submit=fulldownload,6` in `--data`.

## Flashing Firmware

### NVR firmware
1. Copy the `.sw` file to a USB stick
2. Plug into NVR USB port, connect monitor + mouse, power on
3. Click bottom-left corner → **Setup** → enter password
4. **System** → **Maintenance** → **Upgrade** → **Select File**
5. If the USB doesn't appear, swap the USB stick and mouse ports
6. Select the `.sw` file → **OK** → **Upgrade**
7. Wait for success — unit auto-restarts. If not, **Shutdown** from the bottom-left menu and power-cycle.

### Camera firmware (via NVR menu)
1. Copy the `.sw` file to a USB stick
2. NVR menu: **System** → **IP-Camera Maintain** → **Select File** → pick `.sw`
3. **OK** → **IPC Upgrade**
4. Wait for completion

## Known Issues & Resolutions

| Issue | Fix |
|-------|-----|
| NVR randomly restarts after phone app security updates | Flash latest NVR firmware (PIN ZNAKH6FD1SUI) |
| USB not detected in upgrade menu | Swap USB stick and mouse ports |
| Cameras beep continuously (QV5520/QV5522) | Separate firmware update available |

## About .sw Firmware Files

`.sw` files are pre-compiled binary firmware blobs. They cannot be safely modified without:
- The original source code and build toolchain
- Knowledge of the target SoC architecture
- The firmware signature/checksum verification mechanism

Attempting to patch a binary firmware blindly risks bricking the unit (signature rejection or corrupted flash). Only official firmware from Concord/Electus should be used.
