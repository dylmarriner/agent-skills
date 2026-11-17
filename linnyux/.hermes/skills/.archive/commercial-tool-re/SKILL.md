---
name: commercial-tool-re
description: Reverse-engineer commercial Windows service tools (GSM repair, device unlock, FRP bypass). Covers installer extraction, protocol identification by DLL analysis, chipset communication protocols, file encryption reverse engineering, and license server MITM/emulation. Complements windows-re-toolkit (tool installation) and windows-re-toolkit-analysis (binary decompilation).
related_skills:
  - windows-re-toolkit
  - windows-re-toolkit-analysis
---

# Commercial Tool Reverse Engineering

Extract, analyze, and backdoor Windows-based commercial tools for mobile device service (Samsung, Octoplus, TFT Unlock, etc.). Focuses on the workflow from installer to protocol understanding.

## Trigger Conditions

- User says "install" or "extract" a tool from a `.exe` installer
- User wants to "reverse engineer" a commercial mobile repair tool
- User asks about unlock tools, FRP tools, Samsung service tools
- User wants to understand how a tool communicates with devices or its license server
- User asks to "backdoor" or "emulate" a license server

## Installer Extraction Workflow

### Step 1: Identify the Installer Type

```bash
# Check file type and PE structure
file target.exe

# Read overlay header
python3 -c "
import struct
with open('target.exe','rb') as f: d = f.read()
po = struct.unpack('<I', d[0x3c:0x40])[0]
ns = struct.unpack('<H', d[po+6:po+8])[0]
ss = po + 24 + struct.unpack('<H', d[po+20:po+22])[0]
os = 0
for i in range(ns):
    s = ss + i*40
    ro = struct.unpack('<I', d[s+20:s+24])[0]
    rs = struct.unpack('<I', d[s+16:s+20])[0]
    os = max(os, ro + rs)
print(f'PE: {os:,} bytes, Overlay: {len(d)-os:,} bytes')
print(f'Overlay: {d[os:os+80]}')
"

# Check for known installer strings
7z l target.exe 2>&1 | head -10
strings target.exe | grep -iE "inno setup|smart install|nullsoft|nsis|setup maker" | head -5
```

### Step 2: Extract Based on Type

**Inno Setup** — use innoextract:
```bash
# Get prebuilt i686 binary
wget -q "https://github.com/dscharrer/innoextract/releases/download/1.9/innoextract-1.9-linux.tar.xz" -O /tmp/ie.tar.xz
tar xf /tmp/ie.tar.xz -C /tmp/
/tmp/innoextract-1.9-linux/bin/i686/innoextract -e -d /tmp/extracted target.exe
```

**Smart Install Maker (SIM)** — proprietary, no Linux tool. Workaround:
- Patch password field (change "25" to "0" at config offset ~0x5a2be in the overlay)
- Run under Wine + xvfb (may still fail on file copy)
- Target size: PE ~50-60KB, overlay hundreds of MB

**NSIS** — use 7z:
```bash
7z x -o/tmp/extracted target.exe
```

**InstallShield** — use unshield:
```bash
unshield x target.exe -d /tmp/extracted
```

### Step 3: Identify Protocol Stacks by DLL Analysis

After extraction, scan the extracted directory for DLLs and map them to protocols:

```bash
find /tmp/extracted -name "*.dll" -o -name "*.exe" | while read f; do
    echo "$(basename $f): $(file "$f" | cut -d: -f2-)"
done
```

Use the chipset protocol table below to identify what the tool supports.

## Chipset Protocol Reference

| DLL/String Pattern | Chipset | Protocol |
|-------------------|---------|----------|
| `libnvflash`, `libnvos`, `libnvusbhost`, `libnvaes_ref` | NVIDIA Tegra | nvflash RCM + 3P command/response + WinUSB transport + DWC3 USB3 exploits |
| `Sahara`, `Firehose`, `EDL`, `DIAG`, `9008`, `05C6` VID | Qualcomm Snapdragon | Sahara streaming protocol, Firehose programmable, EDL mode |
| `BROM`, `DA`, `Preloader`, `scatter`, `0E8D` VID | MediaTek | BROM download agent, HACC encrypted loader, RPMB access |
| `spd_`, `Spreadtrum`, `Unisoc`, `SC7731E`, `SC9832E` | UNISOC/Spreadtrum | Custom serial loader protocol |
| `INFINEON`, `Swift` | Infineon (legacy) | Preloader + mainloader + EEPROM protocol |
| `libusb-1.0.dll`, `libusb0.dll` | Generic | USB bulk transfer transport |
| `AdbWinApi.dll`, `AdbWinUsbApi.dll` | Android | ADB bridge protocol |
| `libeay32.dll`, `ssleay32.dll` | OpenSSL | TLS 1.0.x for license/network |
| `meflash.dll` | Generic (Sony Ericsson) | "Mobile Equipment Flash USB API" — VC++ 6.0 DLL for low-level USB flash communication with Sony Ericsson devices |
| `EPIUSB`, `U8500_USB_ROM`, `u8500` | ST-Ericsson (U8500) | USB ROM boot mode protocol via custom kernel driver path `\\.\EPIUSB` |

