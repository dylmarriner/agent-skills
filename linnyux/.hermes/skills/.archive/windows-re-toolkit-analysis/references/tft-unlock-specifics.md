# TFTUnlock Tool V6.2.1.1 — Session-Specific RE Analysis

## Acquisition
- Downloaded from provided zip: `TFTUnlock Tool V6.2.1.1.zip` (303 MB)
- Password: `123` (from `Password 123.txt` inside zip)
- Single file inside: `TFTUnlock Tool V6.2.1.1.exe` (303 MB PE32 GUI)

## Initial Reconnaissance

### File type
```
PE32 executable (GUI) Intel 80386, for MS Windows, 11 sections
```

### Compiler
```
Embarcadero Delphi for Win32 compiler version 36.0 (29.0.52631.8427)
```
This is Delphi 11/12 Alexandria (2022-2023 era).

### Section layout (11 sections)
.text, .itext, .data, .bss, .idata, .didata, .edata, @.tls, .rdata, @.reloc, B.rsrc

### Embedded binary signatures
```
GZIP: 4844 hits — massive embedded compressed data store
BZ2:  16 hits
LZMA: 31 hits
PNG:  1 (likely app icon/splash)
JPEG: 17 (screenshots/images in tool UI)
```

## Installer Automation (Wine)

### Steps performed
1. `unzip -P 123 "TFTUnlock Tool V6.2.1.1.zip"`
2. `wine "TFTUnlock Tool V6.2.1.1.exe"` (starts Setup installer)
3. Found window: `Setup - TFTUnlock Tool version 6.2.1.1` (596x432)
4. OCR via tesseract read password dialog: "This installation is password protected"
5. Entered password `123`, clicked through dialogs:
   - Password → Next (key alt+n)
   - Select Destination Location → Next
   - Select Additional Tasks → Next
   - Ready to Install → Install (key alt+i)
6. Installer extracted files for ~90 seconds
7. Completed: "Completing the TFTUnlock Tool Setup Wizard"

### Required Wine dep
```bash
winetricks vb6run  # MSVBVM60.DLL needed
```

## Installed Tool Structure

Install path: `~/.wine/drive_c/Program Files (x86)/TFTUnlock Tool/`
Total size: **1.3 GB**

### Key executables
| File | Size | Type | Purpose |
|------|------|------|---------|
| `TFTUnlock.exe` | 2.6 MB | VB6 GUI | Main tool (crashes on OleLoadPicture in Wine) |
| `TFT Unlock.exe` | 2.6 MB | .NET assembly | .NET version (hangs on font enum in Wine) |
| `TFT_AUTO.exe` | 166 KB | PE | Auto mode |
| `DM.exe` | 160 KB | PE | Download Mode tool |
| `com.exe` | 158 KB | PE | Communications |
| `d.exe` | 824 KB | PE | Helper executable |
| `appres.exe` | 336 KB | PE | App resources |
| `LGUP_Cmd.exe` | 10 MB | PE | LG firmware command tool |
| `main.py` | 7.7 KB | Python | MTK BROM exploit CLI |
| `TFT.exe` (Data/bin/) | 2.0 MB | PE | Main TFT flashing engine |
| `ResearchDownload.exe` | 1.8 MB | PE | Spreadtrum download tool |

### Key DLLs
| DLL | Size | Purpose |
|-----|------|---------|
| `SharpOdinClient.dll` | 336 KB | Samsung Odin protocol client |
| `QC.QMSLPhone.dll` | 591 KB | Qualcomm EDL/Sahara phone interface |
| `QMSL_MSVC10R.dll` | 17.9 MB | Qualcomm diagnostic runtime |
| `LGUP_Common.dll` | 5.6 MB | LG firmware protocol |
| `LibUsbDotNet.dll` | 157 KB | .NET USB wrapper |
| `WinUSBNet.dll` | 46 KB | Windows USB networking |
| `TFT_unlock.dll` | 11 KB | Unlock operations |
| `DotNetZip.dll` | 472 KB | ZIP compression |
| `spd.dll` (Data/bin/) | 262 KB | Spreadtrum protocol |
| `PortHound.dll` | 136 KB | USB port detection |
| `PortHoundd.dll` | 1.4 MB | Port Hound debug |

### Source code (extracted)
Location: `~/Documents/tft-unlock/`

| File | Size | Purpose |
|------|------|---------|
| `src/exploit.py` | 1.5 KB | BROM exploit — crashes preloader, injects payload |
| `src/device.py` | 6.2 KB | Serial/USB device layer with handshake protocol |
| `src/config.py` | 1.3 KB | Config parser (JSON5) |
| `src/common.py` | 618 B | Byte conversion utilities |
| `src/logger.py` | 170 B | Logging |
| `main.py` | 7.7 KB | CLI entry point with argument parsing |
| `default_config.json5` | 7.7 KB | MTK chipset config database |

