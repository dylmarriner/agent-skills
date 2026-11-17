---
name: mobile-tool-re
description: Extract, analyze, and reverse-engineer mobile service tool installers (Octoplus, Chimera, Z3X, TFT Unlock, etc.). Covers installer identification, extraction, post-extraction infrastructure mapping, license-system discovery, and Windows VM runtime setup for commercial GSM/Android repair software.
related_skills:
  - windows-re-toolkit
  - bootrom-exploitation
  - samsung-unlock
---

# Mobile Service Tool Reverse Engineering

Extract and analyze commercial mobile repair tools distributed as Windows installer packages (Inno Setup, Smart Install Maker, NSIS). After extraction, identify the chipset protocols, license infrastructure, and embedded firmware files. Set up a Windows VM to actually run the tools.

## Trigger Conditions

- User sends a download link to a mobile repair tool (Octoplus, Chimera, Z3X, TFT Unlock, SamFw, Apizu, Miracle Box, etc.)
- User asks to "reverse engineer", "tear apart", "analyze", "extract files from" a mobile service tool
- User asks to find license servers, API endpoints, HWID schemes, or activation keys in a GSM tool
- User wants to know what protocols/chipsets a tool supports
- User needs a Windows VM to run extracted mobile repair tools

## Installer Identification

Most mobile tools use one of three installer formats. Identify which before trying to extract:

| Format | Signature | Extraction |
|--------|-----------|------------|
| **Inno Setup** | Tiny PE (<100KB) + massive overlay. `strings exe | grep "Inno Setup"` | `innoextract` |
| **Smart Install Maker** | Overlay starts with `Smart Install Maker v. X.XX` | Password-protected. Try patching (see below) |
| **NSIS** | `strings exe | grep "Nullsoft"` | `7z x` |

```bash
file target.exe                          # PE32 (GUI) Intel 80386
readpe target.exe | grep "Number of sections"
strings target.exe | grep -E "Inno Setup|Smart Install|Nullsoft"
7z l target.exe | grep "Type"            # May show RAR5 for nested archives
```

## Inno Setup Extraction

### Tool: innoextract (prebuilt Linux binary)

Supports Inno Setup 1.2.10 to 6.0.5. Download the i686 prebuilt release:

```bash
# Download and extract
wget -q "https://github.com/dscharrer/innoextract/releases/download/1.9/innoextract-1.9-linux.tar.xz"
tar xf innoextract-1.9-linux.tar.xz

# Extract (i686 binary works on x64 systems)
innoextract-1.9-linux/bin/i686/innoextract -e -d output_dir target.exe
```

### Password-protected installers

- The password hash is stored in the Inno Setup header
- For license-protected tools, the password is given to paying customers — NOT extractable
- No known bypass for Inno Setup password protection without the actual password

## Smart Install Maker Handling

SIM uses proprietary compression — standard tools CANNOT extract the files.

### Identification

The overlay starts with the version string and null-terminated config fields:

```
Smart Install Maker v. 5.04\00\00\00\01\04369121\00\00\00\...
```

File entries use `@$&%04\filename.ext` path syntax. Config field [26] controls password protection (value `25` = enabled, `0` = disabled).

### Password bypass attempt

#### Field patching (skip password check)

SIM v5.04 stores the password-required flag at config field offset 26 in the overlay:
- Value `25` = password required (default)
- Value `0` = no password

```bash
python3 -c "
with open('target.exe', 'rb') as f: d = bytearray(f.read())
pos = d.find(b'25\\x00Copyright')
if pos >= 0:
    d[pos:pos+1] = b'0'
    with open('target_patched.exe', 'wb') as f: f.write(d)
    print('Patched at offset', hex(pos))
else:
    print('Pattern not found - password may be stored differently')
"
```

Then try to install with Wine:

```bash
xvfb-run -a wine target_patched.exe /VERYSILENT /DIR="C:\\extracted"
# Even if /VERYSILENT fails, check temp dir:
# ~/.wine/drive_c/users/<user>/AppData/Local/Temp/$inst/
```

#### Password brute-force via xvfb + xdotool

When the field patch doesn't work (some installers use a different flag scheme), brute-force the password dialog via Wine's virtual display:

