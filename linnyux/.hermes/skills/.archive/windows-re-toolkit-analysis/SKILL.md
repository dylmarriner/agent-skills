---
name: windows-re-toolkit-analysis
description: Add Wine dynamic analysis, installer automation via OCR+xdotool, and embedded component identification to the Windows RE toolkit.
---

# Wine Dynamic Analysis for Windows RE

## Trigger

When a Windows binary doesn't yield enough from static RE — especially GSM unlock tool installers — use dynamic analysis via Wine.

## Workflow

### Install and run via Wine
```bash
# Extract password-protected archive
unzip -P <password> archive.zip

# Run installer
cd ~/Documents
wine target.exe &

# Find window
for wid in $(xdotool search --all "" 2>/dev/null); do
    name=$(xdotool getwindowname $wid 2>/dev/null)
    echo "$wid: $name"
done | grep -iE "setup|install|target"

# OCR the dialog text
import -window <WID> /tmp/screenshot.png
tesseract /tmp/screenshot.png /tmp/screenshot_text
cat /tmp/screenshot_text.txt

# Navigate dialogs
xdotool windowactivate <WID>
xdotool type "password"
xdotool key Return
xdotool key alt+n   # Next
xdotool key alt+i   # Install
xdotool key alt+f   # Finish

# Find installed files
ls -la ~/.wine/drive_c/Program\ Files\ \(x86\)/<ToolName>/
```

### Identify embedded components by scanning strings
| Component | Signal |
|-----------|--------|
| Python 3.x | `python37.dll`, `site-packages/` |
| .NET | DevExpress DLLs, `mscorlib.dll` |
| Delphi | `Embarcadero Delphi`, `TClass`, `TMethod` |
| Firmware store | 1000s of gzip hits in PE binary |

### Missing DLL fixes
```bash
winetricks vb6run    # Visual Basic 6
winetricks dotnet48  # .NET Framework
```

### Installer Format Identification (Static Analysis)

Before running an installer through Wine, identify its format from the PE overlay:

### Overlay header detection
The overlay is data appended after the last PE section. Find it:

```python
pe_end = 0
for i in range(num_sec):
    s = sec_start + i*40
    roff = struct.unpack('<I', data[s+20:s+24])[0]
    rsize = struct.unpack('<I', data[s+16:s+20])[0]
    if roff + rsize > pe_end:
        pe_end = roff + rsize
overlay = data[pe_end:]
```

### Format signatures (read first 64 bytes of overlay)
| Signature string | Installer type | Extraction tool |
|---|---|---|
| `Inno Setup` or `Inno` | Inno Setup | `innoextract` |
| `Smart Install Maker v.` | Smart Install Maker | **No Linux tool** — need Wine + password or custom parser |
| `Nullsoft` or `NSIS` | Nullsoft Scriptable Install System | `7z x` or `unshield` |
| `InstallShield` | InstallShield | `unshield` |
| `7z` / LZMA header at overlay start | 7-Zip SFX | `7z x` |
| `MSCF` | CAB | `cabextract` |

### Smart Install Maker specifics (v5.x)
SIM stores its config as null-terminated strings in the overlay. Parse them:

```python
offset = overlay_start
fields = []
while offset < end_of_config:
    end = data.find(b'\\x00', offset)
    if end < 0 or end > offset + 500:
        break
    val = data[offset:end]
    try:
        fields.append(val.decode('ascii', errors='replace'))
    except:
        break
    offset = end + 1
```

Key fields to look for:
- Field containing `disk@$&%19.pak` + size value = compressed archive descriptor
- Field containing `@$&%04\\\\filename.exe` = embedded file path
- Integer values after file path = size of the uncompressed file
- ~Field 26 may be a flags field — value `25` = password protection enabled

#### Password bypass via field patching
If SIM installer has field ~26 = "25", patching it to "0" can bypass the password:

```python
data = bytearray(open('target.exe', 'rb').read())
pos = data.find(b'25\\x00Copyright', 0x5a200)  # field ~26 in SIM config
if pos >= 0:
    data[pos:pos+1] = b'0'  # '25' → '5' (field becomes "5", password disabled)
    open('target_nopwd.exe', 'wb').write(data)
```

