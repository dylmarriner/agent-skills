---
name: pe-binary-analysis
description: 'Analyze, unpack, and reverse-engineer protected Windows PE binaries from Linux: packer identification, section extraction, entropy analysis, runtime unpacking planning, and remote machine access for cross-platform RE workflows.'
---

# PE Binary Analysis

Analyze protected Windows PE (Portable Executable) binaries from Linux environments. Covers the full pipeline from initial file identification through packer classification, section extraction, encrypted payload detection, and runtime unpacking strategy planning.

## When to Use

- User asks to reverse-engineer, crack, unpack, dump, or analyze a Windows binary
- User asks to identify what packer or protector a binary uses
- User asks to extract embedded resources or sections from an EXE/DLL
- User asks to analyze a protected .NET or native Windows executable
- User has a packed/protected binary and wants to understand its protection scheme

## Prerequisites

```bash
# Core tools
sudo apt-get install -y radare2 xxd file

# Python3 with standard library (struct, re, collections.Counter, math)

# For remote Windows-based RE: Tailscale SSH to a Windows machine, or QEMU/KVM
# For Wine-based analysis on Linux: sudo apt-get install wine wine32
```

## Workflow

### 1. Initial File Identification

```bash
file target.exe
# Shows: PE32 executable (GUI) Intel 80386, for MS Windows, N sections
# Key: 'PE32' = 32-bit, 'PE32+' = 64-bit, 'GUI' vs 'Console'
# Number of sections gives first clue about packing

ls -lah target.exe
# Compare file size to expected size of the unpacked app
# >50 MB with 10+ sections = almost certainly packed
```

### 2. PE Header Analysis (Python)

Parse the PE structure to identify sections, entry point, imports, and subsystem:

```python
import struct

with open('target.exe','rb') as f:
    d = f.read()

pe_offset = struct.unpack('<I', d[0x3c:0x40])[0]
entry = struct.unpack('<I', d[pe_offset+40:pe_offset+44])[0]
num_sections = struct.unpack('<H', d[pe_offset+6:pe_offset+8])[0]
opt_hdr_size = struct.unpack('<H', d[pe_offset+20:pe_offset+22])[0]
section_table_offset = pe_offset + 24 + opt_hdr_size

print(f'Entry Point RVA: {entry:#x}')
print(f'Sections: {num_sections}')

for i in range(num_sections):
    s = section_table_offset + i*40
    name = d[s:s+8].rstrip(b'\x00').decode('ascii', errors='replace')
    vsize = struct.unpack('<I', d[s+8:s+12])[0]
    vaddr = struct.unpack('<I', d[s+12:s+16])[0]
    rsize = struct.unpack('<I', d[s+16:s+20])[0]
    roff = struct.unpack('<I', d[s+20:s+24])[0]
    print(f'  [{name:8s}] VSize={vsize:#010x} VAddr={vaddr:#010x} RSize={rsize:#010x} ROff={roff:#010x}')
```

**Key signals from section analysis:**

| Signal | Meaning |
|--------|---------|
| Randomized section names (e.g. `*P2524Lv`, `LyHORKjI`) | Commercial protector (Themida, Enigma, custom) |
| `.winlice` section | **WinLICE protector** — code virtualization |
| `.boot` section | WinLICE boot loader / runtime |
| `.vmp0`, `.vmp1`, `.vmp2` | **VMProtect** — code virtualization |
| `.enigma1`, `.enigma2` | **Enigma Protector** |
| `.telia` or `.tli` | **TelLock** / **Telia** |
| `.packed` | Generic packer indicator |
| RSize=0 for most sections | Sections allocated at runtime (decrypted in memory) |
| Entropy > 7.5 | Encrypted/compressed payload |
| One huge section with entropy 8.0 | AES or similar quality encryption |
| Section 0 has RSize=0 but large VSize | VirtualAlloc-based unpacking |

### 3. Packer/Protector Signature Check

