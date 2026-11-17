---
name: reverse-engineering
description: Analyze closed-source binaries, bypass license protections, reverse proprietary protocols, and attack hardware authentication tokens. Covers .NET/C++ static/dynamic analysis, USB protocol RE, dongle/smart-card analysis, and license server bypass patterns.
version: 1.1.0
tags: [reverse-engineering, binary-analysis, security, license-bypass, hardware-security, protocol-analysis, cracking]
---

# Reverse Engineering Skill

Class-level methodology for reversing commercial protected software — from obfuscated .NET binaries to hardware-dongle-gated C++ tools with custom USB protocols.

## When to Use

- User asks to "reverse engineer," "crack," "bypass license," "patch," "deobfuscate," or "analyze [commercial tool]" 
- User provides a Windows .exe / .dll that needs deobfuscation or license bypass
- User wants to understand a proprietary USB protocol between software and hardware
- User asks about hardware dongles, smart cards, or authentication tokens

## Workflow

### Phase 1: Reconnaissance

1. Identify the binary type:
   - **.NET / Mono** — check with `dotnet --info`, look for `mscorlib`, `System.Windows.Forms`, or .NET resources in the PE. Confirm by checking for CLR header (BSJB magic at data dir entry 14) and mscoree.dll import.
   - **C++ / Delphi** — check with Detect It Easy (diec) or just look for CRT imports, UPX sections. Use Python struct parsing or `r2 -q -c 'iIe'` to get language hint.
   - **Packed** — check entropy, section names (UPX, Themida, VMProtect, Enigma, WinLICE)

2. Static PE forensics (no runtime needed):
   - Parse section table via Python `struct`: read PE offset from 0x3c, parse IMAGE_FILE_HEADER + IMAGE_OPTIONAL_HEADER to find section table
   - **Section naming patterns** are packer fingerprints:
     - Random 8-char names (`*P2524Lv`, `LyHORKjI`) → heavy commercial packer (Themida/Enigma variant)
     - Blank/empty names → WinLICE or custom protector
     - `.winlice` section → WinLICE protector (confirmed)
     - `.boot` section → WinLICE boot loader
     - UPX0/UPX1 → UPX (trivial)
     - `.themida` → Themida
     - Standard names (`.text`, `.data`, `.rdata`) → likely unpacked
   - **Check RSize vs VSize**: sections with VSize > 0 and RSize = 0 are decrypted at runtime — they hold no raw data on disk
   - **Entry point analysis**: EP in a high RVA far from .text suggests a packer stub. Compare EP address to section ranges.
   - **Subsystem field**: value 0 (unusual) or undefined suggests custom PE loader from a packer
   - **Overlay data** (data after last section): extract and check for Authenticode PKCS#7 signatures, embedded archives (ZIP/7z), or appended config blobs

3. Entropy measurement as a diagnostic:
   - **Entropy < 6.0**: readable code/data — unpacked or lightly obfuscated
   - **Entropy 6.0–7.5**: compressed (common packers like UPX, MPRESS)
   - **Entropy > 7.5**: encrypted — strong crypto (AES, RC4, custom stream cipher). Entropy near 8.00 (max) means it's solid.
   - Use Python `collections.Counter` + `math.log2` for quick entropy checks
   - Measure per-section entropy, not just the whole file — encrypted payload sections vs clear unpacker stubs

4. Quick triage with radare2:
   ```bash
   r2 -q -c 'iIe' binary.exe
   ```
   Returns: arch, bits, bintype, language hint, subsystem, entry point(s), overlay presence. Most useful single command for initial ID.
   - Network calls: what does it phone home? (HTTPS, raw TCP, WebSocket)
   - Hardware auth: PC/SC smart card reader, dongle DLL, libusb device
   - Protocol surface: ADB, fastboot, Qualcomm EDL, Mediatek BROM, Samsung EUB
   - File I/O: license files, cache DBs, config, logs

3. Identify the security layers (multiply the bypass difficulty):
   - Server-side check (low)
   - Crypto-signed license file (medium)
   - Hardware dongle with private key (high)
   - Server-thin-client model (very high — reversing client gives nothing)

### Phase 2: Tooling Setup

| Target | Tools |
|--------|-------|
| .NET / C# | de4dot (deobfuscation), dnSpy / ILSpy (decompiler), ConfuserEx detector |
| C/C++/Delphi | Ghidra (static), IDA Pro (static), x64dbg (dynamic), Detect It Easy (packer ID) |
| Network | Fiddler / mitmproxy + TLS cert bypass, Wireshark |
| USB | USBPcap + Wireshark, API Monitor / rohitab (Win32 API trace) |
| Smart card | pkcs11-tool (OpenSC), gscriptor, pcsc_scan, APDU sniffer |
| Dynamic analysis | Cheat Engine (memory scan), API Monitor (syscall trace), Procmon |