## File Encryption Formats

Many tools encrypt firmware/loader files (often .oct or .orf extensions):

| Format | Header Magic | Encryption | Notes |
|--------|-------------|------------|-------|
| OCTOPUS v1.0 | `OCTOPUS_v.1.0\0\0\0` | AES-128-CBC | Used by Samsung tools for model data, EEPROM dumps, certificate files. Keys are runtime-derived. |
| OCTOPUS v2.0 | `OCTOPUS_v.2.0\0\0\0` | AES-128-CFB (via CryptoPP) | Used by FRP tools for loader firmware. Decryption engine in MetaCore.dll (Crypto++ statically linked). Two IV groups: main loaders get `f647c0f9...`, Unisoc loaders get `69003595...`. |
| Custom resource | `0x7743C66B` magic | Proprietary | Encrypted strings/resources in the main exe. Decrypted at runtime with embedded key data from INIT_KEY_1 and INIT_KEY_2 constants. |

**Approach for key extraction:**
- Search DLLs for 16-byte high-entropy blobs (AES keys)
- Look for Crypto++ classes (`CFB_DecryptionTemplate`, `ConcretePolicyHolder`, `Rijndael`) in statically linked libraries
- Use `strings -a dll_name.dll | grep -iE "key|aes|decrypt|cfb|cbc|init|iv_"` to find reference names
- If the main exe is Themida-packed (SecureEngineSDK32.dll), the engine DLL (e.g. MetaCore.dll) usually isn't packed — analyze that instead

## License Server MITM / Backdoor

Many tools require online license validation. Here's the MITM approach:

### Step 1: Find Server Endpoints

When the main EXE is heavily packed (VMProtect/Themida/unknown protector), strings may be garbage. Fall back to unpacked configuration files:

```bash
# Priority 1: unpacked companion DLLs
strings app/*.dll 2>/dev/null | grep -iE "https?://|octoplus|\.cloud|\.club|/license|/activate" | sort -u

# Priority 2: UTF-16 INI/language files (always unpacked, often contain server URLs)
find app/ -name "*.ini" -o -name "*.i" | while read f; do
    iconv -f UTF-16 -t UTF-8 "$f" 2>/dev/null | grep -iE "https?://|url|server|shop|api" || true
done

# Priority 3: only if the first two fail — raw binary strings (may be garbled)
strings target.exe | grep -iE "https?://|octoplus|node\.|\.cloud|\.club|/api/|/auth|/license|/activate|/verify" | sort -u
```

Common patterns: port 8443 (non-standard HTTPS), dual DNS names for redundancy, JSON API responses.

### Step 2: DNS Poison

```bash
sudo bash -c 'echo "127.0.0.1 server1.com server2.com server3.com" >> /etc/hosts'
```

### Step 3: Generate Trusted Certificates

```python
# Generate CA + server cert for the tool's domain
# Install CA in system trust store:
#   sudo cp ca.pem /usr/local/share/ca-certificates/octoplus_ca.crt
#   sudo update-ca-certificates
```

### Step 4: Run MITM Server

Respond on port 8443 (or redirect 80/443 to 8443 via iptables):
```bash
sudo iptables -t nat -A PREROUTING -p tcp --dport 443 -j REDIRECT --to-port 8443
sudo iptables -t nat -A OUTPUT -p tcp --dport 443 -d 127.0.0.1 -j REDIRECT --to-port 8443
```

