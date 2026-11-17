# Inno Setup Post-Extraction Analysis: Octoplus Samsung v5.x

Session reference: Reverse-engineered `/tmp/octoplus_samsung.exe` (390 MB Inno Setup v5.5.7 installer). Octoplus Samsung is a separate product line from Octoplus FRP Tool — different encrypted resource format and different key material.

## Installer Reconnaissance Summary

| Property | Discovered Value |
|---|---|
| Format | Inno Setup v5.5.7 |
| Product | Octoplus Samsung (author: kr0m@LG.Octoplus.Box) |
| PE Sections | 8 (CODE, DATA, BSS, .idata, .tls, .rdata, .reloc, .rsrc) |
| Inno Signature Offset | 0xA988 ("Inno Setup Setup Data (5.5.7)") |
| Password Protected | No |
| Extracted Files | **4,901 files (942 MB)** |
| Largest EXE | OctoplusSamsung.exe (245 MB) — UPX-packed, Obfuscator-LLVM |
| Second EXE | OctoplusSamsungNew.exe (135 MB) — Qt-based, stripped PDB, NOT packed |

## Key Differences from Octoplus FRP Tool

| Feature | Octoplus FRP Tool v3.0.5 | Octoplus Samsung v5.x |
|---|---|---|
| Inno Setup Version | 5.3.8 | 5.5.7 |
| Encrypted Format | `OCTOPUS_v.2.0` header (.orf/.oct) | Magic `0x7743C66B` + **also** `OCTOPUS_v.1.0` (SamsungModels.oct) |
| Main EXE | Delphi (49 MB) | UPX-packed C++ (245 MB) |
| License Manager | DigitalLicenseManager.exe (separate Qt EXE) | No separate license EXE — built into main binary |
| Anti-Tamper | Oreans Themida/WinLicense | **Obfuscator-LLVM** control-flow obfuscation |
| File Count | ~2,091 files (399 MB) | ~4,901 files (942 MB) |
| Loader Type | Qualcomm EDL, MediaTek, SPD, UNISOC | Infineon, Swift/PNX, NVIDIA Tegra, Qualcomm, MTK |

## Resource Encryption Formats

### Format 1: Magic `0x7743C66B` (23 files in `app/resources/`)

All 23 resource files share the same first 4 bytes `77 43 C6 6B` (= `0x7743C66B` in little-endian) followed by encrypted payload. Sizes range from 240 bytes to 48 MB. Used for the main firmware/loader data.

Files (by hash-name):
```
074d3ae4410f15ef0e5ff9676e52144e      240 B
113D5D88CCAB4D0AE684706D7035F8A9    3.7 MB
1DF8F75337EB705F868D634B300359A9    2.3 MB
2B28A11B981E98B440D1C7A15C619F8C   45.9 MB  (newest, Jun 23)
5743BD2AEAC3A25A48147AFA6637516A    2.3 MB
... (18 more) ...
F798B05C491673B2A0AC69FCB6F360B4   46.1 MB  (newest, Jun 23)
```

The two 46MB+ files are dated **Jun 23** — likely the most recent update. All others are dated **Jan 4 2023**. The 240B files are probably small config/header blocks.

### Format 2: `OCTOPUS_v.1.0` header (SamsungModels.oct)

```
00000000: 4f43 544f 5055 535f 762e 312e 3000 0000  OCTOPUS_v.1.0...
```

Notably **v.1.0** (vs v.2.0 in the FRP tool). Contains encrypted model configuration data (~46 KB). Same header-only identification — no known extraction tool.

### Format 3: MediaTek plaintext (magic `4D544B5F`)

One file uses `0x4D544B5F` which decodes to `MTK_`:
```
E5078674770EDB9356BB7B0E4536D8BE   18.6 MB (magic: "MTK_DOWNLOAD_AGENT")
```
Followed by `MTK_DOWNLOAD_AGENT` and `MTK_AllInOne_DA_v3.3001.11/28/2021.05:37_58039000` — this is a MediaTek Download Agent, versioned and timestamped.

## Key Material Discovered

### Authentication Server Endpoints
```
node.octoplusbox.cloud   (primary)
node.octoplusbox.club    (backup)
```

### MKEYSKEY Identifiers
```
1308.500_MKEYSKEY
6180_Bootloader_10.0_MKEYSKEY
```
These likely map to chip family / bootloader version authorization keys.