```bash
# Known SIM passwords to try first: 1234, hydratool, 123, 12345, admin, tool, unlock, empty string
PASSWORD="1234"

export WINEPREFIX=$HOME/.wine_sim_bf
rm -rf $WINEPREFIX
wineboot -u 2>/dev/null
export DISPLAY=:99
Xvfb :99 -screen 0 1024x768x16 &>/dev/null &
sleep 2

timeout 60 wine "/tmp/target_installer.exe" 2>/dev/null &
sleep 8

# Find the password dialog
WIN=$(xdotool search --name "Password|Setup|Smart Install" 2>/dev/null | head -1)
if [ -n "$WIN" ]; then
    xdotool type "$PASSWORD"
    xdotool key Return
    sleep 3
    # Check if another dialog appeared (success) or error
fi
```

**Known SIM passwords from previous RE:**
| Tool | Password | Method |
|------|----------|--------|
| Apizu Tool V4.4.4 | `1234` | Brute-force through xvfb |
| Hydra Tool V7.0 | `hydratool` | Confirmed via xvfb test |

#### SIM limitation under Wine

**All SIM installers fail file copy under Wine** due to `setupapi:do_file_copyW`. The installer will accept the password, show progress, but never write the actual application files. This is a fundamental Wine limitation — no known workaround exists. A real Windows environment (VM) is required.

**What you CAN get from SIM temp dirs even without a VM:**
- `.tmp` CAB archives — extract with `cabextract *.tmp`
- PNG/BMP images (icons, splash screens)
- RTF documents (EULA, readme)
- Strings from the overlay reveal file names but not content
- The actual application files remain compressed inside the SIM overlay

### Octoplus MITM + DLL Stubs Deploy Pattern

For capturing tool-server communication by running tools inside a Windows VM with a MITM proxy on the host:

```bash
# Host-side setup
# 1. Python MITM server on port 8443 (self-signed CA cert)
# 2. DNS poison in /etc/hosts: *.octoplusbox.* → 127.0.0.1
# 3. iptables redirect: 80/443 → 8443
# 4. Forward host port to VM: add to QEMU -nic user,hostfwd=tcp::8443-:8443

# DLL stubs to bypass hardware checks:
# - WinSCard.dll — stub SCardEstablishContext, SCardConnect, SCardTransmit to return SUCCESS
# - libusb-1.0.dll — stub enumeration to report "device connected"
# Compile as Windows DLLs on Linux via MinGW: x86_64-w64-mingw32-gcc -shared -o WinSCard.dll stub.c

# Deploy into VM via HTTP download from host or shared drive
# Inside VM:
# 1. Place stubs in tool's installation directory (loaded before system path)
# 2. Edit C:\Windows\System32\drivers\etc\hosts pointing tool servers to host IP
# 3. Run tool -> tool traffic hits host MITM server
```

**Note:** This only works for startup-only license checks. If the tool uses server-thin-client architecture (fetches device-specific exploits at runtime), you get the shell but no payloads.

## Post-Extraction Analysis

After extracting an Inno Setup package, do a structured second pass:

### 1. File inventory

```bash
find output_dir -type f | sort > manifest.txt
wc -l manifest.txt
find output_dir -type f -exec file {} \; | sort | uniq -c | sort -rn
find output_dir -type f -size +1M | wc -l     # count large files
```

### 2. Platform identification

```bash
file output_dir/app/*.exe
# Look for:
# - Delphi: Borland/CodeGear refs in strings
# - C++/Qt: QApplication, QNetworkReply
# - .NET: mscorlib, System.Windows.Forms
# - Packed: UPX, VMProtect, Themida, SecureEngineSDK32.dll
```

### 3. Infrastructure discovery

```bash
# Server URLs and API endpoints
strings main.exe | grep -iE "https?://|\.cloud|\.club|\.io|/api/|/auth/|/license" | \
  grep -v "\.dll\|\.txt\|adobe\|w3\.org" | sort -u

# License and auth strings
strings main.exe | grep -iE "key|license|auth|token|hwid|serial|activate|login|register" | \
  grep -v "\.dll" | sort -u

# Crypto references
strings main.exe | grep -iE "aes|des|rsa|sha|md5|pbkdf|hmac|crc|x509|certificate|fingerprint" | sort -u
```

### 4. Database extraction

```bash
find output_dir -name "*.db" -o -name "*.sqlite"
# Dump content:
sqlite3 file.db .dump | head
```

### 5. Encrypted data files

Files with `.oct`, `.pak`, `.dat` extensions often contain chipset firmware/loaders. The Octoplus/Octopus format:

```
Header: OCTOPUS_v.1.0\0\0\0\0
Payload: encrypted binary (AES-GCM or similar)
```

These are loaded by the main tool and decrypted at runtime — the key is in the binary.

## Mobile Service Tool Architecture

### Common structure found in Octoplus-class tools

