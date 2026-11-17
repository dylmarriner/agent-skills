# Inno Setup Post-Extraction Analysis: Octoplus FRP Tool v3.0.5

Session reference: Reverse-engineered `/tmp/octoplus_frp.exe` (310 MB Inno Setup v5.3.8 installer). Contains documented analysis patterns that apply to many large Inno Setup installers.

## Installer Reconnaissance Summary

| Property | Discovered Value |
|---|---|
| Format | Inno Setup v5.3.8 |
| Product | Octoplus FRP Tool v3.0.5 |
| PE Sections | 8 (CODE, DATA, BSS, .idata, .tls, .rdata, .reloc, .rsrc) |
| PE Stub Size | ~54 KB |
| Appended Data | ~310.3 MB (Inno Setup compressed payload) |
| Password Protected | No |
| Extracted Files | 2,091 files (399 MB) |

## Extracted File Inventory

### Core Application
| File | Size | Notes |
|---|---|---|
| `app/OctoplusFRP.exe` | 49 MB | Main app (Borland/Embarcadero Delphi) |
| `app/DigitalLicenseManager.exe` | 25 MB | License validation engine — Qt5 GUI |
| `app/Updater.exe` | ~1 MB | Auto-updater component |
| `app/MetaCore.dll` | 14 MB | Core engine — MTK/SPD/QCOM protocols |
| `app/SecureEngineSDK32.dll` | ~2 MB | **Oreans Themida/WinLicense** anti-tamper |

### Third-Party Components Identified

| Component | File(s) | Version | Source |
|---|---|---|---|
| OpenSSL | `app/libeay32.dll`, `app/ssleay32.dll` | 1.0.1m (2015-03-19) | OpenSSL Foundation |
| ADB USB | `app/AdbWinApi.dll`, `app/AdbWinUsbApi.dll` | Standard Google | Android SDK |
| SQLite | `app/sqlite3.dll` | 3.x | SQLite Consortium |
| 7-Zip | `app/7z.dll` | 23.x | Igor Pavlov |
| UsbDk | `app/usbdk/UsbDk_1.0.22_x64/x86.msi` | 1.0.22 (2020-03-13) | Red Hat, Inc. |
| libusb | `sys/libusb-1.0.dll`, `sys/libusb0.dll`, `sys/drivers/libusb0.sys` | 1.0.x | libusb project |
| iTunes Mobile Device | `app/AMobileDll/iTunesMobileDevice.dll` | Apple | Apple Inc. |
| Microsoft VC Runtime | `app/AMobileDll/msvcp140.dll`, `vcruntime140.dll`, `concrt140.dll` | 2015-2022 | Microsoft |
| ICU (Unicode) | `app/AMobileDll/icudt62.dll`, `libicuin.dll`, `libicuuc.dll` | 62.x | Unicode/ICU |
| libxml2 | `app/AMobileDll/libxml2.dll` | 2.x | GNOME |
| OpenThreads (pthread) | `app/AMobileDll/pthreadVC2.dll` | — | — |

### Proprietary (.orf / .oct) Encrypted Data Files

All use the same format: 16-byte ASCII header `OCTOPUS_v.2.0\x00\x00\x00\x00` followed by encrypted binary data. No known extraction tool exists — decryption is handled at runtime by the app.

| File | Size | Purpose |
|---|---|---|
| `app/Data/QComLoaders.orf` | 52 MB | Qualcomm EDL loaders (firehose programmers) |
| `app/Data/MTKLoaders.orf` | 68 MB | MediaTek bootrom loaders |
| `app/Data/HWDrv.orf` | 10 MB | Huawei/HiSilicon driver protocols |
| `app/Data/SPDLoaders.orf` | 3.9 MB | Spreadtrum/UNISOC loaders |
| `app/Data/AMobile.orf` | 1.4 MB | Apple Mobile device handlers |
| `app/Data/MTKResources.orf` | 144 KB | MediaTek resource data |
| `app/Data/Unisoc/*.orf` (×20) | 1–2.2 MB each | Per-chipset UNISOC bootrom loaders |
| `app/SupportFiles.oct` | ~1 MB | Support/configuration data |
| `app/SupportDownloads.oct` | ~1 MB | Download configuration |

### SQLite Databases