### Device database: `Data/Model_QC/samsung.json`
**140+ Samsung models** across 4 chipset platforms:

#### Qualcomm Snapdragon (EDL mode)
S10-S23 series, Note 10/20, Z Flip/Fold, A52 (US), A71 (US), S21 FE, S22/S23 series

#### MediaTek (BROM exploit)
A01 Core, A02, A03s, A10s, A12, A13, A21, A22, A31, A32, A41, M-series

#### Exynos (Odin protocol)
S6, S7, J-series, A-series 2016, Note FE

#### Unisoc/Spreadtrum (SPD tool)
A03, A03 Core

### MTK Payloads (45+ chipset payloads)
Location: `Brom/mtkclient/payloads/`

Coverage: MT2601 through MT8695, including all common MediaTek SoCs found in Samsung and Xiaomi budget phones.

Payload types:
- `generic_dump_payload.bin` — BROM dump
- `generic_loader_payload.bin` — DA loader
- `generic_patcher_payload.bin` — Memory patcher
- `generic_preloader_dump_payload.bin` — Preloader extraction
- `generic_reboot_payload.bin` — Device reboot
- `generic_stage1_payload.bin` — Stage 1 boot
- Chipset-specific payloads: mt6261, mt6572, mt6580, mt6735, mt6737, mt6739, mt6753, mt6755, mt6757, mt6761, mt6763, mt6765, mt6768, mt6771, mt6779, mt6781, mt6785, mt6833, mt6853, mt6873, mt6877, mt6885, mt6893, etc.

### Samsung Loader files (PAC/MBN/ELF)
Location: `Data/bin/Loader/`

~140 files including:
- PAC files (Samsung flash protocol): 1.pac through 89.pac, b1.pac, b2.pac, it*.pac, etc. (3-10 MB each)
- MBN loaders (Qualcomm): Loader1.mbn through LoderV18.mbn, LoaderH1.mbn-S6.mbn
- ELF loaders (Samsung Exynos): Loader088.elf, Loader089.elf, Loder*.elf, TFT*.elf
- xloader images: sec_usb_xloader*.img, xloader*.img
- fastboot images: fastboot.img, sec_fastboot*.img
- FRP images: frpPartition.img (512KB), frpUnlocked.img (1MB)
- `data.dll` (4MB) — likely encrypted/compressed Samsung firmware

### Bundled mtkclient (Python 3.7 environment)
Location: `Brom/mtkclient/`
Size: **60 MB**

Full standalone Python 3.7 environment with:
- `python37.dll`, `python.exe`
- `Lib/` — standard library
- `Lib/site-packages/` — dependencies: pyusb, pycryptodome, pyserial, json5, charset-normalizer, colorama, certifi, idna, cursesmenu
- `payloads/` — 45+ BROM payload binaries
- `DLLs/` — libffi-7, ctypes, hashlib, socket, queue, select, unicodedata
- `Crypto/` — PyCryptodome for signature verification
- `scripts/` — wipe_data.bin, wipe_lock*.bin

### Dropper mechanism: `Scripts.ps1`
The scripts.ps1 is a dropper/updater that:
1. Elevates to admin privileges
2. Launches `TFT Unlock.exe`
3. Downloads config from `https://maxinstall.github.io/Scripts/config.txt`
4. Downloads an archive from URL in config (with WinRAR password extraction)
5. Adds Windows Defender exclusions
6. Auto-clears temp after 2 minutes

## Notable Observations

### What's notable
- **Full Python source included** — the BROM exploit isn't compiled/binary, it's plain Python with imports
- **No packer/protector detected** — Delphi PE, not packed
- **Tool architecture is multi-tier** — VB6 launcher → .NET core → Python exploit engine
- **GUI fails under Wine** — both VB6 (OleLoadPicture crash) and .NET (font enumeration hang) need real Windows
- **The .NET app references DevExpress v21.2** — commercial UI framework, large DLLs (+100MB total)

### What needs Windows
- GUI operations (license checks, device selection UI)
- USB device discovery via WinUSB/LibUsbDotNet
- .NET runtime for the TFT Unlock.exe
- PowerShell execution for the dropper

### What works on Linux natively
- Python BROM exploit (main.py + src/) — uses pyserial and pyusb
- MTK payload injection via libusb
- Odin protocol (SharpOdinClient.dll — could be analyzed for protocol)
- Qualcomm EDL (QMSLPhone.dll protocol can be reversed)