```
output_dir/app/
├── OctopusSamsung.exe          # Main Delphi GUI (200-400MB)
├── OctopusFRP.exe              # FRP-specific tool
├── DigitalLicenseManager.exe   # Qt-based DRM/license handler (24MB)
├── rd.exe                      # Console-mode C++ device worker (Boost, lwext4)
├── Updater.exe                 # Auto-updater (Qt)
├── SamsungModels.oct           # Encrypted model list (~500KB)
├── SAM_ALL.db                  # SQLite supported model database
├── SecureEngineSDK32.dll       # Themida/Enigma obfuscator (28KB)
├── MetaCore.dll                # Core library
├── libnv*.dll                  # NVIDIA Tegra nvflash stack
│   ├── libnvflash.dll
│   ├── libnvos.dll
│   ├── libnvusbhost.dll
│   ├── libnvaes_ref.dll
│   ├── libnvboothost.dll
│   ├── libnvapputil.dll
│   └── libnvdioconverter.dll
├── lz4.dll                     # LZ4 compression
├── 7z.dll                      # 7-Zip for self-extraction
├── sqlite3.dll
├── libeay32.dll / ssleay32.dll # OpenSSL
├── libusb-1.0.dll              # USB device access
├── AdbWinApi.dll               # Windows ADB bridge
├── Files/
│   ├── Infineon/               # Old Samsung feature phone .oct files
│   ├── Qualcomm/               # Qualcomm fastboot/BCT/EFS repair .oct
│   ├── Swift/                  # MediaTek feature phone .oct
│   └── NVM/                    # NVM (non-volatile memory) .oct files per model
├── EFS/                        # Stock EFS partition images for repair
├── Drivers/                    # USB driver .zip/.rar files
├── img/                        # UI images, splash screens
│   └── mtk_testpoints/         # MTK short-point reference images
├── app/UsbDk/                  # USB Drivers Kit installers
└── Skin/*.asz                  # UI skin files
```

### MetaCore.dll Analysis (Octoplus FRP)

**Location:** MetaCore.dll ships in the FRP installer, NOT the Samsung installer:
```
install_octoplus_FRP_3.0.6.0/app/MetaCore.dll
```
In the Samsung installer the same auth logic is embedded inside the packed `.ybI`/`.(:R` encrypted sections of `OctoplusSamsung.exe`.

**Properties:** 13.5 MB PE32 DLL, Borland Delphi (CryptoPP), no packing (entropy 5.4–6.7).

**Critical auth strings (file offsets):**
- `CompareAllBBChipHWID(): fail!` — `0x938274`
- `AUTH_IsReady():` — `0x90ce28`
- `customer name mismatch with AUTH file` — `0x91dfae`
- `bbchip_name is NULL, skip H/W version check` — `0x91d4d7`

**Delphi xrefs (cross-references in .text section):**
| String | Xref | Instruction |
|--------|------|-------------|
| CompareAllBBChipHWID fail | `0x6300ac` | `PUSH` (`0x68`) |
| AUTH_IsReady(): | `0x581886` | `PUSH` (`0x68`) |
| AUTH_HANDLE::IsReady | `0x5a8eb7` | `MOV [ESP+24]` (`C7 44 24`) |

**Xref search technique:** Delphi/BCB stores string addresses as absolute memory values (`image_base + section_vaddr + (file_offset - section_raw_ptr)`) in `.text`. Search the `.text` section for the 4-byte address preceded by `0x68` (PUSH), `0xB8-0xBB` (MOV reg), or `0xC7 0x44 0x24 XX` (MOV [ESP+xx]).

**Patch strategy:** See `references/octoplus-metacore-patch-analysis.md` under the `reverse-engineering` umbrella for the full walkthrough: RVA calculation, function prologue detection, conditional jump backtracking, and always-return-TRUE function stubs.

### Chipset protocol support

| Chipset | Protocol | Key files |
|---------|----------|-----------|
| **Exynos** | Odin/LOKE/high-speed USB bulk | `exDownload.dll`, heimdall-compatible |
| **Qualcomm** | EDL (Sahara/Firehose) | programmer .elf, `fastboot.exe` |
| **MediaTek** | BROM/preloader DA upload | DA .bin, `etc1tool.exe` |
| **Infineon** | Preloader + mainloader + certificate chain | Model-prefixed .oct files |
| **NVIDIA Tegra** | APX mode via nvflash | `libnvflash.dll`, `libnvos.dll` stack |
| **Spreadtrum/Unisoc** | Research/download mode | Chipset-specific loaders |

### License infrastructure (Octoplus specific)