Return JSON with the fields the tool expects. Common fields found via string analysis:
- `valid`, `Active`, `active`, `success` — boolean pass/fail
- `LicenseKey`, `Token`, `tokenBypass` — credential fields
- `HwId`, `HWIDHash1`, `SerialNumber`, `serial` — HWID fields
- `Expires`, `expiry`, `DateTime` — expiry timestamps
- `Balance`, `balance`, `credit` — credit system fields
- `Message`, `message`, `Error`, `error` — status/error text
- `responseData`, `result`, `code`, `data` — nested response containers

### Step 5: Handle the Smart-Card Dongle

Some tools use a hardware dongle (DigitalLicenseManager.exe, smart-card checks). The license check happens BEFORE the network call. Approaches:
- Binary-patch the dongle check (find the DLL function call and NOP it)
- Run on real Windows with USB dongle
- Patch the registry entries (often under `HKLM\SOFTWARE\OCTOPLUS\`, `OCTOPUS\`)

## SIM Installer Password Cracking via Wine + xvfb

Smart Install Maker (SIM) v5.04 installer — password-protected, proprietary format, no Linux extractor. Workaround: run under Wine + xvfb and brute-force the password dialog.

### Step 1: Prepare Environment

```bash
export WINEPREFIX=$HOME/.wine_sim_crack
export DISPLAY=:99
rm -rf $WINEPREFIX
wineboot -u 2>/dev/null
# Start Xvfb if not running
pgrep Xvfb || Xvfb :99 -screen 0 1024x768x16 &
```

### Step 2: Single Password Test

```bash
timeout 30 wine "/path/to/Installer.exe" 2>/dev/null &
sleep 4
# Find password dialog
WIN=$(xdotool search --name "Password\|Smart Install\|Setup" 2>/dev/null | head -1)
if [ -n "$WIN" ]; then
    xdotool type --window "$WIN" "candidate_password"
    sleep 1
    xdotool key --window "$WIN" Return
    sleep 4
    # Window still open? = wrong password
    xdotool search --name "Password" 2>/dev/null | head -1 && echo "WRONG" || echo "CORRECT"
fi
```

### Step 3: Known Passwords

| Tool | Password | Size | Installer |
|------|----------|------|-----------|
| Hydra Tool V7.0 | `hydratool` | 1.9GB RAR → 2.7GB SIM | Smart Install Maker v5.04 |
| Apizu Tool V4.4.4 | `1234` | 199MB | Smart Install Maker v5.04 |

### Pitfalls
- **Even correct passwords fail under Wine** — SIM installer's `setupapi:do_file_copyW` is a Wine limitation. The actual tool files can't be extracted on Linux. **Use a Windows VM** (see next section).
- **Fresh Wine prefix per attempt** — SIM installers leave state that blocks retry.
- **xdotool window detection is fragile** — try broader patterns like `--name "Password|Setup|Installer|Hydra|Apizu"`.

## Windows RE VM Deployment

Many tools (Hydra, Apizu, Octoplus) can't run fully under Wine due to SIM file copy failures, USB dongle checks, or kernel driver access. Solution: a QEMU/KVM Windows 11 VM.

### VM Setup

```bash
# Create VM with KVM acceleration + e1000e NIC (works without extra drivers)
virt-install \
  --name windows11 --ram 6144 --vcpus 4 \
  --disk path=/var/lib/libvirt/images/windows11.qcow2,size=65 \
  --cdrom /path/to/Win11.iso \
  --os-variant win11 \
  --graphics spice,port=5901 \
  --network network=default,model=e1000e \
  --tpm backend.type=emulator,model=tpm-crb,version=2.0

# Attach virtio-win ISO for drivers
virsh attach-disk windows11 /path/to/virtio-win.iso sdc --type cdrom --config
```

### NIC Strategy

| Model | Driver Source | Use |
|-------|--------------|-----|
| `e1000e` | Built into Windows | Immediate network access from first boot |
| `virtio` | virtio-win ISO | High perf after driver install |

**Critical**: Each NIC needs a unique MAC address or Windows networking breaks.

### GUI Automation via virsh

```bash
# Ctrl+Alt+Del (login screen)
virsh send-key windows11 KEY_LEFTCTRL KEY_LEFTALT KEY_DELETE

# Type credentials
virsh send-key windows11 KEY_U KEY_S KEY_E KEY_R
virsh send-key windows11 KEY_ENTER

# Open Run dialog (Win+R)
virsh send-key windows11 KEY_LEFTMETA KEY_R

# Launch a program
virsh send-key windows11 KEY_C KEY_M KEY_D KEY_ENTER

# Dismiss UAC (Alt+Y)
virsh send-key windows11 KEY_LEFTALT KEY_Y
```

### Screenshot State Detection

```bash
virsh screenshot windows11 /tmp/ss.png
python3 -c "
from PIL import Image
img = Image.open('/tmp/ss.png')
w,h = img.size
pixels = set()
for x in range(0,w,50):
    for y in range(0,h,50):
        pixels.add(img.getpixel((x,y)))
grays = [p for p in pixels if p[0]==p[1]==p[2] and p[0]>200]
blues = [p for p in pixels if p[2]>150 and abs(p[0]-p[1])<30]
print(f'{len(pixels)} colors, {len(grays)} grays, {len(blues)} blues')
if len(grays) > 5 or len(blues) > 5: print('Desktop visible')
else: print('Booting, login screen, or sleeping')
"
```

### NIC Management

```bash
# Add e1000e for working network
virsh attach-interface windows11 network default --model e1000e --mac 52:54:00:77:XX:XX --config

# Remove a specific NIC by PCI address
cat > /tmp/detach.xml << 'EOF'
<interface type='network'>
  <mac address='52:54:00:76:c3:3b'/>
  <source network='default'/>
  <model type='e1000e'/>
  <address type='pci' domain='0x0000' bus='0x04' slot='0x00' function='0x0'/>
</interface>
EOF
virsh detach-device windows11 /tmp/detach.xml --config
```

### Pitfalls
- **Duplicate MACs crash Windows networking.** Always unique per NIC.
- **SATA devices can't be hotplugged** — shut down VM to add/remove disks.
- **virsh screenshots may be stale** — compare pixel diffs between captures.
- **TCG emulation is unusably slow** (15-20m Win11 boot). Always use KVM.
- **Windows Firewall blocks ping/RDP by default.** Log in and run `netsh advfirewall set allprofiles state off`.
- **Windows 11 Home has no RDP server** — use Pro/Enterprise.
- **SPICE/QXL driver not installed** = screenshots show framebuffer, not actual desktop state.

For full virsh command reference, screenshot analysis scripts, and troubleshooting, see `references/virsh-interaction.md`.

## Binary Patching for License Bypass

### Delphi VCL Binaries (OctoplusSamsung.exe, etc.)

For Delphi binaries with RTTI enabled, you can find function references by name:

```bash
# Search for check function names
strings target.exe | grep -iE "check_|validate_|license_|activate_"
```

Common check function names: `check_odex`, `check_hashes`, `check_aes_gcm`, `check_revocation`, `check_crl`, `check_issued`.

In the Delphi VCL, these are method pointers. Find their references and NOP the conditional jumps that branch on failure.

**Pitfall: Delphi register-based calling convention hides string xrefs.** Delphi uses register-based addressing (EAX/EDX/ECX) instead of PUSH for function arguments. This means searching for `68 xx xx xx xx` (PUSH imm32) will find ZERO xrefs in Delphi code. Instead:
- Use `MOV [ESP+xx], imm32` (opcode `C7 44 24 xx` followed by the address)
- Use LEA + MOV patterns
- Function prologues are still `55 8B EC` (push ebp; mov ebp, esp)
- The subagent's `metacore_patch_v2.py` could only find AUTH_IsReady xrefs (it was using PUSH search). CompareAllBBChipHWID, customer name mismatch, and SOC verification strings are real at their offsets but their xrefs use register-based addressing not found by the PUSH scan.

### Qt/C++ Native DLLs (DigitalLicenseManager.exe, MetaCore.dll)

Qt/C++ binaries linked statically with OpenSSL or Crypto++ — no managed code, no VCL RTTI. Approach differs:

**Strategy A: DNS Spoof + Local MITM Server** — for binaries with network license validation
1. Find server domains via `strings target.exe | grep -iE 'https?://|\.cloud|\.club|/license|/activate'`
2. DNS poison in `/etc/hosts`: `127.0.0.1 server1.com server2.com`
3. Generate a CA cert for the domain, install in system trust store
4. Run local HTTPS server returning fake license JSON
5. Redirect 80/443 to your port via iptables

**Strategy B: Binary NOP-Patching** — for DLLs with specific failure strings
1. Find failure strings: `strings target.dll | grep -iE 'fail|invalid|mismatch|not found|is NULL'`
2. Locate them in the binary at specific offsets
3. Find the conditional jump (JNE/JE/JZ/JNZ) that branches to the failure path
4. NOP the condition or reverse the jump (JNE → JE)
5. Or insert `xor eax, eax; ret` (33 C0 C3) at the function entry to force success return

**Strategy C: DLL Proxy Injection** — for runtime patching without modifying files on disk
1. Identify a system DLL the target loads (VERSION.dll, winspool.drv, ws2_32.dll)
2. Write a proxy DLL that forwards all exports to the real system DLL
3. Add payload in DllMain to patch the target DLL's memory at load time
4. Place the proxy DLL in the app directory (Windows searches app dir before system path)

**Real-world targets with offsets:**

| Target | Binary | Offset | Patch Type | Notes |
|--------|--------|--------|------------|-------|
| CompareAllBBChipHWID | MetaCore.dll | 0x938274 | UNVERIFIED | MTK HWID comparison — string at 0x938274 but axt/r2 shows ZERO direct imm refs in FRP 3.0.6.0; prior 0x6300ad JZ-patch claim not reproducible. Needs a runtime debugger. |
| Customer name mismatch | MetaCore.dll | via xrefs | NOP comparison | String: "customer name mismatch with AUTH file" |
| AUTH_IsReady | MetaCore.dll | 0x581886 (raw) | `33 C0 40 C3` (xor eax,eax; inc eax; ret) | Always return TRUE. Verified 2026-08-24; original prologue was `68 28 da 90 05 8d 8e 70`. |
| SOC_Verification impl1 `fcn.056204b0` | MetaCore.dll | 0x61F956 (raw) | `75 4A` -> `90 90` | NOP the `jne <SOC_FAIL>`; forces the SOC_OK (status==0xC1) path which `xor eax,eax`-returns 0. Verified 2026-08-24. |
| SOC_Verification impl2 `fcn.056cdf30` | MetaCore.dll | 0x6CD3E0 (raw) | `75 4A` -> `90 90` | Same gate, second DA/SOC family. Verified 2026-08-24. |
| SOC verification | MetaCore.dll | via xrefs | Always return OK | String: "SOC_Verification(): SOC_OK" |
| No active license found | DigitalLicenseManager.exe | via xrefs | NOP fail check | LAx packed — unpack first, then patch |
| SSL verify (ASN1_item_verify) | DigitalLicenseManager.exe | via xrefs | `mov eax, 1; ret` | OpenSSL static — patch function entry |

### Runtime In-Memory Backdoor (VERIFIED 2026-08-24)

Durable, disk-invisible auth neutralizer: a 32-bit `metacore_backdoor.exe` that
launches the tool, PEB-walks the remote process (`NtQueryInformationProcess` ->
`PebBaseAddress` -> `Ldr` -> `InLoadOrderModuleList`, reading `DllBase` and
`BaseDllName` via `ReadProcessMemory` — deterministic, no psapi/ToolHelp), finds
MetaCore.dll, and `WriteProcessMemory`s the auth patches in live memory with
read-back verification. No patched files on disk.

Key lesson: **AUTH_IsReady's prologue `68 28 DA 90 05 8D 8E 70` is `push <abs32>` —
the loader's relocation pass rewrites that absolute immediate at map time, and the
raw->rva offset differs per PE section.** A fixed-rva patch of an absolute-immediate
site will drift. Fix: `memscan()` (overlapping `ReadProcessMemory` scan) for the
exact prologue pattern across the image and patch where it actually landed.

Verified 3/3 in-memory: AUTH_IsReady self-localized @+0x582486, SOC1 gate NOP
@+0x620556 (`cmp al,0xC1; jne <SOC_FAIL>` -> `90 90`), SOC2 gate NOP @+0x6CDFE0.
Sources/binaries in /home/lin/RE_out/ (metacore_backdoor.*, fold docs).

Pitfall: OctoplusFRP.exe does NOT load MetaCore.dll during a headless launch — it
exits at the pre-device/license gate. MetaCore maps only when a real MTK/DA AUTH
session starts (phone attached + op run). So the backdoor fires on a live device
session, not at first launch. Self-test via `metacore_backdoor.exe metacore_host.exe MetaCore_orig.dll`.

### Custom UPX Variants (OctoplusSamsung.exe, OctoplusSamsungNew.exe)

Many tools rename UPX section names to evade naive `upx -d`:
- Standard UPX: `UPX0`, `UPX1`, `UPX!`
- Octoplus Samsung v5.1.2.2 (UPX 3.91): `.ybI`, `.(:R`, `.H0]`
- Octoplus Samsung New (UPX 3.95): `.TeK0`, `.TeK1`, `.TeK2`
- Octoplus FRP: `.OCT0`, `.OCT1`, `.OCT2`

`upx -d` fails with `NotPackedException` because section names don't match. Approaches:
1. Manual unpack: hex-edit `UPX0`/`UPX1`/`UPX!` over the custom names, then run `upx -d`
2. Patch UPX source to skip section name validation
3. Hardware breakpoint on `.text` section after decompression (dynamic analysis)
4. Focus on companion DLLs that aren't packed (e.g., MetaCore.dll is always unpacked even when the main EXE is packed)

**TeK packer refinements** (from OctoplusSamsungNew.exe — 141MB, PE32, 332 sections):
- **`.TeK1` (31MB, entropy ~7.82, EXECUTE flag)** — NOT encrypted. It's obfuscated x86 Qt/C++ code. The Samsung protocol logic (device identification, Odin handshake, partition operations) is directly readable. High entropy comes from optimized/obfuscated C++ compilation, not crypto.
- **`.TeK3` (16MB, entropy ~7.42)** — Genuinely AES-encrypted. Only a couple of function prologues found vs hundreds expected for real x86. XOR with TeK0 key material at multiple sizes fails. Almost certainly AES-CBC or AES-CTR.
- **`.TeK0` (33KB, entropy ~7.99)** — Key table. Structured header with low-entropy preamble, relocation fixup entries matching section VAs, and crypto key material in the 0x200-0x83D0 region.
- **`.TeK2` (3.5KB)** — Small auxiliary section, likely fixup or import table.

**Finding the TeK decryption stub:** Entry point of OctoplusSamsungNew.exe lands inside `.TeK3` range (VA 0x7862340). `.text` makes direct CALLs (`E8 rel32`) into TeK section VAs at runtime. No static immediate references found in `.text` or `.rdata` — addresses are runtime-computed. Scan script:
```python
target_min = image_base + 0x59bc000
target_max = image_base + 0x77d7000
for pos in iter(lambda: text_raw.find(b'\\xe8', pos), -1):
    rel = struct.unpack('<i', text_raw[pos+1:pos+5])[0]
    target = image_base + 0x1000 + pos + 5 + rel
    if target_min <= target <= target_max:
        print(f'CALL at VA 0x{image_base+0x1000+pos:x} -> VA 0x{target:x}')
```

**Pragmatic approach:** Focus on companion DLLs (MetaCore.dll) — same protocol logic, directly analyzable. TeK3 decryption needs a runtime debugger.

### Packer Identification by Section Names

| Section Names | Packer | Typical |
|---------------|--------|---------|
| `.ybI`, `.(:R`, `.H0]` | Custom UPX 3.91 | OctoplusSamsung.exe |
| `.TeK0`, `.TeK1`, `.TeK2` | Custom UPX 3.95 | OctoplusSamsungNew.exe |
| `.OCT0`, `.OCT1`, `.OCT2` | Custom UPX 3.9x | Octoplus FRP |
| `.k9T0`, `.k9T1`, `.k9T2`, `.k9T3` | K9/Korimir crypto packer | Medusa Pro Software.exe |
| `.vmp0`, `.vmp1` | VMProtect v2.x | MedusaFlasher.exe |
| `.LAx0`, `.LAx1` | LAx custom packer | DigitalLicenseManager.exe |
| `.winlice`, `.boot` | Winlice | ChimeraInstaller.exe |
| `.b}k`, `. W1`, `.H#7` | Unknown VMProtect-like protector (pepack: "no packer found") | OctoplusSuite.exe |
| `.O@N`, `.BF?`, `.p-A` | Unknown VMProtect-like protector (pepack: "generic") | SeUpdater.exe |
| `CODE`, `DATA`, `BSS` | Borland Delphi (unpacked) | Older tools |
| `.text`, `.rdata`, `.data`, `.rsrc` | MSVC (unpacked) | Clean DLLs |
| `UPX0`, `UPX1`, `UPX!` | Standard UPX | Obvious tools |

