---
name: commercial-tool-reversing
description: Reverse-engineer commercial Windows service tools (unlockers, repair software, FRP tools). Covers installer extraction, binary crypto key search, DLL stubbing for Wine-based execution, MITM protocol capture, and encrypted file format analysis.
category: cybersecurity-skills
---

# Commercial Tool Reversing

Methodology for reverse-engineering protected commercial Windows tools — typically mobile-device service software (unlockers, FRP bypass, repair tools) distributed as password-protected installers.

## Trigger Conditions

- User provides a download URL for a mobile-service tool (Samsung/Octoplus/FRP/unlock software)
- User asks to "reverse engineer", "analyze", "find the protocol", or "extract" from a Windows installer
- The tool appears to be a commercial product with license/dongle/activation checks

## Phase 1: Installer Extraction

### Identify installer type

```bash
# Quick check — look for known signatures in the PE stub (first 100KB)
strings installer.exe | head -50 | grep -iE "inno setup|nullsoft|smart install|nsis|installshield|setup factory"

# Or check the overlay header (data appended after PE sections)
python3 -c "
import struct
with open('installer.exe', 'rb') as f:
    data = f.read()
pe_off = struct.unpack('<I', data[0x3c:0x40])[0]
num_sec = struct.unpack('<H', data[pe_off+6:pe_off+8])[0]
sec_start = pe_off + 24 + struct.unpack('<H', data[pe_off+20:pe_off+22])[0]
overlay_start = 0
for i in range(num_sec):
    s = sec_start + i*40
    roff = struct.unpack('<I', data[s+20:s+24])[0]
    rsize = struct.unpack('<I', data[s+16:s+20])[0]
    end = roff + rsize
    if end > overlay_start: overlay_start = end
overlay = data[overlay_start:]
print(f'Overlay: {overlay[:80]}')
"
```

**Common installer signatures:**
| Installer | Overlay starts with | Tool |
|-----------|-------------------|------|
| Inno Setup | `zlb\x1a` or `Inno` | `innoextract` |
| Smart Install Maker | `Smart Install Maker v.` | Manual extraction |
| NSIS | `Nullsoft` | `7z x` |
| InstallShield | `ISSetup` | `i6comp` or `unshield` |

### Inno Setup extraction

```bash
# Download innoextract (prebuilt binary — more reliable than apt / building from source)
wget -q "https://github.com/dscharrer/innoextract/releases/download/1.9/innoextract-1.9-linux.tar.xz" -O /tmp/innoextract.tar.xz
tar xf /tmp/innoextract.tar.xz

# Extract
/tmp/innoextract-1.9-linux/bin/i686/innoextract -e -d output_dir installer.exe
```

**Pitfalls:**
- 32-bit binary may need 32-bit libc (`/lib/i386-linux-gnu/libc.so.6`) — check with `ldd`
- Password-protected installers: try patching the installer config field (look for version/settings block in overlay, try changing `25` to `0` in field values)
- Inno Setup v6.0.5+ may not be supported by innoextract 1.9

### Smart Install Maker (SIM) handling

SIM v5.x stores a version string `Smart Install Maker v. X.XX` at the overlay start. The overlay contains:
1. File entries table with paths like `@$&%04\filename.exe`
2. Compressed file data (proprietary compression, not standard LZMA)

**When simple extraction fails:** Try the Wine + xvfb + password bypass approach (see Phase 3).

### 7z fallback

Sometimes 7z detects embedded RAR/ZIP archives within the installer overlay:

```bash
7z l installer.exe  # Shows detected archive type + offset
```

Extract what 7z finds, even if partial. The remainder may be the SIM/Inno overlay which needs the installer tool.

## Phase 2: Binary Static Analysis

### First-pass reconnaissance

