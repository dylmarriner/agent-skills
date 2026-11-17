# QV5708 / CNK8868PFA-V2 Firmware Download Session

## NVR Firmware

**PIN:** ZNAKH6FD1SUI  
**Download page link:** https://dam.jeg.systems/pindownload/login.do?pin=ZNAKH6FD1SUI  
**Document ID:** 155166  
**File:** `N8XXX_V221013V220921V220929V221123V221102V221102V221013V221013.sw`  
**Size:** 70,265,187 bytes (~70 MB)  
**Date:** July 19, 2024  
**ZIP name:** `CNK8868PFA-V2 QV5708.zip`  
**Readme:** `Firmware Update for Concord NVR CNK8868PFA-V2 QV5708.txt`

### Session transcript

```
# Step 1 - POST PIN
curl -L -c cookies.txt -b cookies.txt \
  --data "pin=ZNAKH6FD1SUI&pinlogin=true" \
  -o step1.html \
  "https://dam.jeg.systems/pindownload/login.do"

# (302 redirect to pindownload.do with JSESSIONID)

# Step 2 - Get download page, extract documentId
grep -o 'documentId=[0-9]*' step1.html
# => documentId=155166

# Step 3 - Show format selection page
curl -L -c cookies.txt -b cookies.txt \
  -o step2.html \
  "https://dam.jeg.systems/pindownload/downloadpinobjects.do?documentId=155166"

# Step 4 - POST format selection (use bare comma, not URL-encoded)
curl -L -c cookies.txt -b cookies.txt \
  --data "submit=fulldownload,6" \
  -o step3.html \
  "https://dam.jeg.systems/pindownload/downloadpinobjects.do"

# (302 to downloadpintargetformat.do?targetFormatId=6)

# Step 5 - Extract download URL
grep -oP 'downloads/[^"]+' step3.html
# => downloads/1779469036041/CNK8868PFA-V2%20QV5708.zip

# Step 6 - Download the ZIP (use %20, not %2520)
curl -L -c cookies.txt -b cookies.txt \
  -o CNK8868PFA-V2_QV5708.zip \
  "https://dam.jeg.systems/pindownload/downloads/1779469036041/CNK8868PFA-V2%20QV5708.zip"
```

---

## Camera Firmware (CNC81BP-V2 / QC5728)

**PIN:** WED8X7QU6GJP  
**Document ID:** 155165  
**File:** `CH528N_F128M_SF_ENU_ELECTUS(CONCORD)_V27.45.8.2.3.4_230816_20737_W.sw`  
**Size:** ~81 MB  
**Date:** August 16, 2023 (version V27.45.8.2.3.4)  
**ZIP name:** `CNC81BP-V2.zip`  
**Readme:** `Firmware for CNC81BP-V2 QC5728.txt`

Same procedure as above with the camera's PIN and documentId.

### Flashing cameras
The camera firmware is flashed **through the NVR menu**, not directly to the camera:
1. Copy `.sw` to USB
2. NVR: **System → IP-Camera Maintain → Select File → IPC Upgrade**
3. Article says this is "only needed if you buy a camera separately from a system" — meaning kit-included cameras should already have correct firmware.

---

## Celum DAM quirks

- The PIN auth is form-based POST, not GET. `login.do?pin=XYZ` GET returns the login page with PIN field pre-filled but NOT authenticated.
- Session expires after inactivity or when cookies are not reused.
- Progress page shows a download URL that's valid for 1,800 seconds.
- `submit=fulldownload,6` with bare comma works; `fulldownload%2C6` (URL-encoded) may trigger a server-side "An error occurred inside of celum imagine" error.
- Downloaded URLs appear with `%2520` (double-encoded space) in the HTML; actual URL uses `%20`.