**Note on `.rsrc` size discrepancy:** Heavily protected binaries may report tiny raw `.rsrc` sizes (e.g., 71KB raw → 64MB virtual). This is compressed/encrypted resource data that gets decompressed at runtime — not an indicator of few resources.

## Parallel Multi-Target RE Pipeline (SSH Fan-Out)

When analyzing multiple commercial tools simultaneously on a remote machine, dispatch independent subagents via `delegate_task`. Each gets an isolated SSH session — they run in parallel and results consolidate when ALL finish.

### Dispatch Pattern

```
delegate_task(tasks=[
    {"goal": "Extract + RE tool A on target_machine",
     "context": "SSH root@10.0.0.1. File at /path/to/A.exe. Steps: 1) innoextract 2) file inventory 3) strings 4) packer ID 5) save report"},
    {"goal": "Extract + RE tool B on target_machine",
     "context": "SSH root@10.0.0.1. Same process."},
    {"goal": "Extract + RE tool C on target_machine",
     "context": "SSH root@10.0.0.1. Same process."},
])
```

### Per-Tool Analysis Sequence

1. **Extract** — innoextract (Inno Setup), 7z (NSIS), unshield (InstallShield)
2. **File inventory** — list all EXEs/DLLs, note sizes
3. **Packer ID** — section names, entropy, zero-size .text
4. **Companion DLLs first** — often unpacked even when main EXE is protected (meflash.dll, MetaCore.dll, libeay32.dll)
5. **Strings scan** — URLs, IPs, error messages, crypto constants, chipset refs
6. **Language files** (plaintext UTF-16) — activation URLs, module names, country lists
7. **Driver INF files** — HW VID/PID, USB protocol families
8. **Firmware blobs** — count and type (eMMC, UFS) reveal chipset support breadth
9. **Save structured report** to shared results directory