```bash
# File type
file *.exe

# PE structure (sections, imports)
python3 -c "
import struct
with open('file.exe', 'rb') as f:
    d = f.read()
p = struct.unpack('<I', d[0x3c:0x40])[0]
n = struct.unpack('<H', d[p+6:p+8])[0]
so = struct.unpack('<H', d[p+20:p+22])[0]
ss = p + 24 + so
for i in range(n):
    s = ss + i*40
    nm = d[s:s+8].rstrip(b'\\x00').decode('ascii', errors='replace')
    vs = struct.unpack('<I', d[s+8:s+12])[0]
    va = struct.unpack('<I', d[s+12:s+16])[0]
    rs = struct.unpack('<I', d[s+16:s+20])[0]
    ro = struct.unpack('<I', d[s+20:s+24])[0]
    print(f'{nm:<8} VSz={vs:<8} VA=0x{va:06x} RSz={rs:<8} ROff=0x{ro:06x}')
"

# Check for packers
strings file.exe | grep -iE "upx|themida|vmpress|vmprotect|enigma|obsidium|code virtualizer"

# Determine language
strings file.exe | grep -iE "borland|delphi|turbo|tobject|cryptopp|boost|libcxx|qt5|msvcr"
```

### Delphi apps (most common for mobile service tools)

RTTI (RunTime Type Information) is embedded. Use `strings -a` to find class names, method names, field names.

**Key search patterns:**
```bash
strings -a file.exe | grep -iE "https?://|node\.|api\.|cloud|\.club|\.com/[a-z]|/api/|/auth|/login|license|activation|check_|validate|hwid|HWID|serial|token|key|aes|pbkdf|certificate|x509|private.key|public.key|rsa_priv|rsa_pub|AES_set|check_odex|check_hashes|check_aes_gcm"
```

**Crypto architecture extraction:**
- Search for `T*Key`, `*Hash`, `*Blob`, `*Payload` class names (Delphi uses `T` prefix)
- Look for `INIT_KEY_*` / `algorithm_*` / `auth_seed` constants
- RTTI shows class field sizes — `size 0x10` = AES-128, `size 0x20` = SHA-256
- The `_hwid_typen` suffix in base64 keys is characteristic of Octoplus/PBOC systems

### C++/Qt apps

Qt5 strings include class structure: `QHttpNetworkReply`, `QNetworkAccessManager`, `QSslSocket`.
Search for: `QHttp`, `QNetwork`, `QSsl`, `QAuthenticator`, `Qt5Network`, `node.octoplusbox`

### X509/PEM extraction

Search hex-encoded certificates:
```python
import re
for m in re.finditer(b'[0-9a-fA-F]{96,}', data):
    hex_str = m.group().decode()
    try:
        der = bytes.fromhex(hex_str)
        if b'BEGIN CERTIFICATE' in der:
            print(f"Cert at 0x{m.start():06x}")
    except: pass
```

## Phase 3: Wine-Based Execution

Many mobile-service tools can run under Wine.

### Required setup

```bash
WINEPREFIX=$HOME/.wine_tool
rm -rf $WINEPREFIX
wineboot -u 2>/dev/null
export DISPLAY=:99  # Requires Xvfb running
```

### Handling protected executables

**Themida/WinLicense packed:** The app will refuse to run under standard Wine. Attempt DLL replacements.

**Smart Card (WinSCard) check:** Tools check for a hardware dongle via the SCard API. Create a stub DLL:

1. Create `WinSCard.dll` that returns `SCARD_S_SUCCESS` for all operations
2. Deploy to `$WINEPREFIX/drive_c/windows/system32/`
3. Pattern: compile with `i686-w64-mingw32-gcc -shared -o WinSCard.dll winscard_stub.c`

**USB dongle (libusb) check:** Tools enumerate USB devices looking for the box. Create a shim DLL:

1. Create `libusb-1.0.dll` that intercepts `libusb_get_device_list()`, `libusb_open_device_with_vid_pid()`, etc. and always returns a fake device
2. Deploy to both the app directory and `$WINEPREFIX/drive_c/windows/system32/`
3. Use a generic VID/PID (e.g. 0x16D0 for MCS Electronics) or check driver .inf files for the actual values

### GUI automation

