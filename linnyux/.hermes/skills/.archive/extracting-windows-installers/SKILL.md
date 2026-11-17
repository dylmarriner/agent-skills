---
category: cybersecurity-skills
description: Download, identify, extract, and analyze Windows-based mobile device repair installers. Covers Inno Setup, Smart Install Maker, NSIS, DLL stubbing for hardware bypass, MITM license server setup, and Wine execution.
name: extracting-windows-installers
trigger: User provides a Windows .exe or installer URL for analysis/extraction, especially mobile repair/service tools (Samsung, Octoplus, Octopus, Chimera, Z3X, etc.)
---

# Extracting Windows Installers

Class-level skill for downloading, identifying, extracting, and analyzing Windows-based mobile device repair tools. Covers the full pipeline from raw .exe to extracted files + bypass techniques.

## Step 1 — Download

Use `wget` with a modern User-Agent header:
```
wget --user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" -O output.exe "<url>"
```

Use `rtk wget` for compact output. Set a generous timeout — installer files can be 200MB–2GB.

## Step 2 — Identify Installer Type

Run `file` and `7z l`:

```
file tool.exe
7z l tool.exe
```

| Type | Detection | Extraction |
|---|---|---|
| **Inno Setup** | "Inno Setup" in strings | `innoextract` (ported binary at /tmp/innoextract-1.9-linux/bin/i686/) |
| **Smart Install Maker** | Overlay starts with "Smart Install Maker v. X.YY" | Patch field 26 or brute-force via xvfb |
| **NSIS** | "Nullsoft Installer" in strings | `7z x` or `nsisunpack` |
| **RAR/SFX** | `7z l` reports Type = Rar/Rar5 | `7z x` directly |

### Inno Setup Extraction
```
/tmp/innoextract-1.9-linux/bin/i686/innoextract -e -d output_dir tool.exe
```

### Smart Install Maker Password Bypass / Brute-Force

SIM is NOT Inno Setup. Innoextract fails with "Not a supported Inno Setup installer!". SIM v5.04 creates a PE + RAR5 self-extracting archive. The RAR header flag byte 0 bit 0 (encrypted) is **False** — the password is enforced by the PE stub, not the RAR.

#### Structure
```
[PE stub: 2.1MB] → code + UI + config
[RAR5 overlay: ~197MB] → compressed files, RAR header at ~0x20454c
SIM config starts at overlay offset 0 with "Smart Install Maker v. X.YY"
```

#### Static Bypass: Patch Field 26
1. Config header: `Smart Install Maker v. X.YY\0` followed by null-terminated value fields
2. Field [26] (numeric value "25" at offset 0x5a2be) = password protection flags
3. Change `"25"` to `"0"` to disable the dialog
4. PITFALL: Config CRC may invalidate — still might show dialog

#### Runtime Brute-Force via xvfb + xdotool
When static bypass fails:

```bash
export WINEPREFIX=$HOME/.wine_bf
rm -rf $WINEPREFIX
wineboot -u
export DISPLAY=:99
timeout 60 wine installer.exe 2>/dev/null &
sleep 6
WIN=$(xdotool search --name "Install Title" | head -1)

for pw in "word1" "word2" "1234"; do
    xdotool windowfocus $WIN
    xdotool mousemove --window $WIN 150 70
    xdotool click 1; sleep 0.5
    xdotool key Ctrl+a; xdotool key Delete; sleep 0.3
    [ -n "$pw" ] && xdotool type "$pw"
    xdotool key Return; sleep 1
    if [ -z "$(xdotool search --name "Install Title" 2>/dev/null)" ]; then
        echo "SUCCESS: $pw"; break
    fi
done
```
Password REUSE across SIM installers is common — always try previously-discovered passwords first.

Known results:
- Apizu Tool v4.4.4 password = **1234**
- Many SIM installers use short numeric passwords (try `1234`, `0000`, `admin` first)