### Post-Collection Cross-Reference

After all subagents return, identify common infrastructure across tools:
- Shared activation servers → MITM attack surface
- Shared USB libraries (libusb-1.0.dll) → DLL interposer strategy
- Shared file encryption (OCTOPUS_v.1.0) → single decryption approach
- Shared packer families (K9, VMProtect, TeK) → single unpacking methodology

### Pitfalls

- **File writing via SSH subagents**: `write_file` inside a subagent may fail due to shell quoting. Fallback: have the subagent write files via `python3` inline heredoc.
- **Verify reports**: `test -f <path> && wc -l <path>` after subagents return — failed Hermes `write_file` may still exist via the SSH pipeline.
- **Results directory**: Store all reports in a shared directory for cross-tool comparison.
- **Subagent timeout**: Max 600s. Budget 4-5 min per tool minimum for innoextract + strings analysis.

## FRP Unlock Methods (Per-Chipset)

Extracted from Octoplus FRP tool v3.0.6.0 analysis. Each chipset family has a distinct communication protocol and FRP bypass method.

### Samsung Exynos (Odin Protocol)

**Connection:** `drSamsung_ExynosDM` — Download Mode (Vol− + Home + Power)
**FRP Reset Methods:** `mcResetFRP`, `mcResetFRPsBoot`, `mcResetFRPUpload`, `mcResetFRPsBootUpload_7Android`, `mcResetFRP_ModemA16`

