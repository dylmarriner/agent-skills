---
name: installer-unpacking
description: Extract embedded files from installer packages — Inno Setup, NSIS, Smart Install Maker, InstallShield, and other formats. Covers tool selection, binary analysis, and manual reverse engineering when standard tools fail.
---

# Installer Unpacking

Extract files from installer executables. Many installer formats exist, each with different tooling. When standard tools fail, manual binary analysis can recover the embedded payload.

## Tool Reference

| Format | Best Tool | Notes |
|--------|-----------|-------|
| Inno Setup | `innoextract` | Works on Inno 1.2.10–6.0.5. Use `innoextract -i` for version detail |
| NSIS | `7z` (extracts), `nsisunpack` | 7z handles basic NSIS |
| InstallShield | `unshield` | Open-source extraction |
| Smart Install Maker | **No open-source tool exists** | Manual analysis required |
| RAR-based embedding | `7z`, `unrar` | May fail on non-standard methods; try older unrar builds |
| ZIP-based | `unzip`, `7z` | Always try first |
| MSI-based | `msiextract`, `7z` | 7z can list/extract MSI files |

## General Methodology

### Phase 1: Reconnaissance
```bash
file installer.exe
# Check for known signatures:
# - "Inno Setup" → innoextract
# - "Nullsoft Installer" / "NSIS" → 7z / nsisunpack  
# - "Smart Install Maker" → manual
# - "InstallShield" → unshield
```

### Phase 2: Structural Analysis
```python
with open(path, 'rb') as f:
    data = f.read()

# Check file size
print(f"File: {len(data)} bytes")

# Search for known signatures
for sig, name in [(b'PK\x03\x04', 'ZIP'), (b'Rar!', 'RAR'),
                  (b'\x1f\x8b\x08', 'GZIP'), (b'MZ', 'PE'),
                  (b'MSCF', 'CAB'), (b'7z\xbc\xaf', '7z')]:
    pos = data.find(sig)
    if pos >= 0:
        print(f"  {name} at offset 0x{pos:x}")

# Look for installer header strings
for name in [b'Smart Install Maker', b'Inno Setup', b'Nullsoft']:
    pos = data.find(name)
    if pos >= 0:
        print(f"  '{name.decode()}' at offset 0x{pos:x}")
```

### Phase 3: Overlay / Tail Analysis
Many installers append compressed data after the PE. Find where the PE ends:
```bash
# Get PE section info to find end of installer stub
python3 -c "
import struct
data = open('installer.exe','rb').read()
pe_off = struct.unpack('<I', data[0x3c:0x40])[0]
num_sects = struct.unpack('<H', data[pe_off+6:pe_off+8])[0]
sec_start = pe_off + 0xF8
last_end = 0
for i in range(num_sects):
    s = sec_start + i * 40
    name = data[s:s+8].decode('latin-1', errors='replace').rstrip('\x00')
    raw_off = struct.unpack('<I', data[s+20:s+24])[0]
    raw_sz = struct.unpack('<I', data[s+16:s+20])[0]
    last_end = max(last_end, raw_off + raw_sz)
    print(f'  {name}: off=0x{raw_off:x} sz=0x{raw_sz:x}')
overlay_start = (last_end + 0x1ff) & ~0x1ff
print(f'Overlay starts at: 0x{overlay_start:x}')
"
```

### Phase 4: Compression Signature Scan
```python
import zlib
# Scan for ZLIB blocks
for off in range(0, len(data)):
    if data[off] == 0x78 and data[off+1] in [0x01, 0x5e, 0x9c, 0xda]:
        try:
            d = zlib.decompress(data[off:off+500000])
            print(f"ZLIB at 0x{off:x}: {len(d)} bytes decompressed")
        except:
            pass
```

### Phase 5: Entropy Check
High entropy (~7.5-8.0) = encrypted or strongly compressed. Low entropy with repeating patterns = simple XOR or weakly obfuscated.

```python
import math
freq = {}
for b in chunk: freq[b] = freq.get(b, 0) + 1
entropy = -sum((c/len(chunk)) * math.log2(c/len(chunk)) for c in freq.values())
print(f"Entropy: {entropy:.3f}/8.0")
```

### Phase 7: Try Wine/Windows
```bash
# Headless Wine setup
export WINEPREFIX=~/.wine_extract
export WINEARCH=win32
wineboot -u 2>/dev/null
Xvfb :99 -screen 0 1024x768x16 -ac &
export DISPLAY=:99
wine installer.exe /?
wine installer.exe /VERYSILENT /SUPPRESSMSGBOXES
```

## Phase 6: Post-Extraction Analysis

After extraction, analyze the recovered files for embedded secrets, version info, and third-party components.

### Database Analysis
Many installers embed SQLite databases (model databases, config, lookup tables):

