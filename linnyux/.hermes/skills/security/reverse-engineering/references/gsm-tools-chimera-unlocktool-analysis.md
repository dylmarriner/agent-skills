# GSM Tool Reverse Engineering: UnlockTool + Chimera Tool

Session reference. Analysis of two commercial mobile phone service tools — their architecture, security layers, RE difficulty, and what makes each one hard.

---

## UnlockTool

**Type:** Windows GSM service tool — FRP removal, flashing, bootloader unlock, IMEI repair
**Platform:** Windows (C/C++ native — **NOT .NET**. Confirmed: no CLR header, no mscoree.dll, native PE32 with 13 sections)
**Protection:** Custom heavy-duty packer with randomized section names (`*P2524Lv`, `LyHORKjI`, etc.) and AES-strength encrypted payload (entropy 8.00). Section 11 (197.7 MB) is the encrypted code blob; section 12 (413 KB) is the unpacker stub with Windows manifest. Not UPX, not VMProtect — custom/proprietary encryption with runtime decryption. The overlay contains an Authenticode PKCS#7 signature.
**License:** Subscription-based (3/6/12 months) via remote license server + cached license file

### Supported Chipset Protocols
- Qualcomm EDL (Emergency Download) — Sahara protocol (upload firehose loader), Firehose (partition R/W)
- Mediatek BROM (BootROM) — DA (Download Agent) upload
- Spreadtrum/Unisoc download mode
- ADB + fastboot (standard Android debugging)

### Security Layers
| Layer | Implementation | Bypass Difficulty |
|-------|---------------|-------------------|
| Encryption | Custom AES-strength crypto (entropy 8.00) | High — key derived at runtime in unpacker |
| License server | HTTPS POST to license API, returns validation token | Low |
| License cache file | Cached .lic/.dat in AppData or install dir | Low |
| Integrity check | Authenticode signature in overlay | Low (patch the check) |

### RE Approach
1. **Static analysis**: Parse PE sections with Python struct. Identify randomized section names as packer fingerprint.
2. **Extract sections**: Section 11 (encrypted payload) + Section 12 (unpacker stub with Windows manifest)
3. **Entropy measurement**: Section 11 entropy = 8.00 (solid encryption), Section 12 entropy = 3.72 (unpacker code)
4. **Map imports**: Uses wininet.dll + winhttp.dll for license server calls
5. **Unpacking**: Requires runtime dump on Windows. No static unpack possible — decryption key derived at runtime.
   - Set up Windows VM or Wine
   - Use x64dbg + ScyllaHide to bypass anti-debug
   - Dump decrypted process memory at OEP
   - Rebuild IAT with Scylla
6. **Patch license check**: Find HTTPS call to license server, patch response parser

### What You Actually Get
The exploit database (mapping of build number → exploit method) is in the decrypted payload. Cracked copies retain full functionality assuming the model DB isn't server-gated.

### Difficulty: **Moderate-High** (not .NET — native C with custom encryption)

---

## Chimera Tool

