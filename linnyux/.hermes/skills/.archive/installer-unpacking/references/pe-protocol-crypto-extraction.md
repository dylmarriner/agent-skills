# PE Binary — Protocol & Crypto Extraction

Systematic extraction of network protocol details, crypto parameters, and license validation flows from Windows PE binaries (Delphi/.NET/Qt). Designed for large binaries (50MB+) where a targeted search is faster than full decompilation.

## Toolkit Requirements

```
strings, grep, xxd, python3    # Core — always available
readpe / pescan / diec         # PE header analysis (optional)
```

## Core Methodology

### Phase 1: String Extraction & Classification

Extract ALL strings with file offsets, then run parallel pattern searches:

```bash
# Extract with offsets (critical for cross-referencing)
strings -a -t x target.exe > strings.txt
wc -l strings.txt  # Track total — >500K lines is normal for large PEs

# Pattern classes to search (run in parallel):
echo "=== Server Domains ==="
grep -i 'https\?://\|www\.\|\.cloud\|\.club\|\.com/api' strings.txt | sort -u

echo "=== Port Numbers ==="
grep -E ':[0-9]{4,5}[^0-9]' strings.txt | grep -v '16-bit\|32-bit\|64-bit\|:\\.\|:\\\' | head -20

echo "=== API Paths ==="
grep -i '\.json\|\.php\|\.asp\|/api\|/v[0-9]\|/auth\|/licen\|/update' strings.txt | head -30

echo "=== Crypto Primitives ==="
grep -i 'AES\|GCM\|PBKDF\|SHA256\|SHA512\|X509\|HMAC\|RSA\|ECC\|curve' strings.txt | head -40

echo "=== Hash/KDF Variants ==="
grep -i 'pbkdf\|scrypt\|bcrypt\|hkdf\|sha.*[0-9]\{3,4\}\|iterat[ei]on\|rounds=' strings.txt | head -20

echo "=== Certificates / Keys ==="
grep -i 'BEGIN.*CERTIFICATE\|BEGIN.*KEY\|PRIVATE KEY\|PUBLIC KEY\|Fingerprint\|CRL\|revocation\|certificate' strings.txt | head -20

echo "=== Error Messages ==="
grep -i 'connect.*fail\|server.*error\|license.*error\|invalid.*license\|licen.*expir\|valid.*fail\|auth.*fail\|security.*check' strings.txt | head -20
```

### Phase 2: PE Class / RTTI Extraction (Delphi)

Delphi's rich RTTI (runtime type information) stores class field names, method names, and field sizes directly in the binary. These are **not runtime values** — they are metadata about the data structure.

**Critical distinction: RTTI field names vs actual values**

```bash
# RTTI field names are typically mixed-case with underscores, prefixed by 'm_':
grep -i 'm_\|T[A-Z][a-z]\|TAES\|TCrypto\|TSeed\|THash\|TBlob\|TElf' strings.txt | head -30
# Example: TAESKey, TCryptoBlob, TSeedPackage, m_aesEncryptKey, m_recvSeedPackage

# Field SIZE (in bytes) follows the name in RTTI — encoded as hex in the struct:
# In xxd output, the pattern is: field_name 0x02 0x00 <size_dword>
# Size 0x10 = AES-128 (16 bytes)
# Size 0x20 = SHA-256 (32 bytes)
# Size 0x80 = BlobPayload (128 bytes)
# Size 0x34 = INIT_KEY_1 (52 bytes)
# Size 0x54 = INIT_KEY_2 (84 bytes)

# Extract around RTTI field names to find sizes:
grep -n 'TAESKey\|TSHA256\|TBlobPayload\|INIT_KEY' strings.txt
# Then xxd at those offsets to read the size dwords
```

**Pitfall**: `auth_seed`, `algorithm_mkey`, `algorithm_auth` in RTTI are **field names**, not values. `algorithm_mkey`/`algorithm_auth` are actually OpenSSL `SSL_CIPHER` struct member names, not custom application values. Always verify by checking context — are they surrounded by other OpenSSL/Crypto struct fields (`algorithm_enc`, `algorithm_mac`, `algo_strength`)?

### Phase 3: Class Hierarchy Reconstruction

Build the data flow from field names:

```bash
# Extract all field names from a class block:
grep -n 'TSeedPackage\|TElfToolAuth\|TCryptoBlob\|TOCTHWID' strings.txt
# Notes the fields in order — they reveal the protocol flow:
# TSeedPackage: auth_seed → elf_hash_2 → blob_payload_hash → concealedReport
# TElfToolAuth: m_elfToolVersion → m_elfToolBuffer → m_cryptoBlob → 
#               m_hashElfFinal → m_recvSeedPackage → m_aesEncryptKey → m_aesDecryptKey
# This tells us: seed received → hashes verified → AES keys derived
```

### Phase 4: Binary-Level Verification

For each interesting string at offset X, verify the surrounding binary context:

```bash
# 64 bytes before and after gives enough context
xxd -s $((X - 64)) -l 192 target.exe

# Look for:
# 1. Null-separated string tables (common in Qt/C++ binaries)
# 2. Hex-encoded data right after the string (embedded certs/keys)
# 3. Adjacent strings that form a "block" (protocol fields)
# 4. Size dwords preceding/following strings
```

