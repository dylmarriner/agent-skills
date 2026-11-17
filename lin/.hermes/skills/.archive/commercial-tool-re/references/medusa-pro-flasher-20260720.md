# Medusa Pro 2.2.5.8 + Medusa Flasher 1.1.0.2 Analysis (2026-07-20)

## Overview

Two installer EXEs extracted via innoextract on a Linux remote host:
- **Medusa Pro_2.2.5.8.exe** (130MB) → `Medusa Pro Software.exe` (73MB main bin) + `MedusaUpdater.exe`
- **install_medusa_flasher_1.1.0.2.exe** (61MB) → `MedusaFlasher.exe` + `Updater.exe` + `meflash.dll`

Both are Inno Setup installers. Both are part of the Octoplus/Medusa family of GSM repair tools. Both share the same activation/license infrastructure.

## Packer Summary

| Binary | Packer | Section Names | Entropy | Notes |
|--------|--------|---------------|---------|-------|
| Medusa Pro Software.exe | K9/Korimir | `.k9T0`, `.k9T1`, `.k9T2`, `.k9T3` | 8.00 (max) | 15 sections x86, EP 0x13040a64 |
| MedusaUpdater.exe | K9/Korimir | `.k9T0-3` | 7.98 | 12 sections, EP 0x8dbf77 |
| MedusaFlasher.exe | VMProtect v2.x | `.vmp0`, `.vmp1` | 7.98 | 11 sections x86, EP 0x80e4f5 |
| Updater.exe | VMProtect v2.x | `.vmp0`, `.vmp1` | 7.88 | 12 sections, EP 0x1018935 |
| meflash.dll | Unpacked | `.text`, `.rdata`, etc. | 6.56 | 73KB VC++6 USB bridge DLL |

## Activation Server

```
http://gsmserver.com/gsm/credits-and-activations/?brand=octopus,octoplus
```

Found in `LANGUAGES/English.ini` (UTF-16 LE). Both Medusa Pro and Medusa Flasher use this same URL. This is the shared license/activation infrastructure with Octoplus tools.

## Activation System (from language file analysis)

- **Dongle-based**: Physical USB hardware key required (Octoplus/Medusa card)
- **Per-module activation**: LG, Samsung, Medusa, Huawei, FRP Tool — each separately licensed
- **Geo-restriction**: Full ISO 3166 country list — server checks connection country vs destination country
- **Card blacklisting**: Stolen/revoked dongles blocked server-side
- **Activation string system**: Server-issued activation codes
- **Update counting**: Maximum firmware update count enforced
- **Protocol version negotiation**: Version checking between client and server
- **TLS/SSL** for server communication
- **Proxy support** available

## USB Transport Comparison

| Aspect | Medusa Pro | Medusa Flasher |
|--------|-----------|----------------|
| USB Library | `libusb-1.0.dll` (standard) | Custom kernel driver |
| Device Path | Standard WinUSB | `\\.\EPIUSB` |
| Communication | libusb_bulk_transfer, WinUsb_ReadPipe/WritePipe | DeviceIoControl |
| Smart Card | WinSCard.dll | N/A |

## Chipset Support

| Chipset | Medusa Pro | Medusa Flasher | Evidence |
|---------|-----------|----------------|----------|
| Qualcomm (EDL 9008/900E) | ✅ | ✅ | QHSUSB drivers, qcusbser.sys |
| MediaTek (MTK) | ✅ | ❌ | MTK strings in Pro |
| Spreadtrum/Unisoc (SPD) | ✅ | ❌ | SPD strings in Pro |
| Samsung Exynos | ✅ | ❌ | 60+ eMMC/UFS firmware files |
| ST-Ericsson U8500 | ✅ | ❌ | U8500_USB_ROM.inf driver |
| FTDI Serial/JTAG | ✅ | ❌ | FTDI driver directory |
| Sony Ericsson (SEMC) | ❌ | ✅ | ggsemc.sys, repair .oct files, meflash.dll |
| Android ADB | ✅ | ✅ | AdbWinApi.dll |

## Key Binaries

### Medusa Pro
- **73MB main EXE**: K9-packed, Qt-based, all protocol code encrypted
- **Drivers**: U8500 (ST-Ericsson), FTDI, Smart Card CCID, QHSUSB (Qualcomm), Octoplus Box
- **Firmware**: 60+ Samsung eMMC (KL*, KM*, KMV*) and 6 UFS firmware images for chip reinit
- **DLL imports**: WS2_32 (network), WINUSB, WinSCard, SETUPAPI, ADVAPI32, CFGMGR32

### Medusa Flasher  
- **8.4MB main EXE**: VMProtect-packed
- **meflash.dll (73KB)**: Unpacked VC++6 DLL. Imports ONLY from KERNEL32.dll. Communicates with hardware via `DeviceIoControl` + `CreateFileA` on `\\.\EPIUSB`. Minimal USB bridge — sends raw commands, receives responses.
- **Repair files**: 5 HTC .oct files (Desire S, Inspire 4G, Desire HD, Desire Z, Incredible S)
- **Drivers**: Qualcomm QHSUSB + ggsemc.sys (Sony Ericsson custom USB flash driver)
- **Manuals**: Sony Ericsson Xperia repair manuals with test point images

## Extraction Notes

- Both installers are **Inno Setup** format — `innoextract` works cleanly
- `LANGUAGES/English.ini` is UTF-16 LE — use `iconv -f UTF-16 -t UTF-8` to read properly
- K9/Korimir packer leaves all readable strings encrypted — only language files, DLLs, and driver INFs yield static intelligence
- VMProtect similarly locks down the main EXE, but companion DLLs (meflash.dll) are unpacked and analyzable

## Written Reports

Full reports saved to remote host at:
- `/home/kubuntux/Downloads/RE/results/medusa_pro_2258_report.md`
- `/home/kubuntux/Downloads/RE/results/medusa_flasher_1102_report.md`
