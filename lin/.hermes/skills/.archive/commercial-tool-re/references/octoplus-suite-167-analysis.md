# Octoplus Suite 1.6.7 — Static RE Analysis (2026-07-20)

## Overview

Suite 1.6.7 is the "Octopus box" main desktop application — a unified launcher/UI for all Octoplus modules (Samsung, Huawei, LG, Qualcomm, etc.). Unlike the per-module tools (OctoplusSamsung.exe, OctoplusFRP.exe), Suite acts as a hub.

## Key Findings

### Protector

OctoplusSuite.exe uses an **unknown VMProtect-like protector** — not UPX, not LAx:

| Section | Virtual Size | Raw Size | Notes |
|---------|-------------|----------|-------|
| `.text` | 8,571,044 | **0** | Runtime decryption |
| `.itext` | 59,640 | **0** | Runtime decryption |
| `.data` | 206,944 | **0** | Runtime decryption |
| `.b}k` | 11,847,276 | **0** | Obfuscated name, code |
| `.H#7` | 37,822,848 | 37,822,976 | Main encrypted code body |
| `.rsrc` | 64,005,736 | 71,680 | Highly compressed resources |

- `pepack` reports: "no packer found" (signature not in database)
- All code sections except `.H#7` have raw size = 0 (pure runtime decryption)
- `.rsrc` raw is only 71KB but maps to **64MB virtual** — extreme compression ratio

### Companion DLLs

| DLL | Size | Protection | Notes |
|-----|------|-----------|-------|
| `meflash.dll` | 73 KB | VC++ 6.0, unpacked | "Mobile Equipment Flash USB API" |
| `libeay32.dll` | 1.1 MB | OpenSSL 0.9.x, unpacked | Crypto for TLS/activation |

### Model Files (.oct)

Both `SuiteModels.oct` (18.5 KB) and `RemoteService_Models.oct` (248 KB) share the header `OCTOPUS_v.1.0` followed by encrypted payload — same AES-128-CBC format documented in the parent skill.

### Activation URL

From `English.ini` (UTF-16, unpacked plaintext):

```
[URLS]
GsmServerShopUrl=http://gsmserver.com/gsm/credits-and-activations/?brand=octopus,octoplus
```

This is the **purchase endpoint** for activation strings. The actual license validation uses the `node.octoplusbox.cloud:8443` endpoint found in the Samsung module.

### Driver Hardware IDs

All Sony Ericsson (VID 0FCE):

| PID | Label | Notes |
|-----|-------|-------|
| 0xADDE | Flash | Primary flash device |
| 0xD064 | HCB-100 | Hardware box |
| 0xD083/0xD0AA/0xD0A8/0xD0F9 | HCB-120/105/100E/108 | Hardware box variants |
| 0xD104 | MBS-200 | Multi-box |
| 0xD101 | AB900 | Accessory |
| 0xFFFF | DFU | Device Firmware Update |
| 0xF0AA/0xF0F9/0xF104/0xF101/0xF0FA | DFU | SEMC DFU modes |
| 0xF106 | X1Boot | X1 Boot mode |
| 0xD14C | ETS | ETS USB |

Generic: VID 0BDB PID 100E.

ADB interface PIDs: 0x612E, 0xD12E, 0xE12E, 0x212E, 0x312E (sa0101) and 0x215D, 0x815D, 0x615D, 0x515D, 0x215B, 0x815B, 0x915B, 0x214F, 0x814F, 0x614F, 0x514F, 0x2156, 0x8156, 0x6156, 0x5156, 0x215C, 0x815C, 0x615C, 0x515C (sa0102).

### Operation Strings (from packed binary — survived garbling)

**Samsung:** SAMSUNG_TMB_SERVERUNLOCK, SAMSUNG_TMB_SERVERUNLOCKRIL, SAMSUNG_S8_TMOBUNLOCKLOADER, SAMSUNG_S8_TMOBUNLOCKTOOL, SAMSUNG_EXYNOS_ATPATCH_LOADER, SAMSUNG_EXYNOS_ATSENDER_JVM_NEW/OLD, SAMSUNG_EFS_UPLOADMODE, SAMSUNG_UPLOADMODE, SAMSUNG_J327_TMB, SAMSUNG_J327_TMB_DEBUG, GETROOTKINGO/2/3, BTN_UNLOCK, BTN_UNLOCKBOOTLOADER, BTN_UNROOT

**Huawei:** 50+ modem models (E153..K5005) with NVM-REPAIR, LOADER-EMERGENCY, LOADER-NORMAL suffixes

**Qualcomm:** QUALCOMM_MSM8255, QUALCOMM_MSM8255_NAND4K_LOADER

**Sharp:** SHARP_ROOT

## Next Steps for Suite 1.6.7

1. **Runtime analysis** in Windows VM to capture the activation server communication
2. **Extract RSA public key** from the binary for .oct decryption attempts
3. **Network capture** of Suite's HTTPS traffic to both `gsmserver.com` and `node.octoplusbox.cloud`
4. **Patch the main EXE** (offset discovery needed — protector makes static xrefs difficult)