Run the patched installer via Wine + xvfb:
```bash
xvfb-run -a wine target_nopwd.exe /VERYSILENT /DIR="Z:\\tmp\\install\\app"
```

Check the Wine temp directory for decompressed installer infrastructure files:
```bash
export WINEPREFIX=/tmp/install_prefix
find "$WINEPREFIX/drive_c/users/*/AppData/Local/Temp/" -type f
# Decompressed .tmp files appear under $inst/ — icons, splash BMPs, a CAB archive
```

#### Wine limitation: setupapi file copy
SIM installers use `setupapi:do_file_copyW` with style flag `0x10` (`SP_COPY_NEWER_OR_DIFFERENT`). Wine does NOT support this flag — the installer stalls during actual file copy to Program Files. The decompressed temp files (icons, CAB archives, RTF docs) ARE accessible, but application binaries won't copy. This is a dead end without real Windows.

To extract what WAS decompressed into Wine temp:
```bash
export WINEPREFIX=/tmp/install_prefix
cabextract "$WINEPREFIX/drive_c/users/*/AppData/Local/Temp/\$inst/2.tmp" -d /tmp/cab_output/
# 2.tmp is a Microsoft CAB containing more temp files (icons, splash, installer resources)
```

#### SIM compression is NOT standard LZMA
Do NOT scan the SIM overlay for standard LZMA headers (`0x5D`) — they won't decompress. SIM v5.x uses a proprietary compression variant embedded in its own CODE section. 7z detects only the small RAR5 archive that some SIM installers embed for auxiliary files (e.g., adbsdm.exe). The bulk of the file data stays in the SIM overlay and is NOT extractable with standard off-the-shelf tools on Linux.

### 7z as first-pass probe
```bash
7z l target.exe
```
7z often detects embedded RAR5/ZIP archives inside PE files even when the main format is unrecognized. The detected archive offset tells you where the PE ends and the overlay begins.

### PE section names as packer indicators
| Section names | Packer |
|---|---|
| `CODE`, `DATA`, `BSS`, `.idata`, `.tls`, `.rsrc` | Borland Delphi (unpacked) |
| `.text`, `.rdata`, `.data`, `.rsrc` | MSVC (unpacked) |
| `UPX0`, `UPX1`, `UPX!` | UPX |
| `.packed`, `.yc`, `.vmp` | VMProtect/其它 |

### Finding embedded files without extraction
When you can't extract (password-locked, unsupported format), you can still enumerate all embedded files by scanning the config overlay. In Smart Install Maker, files are stored with the `@$&%04\` prefix:

```python
import re
files = set()
for m in re.finditer(b'@\\$&%04\\\\([^\\x00]+)', data):
    files.add(m.group(1).decode('ascii', errors='replace'))
for f in sorted(files):
    print(f)
```

For Inno Setup, file entries follow a different pattern — search for `Source:` fields in the setup script data instead.

This works for SIM, Inno Setup, and similar installers that store file paths in the config area. Save full session-specific findings (file lists, binary signatures, RE observations) as `references/<tool-name>-specifics.md` under this skill.

### Password hunting strategy (ordered)
1. Check bundled `Password*.txt` or `README*.txt` in the download
2. Check the download/seller website
3. Brute-force common passwords via Wine+xvfb
4. Search for plaintext password strings in the PE .rdata and DATA sections
5. Search for password hash (MD5/CRC32 of common passwords) in the binary
6. Patch the installer to skip the password dialog (modify conditional jump)

## Pitfalls
- Keyboard accelerators (`alt+n`) work better than mouse coords
- OCR garbles long text but reads button labels well
- Log Wine output: `wine target.exe 2>&1 | tee /tmp/wine.log`
- Password is NEVER guaranteed. `123` was correct for ONE tool (TFTUnlock), NOT for all. Always check: (a) a `Password 123.txt` file bundled with the download, (b) the download page itself, (c) the seller's website/forum, (d) the installer's own config strings for stored password/hash. Do NOT assume a password across tools — each tool has its own.