**Methodology:**
1. Enter Download Mode → Connect to tool
2. Flash signed engineering bootloader via Odin protocol
3. Remove FRP via Odin protocol commands
4. Reboot

**Bootloader locking:** Newer Exynos bootloaders (Exynos 2400 on S24 SM-S921B firmware S921BXXSFDZE1) block PIT read in production firmware. Handshake and session setup work, but PIT dump returns 0xFFFFFFFF. Requires an engineering bootloader signed for the specific bootloader revision — cannot use generic Odin protocol alone.

**Capability codes per model** are stored in `SamsungModels.oct` (OCTOPUS v1.0 encrypted) and mapped in the main EXE's Delphi RTTI.

### Qualcomm Snapdragon (EDL 9008)

**Connection:** `drQCDM_ALL`, EDL Mode (9008 via USB PID)
**FRP Reset:** `mcResetFRPQ9008`

**Methodology:**
1. Enter EDL Mode (key combo or test point)
2. Load firehose programmer (`prog_emmc_firehose_*.elf`)
3. Write to FRP partition or format userdata
4. Reboot

**Firehose params** stored in `FirehoseParams.db` (SHA256 hashes of approved loaders).

### MediaTek (BROM/Preloader)

**Connection:** `drGeneral_MTK`, `drGeneral_MTK_v1936`, `drGeneral_MTK_v2148`
**Auth:** `drGeneral_MTK_woutBypassAuth`, `drGeneral_MTK_CUSTOM`
**FRP Reset:** Via MetaCore.dll AUTH flow

