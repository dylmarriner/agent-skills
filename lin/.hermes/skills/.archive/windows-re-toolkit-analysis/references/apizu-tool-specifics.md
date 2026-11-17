# Apizu Tool V4.4.4-2026 — Session-Specific RE Analysis

## Acquisition
- Downloaded from: `https://apizutool.one/TOOL/Apizu_Tool_[Alien]-V4.4.4-2026.zip`
- File: `Apizu_Tool_[Alien]-V4.4.4-2026.zip` (199 MB)
- Extracted: `Apizu_Tool_[Alien]-V4.4.4-2026.exe` (199 MB)
- Website: apizutool.one (Tanzania-based, contact: support@apizutool.one, +255 653 420 210)
- License: Paid subscription (50K TZS / 20 USDT per 3 months)

## Initial Recon

### File type
```
PE32 executable (GUI) Intel 80386, for MS Windows, 8 sections
```
Borland Delphi compiler (SOFTWARE\Borland\Delphi\RTL in strings).

### Packer
Not packed. Standard 8-section layout: CODE, DATA, BSS, .idata, .tls, .rdata, .reloc, .rsrc.

## Installer Format

**Smart Install Maker v5.04** — NOT Inno Setup. innoextract fails with "Not a supported Inno Setup installer!".

### File structure
```
[0x000000]  PE executable (Smart Install Maker installer + RAR extraction code)
[0x05a200]  SIM overlay header + config + compressed files (1.7 MB)
[0x203ecc]  RAR5 archive containing adbsdm.exe (264 KB, unsupported compression method)
[0x244755]  Tail data (198 MB) — SIM compressed data
```

### 7z detection
```
7z l target.exe
  → Type = Rar5 (at offset 0x203ecc, 264 KB)
  → "Unsupported Method: adbsdm.exe"
  → Tail = 206,665,287 bytes (unrecognized)
```

## Embedded Files

### Main Application
| File | Size (uncompressed) | Notes |
|------|--------------------|-------|
| Apizu Tool.exe | 6,592,464 bytes | .NET WinForms app (MaterialSkin + Guna UI2 + Newtonsoft.Json) |
| exDownload.dll | — | Custom Samsung Exynos download mode DLL |
| GDl32.dll | — | GDI wrapper |
| gdl32.dll.000 | — | GDI data |
| Uninstall.exe | — | Uninstaller |

### .NET Dependencies (7 DLLs)
Guna.Charts.WinForms.dll, Guna.UI2.dll, MaterialSkin.dll,
Microsoft.VisualBasic.PowerPacks.dll, Newtonsoft.Json.dll,
System.Net.Http.Formatting.dll

### ADB / Device Tools
adb.exe, adbsdm.exe, ADB.rar, adbsdm.rar, AdbWinApi.dll, AdbWinUsbApi.dll,
fastboot.exe, cmd-here.exe

### Data/Debug Tools (data\ subdirectory)
etc1tool.exe, hprof-conv.exe, dmtracedump.exe,
make_f2fs.exe, make_f2fs_casefold.exe, mke2fs.exe,
sqlite3.exe, cmd.exe

### FRP / Firmware
frp.bin, dopher.img, pitiful.img, driver.msi

### Screen Mirroring
scrcpy.exe, scrcpy-server, scrcpy-console.bat, scrcpy-noconsole.vbs,
SDL2.dll, cygwin1.dll, cygusb-1.0.dll, libusb-1.0.dll, libwinpthread-1.dll,
avcodec-60.dll, avformat-60.dll, avutil-58.dll, swresample-4.dll

### Mobile APKs (17 files)
1.apk, 2.apk, 3.apk, alncshld.apk, apz1.apk, apz2.apk, dvc-id.apk,
ft@.apk, hd.apk, liah.apk, nuagi.apk, pcdblr.apk, pl.apk, rnk.apk,
tcnsms.apk, tctps.apk, terminal.apk, x.apk

### Other Files
README ME.txt, Updates.txt, Disclaimer.txt, Project1.rtf, Uninstall.ini
Icons: apizu.ico, Allien Tool LOGO2.ico, apizu tool 2024 new2.ico, logo new.ico, ..ico
aeiou.iss (Inno Setup script remnant, possibly for a previous version)

## SIM Config Fields (key)
Fields parsed from overlay at 0x5a200:
- [4] 4369121 — unknown
- [21] disk@$&%19.pak — compressed archive descriptor
- [23] 415234798 — compressed total size
- [26] 25 — flags field (value "25" = password enabled)
- [34] 4.4.4 — version
- [59] 6592464 — Apizu Tool.exe uncompressed size

## Extraction Attempts

| Method | Result |
|--------|--------|
| innoextract | ❌ "Not a supported Inno Setup installer!" |
| 7z (RAR5)  | ❌ "Unsupported Method: adbsdm.exe" |
| unrar       | ❌ "is not RAR archive" |
| LZMA manual decompression | ❌ No valid standard LZMA headers in SIM overlay |
| PE section analysis | ✅ Identified Delphi, 8 sections, unpacked |
| String analysis | ✅ Full embedded file list enumerated |
| Website analysis | ✅ Identified commercial tool, Tanzania-based |

### Wine + Patched Installer (new as of Jul 2026)
**Patched field [26] from "25" to "0"** in the SIM config to bypass the password dialog. The modified binary at `/tmp/apizu_extract/Apizu_Tool_NoPwd.exe` launched under Wine + xvfb but stalled at file copy:

```
setupapi:do_file_copyW Unsupported style(s) 0x10
```

**What was extracted:**
- Decompressed installer temp files at `$inst/` in Wine's Temp dir:
  - `2.tmp` (30.9K) — Microsoft CAB archive containing icons, splash, RTF readme
  - `4.tmp` (4.1K) — PNG 48×48 icon
  - `5.tmp` (201.2K) — BMP 164×314×32 splash image  
  - `8.tmp` (2.6K) — PNG 48×48 icon
  - `15.tmp` (524B), `16.tmp` (318B) — RTF text snippets

**Blocked by:** Wine's setupapi can't handle `SP_COPY_NEWER_OR_DIFFERENT` (style 0x10). The installer can decompress infrastructure files but cannot copy application binaries to the target directory. Requires real Windows to complete installation.

## Password Status
**Unknown.** Not found in config overlay. Common GSM passwords (`123`, `apizu`, `alien`, `2026`) all failed via Wine. License is sold commercially — password likely issued to paying customers only. Field patching (25→0) bypasses the password dialog entirely.

## Tool Purpose (from website)
Samsung MDM removal + FRP bypass + device unlock for Samsung, Nokia, Tecno, Infinix, Xiaomi, ZTE, Oppo, Vivo, Realme, Huawei. Multi-brand phone repair tool. URL scanning, QR scanning, diagnostics. Based in Dar es Salaam, Tanzania.
