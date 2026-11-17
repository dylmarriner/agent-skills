# Octoplus Tool Suite — RE Findings

Tools analyzed: Octoplus Samsung v5.1.2.2, Octoplus FRP v3.0.5.0
Session date: 2026-07-15

## Installers

Both are Inno Setup installers (not password-protected). Extracted with innoextract v1.9.
- Samsung: 389MB installer → 4901 files, 942MB unpacked
- FRP: 310MB installer → 2091 files, 399MB unpacked

## Octoplus Samsung v5.1.2.2

### Key Executables
- `OctoplusSamsung.exe` — 245MB Delphi GUI, 12 sections (main app, heavily packed/obfuscated)
- `OctoplusSamsungNew.exe` — 135MB Qt/C++, stripped PDB (secondary/updated version)
- `rd.exe` — 298KB C++ console tool, "Ext4 Worker" by Mich@el — mounts ext4 images to inject IMEI data at path `md/NVRAM/NVD_IMEI/LD0B_001`. NOT a device comm tool.
- `SamsungUpdater.exe` — 8.9MB auto-updater
- `DigitalLicenseManager.exe` — smart-card dongle license manager

### DLL Protocol Stack
- NVIDIA Tegra: libnv3p.dll, libnvaes_ref.dll, libnvapputil.dll, libnvboothost.dll, libnvdioconverter.dll, libnvflash.dll, libnvos.dll, libnvusbhost.dll
- OpenSSL 1.0.1m: libeay32.dll, ssleay32.dll
- SQLite: sqlite3.dll, SAM_ALL.db (2136 Samsung model names)
- LZ4: lz4.dll
- MySQL: libmysql.dll
- Themida: SecureEngineSDK32.dll

### Device Support
- 2136 models in SAM_ALL.db database (GT-*, SM-*, SPH-*, SCH-*, SHV-*, SHW-* series)
- 370+ .oct files: preloaders, mainloaders, certificates (each 15971 bytes), EEPROM dumps, NVM configs
- EFS repair images for flagship models (GT-I9100, GT-I9300, etc.)
- Qualcomm boot images (bct, fastboot)

### License System
- **Servers:** node.octoplusbox.cloud, node.octoplusbox.club (port 8443)
- **Secondary:** mussaurus.octoplusbox.club/269C639C2D421A99163EA24710F4ED5D.json
- **HWID:** PBKDF2-HMAC-SHA512 (5000-9000 iterations), salt from Win32_PhysicalMemory (Manufacturer + SerialNumber)
- **HWID key:** 81-byte blob, URL-safe base64, ends with `_hwid_typen` suffix
- **Auth flow:** (1) Smart-card dongle → (2) HWID validation → (3) AES-GCM decrypt → (4) X509 verify → (5) Load resources
- **Crypto:** AES-128-GCM, TAESKey (16 bytes), INIT_KEY_1 (52 bytes), INIT_KEY_2 (84 bytes) in RTTI
- **RSA public key:** embedded for license signature verification
- **Registry:** HKLM\SOFTWARE\OCTOPUS\SAMSUNG_TOOL\
- **Transport:** Indy TIdHTTP + TIdSSLIOHandlerSocketOpenSSL (Delphi) or Qt QNetworkAccessManager (new exe)

### File Encryption
- `.oct` files: OCTOPUS_v.1.0 header, AES-CBC encrypted, key runtime-derived
- Some resources use custom encryption with magic 0x7743C66B

## Octoplus FRP v3.0.5.0

### Key Executables
- `OctoplusFRP.exe` — 49MB Qt C++, Themida-packed (13 sections)
- `DigitalLicenseManager.exe` — 24MB Qt, stripped PDB (DRM/license manager)
- `Updater.exe` — 8.5MB
- `MetaCore.dll` — 13.5MB, **NOT packed**, statically linked Crypto++ (core engine)
- `SecureEngineSDK32.dll` — 28KB Themida/WinLicense protector

### .orf File Format
All loader files use OCTOPUS_v.2.0 format with AES-128-CFB encryption via Crypto++:

| File | Size | Chipset |
|------|------|---------|
| MTKLoaders.orf | 70.7MB | MediaTek (BROM/DA loaders) |
| QComLoaders.orf | 54.3MB | Qualcomm (Firehose/Sahara loaders) |
| HWDrv.orf | 10.4MB | Hardware drivers |
| SPDLoaders.orf | 4.0MB | Spreadtrum/UNISOC |
| AMobile.orf | 1.4MB | Android mobile drivers |
| 22 Unisoc .orf files | 1-2MB each | SC7731E, SC9832E, SC9863A, Tiger T310/T606/T610/T612/T616/T700/T760 |

**Two IV groups:**
- Group 1 (main): `f647c0f93b71a0c4915c406aa035a05c` + 48 more bytes
- Group 2 (Unisoc): `69003595fef6c855ccb26638541012c6` + 48 more bytes

### Device Database
- `OctFrpModelsDB.db` — 16,744 models across 1,227 vendors
- `FirehoseParams.db` — Qualcomm Firehose loader hashes

### Crypto Constants (from MetaCore.dll)

MetaCore.dll has Crypto++ statically linked. Key classes:
- AES-128 Rijndael in CFB mode (CFB_DecryptionTemplate, CFB_EncryptionTemplate)
- AES in CBC mode also available
- DES/3DES CBC
- SHA-1, SHA-256, SHA-512
- HMAC
- ElGamal (public key encryption)
- PBKDF2 (PasswordBasedKeyDerivationFunction)

The decryption key is likely embedded in MetaCore.dll as a byte array. Search for 16-byte high-entropy blobs near Crypto++ class references.

### License System
Same server endpoints as Samsung tool (node.octoplusbox.cloud:8443, node.octoplusbox.club:8443)
Runs through DigitalLicenseManager.exe for smart-card auth
Qt-based HTTPS stack (QHttpNetworkReply, QSslSocket, QAuthenticator)

## MITM Server

A working MITM server was deployed at `/tmp/octoplus_mitm_server.py`:
- Listens on 0.0.0.0:8443 with TLS (CA-trusted cert for octoplusbox.* domains)
- DNS poisoned in /etc/hosts for all octoplusbox domains
- Returns fake JSON license response with all known fields
- Port 80/443 redirected to 8443 via iptables