### Phase 3: License Bypass (common patterns)

**Pattern A — Server check patch:**
```python
# Find the HTTPS call in decompiled code (e.g., "https://license.tool.com/check")
# Patch the success/failure condition to always succeed
# Alternative: DNS redirect to local server that always returns valid response
```

**Pattern B — Cached license file:**
```python
# Find where .lic / .dat / .key is stored (AppData, install dir, registry)
# Reverse the validation logic (RSA? AES? HMAC? just obfuscated comparison?)
# Generate a valid one or copy from a known-good activation
```

**Pattern C — Runtime patching:**
```python
# Set breakpoint on the return value of the auth function
# NOP out the conditional jump, or set eax=1 at the return site
# Watch for time-bomb checks (CompareTime, timer expiration)
```

### Phase 4: Hardware Authentication

**Smart card / dongle steps:**
1. `pcsc_scan` — detect the reader, get ATR (Answer To Reset)
2. `pkcs11-tool --module <driver>` — enumerate slots, tokens, certs, keys
3. `gscriptor` — send raw APDUs to understand the command set
4. Determine if private key is **in card secure element** (extractable via fault injection / decap) or **emulatable** (just signature verification you can capture and replay)

Attack vectors (in increasing difficulty):
- APDU capture/replay (if no freshness/challenge)
- Side-channel (power analysis, timing — needs oscilloscope)
- Chip decap + microprobing (needs FIB/SEM — $10K+ lab)
- Software emulation of the card protocol (if key is not truly random)

**Dongle proxy pattern** (for when dongle check happens at startup only):
```
Tool ──→ PC/SC ──→ dongle
                            
Patch the tool to use a local proxy that caches the dongle responses
```

### Phase 5: Protocol Analysis (USB)

1. Capture with USBPcap
2. Filter by device in Wireshark: `usb.device_address == X`
3. Look for USB bulk transfers — these carry the actual protocol data
4. Identify protocol markers:
   - Qualcomm Sahara: magic bytes `0x00 0x00 0x00 0x01` (hello packet)
   - Qualcomm Firehose: XML over USB bulk endpoints
   - MTK BROM: DA (Download Agent) upload over USB
   - Samsung EUB: proprietary Exynos bulk endpoint protocol

Common tool capabilities that come from USB protocol access:
- FRP bypass (ADB/fastboot commands, or EDL firehose writes)
- Bootloader unlock (vendor OEM commands)
- Partition read/write (low-level memory access)
- IMEI repair (NV item write via Qualcomm DIAG or MTK meta mode)

### Phase 6: Validation

After bypass:
1. Launch the tool, verify it shows "activated" / "registered"
2. Test a device operation (connect via USB, run a FRP bypass, check output)
3. Verify no time-bomb activates after restart
4. Test across a second device to confirm it's not device-locked

### Smart Install Maker (SIM) v5.04 Installers

Used by: Apizu Tool, Hydra Tool, many Chinese-market GSM tools.

**Identification:** The installer is a PE32 (Delphi/Borland) stub with a SIM overlay. Check for:
- `Smart Install Maker` strings
- Overlay data starting with compressed file index (RAR5 or custom compression)
- Password protection — user must enter a password before extraction

**Extraction workflow:**

1. **Password cracking:**
   - Launch installer in Wine with xvfb display (`DISPLAY=:99`)
   - Use `xdotool search --name "Password|Setup"` to find the password dialog
   - Try common passwords first, then brute-force wordlists
   - Known SIM passwords from experience: `1234`, `hydratool` (Hydra Tool V7.0), `123` (common)
   - Once found, confirm by running the installer and checking for error free output

2. **Field-byte patching** (skip password check):
   - SIM v5.04 stores the password check flag at field offset 26 in the config overlay
   - `field[26] = 0` means "no password", `field[26] = 25` (default) means "password required"
   - Patch: change byte at config offset 26 from `25` to `0`

3. **RAR5 overlay extraction:**
   - After the PE stub (~2.1MB) and SIM overlay header, there's a RAR5 archive
   - `unrar x installer.exe` may extract it if password is known
   - Some installers use unsupported compression methods in the RAR5

4. **Embedded file manifest** (even without extraction, find filenames via strings in the overlay):
   - Main executable (.exe) — usually .NET WinForms or Delphi
   - ADB/fastboot binaries, DLLs (exDownload.dll, AdbWinApi.dll)
   - APK files for side-loading on devices
   - Firmware images (frp.bin, pitiful.img, dopher.img)

**Pitfall:** Wine's `setupapi:do_file_copyW` blocks SIM installer file extraction. The actual files can only be extracted on a real Windows environment, or by running the installer inside a Windows VM and capturing files.

### Inno Setup Installers (Octoplus, SamFw)