### Auth Algorithm References
```
auth_seed
algorithm_auth
algorithm_mkey
NEEDAKAUTH
NEEDMSLAUTH
Bypassing msl cert.<br>
```

### Key Classification (from OctoplusSamsungNew.exe)
| Type | Count | Example |
|---|---|---|
| 32-char hex (MD5-length) | 87 | `0123456789ABCDEF0123456789abcdef` |
| 64-char hex (SHA-256 length) | 538 | `53467944EF6800F5DC70B8474149DAF8...` |
| 128-char hex | 1 | `DB670EAB3DEF40D79D2B24B3AEF988C1...` |
| 256+ char hex (RSA-like) | Several | `106539FD61AF6A02F9A31AB4F3BEA626...` |

### Compound Key with Chip Suffix
A large blob with format `<keyPart>_<chipID>`:
```
4C173D93762B496EF2A853A41ACA6799..._4000000031C88C242F6F7A...
```
The suffix (e.g., `4000000031C88C...`) likely identifies a specific chip or device family. Multiple such entries suggest per-device authorization keys.

## Obfuscation

### Obfuscator-LLVM (not Themida)
The main EXE is obfuscated with **Obfuscator-LLVM** (not Themida like the FRP tool):
```
Obfuscator-LLVM clang version 8.0.0  
  (https://github.com/heroims/obfuscator.git 
   29d9dc8c1bd662f3a73d1b1b009266af1786b7b8)
```

The `OctoplusSamsungNew.exe` is compiled with a different toolchain (Obfuscator-LLVM 3.5/3.6 based on strings) and is NOT UPX-packed, making it the easier analysis target.

## Firmware / Loader Inventory

| Platform | Count | Details |
|---|---|---|
| Infineon | 30+ | Samsung feature phone loaders (GT-C, GT-E, GT-S, SM-B series) |
| Swift/PNX | 50+ | Broadcom/Infineon phone loaders (PNX6515, PNX6529, PNX6712) |
| Qualcomm | 2 | GT-I9100 EFS repair + boot images |
| NVM | 120+ | Samsung phone NVM (non-volatile memory) dumps |
| EFS | 20 | Partition dumps for popular Android models |
| MTK DA | 1 file (18.6 MB) | MediaTek All-In-One Download Agent v3.3001 |

## Digital License Manager Integration

Unlike the FRP tool's separate `DigitalLicenseManager.exe`, the Samsung tool embeds license logic directly in the main binary. However, the license state uses the **same registry schema** as the FRP tool:

```
HKEY_LOCAL_MACHINE\SOFTWARE\OCTOPUS\SAMSUNG_TOOL\
HKEY_LOCAL_MACHINE\SOFTWARE\OCTOPUS\HUAWEI_TOOL\
HKEY_LOCAL_MACHINE\SOFTWARE\OCTOPUS\LG_TOOL\
HKEY_LOCAL_MACHINE\SOFTWARE\Wow6432Node\OCTOPUS\SAMSUNG_TOOL\
```

The HWID binding uses WMI query `SELECT Manufacturer,SerialNumber FROM Win32_PhysicalMemory`.

## rd.exe Analysis: Ext4 Worker (NOT a Device Communication Tool)

`rd.exe` (298KB) is an **ext4 filesystem IMEI manipulation utility** — NOT a Samsung device protocol tool:

- **Title**: `Ext4 Worker ver %s by Octoplus`
- **Author**: `Mich@el`
- **Build Path**: `D:\work\VS_Projects\Project1__lwext4\Work_ext4\main.cpp`
- **Framework**: Boost.ProgramOptions, MSVC 2015+ (MSVCP140.dll)

### Command Line Interface
```
Usage: rd.exe [OPTION]...
  -i / --img PATH       input ext4 image file path
  -c / --create PATH    create file(s) in ext4 image
  -m / --modify PATH    modify file in ext4 image
  -d / --delete PATH    delete ext4 file
  -D / --delete_dir     delete ext4 directory
  -z / --zero PATH      replace file content with zero bytes
  -I / --imei-skelet    create imei file at md/NVRAM/NVD_IMEI/LD0B_001
  --content FILE        file content for IMEI file
  --mode MODE           set file mode
  --owner UID:GID       set file owner
  --log PATH            logging
```

Creates/modifies IMEI at ext4 path `mp/md/NVRAM/NVD_IMEI/LD0B_001` with ACL `system.posix_acl_access`, owner `system:system`, mode `0660`.

## Developer/Engineer Identities