```bash
# List windows
xdotool search --name ".*" 2>/dev/null | while read w; do
    name=$(xdotool getwindowname $w 2>/dev/null)
    [ -n "$name" ] && echo "  Win $w: '$name'"
done

# Take screenshots
import -window <WIN_ID> /tmp/screenshot.png
tesseract /tmp/screenshot.png - --psm 6 2>/dev/null

# Type and click
xdotool type "ACTIVATION-CODE"
xdotool key Return
```

**Pitfall:** The Qt `QNetworkAccessManager` under Wine sometimes fails silently without a proper Windows networking stack. The tool may not make HTTPS calls even when the login dialog progresses.

## Phase 4: Protocol Capture (MITM)

### DNS poison

```bash
echo "127.0.0.1 server.domain.com api.server.com" | sudo tee -a /etc/hosts
```

### HTTPS server

Build a Python HTTPS server that responds with fake JSON containing all expected license fields. Use a self-signed CA cert installed in the system trust store:

```bash
# Generate CA + server cert
python3 /tmp/gen_certs.py
sudo cp /tmp/octoplus_ca.pem /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

Key JSON fields to populate (found via static analysis — search for error messages like "Server response is not valid JSON"):
- `Status`, `status`, `success`, `failed`, `Error`, `error`
- `valid`, `Validated`, `Active`, `active`
- `LicenseKey`, `Token`, `tokenBypass`
- `HwId`, `HWIDHash1`, `SerialNumber`, `serial`
- `Expires`, `expiry`, `DateTime`
- `Balance`, `balance`, `credit`

### Traffic capture

```bash
# Capture port 8443 (or whatever port the tool uses)
tshark -i lo -f "port 8443 or port 443" -w /tmp/traffic.pcap -a duration:60

# Analyze
tcpdump -r /tmp/traffic.pcap -A
```

## Phase 5: Crypto Key & File Format Analysis

### Finding AES keys in binaries

AES-128 keys are 16 bytes with high entropy (14+ unique byte values out of 16):

```python
for off in range(0x100000, len(data) - 16):
    chunk = data[off:off+16]
    unique = len(set(chunk))
    if unique >= 14:
        before = data[off-8:off]
        if b'key' in before.lower() or b'aes' in before.lower() or b'\x00\x00' in before:
            print(f"0x{off:08x}: {chunk.hex()}")
```

**Crypto++ statically linked libraries:** Search for Rijndael, CFB_Cipher, CBC_Mode, SHA256, etc. The key is often stored as a comma-separated byte array `"%c,%c,%c,%c"` or as a hex string nearby.

### Encrypted file format analysis

Common pattern: 16-byte magic + IV + encrypted payload:

```python
magic = data[:16]
if magic.startswith(b'OCTOPUS_v'):
    version = magic[8:12]
    iv = data[16:32]
    encrypted = data[32:]
```

- **Group testing:** Same IV = same key (per-group encryption, often AES-CBC/CFB)
- **Entropy check:** Encrypted data has 245+/1024 unique bytes
- **Algorithm hints:** Search error strings like `"aes_cbc_decrypt error"`, `"CFB_Mode: invalid feedback size"`, `"AES_KEY"`, `"AES_128"`, `"AES_256"`

## Phase 6: Embedded Assets Inventory

Document everything found:

- **Server endpoints** — hostnames, ports, API paths
- **Crypto keys** — AES keys/RSA keys/PEM certs with file offsets
- **Chipset protocols** — Exynos (ODIN/DWC3), Qualcomm (Sahara/EDL/Firehose), MediaTek (BROM/DA), Infineon, NVIDIA Tegra (nvflash), SPRD/Unisoc
- **Driver files** — USB drivers (.sys/.inf), FTDI drivers, libusb
- **Model databases** — SQLite .db files with device model lists
- **Embedded loaders** — `.oct`/`.orf` files for boot ROM exploitation
- **USB VID/PID** — from driver .inf files and libusb_open_device_with_vid_pid calls