#### SIM Config Field [26] Bit Analysis
The password flag field (value `"25"` = 0x19 at config offset +0x2be) has these bits:
- Bit 0: Password enabled
- Bit 3: Unknown
- Bit 4: Unknown
Setting to `"0"` removes bit 0 but the installer may still show the dialog due to config CRC validation or a secondary check. The definitive bypass is providing the correct password at runtime.

#### SIM Installer Scale
SIM v5.04 handles ANY size overlay. Observed range:
- Apizu Tool: 199MB overlay, PE stub 2.1MB
- Hydra Tool V7.0: 2.7GB overlay, PE stub 192KB
- The RAR5 data always starts after the SIM config area; offset varies by PE stub size.

#### RAR5 Header Analysis (SIM-modified)
SIM prepends a PE stub to a standard RAR5. The RAR CRC is correct but free tools can't extract it.

```python
# Verify RAR5 CRC matches
rar_start = 0x20454c  # offset in combined file
rar = data[rar_start:]
crc_data = rar[12:hdr_end]
calc_crc = zlib.crc32(crc_data) & 0xFFFFFFFF
```

PITFALL: SIM file copy (`setupapi:do_file_copyW`) fails under Wine even with correct password. Temp files extract to `$inst/` but final copy to Program Files fails. This is a Wine limitation — real Windows needed for full install.

## Step 3 — Analyze PE Structure

```
python3 -c "
import struct
with open('tool.exe','rb') as f: data=f.read()
pe_off = struct.unpack('<I', data[0x3c:0x40])[0]
num_sec = struct.unpack('<H', data[pe_off+6:pe_off+8])[0]
sec_start = pe_off + 24 + struct.unpack('<H', data[pe_off+20:pe_off+22])[0]
for i in range(num_sec):
    s = sec_start + i*40
    name = data[s:s+8].rstrip(b'\\x00').decode('ascii',errors='replace')
    vsize = struct.unpack('<I', data[s+8:s+12])[0]
    roff = struct.unpack('<I', data[s+20:s+24])[0]
    rsize = struct.unpack('<I', data[s+16:s+20])[0]
    print(f'{name:<8} VSz={vsize:<8} RSz={rsize:<8} ROff=0x{roff:06x}')
"
```

Identify protection:
- **UPX:** UPX string in binary
- **Themida:** `SecureEngineSDK32.dll`, 2-section DLLs
- **Delphi:** "SOFTWARE\\Borland\\Delphi\\RTL" in strings, register naming
- **.NET:** CLI header RVA is non-zero

## Step 4 — Extract Strings

```
strings -a -t x tool.exe | grep -iE "https?://|/api/|key=|license|hwid|serial|aes|rsa|x509|cert|vid|pid|libusb" | sort -u
```

Key targets: server URLs, crypto keys, USB VID/PID, registry paths.

## Step 5 — Bypass Hardware Checks

### WinSCard.dll Stub (Smart Card)
When a tool needs `WinSCard.dll`, compile a stub:
```
i686-w64-mingw32-gcc -shared -o WinSCard.dll winscard_stub.c winscard.def
```
Place in `$WINEPREFIX/drive_c/windows/system32/`.
Key: all SCard API calls return success with fake handles. `SCardTransmit` returns APDU success (0x90, 0x00).

### libusb-1.0.dll Stub (USB Dongle)
When a tool uses libusb for hardware detection, compile a stub:
```
i686-w64-mingw32-gcc -shared -o libusb-1.0.dll libusb_shim.c -Os -s
```
Place in the tool's app directory.
Key: `libusb_get_device_list` returns 1 fake device, all open/claim calls succeed.
Also stub `libusb0.dll` (old API) for tools using the legacy USB API.

Reference: /tmp/libusb_shim.c, /tmp/winscard_stub.c

## Step 6 — MITM License Server