### Phase 5: Multi-Binary Cross-Reference

When two versions of the same tool exist (e.g., main Delphi `.exe` and newer Qt `.exe`):

```bash
# Extract both
strings -a -t x OctoplusSamsung.exe > main_strings.txt
strings -a -t x OctoplusSamsungNew.exe > new_strings.txt

# Compare payloads
grep -c 'mussaurus\|apiakey\|kPbkdf2\|BEGIN PRIVATE' new_strings.txt
# The newer binary often has MORE endpoints, different iter counts, actual key data

# Shared elements (same across both):
grep -f <(cut -d' ' -f2- main_strings.txt | sort -u) \
        <(cut -d' ' -f2- new_strings.txt | sort -u) | head -20
```

### Phase 6: Embedded Certificate & Hex Data Extraction

PEM certificates and private keys are often hex-encoded in the binary (not stored as plain PEM):

```bash
# Detection pattern:
# "2D2D2D2D2D424547494E20" = "-----BEGIN " (hex-encoded PEM marker)

python3 -c "
import binascii
with open('target.exe', 'rb') as f:
    data = f.read()
# Search for hex-encoded PEM
marker = b'2D2D2D2D2D424547494E20'  # '-----BEGIN '
idx = data.find(marker)
if idx >= 0:
    # Consume contiguous hex chars
    hex_chars = bytes(c for c in data[idx:idx+5000] if chr(c) in '0123456789ABCDEFabcdef')
    raw = bytes.fromhex(hex_chars.decode('ascii'))
    print(raw.decode('utf-8', errors='replace'))
"

# For raw hex blobs (potential DER/raw key data):
python3 -c "
with open('target.exe', 'rb') as f:
    d = f.read()
# Find long hex strings (potential keys/certs)
import re
for m in re.finditer(rb'[0-9A-Fa-f]{100,}', d):
    hs = m.group().decode('ascii')
    print(f'Hex blob at 0x{m.start():x}: {len(hs)} chars = {len(hs)//2} bytes')
"
```

### Phase 7: Crypto Parameter Discovery Pattern

Map PBKDF2 variants by iteration count and chip suffix:

| Pattern | Interpretation |
|---------|---------------|
| `BT_PBKDF2_HWID` | PBKDF2 used for HWID generation |
| `ebaPBKDF2_5000` / `ebaPBKDF2_9000` | 5000 / 9000 iterations |
| `ebaPBKDF2_S5123` / `ebaPBKDF2_S5308AP` | Per-chip variants (Exynos 5123, 5308 AP) |
| `kPbkdf2_5000_HW` | Hardware variant |
| `bt_sha_1000` | 1000 iterations of SHA (not PBKDF2) |

For AES key sizes: Search for `TAESKey` in strings, then at that offset read the size dword (typically `0x10` = AES-128, `0x20` = AES-256).

### Phase 8: Protocol Flow Reconstruction

From all the above, reconstruct the protocol:

```
1. App start → check smart-card (DigitalLicenseManager.exe)
                ↓ fail = "Smart-Card readers not found"
2. TCP connect → node.productbox.{cloud|club}:8443
   TLS handshake (OpenSSL 1.0.1m, TIdSSLIOHandlerSocketOpenSSL)
3. Exchange: client sends HWID → server validates license
   Response: JSON
   Error states: "Serial number validation error", "Locked"
   Success: loads resources (SamsungResources)
4. Per-operation validation:
   PBKDF2_HMAC_SHA512(hwid_or_seed) → AES-128-GCM key
   check_odex + check_hashes + check_aes_gcm
5. Periodic: Octoplus_Updates check (version polling)
```

## Common Pitfalls

- **RTTI field names are NOT values**: `auth_seed` is a Delphi class field name in `TSeedPackage`, not the actual seed value. The actual seed is received from the server at runtime. Searching for this string alone and claiming you found "the auth_seed value" is incorrect.
- **`algorithm_mkey`/`algorithm_auth` are OpenSSL struct members**: These are `SSL_CIPHER` field names from libeay32, not custom application auth tokens. If they're near `algorithm_enc`, `algorithm_mac`, `algo_strength`, `algorithm2`, `valid`, `name` — they're part of an OpenSSL cipher definition.
- **Large binaries produce massive noise**: `strings` on a 245MB PE produces 1M+ lines. Most are Win32 API names, Delphi RTTI, and compiler metadata. Always use targeted `grep` patterns, not blind browsing.
- **Qt binaries have different string organization**: Qt apps store strings null-separated in tables, not Delphi-style length-prefixed. The `strings` output is cleaner but some strings may be fragmented.
- **SecureEngine / Themida protected sections**: Code in protected sections (marked by `ValidatOR` messages, custom VM markers) is encrypted/virtualized. Strings within those sections ARE real and extractable, but their code context cannot be statically analyzed. Look for debug/warning messages at those offsets to infer what the code does.
- **Port 8443, not 443**: Non-standard HTTPS ports are common in licensing tools. Don't assume standard ports.