- **Server endpoints:** `node.octoplusbox.cloud`, `node.octoplusbox.club`
- **HWID generation:** PBKDF2-based fingerprint (`bt_PBKDF2_HWID`, `FHWIDHash1`, `GetHWID`)
- **Auth validation:** X509 certificate fingerprints, AES-GCM checksum, CRL/revocation
- **Error codes:** `NG NEEDAKAUTH`, `NG NEEDMSLAUTH`, `29 User authentication failed`
- **Sprint unlock:** `assets/OctoPlusSprint`, `assets/OctoPlusSprintPK`

## Pitfalls

- **Do not try to run the extracted .exe files** on Linux — they won't execute and the license check will fail without the Octoplus hardware box
- **SIM (Smart Install Maker) password bypass** only works if field [26] is the password flag. Some tools use field [26] for unrelated settings — patching it may crash the installer
- **Inno Setup with modern versions >6.0.5** cannot be extracted — the format changed. `innoextract` will report "Not a supported Inno Setup installer"
- **7z sometimes misidentifies** Inno Setup installers as RAR5 — the RAR is only a small nested component (e.g. adbsdm.exe) and the bulk of the data is in the tail
- **Strings scan on multi-hundred-MB binaries** takes significant time and memory. Start with targeted greps before doing full string dumps
- **The `.oct` encrypted format** cannot be decrypted without the runtime key from the Delphi binary. Static extraction of the key may require Ghidra or IDA analysis of the Delphi decompression routine
- **Mobile tools check for USB dongle** — if the tool requires a physical Octoplus box connected, it may refuse to start or show limited functionality even in Wine
- **Wine cannot run these tools** — they depend on Windows driver APIs (setupapi for driver installation, WinSCard for smart card/dongle, libusb via proper Windows USB stack), Themida/VMProtect packing, and direct hardware access. A native Windows VM is required.

## Runtime Environment: Windows VM

After extraction and analysis, the tools need a real Windows environment to run.
Wine fails on setupapi, WinSCard, Themida-packed binaries, and USB dongle access.
Use QEMU/KVM with a Windows 11 VM.

### Recommended VM Setup

| Setting | Value | Reason |
|---------|-------|--------|
| Machine | q35, accel=kvm | Best KVM performance, modern chipset |
| CPU | host passthrough, 4 cores | Required for KVM acceleration |
| RAM | 8GB | Comfortable for Win11 + tools |
| Disk | 80GB qcow2 on fast storage | Win11 needs ~40GB, leaves room for tools |
| Disk bus | SATA (IDE) | Avoids virtio driver ISO requirement |
| Firmware | OVMF (UEFI) | Win11 requires UEFI |
| Display | qxl + VNC | Remote access, no local GUI needed |
| Network | e1000, user-mode NAT | Simple, no bridge config needed |

### QEMU Launch Command (no libvirt dependency)

```bash
# Install deps
sudo apt install qemu-system-x86 ovmf

# Create disk
qemu-img create -f qcow2 /path/to/win11.qcow2 80G

# Copy OVMF vars (so we don't modify the master)
cp /usr/share/OVMF/OVMF_VARS_4M.fd /tmp/ovmf_vars.fd

# Launch installer
qemu-system-x86_64 \
  -machine q35,accel=kvm \
  -cpu host \
  -smp 4 \
  -m 8G \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd \
  -drive if=pflash,format=raw,file=/tmp/ovmf_vars.fd \
  -drive file=/path/to/win11.qcow2,format=qcow2,if=ide \
  -drive file=/path/to/Win11.iso,format=raw,if=ide,media=cdrom \
  -vga qxl \
  -vnc :1,password=off \
  -netdev user,id=net0 \
  -device e1000,netdev=net0 \
  -device usb-ehci,id=ehci \
  -device usb-tablet \
  -daemonize
```

Connect with any VNC viewer: `vncviewer <host>:1`

### Post-Install Steps