**Type:** Professional Samsung-focused service tool — flashing, EUB mode repair, FRP, boot repair
**Platform:** Qt/C++ (cross-platform) — the distributed exe is a 14.5 MB **installer** (not the tool itself)
**Protection:** **WinLICE protector** (confirmed via `.winlice` section). Sections 0-2 encrypted (entropy 7.93), `.winlice` section is 6.4 MB of virtualized VM bytecode, `.boot` section is 3.9 MB boot loader. NOT UPX. Qt library strings found in sections.
**License:** Username/password + **hardware smart card dongle** (Chimera Authenticator — PKCS#11 smart card) + license server

### Supported Protocols
- Samsung Exynos EUB (Emergency UnBrick) mode — **crown jewel**, low-level memory access
- Qualcomm EDL
- Mediatek BROM/DA
- Samsung OneUI ADB operations

### Security Layers
| Layer | Implementation | Bypass Difficulty |
|-------|---------------|-------------------|
| Binary protection | WinLICE — code virtualization (VM bytecode, not raw x86) | Very High (VM trace needed) |
| Login | Username/password → license server → session token | Low |
| Hardware dongle | Smart card (PKCS#11) — stores private key for server challenge-response | High |
| API signing | Requests include HMAC-signed payloads using dongle-derived key | High |
| EUB protocol | Proprietary Samsung Exynos low-level bulk endpoint protocol | Very High |

### RE Approach

**Phase 1 — Installer (trivial)**
- The `chimera_setup.exe` is a WinLICE-packed installer (14.5 MB)
- Install on Windows to get the actual tool binary
- The real application binary will also be WinLICE-protected

**Phase 2 — Binary analysis (hard)**
- WinLICE virtualizes critical code into VM bytecode
- Need to either: trace the VM interpreter, or find the OEP after WinLICE decrypts sections
- Use x64dbg + ScyllaHide + WinLICE unpacker plugin
- Cracked copies do exist — they bypass the dongle check but **EUB features may still require server**

**Phase 3 — Dongle (hard)**
- `pcsc_scan` → get ATR, identify card type (likely JavaCard)
- `pkcs11-tool --module <driver>` → enumerate slots, certs, keys
- `gscriptor` → send raw APDUs, map the command set
- Challenge-response pattern: server sends random challenge → card signs → server verifies

**If key is in card secure element:**
- Not software-extractable
- Requires: fault injection (voltage glitch), side-channel (timing/power), or physical decap (FIB/SEM — $10K+ lab)

**If server validates EUB:**
- Even with a cloned card, if EUB commands are server-gated, the client is useless without it

**Phase 4 — EUB Protocol (very hard)**
- Exynos-specific low-level USB bulk endpoint protocol
- Reportedly derived from leaked Samsung internal source code
- Provides: partition R/W, bootloader patch, unsigned code execution
- Re-reversing from scratch = months of USB fuzzing against Exynos boot ROM
- Last public Exynos bootROM vulns were years ago; Samsung seals these tight

### Difficulty: **High**

The critical question before attempting: **is EUB protocol logic client-side or server-side?**
- Client-side: cracking auth unlocks full power
- Server-side: cracking auth gives you a shell with no real capabilities

---

## Comparison

| Aspect | UnlockTool | Chimera Tool |
|--------|------------|--------------|
| Language | Native C/C++ (NOT .NET) | Qt/C++ (WinLICE VM) |
| Protection | Custom encryption (entropy 8.00) | WinLICE code virtualization |
| License | Server + cached file | Server + server + **hardware dongle** |
| Exploit DB | Embedded (works cracked) | Partially embedded (may need server for EUB) |
| Unique capability | Large FRP database | Samsung Exynos EUB mode |
| RE difficulty | Moderate-High | High |
| Worth cracking? | Yes — full functionality offline | Maybe — depends on EUB client-side availability |

---

## Forensics Data (from May 2026 session)

### UnlockTool (UnlockTool-2026-05-29-0.exe)
```
Size:        207,784,408 bytes (198.2 MB)
Format:      PE32 (GUI) Intel 80386, 13 sections
Sections:    10 virtual-only (allocated at runtime)
             Section 11: 207 MB encrypted payload (entropy 8.00)
             Section 12: 413 KB unpacker stub (entropy 3.72)
Overlay:     Authenticode PKCS#7 signature
Entry point: 0x1afd5aa3 (very high RVA — packer stub)
Imports:     kernel32, user32, advapi32, wininet, winhttp,
             ole32, comctl32, gdi32, shell32
No .NET:     no CLR header (data dir entry 14 = 0), no mscoree.dll
No UPX:      UPX string found in encrypted data, not a real section
Requires:    Administrator (Windows manifest: requireAdministrator)
Signed by:   UnlockTool / Ha Noi / unlocktool.net@gmail.com
```

### Chimera Tool (chimera_setup.exe)
```
Size:        15,178,584 bytes (14.5 MB)
Format:      PE32 (GUI) Intel 80386, 11 sections
Sections:    Sections 0-2 encrypted (entropy 7.93)
             .idata — standard import table
             .rsrc  — 82 KB resources
             .winlice — 6.4 MB (code virtualization layer)
             .boot    — 3.9 MB (boot loader)
Protection:  WinLICE (confirmed by .winlice section name)
Framework:   Qt (strings found in binary)
Imports:     kernel32, ole32, user32, Qt libraries
```

---

## Generic Static Analysis Methodology

For any protected Windows binary, the following steps can be done on Linux without runtime:

### PE Section Analysis (Python)
```python
import struct
with open('target.exe','rb') as f:
    d = f.read()
pe = struct.unpack('<I', d[0x3c:0x40])[0]
ns = struct.unpack('<H', d[pe+6:pe+8])[0]
ohs = struct.unpack('<H', d[pe+20:pe+22])[0]
so = pe + 24 + ohs
for i in range(ns):
    s = so + i*40
    name = d[s:s+8].rstrip(b'\x00').decode('ascii', errors='replace')
    vsize = struct.unpack('<I', d[s+8:s+12])[0]
    rsize = struct.unpack('<I', d[s+16:s+20])[0]
    print(f'{name}: VSize={vsize:#x} RSize={rsize:#x}')
    # RSize=0 means virtual-only — decrypted at runtime
```

### Entropy Check
```python
from collections import Counter
import math
freq = Counter(data)
entropy = -sum((c/len(data))*math.log2(c/len(data)) for c in freq.values() if c>0)
print(f'Entropy: {entropy:.2f}')
```

### Quick Binary Triage (r2)
```bash
r2 -q -c 'iIe' target.exe
```
Returns: architecture, bits, language hint (c, cxx, dotnet, etc.), subsystem, entry point, overlay presence.

### Packer Fingerprint Summary
| Pattern | Likely Protector |
|---------|-----------------|
| Random 8-char section names | Themida / Enigma variant |
| Blank/empty section names | WinLICE or custom |
| `.winlice` + `.boot` sections | WinLICE (confirmed) |
| UPX0 / UPX1 | UPX |
| `.themida` | Themida |
| Standard names + low entropy | Unpacked |