Used by: Octoplus Samsung, Octoplus FRP, many professional GSM tools.

**Extraction:**
```bash
innoextract -m installer.exe -d /tmp/output/
7z x installer.exe -o/tmp/output/  # fallback
```

**Analysis workflow:**
1. Extract all 1000-5000 files
2. Identify main executable(s) — Delphi GUI + C++ helper binaries
3. Map architecture: GUI → helper (C++) → USB/ADB/fastboot → device
4. Locate license validation code, USB protocol libraries, exploit databases

### License Bypass via MITM + DLL Stubs

For tools with remote license servers AND hardware dongles:

**Infrastructure setup:**
```bash
# DNS poison in /etc/hosts:
echo "127.0.0.1 license.tool.com api.tool.com" >> /etc/hosts

# WinSCard.dll stub — bypasses smart-card authentication
# Replace the real winscard.dll with one that always returns SUCCESS
# Key functions to stub: SCardEstablishContext, SCardConnect, SCardTransmit, SCardDisconnect

# libusb-1.0.dll stub — bypasses USB dongle checks
# Replace with a stub that reports "device connected" on any enumeration attempt
```

**MITM server patterns:**
- Listen on port 8443 (HTTPS) with self-signed CA cert
- Respond with valid-looking JSON: `{"valid": true, "Active": true, "Expiry": "2099-12-31"}`
- Tool-specific JSON field names matter — extract from binary strings

**When this works:** startup-only license checks, cached license fallback, timeout-tolerant tools.
**When it doesn't:** server-thin-client architecture, fresh challenge per session, token rotation.

### Windows VM Deployment Pattern

For tools that can't run under Wine (SIM installers, kernel drivers, USB passthrough):

**VM setup (QEMU/KVM):**
```bash
virt-install --name windows11 --ram 6144 --vcpus 4 \
  --disk path=/var/lib/libvirt/images/windows11.qcow2,size=65 \
  --cdrom /path/to/Win11.iso \
  --os-variant win11 \
  --network network=default,model=e1000e \
  --graphics spice,port=5901
```

**Key VM tips:**
- Use two NICs: virtio (fast, needs driver) + e1000e (built-in, immediate network)
- KVM acceleration is critical — TCG is 10-20x slower
- Interact via keyboard: `virsh send-key windows11 KEY_LEFTMETA KEY_R` (Win+R)
- UAC prompts need Alt+Y to accept
- Screenshots: `virsh screenshot windows11 /tmp/screenshot.png`
- Enable RDP: `reg add "HKLM\\System\\CurrentControlSet\\Control\\Terminal Server" /v fDenyTSConnections /t REG_DWORD /d 0 /f`

**Capturing tool behavior:**
- Run tool inside VM → capture API calls via MITM server on host
- Forward host ports: `-nic user,hostfwd=tcp::8443-:8443`
- DNS in VM should point to host for MITM interception

### Octoplus Tools Specifics

**Octoplus Samsung v5.1.2.2:**
- Inno Setup → 4901 files extracted
- Architecture: Delphi GUI (245MB) + rd.exe (298KB C++ console helper)
- Crypto: AES-GCM, PBKDF2-HMAC-SHA512 (5000/9000 iterations), RSA PKCS#1.5
- License endpoints: `node.octoplusbox.cloud:8443`
- HWID: PBKDF2 from `SELECT Manufacturer,SerialNumber FROM Win32_PhysicalMemory`
- File format: `.oct` v1.0, `.orf` v2.0 (OCTOPUS format, 16-byte IVs)
- Standalone exploit: `rd.exe` can patch IMEI via ext4 mount at `md/NVRAM/NVD_IMEI/LD0B_001`

**Octoplus FRP v3.0.5.0:**
- Inno Setup → 2091 files extracted
- Same crypto as Samsung tool, different license endpoints

## Pitfalls

- **Server-thin-client architecture**: If the device-specific exploits are fetched from the server at runtime, cracking auth gives you an empty shell. Check what happens offline first.
- **Dongle with freshness**: If the server sends a new challenge each session, APDU replay won't work — need actual key extraction.
- **Packed C++ tools**: UPX is trivially unpackable. Themida/VMProtect can take weeks. Know the packer before committing.
- **Anti-debug / anti-VM**: Check for IsDebuggerPresent, NtQueryInformationProcess, VMware detection. Use ScyllaHide or a bare-metal environment.
- **Crashing on crack attempts**: Many GSM tools have integrity checks (hash of .exe, checksum of loaded assemblies). Patch those first.

## Verification

Always verify with a real device connection after bypass work:
1. Connect target device in the required mode (EDL, BROM, EUB, ADB)
2. Run a supported operation
3. Confirm the tool reports success

Don't skip this step — "activated" in the UI means nothing if the actual driver/protocol layer doesn't work without server validation.