1. **Complete Windows 11 setup** via VNC (region, account, etc.)
2. **Transfer tool files** — copy the extracted tool directory into the VM:
   - Use `scp` from the host (the VM gets NAT'd IP on 10.0.2.x)
   - Or create an internal HTTP server on the host: `python3 -m http.server 8080` and download in VM
   - Or attach an extra disk/image with the files
3. **Install the tool** using its installer inside the VM
4. **Pass USB dongle** (if required): add `-device usb-host,vendorid=0xXXXX,productid=0xYYYY` to the QEMU command. Find VID/PID with `lsusb` on the host while the dongle is plugged in.

### QEMU Known Issues

- **`-bios` vs `-drive if=pflash`**: OVMF requires the pflash drive format. `-bios /usr/share/OVMF/OVMF_CODE_4M.fd` does NOT work for UEFI. Always use `if=pflash`.\n- **Spice vs VNC**: Spice requires swtpm for UEFI VMs unless configured without TLS. VNC is simpler and more reliable for headless setups.\n- **x11vnc conflict**: If a VNC server already runs on port 5900, use `-vnc :1` for port 5901.\n- **No virtio drivers**: Using IDE/SATA avoids the need for a virtio-win ISO during install.\n- **SWTPM missing**: If virt-install fails on swtpm, skip libvirt entirely and use raw QEMU.

### VM Guest Interaction (libvirt/virsh)

When the VM has no network yet and you can't RDP in, use keyboard injection:

```bash
# Win+R (Run dialog)
virsh send-key windows11 KEY_LEFTMETA KEY_R

# Ctrl+Shift+Enter (run as admin — for PowerShell/cmd)
virsh send-key windows11 KEY_LEFTCTRL KEY_LEFTSHIFT KEY_ENTER

# UAC confirmation (Yes)
virsh send-key windows11 KEY_LEFTALT KEY_Y

# Ctrl+Alt+Del (security screen / login)
virsh send-key windows11 KEY_LEFTCTRL KEY_LEFTALT KEY_DELETE

# Tab navigation (move between dialog buttons)
virsh send-key windows11 KEY_TAB

# Space / Enter (activate focused button)
virsh send-key windows11 KEY_SPACE
virsh send-key windows11 KEY_ENTER
```

**Common Windows operations via keyboard:**
1. `Win+R` → type `cmd` → `Ctrl+Shift+Enter` → `Alt+Y` → `netsh advfirewall set allprofiles state off` → `Enter`
2. `Win+R` → `sysdm.cpl` → `Enter` → `Alt+R` (Remote tab) → check "Allow remote connections"
3. `Win+R` → `powershell` → `Ctrl+Shift+Enter` → `Alt+Y` → `Disable-NetFirewallProfile -All` → `Enter`

**Screenshot verification:**
```bash
virsh screenshot windows11 /tmp/vm_screenshot.png
```

**Pitfall:** Long key sequences often fail silently because key names must match Linux `KEY_*` constants and timing between keys matters. Prefer short commands split across multiple sequential `send-key` calls.

### Dual NIC Strategy

For maximum Windows VM network compatibility, use two adapters:

| Model | Driver | Boot-time access |
|-------|--------|-----------------|
| **e1000e** (Intel) | Built into Windows 11 | Immediate internet during setup |
| **virtio** | Needs virtio-win ISO | After driver install |

```bash
# Via libvirt XML:
# <interface type='network'>
#   <mac address='52:54:00:76:c3:3b'/>
#   <source network='default'/>
#   <model type='virtio'/>
# </interface>
# <interface type='network'>
#   <mac address='52:54:00:77:c3:3b'/>
#   <source network='default'/>
#   <model type='e1000e'/>
# </interface>
```

**Duplicate MAC warning:** If both NICs share the same MAC address, libvirt and Windows both get confused. Always use unique MACs.

**Assigning unique MACs:**
```bash
# Generate a unique MAC based on model type:
# virtio:  52:54:00:76:c3:3b
# e1000e: 52:54:00:77:c3:3b
# Toggle the second byte for more VMs: 52:54:00:76:c3:3c, etc.
```

### Host Disk Space Check

**Always check before creating/starting a VM:**

```bash
df -h /                          # Host root — qcow2 images live here
qemu-img info /var/lib/libvirt/images/vm.qcow2
```

If root is >95% full:
- VM will fail to boot or act erratically
- Windows inside the VM can't write to its virtual disk
- qcow2 snapshots need host space for the delta

**Quick host space recovery:**
```bash
sudo rm -f /tmp/*.iso /home/*/Downloads/*.iso
sudo apt-get clean && sudo apt-get autoremove -y
sudo journalctl --vacuum-time=3d
docker system prune -f
sudo rm -rf /var/lib/snapd/cache/*
rustup toolchain remove <old-toolchains>
rm -rf ~/.cargo/registry/cache/*


## References

- `references/octoplus-server-discovery.md` — Detailed Octoplus license server endpoints, HWID scheme, and auth protocol specifics discovered during RE.
- `references/apizu-hydra-tool-details.md` — Apizu Tool V4.4.4 and Hydra Tool V7.0 findings: SIM installer structure, passwords, file manifest, and Wine limitations.
- `references/qemu-win11-vm-setup.md` — Session-specific: QEMU/KVM Windows 11 VM setup for running Octoplus/Apizu tools on kubuntux.