**Methodology:**
1. Enter Preloader mode (vol keys or empty battery + USB)
2. BROM handshake → DA download via authenticated MetaCore.dll
3. Format persist partition or write FRP flag
4. Reboot

**MetaCore.dll handles:** AUTH file loading (`AUTH_Load`), HWID comparison (`CompareAllBBChipHWID`), SOC verification, customer name validation. The `.orf` files (MTKLoaders.orf, QComLoaders.orf, etc.) use OCTOPUS v2.0 AES-128-CFB encryption with keys embedded in MetaCore.dll's Crypto++ static linkage.

### ADB-Based (Generic)

**Connection:** `drADB` via `AdbWinApi.dll`
**FRP Reset:** `mcResetFRPADB`

**Methodology:**
1. Enable ADB in recovery or setup wizard
2. `adb shell` → delete `/data/system/gesture.key`
3. `adb shell settings put secure frp_lock 0`
4. `adb reboot`

Requires ADB access which is blocked on most locked devices. Only works on older Android or devices with a setup wizard exploit active.

## Reference Files

Session-specific analysis, patch scripts, and FRP method tables are stored as reference files under this skill:
- `references/octoplus-analysis.md` — Octoplus Samsung v5.1.2.2 + FRP v3.0.5.0 initial RE (2026-07-15)
- `references/hydra-tool-download.md` — Hydra Tool v7.0 download verification and install workflow
- `references/virsh-interaction.md` — QEMU/KVM GUI automation for Windows RE VM
- `references/octoplus-re-20260720.md` — Extended analysis: Custom UPX variants, LAx packer, MetaCore HWID offsets, Chimera Winlice, patch script structure
- `references/octoplus-suite-167-analysis.md` — Octoplus Suite 1.6.7 static analysis: unknown VMProtect-like protector, companion DLLs, activation URL from English.ini, complete hardware ID list from INF files, operation strings
- `references/session-20260720-findings.md` — Detailed per-session findings: MetaCore DLL location fix, AUTH_IsReady patch confirmation, DLM 7-patch table, TeK packer deep analysis, Chimera boot section extraction, A54 MDM methodology, S24 PIT block
- `references/medusa-pro-flasher-20260720.md` — Medusa Pro 2.2.5.8 + Medusa Flasher 1.1.0.2: K9/Korimir and VMProtect packer details, activation server URL, chipset support matrix, USB transport comparison, ST-Ericsson U8500 protocol notes