**OctFrpModelsDB.db** (6.3 MB, SQLite 3.7.13)
- Tables: `Models`, `ModelConnection`, `ModelCapabilities`, `Params`
- Schema:
  ```sql
  Models(ID, Vendor, Model, ConnectionID, CapabilityID, RegistrationType, ManualGenerator, Picture, Release)
  ModelConnection(ID, ConnectionMode)
  ModelCapabilities(ID, ConnectionMode, Capability)
  Params(ModelID, Name, Value)
  ```
- Contains **16,744 models** across **1,227 vendors**
- `RegistrationType` field values include: `drQcom_9008_wLoader`, `drGeneral_MTK`, `drSPD_SC7731C`, `drQcom_9008`, `drADB`, `drAsus_Fastboot_ADB`, `drXiaomi`, `drExynosARM32`, `drIPhone`, etc.

**FirehoseParams.db** (77 KB, SQLite 3.24.0)
- Table: `Loaders(hw_id, pk_hash, size, name)`
- Maps hardware IDs (hex string) to PK hash (MD5-like) and firehose loader filename
- Example: `0000000000000000|041E79F9D25C0EC59F49FD90C33B547D|342500|0000000000000000_041e79f9d25c0ec5_fhprg_peek.bin`

### Firmware / Patch Files

| File | Size | Notes |
|---|---|---|
| `app/Data/Firmwares/factory_mode_patch.bin` | 5.3 MB | Binary patch for factory mode |
| `app/Data/Firmwares/on_factory_mode_std.app` | 1,050 bytes | Empty/zero-filled header stub |

### License Analysis

**DigitalLicenseManager.exe** key findings:

- Built with **Qt5** (cross-platform GUI framework)
- Uses **AES-NI hardware-accelerated encryption** (CRYPTOGAMS by Andy Polyakov)
- Displays `No active license found` as the default state
- Date-bound licensing: `License activation:`, `License ending:`
- Branded as `Octoplus %1 %2 Digital License`
- Contains Qt SSL/network stack (QNetworkProxy, QSslCertificate, QSslError) — validates online
- All license logic is likely inside the **Oreans Themida**-protected code sections

#### HWID Binding
The primary HWID source is the **RAM module serial number** via WMI:
```sql
SELECT Manufacturer,SerialNumber FROM Win32_PhysicalMemory
```
Other license state fields tracked:
- `lbl_license_name`, `lbl_activation_start_date_val`, `lbl_activation_end_date_val`
- `lbl_hwid_change_count_val`, `lbl_hwid_change_date_val` — HWID mutation tracking

