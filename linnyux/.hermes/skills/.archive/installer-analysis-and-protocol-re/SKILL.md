---
name: installer-analysis-and-protocol-re
description: Extract Windows installer packages (Inno Setup, Smart Install Maker, NSIS) on Linux, then reverse engineer the extracted binaries for crypto keys, server endpoints, and device communication protocols.
---

# Installer Analysis & Protocol Reverse Engineering

Class-level workflow for extracting and understanding Windows service tools (mobile unlock/FRP/repair tools) on Linux.

## When to Use

- User asks to "reverse engineer" or "tear apart" a Windows installer `.exe`
- User sends a download link to a mobile service tool (Octoplus, TFT, Octopus, Chimera, etc.)
- User needs to understand a tool's license/DRM, device protocol, or encrypted file format

## Workflow

### 1. Download

```bash
wget --user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" -O tool.exe "URL"
```

Use a desktop-class UA to avoid server blocks. Large files (300MB+) may take minutes — use background mode.

### 2. Identify Installer Type

```bash
# Quick check
file tool.exe
7z l tool.exe 2>&1 | head -10

# Check overlay header
python3 -c "
import struct
with open('tool.exe','rb') as f: d=f.read()
pe_off=struct.unpack('<I',d[0x3c:0x40])[0]
n=struct.unpack('<H',d[pe_off+6:pe_off+8])[0]
s=struct.unpack('<H',d[pe_off+20:pe_off+22])[0]
ss=pe_off+24+s
overlay_start=max(struct.unpack('<I',d[ss+i*40+20:ss+i*40+24])[0]+struct.unpack('<I',d[ss+i*40+16:ss+i*40+20])[0] for i in range(n))
print(d[overlay_start:overlay_start+40])
"
```

**Inno Setup:** Overlay starts with compressed data, strings contain "Inno Setup"
**Smart Install Maker:** Overlay starts with `b'Smart Install Maker v.'`
**NSIS:** Strings contain "Nullsoft Install System"

### 3. Extraction

| Type | Tool | Command |
|------|------|---------|
| Inno Setup | `innoextract` | `innoextract -e -d out tool.exe` |
| NSIS | `7z` | `7z x -oout tool.exe` |
| Smart Install Maker | Wine + xvfb | See below |
| Unknown | Try all above | |

**SIM extraction with Wine:**
```bash
export WINEPREFIX=/tmp/wp_$(date +%s)
wineboot -u 2>/dev/null
timeout 120 xvfb-run -a wine tool.exe /VERYSILENT
# Check: $WINEPREFIX/drive_c/users/*/AppData/Local/Temp/\$inst/
```

**Password bypass (SIM only):**
Patch the overlay config — change field "25" (password flag) to "0" at the config offset, then run with patched binary.

**Precompiled innoextract:**
Download v1.9 from GitHub releases — i686 variant works on any Linux.

### 4. Binary Analysis

```bash
# Strings extraction (background for large files)
strings tool.exe > /tmp/strings.txt &
pestr tool.exe | head -50

# Find server endpoints
grep -iE "node\.|\.cloud|\.club|https?://|/api/|/auth|/license" /tmp/strings.txt | sort -u

# Find crypto references  
grep -iE "aes|rsa|pbkdf|x509|cert|hash|hmac|sha|md5|pbkdf" /tmp/strings.txt | sort -u

# Find protocol markers
grep -iE "hwid|token|seed|algorithm_|auth_|_key\b|iv_|salt|nonce" /tmp/strings.txt | sort -u

# Find network stack (Qt apps)
grep -iE "QHttp|QNetwork|QUrl|QAuthenticator|QSsl" /tmp/strings.txt | sort -u

# Find USB/device comm
grep -iE "usb|vid_|pid_|adb|fastboot|odin|download|serial|com[0-9]" /tmp/strings.txt | sort -u
```

### 5. Encrypted File Formats

Two known formats from Octoplus tools:

**.oct (v1.0):**
- Header: `OCTOPUS_v.1.0\0\0\0` (16 bytes)
- Rest: AES-CBC encrypted data
- Contains: device bootloaders, certificates, EEPROM dumps

**.orf (v2.0):**
- Header: `OCTOPUS_v.2.0\0\0\0` (16 bytes)
- Next 16 bytes: AES-CBC IV
- Rest: AES-CBC encrypted data
- Different IVs = different keys per chipset family
- Contains: MTK/Qualcomm/Unisoc/SPD bootrom loaders

**Extraction approach:**
- The decryption key is either hardcoded in the EXE, fetched from the license server, or derived from HWID
- Search for the IV bytes in the binary (they may be stored alongside the key)
- AES keys are often 16 or 32 bytes, stored as hex strings or binary

### 6. License/DRM Model Mapping

Map the auth flow:
1. HWID collection (PBKDF2 of machine identifiers)
2. Encrypted handshake with license server
3. Token/certificate response
4. Recurring validation (on launch, per operation)

**Typical server pattern:** `node.<productname>.cloud` with DNS round-robin fallback

## User Preferences

- Dylan prefers EXECUTION over narration — dispatch parallel analysis tasks, don't narrate every step
- Deliver concrete findings (server URLs, keys, file formats) not analysis prose
- When stuck on extraction, try Wine + patching before deep-diving into compression formats
- Use delegate_task for parallel RE of multiple executables

## See Also

`references/octoplus-re-findings.md` — complete Octoplus Samsung + FRP RE results from one session