```bash
# Check for SQLite
file app/*.db

# Dump schema
sqlite3 database.db ".schema"

# Look for sensitive columns
sqlite3 database.db ".tables"
sqlite3 database.db "PRAGMA table_info(table_name);"

# Count records
sqlite3 database.db "SELECT COUNT(*) FROM table;"
```

Typical schemas found in repair tools: `Models`, `ModelConnection`, `ModelCapabilities`, `Params`, `Loaders` — mapping devices to capabilities and containing loader hashes.

### Proprietary Format Detection
Search for custom magic headers in recovered data files:

```bash
# Scan unknown data files
for f in app/Data/*.orf app/*.oct; do
  echo "$(basename $f): $(xxd $f | head -1)"
done
```

Common patterns:
- `OCTOPUS_v.2.0\x00\x00\x00\x00` + encrypted payload → proprietary Octoplus format
- Followed by 16 bytes of what appears to be random data (high entropy = encrypted, not compressed)

### Anti-Tamper Identification
Look for signature strings in extracted DLLs to identify code protection:

| Signature | Vendor | Product |
|-----------|--------|---------|
| `CustomVM*`, `CodeReplaceStart/End`, `ClearStart/End`, `RegisteredStart/End`, `RegisteredVM/UnregisteredVM` | **Oreans** | Themida / WinLicense |
| `VMProtect*`, `VMP*` | **VMProtect** | VMProtect |
| `Enigma`, `Enigma_*` | **Enigma** | Enigma Protector |
| `EXECryptor*` | **Strongbit** | EXECryptor |

```bash
strings suspect.dll | grep -E '(CustomVM|CodeReplace|ClearStart|RegisteredStart|VMProtect|Enigma_)' | head -5
```

**Extreme virtualization signal — 267+ PE sections:** Themida/WinLicense can produce binaries with 267+ PE sections where section names are garbage bytes and RawSize/VSize values are nonsensical (often much larger than the actual file). A normal PE has 4-10 sections; 200-300+ sections with scrambled names is a reliable indicator of aggressive code virtualization. Detect it via PE header:

```bash
python3 -c "
import struct
with open('suspect.exe', 'rb') as f:
    f.seek(0x3C)
    pe_off = struct.unpack('<I', f.read(4))[0]
    f.seek(pe_off + 6)
    num_sects = struct.unpack('<H', f.read(2))[0]
    print(f'Section count: {num_sects}')
    if num_sects > 100:
        print('Likely Themida/WinLicense — extreme code virtualization')
"
```

### Third-Party Component Fingerprinting
Identify embedded open-source components and their versions:

```bash
# OpenSSL version
strings libeay32.dll | grep -i 'OpenSSL'
strings ssleay32.dll | grep -i 'OpenSSL'

# Qt version (common in cross-platform apps)
strings *.exe | grep -i 'Qt[0-9]'

# .NET assembly info
strings *.exe | grep -i 'publicKeyToken'
# Public key tokens are 16-char hex identifiers for strong-named .NET assemblies
```

### License Manager Discovery
If a file named `*License*` or `*LicenseManager*` exists:

```bash
# Extract license-related strings
strings DigitalLicenseManager.exe | grep -iE '(license|activation|expir|valid|register|unlock)' | grep -v '^[A-Z_]\+$'
# Look for AES markers indicating encrypted licensing
strings DigitalLicenseManager.exe | grep -iE '(AES|RSA|CRYPTOGAMS|Intel AES-NI)'
```

Typical findings:
- `No active license found`, `License not found` — empty/default state
- `License activation:`, `License ending:` — date-bound licensing
- `AES for Intel AES-NI, CRYPTOGAMS by <appro@openssl.org>` — hardware-accelerated AES
- `Octoplus %1 %2 Digital License` — branded license template

### Qt Digital License Manager Analysis

Many modern servicing tools (e.g. Octoplus FRP/Samsung) ship a separate `DigitalLicenseManager.exe` — a **Qt5 + OpenSSL** application that handles license validation, HWID binding, and activation.

#### HWID Binding Method

The primary HWID source is the **RAM module serial number** via WMI:

```bash
# The WMI query used is:
# SELECT Manufacturer,SerialNumber FROM Win32_PhysicalMemory
strings DigitalLicenseManager.exe | grep -i 'Win32_PhysicalMemory'
```

Other HWID sources seen in the wild: `Win32_DiskDrive` (disk serial), `Win32_BaseBoard` (motherboard), MAC address, CPU ID.

#### Registry Persistence Points