```python
sigs = [
    (b'VMProtect', 'VMProtect'),
    (b'Themida', 'Themida'),
    (b'Enigma', 'Enigma Protector'),
    (b'WinLICE', 'WinLICE'),
    (b'UPX!', 'UPX'),
    (b'UPX0', 'UPX'),
    (b'MPRESS', 'MPRESS'),
    (b'ASPack', 'ASPack'),
    (b'PECompact', 'PECompact'),
    (b'Obsidium', 'Obsidium'),
    (b'zProtect', 'ZProtect'),
    (b'EXECryptor', 'EXECryptor'),
    (b'Code Virtualizer', 'Code Virtualizer'),
    (b'SafeNet', 'SafeNet/Sentinel'),
    (b'StarForce', 'StarForce'),
]
for sig, name in sigs:
    idx = d.find(sig)
    if idx >= 0:
        print(f'  {name} at offset {idx:#x}')
```

**Common protector behavior:**

- **UPX**: `pushad` at entry (0x60), `popad` before OEP (0x61). Sections: UPX0, UPX1
- **Themida**: 13+ sections with random names, very large virtual sizes, subsystem sometimes 0
- **WinLICE**: `.winlice` + `.boot` sections, Qt-based apps common target
- **Enigma**: Multiple encrypted sections, overlay with embedded files
- **VMProtect**: `.vmp0`+ sections, entry in VM interpreter, anti-debug traps

### 4. Entropy Analysis for Encrypted Payload Detection

```python
from collections import Counter
import math

def calc_entropy(data):
    freq = Counter(data)
    return -sum((c/len(data)) * math.log2(c/len(data)) for c in freq.values() if c > 0)

entropy = calc_entropy(section_data)
print(f'Entropy: {entropy:.2f}')
# < 6.5: code or compressed data
# 6.5 - 7.5: compressed or weakly encrypted
# > 7.5: likely encrypted with a modern cipher
# 8.0: maximum entropy (AES, ChaCha20, etc.)
```

### 5. Import/DLL Dependency Analysis

```python
imports_to_check = [
    b'kernel32.dll', b'user32.dll', b'advapi32.dll',
    b'wininet.dll', b'winhttp.dll',     # License server communication
    b'crypt32.dll', b'bcrypt.dll',       # Crypto operations
    b'libusb', b'setupapi', b'winusb',   # USB device communication
    b'mscoree.dll',                      # .NET CLR host
    b'Qt',                               # Qt framework
    b'ws2_32',                           # Networking
    b'ole32', b'comctl32', b'comdlg32',  # GUI
    b'shell32', b'gdi32',                # GUI
]
```

### 6. Section Extraction

Extract sections with raw data (RSize > 0, ROff > 0):

```python
for i in range(num_sections):
    s = section_offset + i*40
    rsize = struct.unpack('<I', d[s+16:s+20])[0]
    roff = struct.unpack('<I', d[s+20:s+24])[0]
    if rsize > 0 and roff > 0:
        with open(f'target_section{i}.bin', 'wb') as fw:
            fw.write(d[roff:roff+rsize])
```

### 7. Overlay Analysis

Data appended after the last PE section (often digital signatures or embedded archives):

```python
last_section = section_offset + (num_sections-1)*40
last_rsize = struct.unpack('<I', d[last_section+16:last_section+20])[0]
last_roff = struct.unpack('<I', d[last_section+20:last_section+24])[0]
overlay_offset = last_roff + last_rsize
overlay = d[overlay_offset:]
# Check for PKCS#7 (Authenticode signature)
# First bytes: 0x30 0x82 (ASN.1 SEQUENCE)
# Check for embedded archives: PK\x03\x04 (ZIP), 7z, Rar
```

### 8. .NET / CLR Detection

```python
is_dotnet = b'BSJB' in d[:pe_offset+512]  # CLR metadata header
is_dotnet |= b'mscoree.dll' in d          # .NET runtime import
cor20_rva = struct.unpack('<I', d[pe_offset+208:pe_offset+212])[0]  # CLR header data directory
```

### 9. Runtime Unpacking Strategy Decision

Once the protector is identified, choose the approach:

