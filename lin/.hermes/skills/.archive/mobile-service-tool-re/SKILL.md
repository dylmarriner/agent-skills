---
name: mobile-service-tool-re
description: Reverse-engineer Windows mobile repair/service tool installers (Octoplus, Octopus, Chimera, Z3X, etc.) — extract files, map license validation, find crypto keys, build MITM infrastructure.
---

# Mobile Service Tool Reverse Engineering

Use when Dylan provides Windows mobile service tool installers (`.exe`) that need to be extracted, analyzed, and understood for protocol backdooring or reimplementation.

## Workflow

### Phase 1: Detection
1. `file <installer.exe>` — check PE32/PE32+, section count
2. `strings <installer.exe> | grep -iE "inno|nsis|smart install|nullsoft|setup"` — identify installer type
3. `7z l <installer.exe>` — check if 7z can detect (Rar5, NSIS, Inno)
4. Large overlay (300MB+) with tiny PE stub = installer. Small overlay = packed executable

### Phase 2: Extraction
**For Inno Setup** (most common):
- Use prebuilt `innoextract` at `/tmp/innoextract-1.9-linux/bin/i686/innoextract -e -d <outdir> <file>`
- Inno Setup 5.x-6.x supported. For newer versions, try wine + installer

**For Smart Install Maker**:
- No Linux extraction tool exists
- Patch the SIM config: find field values in the config area (~0x5a200 range) and change flags
- Run with wine + xvfb + /VERYSILENT flags
- Check `$inst/` temp folder for decompressed .tmp files (CAB archives, etc.)

**For NSIS**:
- `7z x <file>` — 7z handles NSIS natively

### Phase 3: Binary Analysis
- `strings -a <target.exe> | grep -iE "https?://|\.cloud|\.club|\.com|api|auth|license|key|hwid|token|activate|server" | sort -u` — find endpoints
- `strings -a <target.exe> | grep -iE "aes|rsa|pbkdf|x509|cert|sha|md5|crc|encrypt|decrypt|key\b|iv_" | sort -u` — find crypto
- For Delphi apps: check for `check_odex`, `check_hashes`, `check_aes_gcm` — these are validation check function names (RTTI visible)
- For Qt apps: the actual logic is often in a separate .dll (e.g. MetaCore.dll)

### Phase 4: Crypto Extraction
- Search for base64-encoded blobs ending in `_hwid_typen` or similar suffixes
- Search for hex-encoded PEM certificates: pattern `2D2D2D2D2D...` at known offsets
- Search for `INIT_KEY_1`, `INIT_KEY_2` in RTTI/strings
- Look for `.oct` and `.orf` file headers: `OCTOPUS_v.1.0\0\0\0` or `OCTOPUS_v.2.0\0\0\0`
- ORF/OCF files use AES-128-CBC/CFB with per-group IVs

### Phase 5: License Bypass
1. **Smart-card check**: Build a stub `WinSCard.dll` using i686-w64-mingw32-gcc. Export all SCard* functions returning SCARD_S_SUCCESS with a fake ATR and reader name. Deploy to Wine system32.
2. **Activation code**: The format is typically `XXXX-XXXX-XXXX-XXXX`. Any well-formatted string passes local validation.
3. **DNS poison**: Redirect `*.octoplusbox.*` to 127.0.0.1 via /etc/hosts
4. **MITM server**: Python HTTPS server on :8443 with proper CA-signed cert. Respond to all paths with JSON containing `{"Status":"success","valid":true,"Active":true,...}`
5. **Cert trust**: Generate a CA cert, sign server certs, install CA in system trust store (`update-ca-certificates`), add iptables redirect: `iptables -t nat -A OUTPUT -p tcp --dport 443 -d 127.0.0.1 -j REDIRECT --to-port 8443`

### Phase 6: Wine GUI Automation
- `xvfb-run -a wine <exe>` — headless GUI
- `xdotool search --name "Window Title"` — find windows
- `xdotool windowfocus <win>` + `xdotool type "text"` + `xdotool key Return` — interact
- `import -window <win> <file>.png` — screenshot
- `tesseract <file>.png - --psm 6` — OCR the dialog
- For login dialogs: click center-left area first to focus the text field, then type, then Tab, then Return

### Pitfalls
- LD_PRELOAD does NOT work with Wine (Wine uses its own libc)
- strace -f -e trace=network works but won't capture Win32 socket calls
- Themida/WinLicense packed EXEs (SecureEngineSDK32.dll) need unpacking first
- Without the Octoplus Box hardware USB dongle, the tools won't contact the license server
- Always check for missing DLLs in Wine stderr (like `WinSCard.dll`)
- Inno Setup installers sometimes ship Qt DLLs — the extracted directory may lack them