License state is stored in `HKEY_LOCAL_MACHINE\SOFTWARE\` under vendor-specific keys. Common patterns:

```
HKEY_LOCAL_MACHINE\SOFTWARE\{VENDOR}\{PRODUCT}\
HKEY_LOCAL_MACHINE\SOFTWARE\Wow6432Node\{VENDOR}\{PRODUCT}\
```

Search for the 32-on-64 WOW6432Node variant with:
```bash
strings DigitalLicenseManager.exe | grep -iE '(HKEY_LOCAL_MACHINE|Wow6432Node)'
```

#### License State Fields

Qt-based license managers typically track via UI label fields:
- `lbl_license_name` — product name
- `lbl_activation_start_date` / `lbl_activation_start_date_val` — activation window start
- `lbl_activation_end_date` / `lbl_activation_end_date_val` — activation window end (expiry)
- `lbl_hwid_change_count` / `lbl_hwid_change_count_val` — HWID mutation counter
- `lbl_hwid_change_date` / `lbl_hwid_change_date_val` — last HWID change timestamp

Search with:
```bash
strings DigitalLicenseManager.exe | grep -E '(lbl_|activation|hwid)'
```

#### License Server Discovery

Scan for hardcoded server names — license servers often follow pattern `node.{product}box.{tld}`:
```bash
strings DigitalLicenseManager.exe | grep -iE '(node\.|\.cloud|\.club|\.license|\.activate)'
strings MetaCore.dll | grep -iE '(node\.|\.cloud|\.club|api\.|/v[0-9])'
```

#### OpenSSL & Qt Network Stack Fingerprinting

Qt license managers statically link OpenSSL for TLS validation:
```bash
# OpenSSL implementation
strings DigitalLicenseManager.exe | grep -iE '(CRYPTOGAMS|AES|SHA|Intel AES-NI|appro@openssl)'

# Qt network authentication support
strings DigitalLicenseManager.exe | grep -iE '(QSsl|QNetworkProxy|QAuthenticator|ProxyAuthentication)'
```

#### Default/Error State Strings

Identify unlicensed states:
```bash
strings DigitalLicenseManager.exe | grep -iE '(No active license|License not found|expired|trial|demo|unlicensed)'
```

These reveal what screen is shown to unlicensed users and can help bypass demo restrictions by finding the license check branch.

### Hardcoded Key & License Search
Structured search across all extracted executables and DLLs:

```bash
# Phase A — license/registration strings
strings *.exe *.dll | grep -iE '(licen[sc]e|auth.key|private.key|public.key|serial|register|activation|unlock)'

# Phase B — API endpoints and server URLs (include node., .cloud, .club patterns)
strings *.exe *.dll | grep -iE '(https?://|node\.|api\.|\.cloud|\.club|\.com/api|\.ru|\.net)'

# Phase C — embedded IP addresses
strings *.exe *.dll | grep -E '([0-9]{1,3}\.){3}[0-9]{1,3}'

# Phase D — alphanumeric tokens (base64-like, hex keys)
strings DigitalLicenseManager.exe | grep -E '(^[A-Z0-9]{8,40}$)'
```

Filter out noise (Windows API names, registry paths, DLL name noise) with `grep -v -E '(^[A-Z_]+$|\.dll$|\.exe$|ERROR|VK_|WM_KEY|KeyPress|Keyboard|Registry)'`.

#### Bulk Key Classification by Length
After extracting all hex strings, classify by length to identify different key types:

```bash
# Extract and count by hex string length
strings *.exe | grep -E '^[0-9A-Fa-f]{32}$' > hex_keys_32.txt   # MD5-length (128-bit)
strings *.exe | grep -E '^[0-9A-Fa-f]{64}$' > hex_keys_64.txt   # SHA-256 length
strings *.exe | grep -E '^[0-9A-Fa-f]{128}$' > hex_keys_128.txt # SHA-512 length
strings *.exe | grep -E '^[0-9A-Fa-f]{256,}$' > hex_keys_long.txt # RSA-like
wc -l hex_keys_*.txt
```

Typical counts from real-world servicing tools: 50–600 key-like hex strings may be embedded, often spanning multiple key classes.

#### Key Identifier Pattern Detection
Some tools embed structured key identifiers alongside the key material:

```bash
# MKEYSKEY pattern — common in Octoplus/Samsung tools
strings *.exe | grep -E 'MKEYSKEY'
# Examples: "1308.500_MKEYSKEY", "6180_Bootloader_10.0_MKEYSKEY"