| Protector | Recommended Approach | Difficulty |
|-----------|---------------------|------------|
| UPX | `upx -d target.exe` or manual OEP search | Easy |
| ASPack | Generic unpacker stub + OEP search | Easy |
| Themida | ScyllaHide + x64dbg + dump at OEP | Hard |
| WinLICE | Process dump + IAT rebuild + VM trace | Very Hard |
| VMProtect | Code tracing + deobfuscation scripts | Very Hard |
| Enigma | Custom unpacker per version | Hard |
| Unknown (encrypted) | OEP search in dumped memory | Hard |

**Approach comparison:**

1. **Wine on Linux** — Fastest for simple packers (UPX, ASPack). Fails for anti-Wine protectors (Themida, WinLICE often crash).
   ```bash
   wine target.exe 2>&1
   # If it runs, use winedbg + process dump
   ```

2. **Windows VM (QEMU/KVM)** — Most reliable. Full ScyllaHide + x64dbg + Process Hacker.
   ```bash
   # QEMU Windows VM setup via virt-manager or CLI
   # Inside VM: x64dbg + ScyllaHide plugin
   # Set breakpoint at OEP → dump → IAT rebuild
   ```

3. **API monitoring (no unpack)** — For understanding license checks without full unpack.
   - Sysinternals Process Monitor
   - API Monitor (rohitab)
   - Fiddler/mitmproxy for HTTP license calls

4. **Remote Windows instance** — Cloud GPU boxes (RunPod) can run Windows containers.

5. **Static-only analysis** — For understanding structure without runtime:
   - Already covered by steps 1-8 above
   - Limited: encrypted payloads cannot be decrypted statically

## Remote Machine Access via Tailscale for Cross-Platform RE

When you need to access files on another machine or run Windows tools remotely:

```bash
# 1. Find the target on the tailnet
tailscale status | grep <hostname-pattern>
# Active nodes show: active; direct <ip>:<port> or active; relay "<location>"
# Offline nodes show: offline, last seen X ago

# 2. SSH to the remote machine
ssh <user>@<tailscale-ip> "command"

# 3. Check what files exist remotely before copying
ssh user@100.x.x.x "ls -la /path/to/files && unzip -l /path/to/archive.zip | head -20"

# 4. Copy files via SCP
scp user@100.x.x.x:/remote/path /local/path
```

## Pitfalls

- **Entry point in a virtual-only section**: If EP RVA falls in a section with RSize=0, the real code hasn't been written to disk — it's decrypted at runtime. Static analysis at that address is meaningless.
- **Subsystem 0**: Some protectors (Themida) set subsystem to 0, which is non-standard. The binary still runs as GUI.
- **False UPX positives**: Some protectors embed "UPX" as a distraction string inside encrypted data. Check for real UPX section names (UPX0, UPX1) to confirm.
- **Wine incompatibility**: Commercial protectors (Themida, Enigma, WinLICE) often detect Wine and crash or refuse to run. Don't waste time debugging — switch to a real Windows environment.
- **Large downloads over Tailscale relay**: Relay connections are slow and drop-prone. Write remote data to a script file first via SSH, then execute it. Use `scp` for smaller files; use `rsync --partial` with resume support for large transfers.
- **Entropy can mislead**: A section with entropy 8.0 could also be pre-compressed data (not encrypted). Check if the first few bytes match known compression signatures (zlib: 0x78 0x9C, LZMA: 0x5D 0x00, etc.).
- **Process dumps need IAT rebuild**: Dumping the decrypted process memory is only half the work. The Import Address Table (IAT) must be reconstructed. Use Scylla (x64dbg plugin) for this.

## Verification

After analysis, confirm findings:

1. **Packer identified?** — Cross-reference section names + entropy + signatures against known protectors table
2. **Payload encrypted?** — Entropy > 7.5, no recognizable headers in the first 100KB
3. **Unpacker found?** — Section with low entropy (< 5.0) containing CALL/JMP instructions
4. **Can it run under Wine?** — Test with `wine target.exe`, watch for crash at protector load

## References

See `references/session-unlocktool-chimera-re.md` for a detailed walkthrough of reverse-engineering UnlockTool (custom encrypted packer, 198 MB, 13 sections, entropy 8.0) and Chimera Tool (WinLICE protector, Qt-based, smart card dongle auth).