1. DNS poison: `127.0.0.1  server.domain.com` in `/etc/hosts`
2. Generate CA + server certs with `python3 gen_certs.py`
3. Install CA: `sudo cp ca.pem /usr/local/share/ca-certificates/ && sudo update-ca-certificates`
4. Run HTTPS server on port 8443, redirect 80/443 with iptables
5. Respond with JSON containing all expected license fields
6. Enable old TLS (`TLSv1`, `@SECLEVEL=0`) for OpenSSL 1.0.x clients

Reference server: /tmp/octoplus_mitm_server.py

## Step 7 — Run Under Wine

```
export WINEPREFIX=$HOME/.wine_tool
rm -rf $WINEPREFIX
wineboot -u
export DISPLAY=:99
timeout 60 xvfb-run -a wine tool.exe
```

GUI automation:
```
WIN=$(xdotool search --name "Window Title" | head -1)
xdotool windowfocus $WIN
xdotool type "text" && xdotool key Return
```

## Step 8 — QEMU Windows VM (for Wine-incompatible tools)

When a tool fails under Wine (Themida packing, SIM setupapi file copy, kernel drivers), use a QEMU Windows VM with TCG (software emulation — slow but works).

### Create Disk
```bash
qemu-img create -f qcow2 /tmp/win11_vm.qcow2 40G
```

### Start VM (Windows Install Phase)
```bash
qemu-system-x86_64 \
  -machine type=pc,accel=tcg \
  -cpu max -smp cores=2 -m 3072 \
  -drive file=/tmp/win11_vm.qcow2,format=qcow2,if=virtio \
  -cdrom /tmp/Win11.iso \
  -drive file=/tmp/virtio-win.iso,format=raw,if=virtio,media=cdrom \
  -nic user,model=virtio-net-pci \
  -vga virtio -display none -vnc :1 \
  -usb -device usb-tablet -rtc base=localtime
```
Connect via VNC to localhost:5901.

Key details:
- No HW virt (`accel=tcg`) makes install slow (1-2 hours for Win11)
- `virtio-win.iso` contains disk/network drivers needed during Windows setup
- Check for port conflicts before adding `hostfwd` — especially :8443 if MITM server is running

### VM-to-Host Networking
QEMU user-mode: host is at `10.0.2.2` from the guest.
- MITM server on host :8443 → VM reaches at 10.0.2.2:8443
- Edit `C:\Windows\System32\drivers\etc\hosts` inside VM to point tool domains to 10.0.2.2
- Or run a DNS forwarder on the host that overrides specific domains

### Post-Install Deployment
1. Install Octoplus/Apizu/Hydra tools normally
2. Deploy WinSCard.dll + libusb-1.0.dll stubs in the tool directories
3. Add DNS poison in `C:\Windows\System32\drivers\etc\hosts`
4. Run tools — watch traffic hit MITM server on the host

## Step 9 — Standalone Tool Extraction (rd.exe pattern)

Some installers contain standalone console tools usable outside the full suite. After Inno Setup extraction, check for:

```bash
export WINEPREFIX=$HOME/.wine_standalone
wine extracted_app/tool.exe --help
```

Look for: C++ console tools with Boost/lwext4, Delphi CLI tools, or Python-based helpers.

Example: `rd.exe` (Ext4 Worker v1.0.1 by Octoplus) — mounts ext4 images and patches IMEI at `md/NVRAM/NVD_IMEI/LD0B_001`. Works standalone under Wine without dongle or license.

## References

- `references/octoplus-crypto.md` — full crypto architecture from Octoplus Samsung + FRP tools
- `references/re-methodology.md` — structured reverse engineering methodology guide

## Pitfalls
- **32-bit stubs** — use `i686-w64-mingw32-gcc`, not x86_64
- **winscard.h conflicts** — define types manually, don't include the Mingw header
- **SIM under Wine** — `setupapi:do_file_copyW` with style flag 0x10 is unsupported
- **Old OpenSSL** — enable TLS 1.0/1.1 and weak ciphers in MITM server
- **RAR5 extraction** — free 7z/unrar may not handle SIM-modified RAR5 archives; real Windows needed
- **xvfb password brute-force** — each attempt takes ~2s; budget time accordingly