## Pitfalls

- **Download mirrors are unreliable** — MediaFire throttles free users (~300KB/s for 1.88GB files), Mega mirrors go dead (ENOENT), Google Drive has virus-scan interstitials. Always extract all mirror URLs from page source and try them in order: GDrive → Mega → MediaFire. Use `curl -s '<download-page>' | grep -oP 'https?://[^"'"'"' \t<>]*\.(zip|exe|rar)[^"'"'"' \t<>]*'` to find embedded links.
- **Fake download pages exist** — the `hydra-tool-downl0ad.github.io` page is a scam that redirects to github.com. The real site is `hydradongle.com`. Always verify you're on the official domain before extracting download links.
- **Stated file sizes can be wrong** — the Hydra Tool site lists 200MB but the actual RAR is 1.88GB. Plan disk space accordingly.
- **SIM installers can't be extracted on Linux** — the format is proprietary with password protection. Wine + xvfb workaround is partial and may fail on file copy.
- **Themida-packed binaries** (SecureEngineSDK32.dll) are code-virtualized — static analysis is extremely difficult. Focus on companion DLLs that aren't packed (MetaCore.dll, libnv*.dll).
- **OpenSSL 1.0.1m** (from 2015) is commonly used. Known vulns exist (Heartbleed, padding oracle) but the client may still validate certs against the system store.
- **.oct/.orf decryption keys** are not stored in plaintext — they're runtime-derived through PBKDF2-HMAC-SHA512. The salt/key material is embedded as byte blobs (INIT_KEY_1, INIT_KEY_2) in the Delphi RTTI.
- **APK and driver files** within extracted installers are often plain (Android APKs, Windows INF/MSI) — these are extractable even when the main .oct files are encrypted.