| Identity | Role | Source |
|---|---|---|
| `kr0m@LG.Octoplus.Box` | Tool author | Inno Setup metadata |
| `Mich@el` | rd.exe (ext4 worker) author | rd.exe strings |
| `jy8507.lee` | IMEI certificate engineer | Exynos cert code paths |
| `achernenko` | OpenSSL build engineer | Build server path |

## Full Chipset Tab Mapping (from Delphi component names)

| Tab ID | Chipset | Operations |
|--------|---------|------------|
| `MainTabSheetQQ` / `RepairTabSheetQQ` | Qualcomm (Snapdragon) | Sahara, Firehose, EDL, DIAG, cert repair |
| `MainTabSheetIN` / `RepairTabSheetIN` | Infineon | Old feature phones |
| `MainTabSheetBC` / `RepairTabSheetBC` | Broadcom | WiFi/Bluetooth firmware |
| `MainTabSheetSW` / `RepairTabSheetSW` | Swift (MediaTek) | Preloader/DA, MT62xx-MT68xx |
| `STTabSheetST` | Spreadtrum/Unisoc | SPD flash operations |
| `MainTabSheetAG` / `RepairTabSheetAG` | Android General | Generic Android |
| `DevelopersTabSheet` | — | Debug/developer |

## Embedded RSA Public Key
```
PubKey=40000000B7E8FA2EF98A874CB3D55425FAA0A8E519695B67040FAAF91264A2CCAEAABC956F4D3B3C4FAE042E901F5EC9721313D555A9C7570F9C42A7A517DC52C678E5E8157C9AC208483CD4862471105FA87BA7AA4C39715AC4B312A39D9F255E70B4EE06912E8AE3CC1C79D4D9E992524E00144524DA83C640A19CD2B978D196A30459818F509B485185BAC283E338BBC0791AFCE1F2496ABC8BA6162F2F54EE21537AAE0762430306F7707694983279585D96E75DE722B016553E641072E74392C27BC637130FFA1B5C74AB4950833D0C92BAE8AD16D15F92FF87E0FD04ADF29AFB064563963BF6F9DCA411256EAC42AEE4220B8AF7E8E727EB52D80198220084E1D1A29E32F5EFB62BA309948B4D6923935E125B23786AEA1452BF611B905A12B0F2B112663467C09D4DE62E97DAB6436622A075EAC0642B0612D2DA02581012668289CAFE33FD069CDE0495E8F0322D39CAC75E5B9812B66A8A23C913F2383315D5741153491DFDE9EB9CA6A85DADC786DE5B53DF4A4FC05D5ADA9AF8F0CC4006B49E79AB4236D1ABEFCFCA497CF5783723852CA9F15710DA780B425F919D7B76165AFDC76927605C375816F2806CC7004278EDDA9F4341A5690950A76DA8769D16E6716505E1715E357D1156400B0CF06EE126D286C005FC5B2C3DA50D11D3FBF86361F3A6789936D2D19B2BCC4F4ABE4D7976F66CCF564F87037D463FEB96880DD5588089
```
Referenced via `GetPublicKeyInTIM` and `getBlobValidationBlobCertPublicKey`.

## HWID Key Blob
```
7QxDHBCSemNzO0epsBDqw2tZ3Ig_V4kkTxsU0w9zvSvNOm5hd5+4zUg_4ydUdHa1UY2c6VoF6FKZ1SXX8TA_KhG0KJR94V7uH+RBiEjIvwRDC6E_hwid_typen
```
Base64 blob with `_hwid_typen` suffix — HWID generation seed.

## Additional Key References
- `bt_PBKDF2_HWID`, `device_key`, `aes_key`, `encdec_key`
- `set_entitlement_key::aes_ecb_decrypt`, `wrap_keybox`, `install_keybox`

## Build Server Paths
- `/home/achernenko/buildsrvskm/CryptoCore/src/crypto_core/`
- `vendor/marvell/generic/marvell-telephony/apps/atcmd_server/src/`

## Observations

1. **Dual-EXE architecture**: Old (UPX-packed, Obfuscator-LLVM) + New (Qt, stripped).
2. **Resource encryption**: Uses `0x7743C66B` magic (different from FRP tool's OCTOPUS_v.2.0).
3. **License validation**: Shares DLM registry schema and HWID binding with FRP tool.
4. **rd.exe is NOT a communication tool**: It is a specialized ext4 IMEI manipulation utility.