# Compound keys with chip-specific suffixes (underscore-separated)
strings *.exe | grep -E '^[0-9A-Fa-f]{100,}_[0-9A-Fa-f]+$'
# Format: <keyPart>_<chipID/suffix> — per-chip authorization keys
```

#### UPX Packing Detection
```bash
strings *.exe | grep -i 'UPX'
# "This file is packed with the UPX executable packer http://upx.sf.net $"
# If found, the EXE can be unpacked: upx -d file.exe
```

#### Compiler / Obfuscator Fingerprinting
```bash
strings *.exe | grep -iE '(clang|Obfuscator-LLVM|GCC|MSVC|Delphi|Borland|Qt[0-9])'
# Obfuscator-LLVM indicates control-flow obfuscation
# "Obfuscator-LLVM clang version 8.0.0" with commit hash pinpoints the framework
```

### Inno Setup: In-Depth

Inno Setup appends compressed setup data after the PE. The PE stub is typically small (~54KB), and the overlay is the bulk of the file.

#### Version Inspection
```bash
innoextract -i octoplus_frp.exe
# Example output:
#   Inspecting "Octoplus FRP Tool v.3.0.5" - setup data version 5.3.8
#   Languages: english, french, german, ...
#   No GOG.com game ID found!
#   Setup is not passworded!
```

#### Manual Installation of innoextract
When `apt-get` is unavailable (locked dpkg):
```bash
apt-get download innoextract
dpkg -x innoextract_*.deb /tmp/innotmp
/tmp/innotmp/usr/bin/innoextract -d /outdir installer.exe
```

#### Overlay Boundary Identification
```bash
python3 -c "
import struct
with open('installer.exe','rb') as f:
    dos = f.read(64)
    e_lfanew = struct.unpack('<I', dos[0x3C:0x40])[0]
    f.seek(e_lfanew)
    pe_sig = f.read(4)
    fh = f.read(20)
    machine, num_sections = struct.unpack('<HH', fh[:4])
    opt_hdr_size = struct.unpack('<H', fh[16:18])[0]
    f.read(opt_hdr_size)
    last_end = 0
    for i in range(num_sections):
        name = f.read(8).rstrip(b'\\x00').decode('ascii', errors='replace')
        vsize, vaddr, rawsize, rawptr = struct.unpack('<IIII', f.read(16))
        f.read(16)  # skip remaining section fields
        last_end = max(last_end, rawptr + rawsize)
    f.seek(0, 2)
    file_size = f.tell()
    print(f'Sections: {num_sections}, Last section ends at: {last_end}')
    print(f'Overlay/appended data: {file_size - last_end} bytes ({file_size - last_end:,})')
"
```

#### Extracting PE Stub from Overlay via 7z
```bash
7z l -t# installer.exe
# Shows: 1.exe (PE stub) + 2 (appended data)
7z x -y -t# -o/outdir installer.exe
# /outdir/1.exe = PE stub, /outdir/2 = raw overlay data
```

## Protocol & Crypto Extraction from PE Binaries
See `references/pe-protocol-crypto-extraction.md` for systematic extraction of server endpoints, crypto constants, X509 certs, PBKDF2/AES-GCM parameters, and license validation flows from Delphi/Qt PE binaries. Use alongside the post-extraction analysis when the goal is understanding the binary's network protocol and crypto, not just its installer packaging.

## Common Pitfalls
- **Password-protected installers** encrypt the embedded payload with a password-derived key. Without the password, the data cannot be extracted via static analysis. The only options are: (a) guess/brute-force the password, (b) patch the password check in the PE and run via Wine, or (c) reverse-engineer the decryption algorithm.
- **RAR archives with "Unsupported Method"** — 7z may report this on non-standard or modified RAR archives. Try updating 7z or using an older unrar build. The RAR version detection in 7z sometimes fails on old RAR2/RAR3 formats.
- **Over-eager signature matching** — `MZ` bytes inside other data can be mistaken for PE executables. Always verify by checking `e_lfanew` offset points to a valid `PE\x00\x00` signature.
- **Large installers** (300MB+) may embed PE files, ZIP archives, APK files, RAR archives, and MSI installers in nested layers — extract each sequentially.
- **`strings` output noise** — searching for keys/licenses in Windows PE files produces massive noise from window class names, GDI messages, and API names. Always chain with exclusion filters: `grep -v -E '(VK_|WM_|KeyDown|KeyPress|Keyboard|KeyUp|VirtualKey|Registry|Check|check|Socket|socket|Handle|Error|ERROR)'`.
- **SQLite version mismatch** — extracted `.db` files may use an older SQLite format. `sqlite3` from the system can still read them; check the `last written using SQLite version` from `file` output.

## References
- `references/smart-install-maker.md` — Full analysis of SIM v5.04 format, including overlay parsing, password protection mechanism, and file manifest extraction
- `references/inno-setup-post-extraction.md` — Octoplus FRP Tool v3.0.5 analysis: 2,091 files, ORF/OCT v2.0 encryption, Themida anti-tamper, SQLite model database (16,744 models)
- `references/inno-setup-post-extraction-samsung.md` — Octoplus Samsung v5.x analysis: 4,901 files, 0x7743C66B resource encryption, Obfuscator-LLVM, 600+ hex keys