#### Registry Persistence
Licenses persisted to `HKLM\SOFTWARE\` under these vendor keys:
```
OCTOPLUS\FRP_TOOL\
OCTOPUS\SAMSUNG_TOOL\
OCTOPUS\HUAWEI_TOOL\
OCTOPUS\LG_TOOL\
Wow6432Node\OCTOPLUS\FRP_TOOL\
```

#### License Server Addresses
- `node.octoplusbox.cloud` (primary)
- `node.octoplusbox.club` (backup)

**SecureEngineSDK32.dll** markers visible in string table:
- `RegisteredStart`, `RegisteredEnd` — license state check wrappers
- `UnregisteredStart`, `UnregisteredEnd` — trial/unlicensed paths
- `CustomVM00000100_Start` through `CustomVM00000110_End` — code virtualization sections
- `CodeReplaceStart/End`, `ClearStart/End`

### Driver Bundles
- `Drivers/libUsb/install-filter.exe` — PE32 console, libusb filter installer
- `Drivers/Reader driver/Cypress_reader_driver.exe` — PE32 GUI, Cypress USB reader
- `Drivers/Card driver/TOP_GX4_card_driver.rar` — SmartCard CCID driver (RAR with unsupported method, x32 + x64)

### Other Notable Files
- `app/Skin/*.asz` — 21 compressed skin files (AfterBurner, Metro, iOS4, etc.)
- `app/Lang/*.ini` — 6 language translations (English, Portuguese, Spanish, Turkish, Ukrainian, Vietnamese)
- `app/Manuals/images/phones/*.png` — Thousands of phone model images for connection guides
- `app/Manuals/images/cables/*` — Cable diagram images (USB, UART, EDL, JTAG)
- `app/Manuals/res/*` — HTML/CSS/JS resources for the built-in documentation viewer

## Key Observation: .orf Encryption Header

All ORF/OCT files share identical first 16 bytes:
```
4f 43 54 4f 50 55 53 5f 76 2e 32 2e 30 00 00 00  = OCTOPUS_v.2.0...
```

The next 16 bytes appear to be an IV or per-file key, followed by encrypted payload. The main ORF files (AMobile, HWDrv, MTKLoaders, QComLoaders, SPDLoaders) all share the **same** IV:
```
f6 47 c0 f9 3b 71 a0 c4 91 5c 40 6a a0 35 a0 5c
```

While the Unisoc per-chip ORF files share a **different** common IV:
```
69 00 35 95 fe f6 c8 55 cc b2 66 38 54 10 12 c6
```

This dual-IV pattern suggests two encryption contexts within the app — one for the core data module and one for UNISOC loaders specifically.

### Detailed Header Structure (v2.0)

| Offset | Size | Field | Notes |
|--------|------|-------|-------|
| 0x00   | 16   | Magic | `OCTOPUS_v.2.0\0\0\0` |
| 0x10   | 64   | Key material | Encrypted/salted AES-128 key + IV (two groups) |
| 0x50   | N    | Payload | AES-128-CFB encrypted AUTH data (entropy ≈ 8.0) |

The 64 bytes at 0x10-0x4F form a single blob used for key derivation. The two groups identified:

**Group 1** (6 files: MTKLoaders, QComLoaders, HWDrv, SPDLoaders, AMobile, MTKResources):
```
f6 47 c0 f9 3b 71 a0 c4 91 5c 40 6a a0 35 a0 5c
33 60 6f 5d 63 fb 7a 28 8f 09 1c d9 74 52 63 b5
7b e2 15 b8 1a 8e 4f d0 4b 7b 44 6f af c1 e3 a2
55 ec 7c f7 de e7 4a 11 ab e1 36 bf de fa 14 c0
```

**Group 2** (22 Unisoc files):
```
69 00 35 95 fe f6 c8 55 cc b2 66 38 54 10 12 c6
4e ae 7a 65 ed 48 d1 6c 46 52 43 ef 9d 89 2a 64
91 0c fa 4a f8 13 44 ce 52 51 02 cc de a3 2e d7
98 56 38 e6 44 f8 c1 58 54 bf 60 80 aa f8 05 52
```

### MetaCore.dll — The ORF Decryption Engine

MetaCore.dll (13.5 MB) statically links **Crypto++ (CryptoPP)** and implements the full MediaTek BootROM authentication protocol. It is the core engine — OctoplusFRP.exe delegates all ORF loading to it.

#### Crypto++ Classes Identified (static linking)

| Class Pattern | Algorithm | Use |
|---|---|---|
| `Rijndael_Info` / `Enc@Rijndael` | AES (Rijndael) | Block cipher |
| `CFB_DecryptionTemplate` / `CFB_EncryptionTemplate` | AES-128-CFB | **ORF stream decryption** |
| `CBC_Decryption` / `CBC_Encryption` | AES-CBC | Alternative block mode |
| `DES_EDE2`, `DES` | Triple DES / DES | Legacy algorithms |
| `HMAC@SHA1` | HMAC-SHA1 | Integrity verification |
| `ECDSA@ECP`, `ECDSA@EC2N` | ECDSA | Signature verification |
| `DLIES` | Discrete Log Integrated Encryption Scheme | Key exchange |
| `AutoSeededX917RNG@Rijndael` | X9.17 PRNG | Random number generation |

#### AUTH_HANDLE API (the ORF loading API)

Decryption is orchestrated through the AUTH (Authentication) subsystem:

```
AUTH_Create()          → Allocate AUTH_HANDLE
AUTH_Load()            → Read ORF from file
AUTH_LoadBuf()         → Read ORF from memory buffer
AUTH_GetInfo()         → Extract version, customer name, description
AUTH_IsReady()         → Check if decryption/validation succeeded
AUTH_Destroy()         → Free AUTH_HANDLE
```

The decryption pipeline:

1. **`Auth_Wrapper::Auth_Init_Key`** — Derives the 16-byte AC_KEY from the 64-byte key material in the ORF header. Confirmed 16-byte key via error string: *"AC Key length invalid : %d byte (16 byte is correct)"*

2. **AES-128-CFB decrypt** — Using Crypto++'s `CFB_DecryptionTemplate<Rijndael>` with the derived key and IV from the ORF header region

3. **`Auth_Wrapper::Auth_Hash`** — Integrity check on decrypted payload

4. **`Auth_Wrapper::Auth_Verify`** — Verifies against the embedded GFH (Generic File Header) structures

5. The decrypted payload contains MediaTek **GFH** format structures:
   - `GFH_TOOL_AUTH_v1` — Tool authentication blob
   - `GFH_SCTRL_CERT_v1` — Secure control certificate
   - `GFH_BL_SEC_KEY` — Bootloader security key
   - `GFH_FILE_INFO_v1` — File metadata header
   - `GFH_ANTI_CLONE` — Anti-clone token
   - `GFH_BL_INFO` — Bootloader info
   - `GFH_CHECK_CONFIG` — Check config

#### BootROM Protocol — How ORF Data Reaches the Phone

Once decrypted, the AUTH certificate is sent to the target device's bootROM via the MediaTek Secure Download Protocol:

```
BromCmd_SendAUTH(AUTH_HANDLE)      → Send AUTH certificate to bootROM
  ├── Write32DataWithEcho()        → Send length prefix
  ├── WriteData()                  → Send AUTH blob
  └── Read16Data()                 → Read checksum + status

BromCmd_SendCERT(CERT_HANDLE)      → Send SCERT certificate
  └── Read16Data()                 → Verify checksum

Brom_SendSCERT()                   → High-level SCERT send wrapper

Boot_FlashTool()                   → After auth → download DA → flash
  ├── DA (Download Agent) loading via DL_HANDLE
  ├── Preloader communication (DL_Get_PreloaderFilePath)
  └── NAND/eMMC ReadBack commands (CMD_NAND_ReadBack, CMD_ReadBack)
```

The protocol flow: **ORF → AES-128-CFB decrypt → GFH parse → AUTH cert → USB (BROM) → phone BootROM → authenticate → allow DA download → flash operation**

### FirehoseParams.db Detail

This SQLite database maps Qualcomm hardware IDs to Firehose programmers:

```sql
CREATE TABLE [Loaders](
  [hw_id] TEXT(20) NOT NULL,
  [pk_hash] TEXT(40) NOT NULL,
  [size] INT64 NOT NULL,
  [name] TEXT(100) NOT NULL
);
```

- `hw_id`: Qualcomm hardware ID (e.g., `0000000000000000` — the SoC identifier)
- `pk_hash`: MD5 hash of the programmer binary (32-char hex)
- `size`: Programmer size in bytes
- `name`: Filename matching pattern `_<md5hash>_fhprg[_peek].bin`

Example entry:
```
hw_id=0000000000000000 | pk_hash=041E79F9D25C0EC59F49FD90C33B547D | size=342500 | name=..._041e79f9d25c0ec5_fhprg_peek.bin
```

### Architecture Summary

```
┌─────────────────────┐     ┌──────────────────────┐
│ DigitalLicenseMgr   │     │  OctoplusFRP.exe     │
│ (Qt5 + OpenSSL)     │     │  (Themida-packed)    │
│                     │     │                      │
│ node.octoplusbox    │     │  ┌────────────────┐  │
│       .cloud:443    │     │  │  MetaCore.dll  │  │
│ HWID: RAM+disk S/N  │     │  │  (Crypto++     │  │
│ HKLM\SOFTWARE\      │     │  │   static)      │  │
│   OCTOPLUS\FRP_TOOL │     │  │                │  │
└─────────┬───────────┘     │  │ ORF → AES-128  │  │
          │ license check   │  │   -CFB decrypt │  │
          ▼                 │  │              → │  │
┌─────────────────────┐     │  │ GFH parse →    │  │
│ License Valid:      │     │  │ AUTH cert →    │  │
│ Loaders unlocked    │─────│→│ BROM protocol  │  │
└─────────────────────┘     │  │ → USB → phone  │  │
                            │  └────────────────┘  │
                            │                      │
                            │  SQLite DBs:         │
                            │  • OctFrpModelsDB.db │
                            │    (16K models)      │
                            │  • FirehoseParams.db │
                            │    (QCOM programmer  │
                            │     hash table)      │
                            └──────────────────────┘
```

### .oct Support Files

`SupportDownloads.oct` and `SupportFiles.oct` use the same `OCTOPUS_v.2.0` format but with a **third distinct key region** — they are encrypted with different key material, not shared with the loader ORF files.
