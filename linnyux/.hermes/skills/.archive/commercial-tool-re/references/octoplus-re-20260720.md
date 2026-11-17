# Octoplus Suite — Extended RE Analysis (2026-07-20)

## Session Context

Continuation of Octoplus RE work. Previous analysis (2026-07-15) covered basic installer extraction, DLL protocol stack mapping, file encryption formats, and MITM server deployment. This session focuses on deeper binary analysis: packer identification, license bypass strategies, and FRP method extraction.

## Four Installers Analyzed

| Installer | Version | Key Binaries | Size |
|-----------|---------|--------------|------|
| Samsung | 5.1.2.2 | OctoplusSamsung.exe (246M), OctoplusSamsungNew.exe (136M) | 389MB |
| FRP Tool | 3.0.6.0 | OctoplusFRP.exe (49M), DigitalLicenseManager.exe (25M), MetaCore.dll (14M) | 310MB |
| Suite | 1.6.7 | OctoplusSuite.exe | — |
| JTAG | 1.9.5.6 | Medusa.exe | — |

## Packer Deep-Dive

### OctoplusSamsung.exe — Custom UPX 3.91 (not Obfuscator-LLVM)

Initial analysis misidentified this as Obfuscator-LLVM due to high entropy. Closer PE section analysis proves it's UPX 3.91 with renamed sections:

| Section | Size | Entropy | Would Be (standard UPX) |
|---------|------|---------|------------------------|
| `.text` | 11.7 MB | 6.33 | UPX0 (decompressed code stub) |
| `.ybI` | 21.7 MB | 7.99 | UPX1 (compressed payload) |
| `.(:R` | 3.0 MB | 7.86 | UPX2 (compressed resources) |
| `.H0]` | 5 KB | 6.16 | UPX! (stub) |
| `.rsrc` | 336 MB | 6.51 | Resources (skins, images, model DBs) |

**Evidence:** UPX string `$Id: UPX 3.91 Copyright (C) 1996-2013 the UPX Team. All Rights Reserved. $` found in binary. `upx -d` fails with `NotPackedException` because section names don't match `UPX0/UPX1/UPX!`.

### OctoplusSamsungNew.exe — Custom UPX 3.95 (TeK Packer)

| Section | Size | Entropy | Description |
|---------|------|---------|-------------|
| `.TeK0` | 33 KB | 7.99 | Decryption key table / IV block |
| `.TeK1` | 31.5 MB | 7.82 | Encrypted x86 payload (contains `55 8B EC` = push ebp; mov ebp,esp prologue) |
| `.TeK2` | 4 KB | 6.17 | Metadata table |
| `.TeK3` | 16.2 MB | 7.42 | Secondary encrypted payload |

### DigitalLicenseManager.exe — LAx Custom Packer

Qt 5/C++ binary, stripped PDB. Not UPX — uses proprietary LAx packer:

| Section | Size | Entropy | Description |
|---------|------|---------|-------------|
| `.LAx0` | 5.8 MB | 7.94 | Encrypted license validation code + resources |
| `.LAx1` | 2.4 MB | 7.79 | Unpacker stub — contains DLL imports for decryption APIs |

**`.LAx1` contains critical unpacker APIs:**
- `VirtualAlloc`, `VirtualProtect`, `VirtualFree`, `VirtualQuery` — memory management
- `WriteProcessMemory`, `CreateThread`, `CreateProcessW` — code injection
- `ReadFile`, `WriteFile` — payload I/O
- `LoadLibraryA`, `LoadLibraryW`, `GetProcAddress` — dynamic API resolution
- `CreateFileMappingW`, `CreateFileW` — file-backed unpacking

### ChimeraInstaller.exe — Winlice Packer

Euroserver Sro. (Czech), version 13.88.1015.0. Winlice LZSS-packed:

| Section | Size | Description |
|---------|------|-------------|
| `.boot` | — | Winlice decryption stub with ADC-based LZSS decompression |
| `.winlice` | 6.5 MB | Encrypted payload (RWX permissions) |

**Decryption stub starts at offset 0x58 in .boot section:**
```
58: e8 4b 01 00 00    call 0x1a8          ; call sub
5d: 53                push ebx
5e: 89 e3             mov ebx, esp
60: 53                push ebx
61: 8b 73 08          mov esi, [ebx+8]     ; source ptr
64: 8b 7b 10          mov edi, [ebx+0x10]  ; dest ptr
67: fc                cld
68: b2 80             mov dl, 0x80         ; bit buffer
```

Single import per DLL pattern — all imports dynamically resolved by Winlice at runtime. An embedded PE was extracted at offset 0x0 (1MB, padding + actual PE).

## License Server Infrastructure

### Primary Endpoints

```
IP:     38.242.233.249
Host:   node.octoplusbox.cloud   (ALIAS)
Host:   node.octoplusbox.club    (ALIAS)
Port:   8443 (non-standard HTTPS, found as string in SamsungNew binary)
```

### Activation Endpoint

```
https://mussaurus.octoplusbox.club/.269C639C2D421A99163EA24710F4ED5D.json
```

Found at 3 offsets in OctoplusSamsungNew.exe, in context with:
- `/proc/kg_drv_info | grep resource_locked` (offset 0x01CAB36C)
- `rm -rf /data/local/tmp/*` (offset 0x01CADE1C)
- base64-encoded data (offset 0x01CB058C)

### Registry Keys (after activation)

```
HKLM\SOFTWARE\OCTOPLUS\FRP_TOOL\
HKLM\SOFTWARE\OCTOPUS\HUAWEI_TOOL\
HKLM\SOFTWARE\OCTOPUS\LG_TOOL\
HKLM\SOFTWARE\OCTOPUS\SAMSUNG_TOOL\
HKLM\SOFTWARE\Wow6432Node\OCTOPLUS\FRP_TOOL\  (x86 on x64)
```

## MetaCore.dll Hardware ID Bypass

MetaCore.dll (14MB, native C++ MSVC 9.0, CryptoPP statically linked) is the MediaTek BROM/DA authentication library. It is NOT packed — the main EXE is packed but MetaCore.dll is clean.

### Key Exported Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `AUTH_Create` | `void* __stdcall AUTH_Create()` | Create auth handle |
| `AUTH_Destroy` | `void __stdcall AUTH_Destroy(void*)` | Destroy auth handle |
| `AUTH_Load` | `int __stdcall AUTH_Load(void*, const char* path)` | Load AUTH file from disk |
| `AUTH_LoadBuf` | `int __stdcall AUTH_LoadBuf(void*, const uint8_t* buf, int len)` | Load AUTH from memory |
| `AUTH_Unload` | `void __stdcall AUTH_Unload(void*)` | Unload current AUTH |
| `AUTH_IsReady` | `bool __stdcall AUTH_IsReady(void*)` | Check if auth loaded |
| `AUTH_GetInfo` | `void __stdcall AUTH_GetInfo(void*, AUTH_INFO* out)` | Get auth metadata |
| `AUTH_SetCallback` | `void __stdcall AUTH_SetCallback(void*, AUTH_CALLBACK cb)` | Set progress callback |

### Critical Failure Strings and Offsets

| String | Offset | Purpose |
|--------|--------|---------|
| `CompareAllBBChipHWID(): fail!` | 0x938274 | HWID comparison fail — **PRIMARY PATCH TARGET** |
| `customer name mismatch with AUTH file` | via xref | Customer/device mismatch |
| `SOC_Verification(): SOC_OK` | via xref | Success path |
| `SOC_Verification(): SOC_FAIL` | via xref | Failure path — NOP to force OK |
| `bbchip_name is NULL, skip H/W version check` | via xref | Skip path — can be forced |
| `STATUS_SEC_AUTH_FILE_NEEDED` | via xref | Auth file required |

### AUTH File Format

```
GFH_SCTRL_CERT_v1  — Security certificate header
GFH_TOOL_AUTH_v1   — Tool authorization structure
  m_version        — Auth file version
  m_secure_custom_name — Customer name (compared at runtime)
  m_description    — Auth description
```

### HWID Verification Chain

1. AUTH_Load → parse GFH headers → extract customer name + cert
2. DLM (DigitalLicenseManager) → contact license server → get HWID token
3. CompareAllBBChipHWID() → compare device HWID against token:
   - bbchip_name
   - HW version
   - SW version
   - HW code
   - DSP version
4. If bbchip_name is NULL → skip check (this is the most promising bypass — patch the name pointer to NULL)
5. SOC_Verification() → verify SOC integrity
6. If all pass → AUTH_IsReady returns TRUE → tool proceeds with FRP/DA operations

## FRP Reset Capabilities

Extracted from OctoplusFRP.exe strings. Each capability is a method pointer in the Delphi VCL:

### Samsung-Specific

| Capability Code | Description |
|----------------|-------------|
| `mcResetFRP` | Generic FRP reset (varies by model) |
| `mcResetFRPADB` | FRP reset via ADB shell commands |
| `mcResetFRPUserData` | Format userdata partition |
| `mcResetFRPsBoot` | FRP reset via signed boot image |
| `mcResetFRPUpload` | FRP reset via upload mode |
| `mcResetFRPsBootUpload_7Android` | Android 7+ signed boot + upload |
| `mcResetFRPQ9008` | Qualcomm EDL 9008 mode reset |
| `mcResetFRP_CscUsa` | USA carrier CSC FRP reset |
| `mcResetFRP_ModemA16` | Modem-based FRP unlock (A16 chipset) |
| `mcFactResFRPReact` | Factory reset + FRP reactivation lock |
| `mcResetKnoxSamsung` | Samsung Knox counter reset |

### Device Support

- 2136 Samsung models in SAM_ALL.db database
- 16744 models across 1227 vendors in OctFrpModelsDB.db
- Connection drivers per chipset: ExynosDM, MTKPort, QCDM, FirstSamsungUpdate

## Patch Scripts

Created at `/home/kubuntux/Downloads/RE/patches/`:

| Script | Target | Approach | Status |
|--------|--------|----------|--------|
| `dlm_patch.py` | DigitalLicenseManager.exe | String scan + offset location for SSL/ASN1 patch + license server URL | Stub — scans but doesn't write NOPs |
| `metacore_patch.py` | MetaCore.dll | String scan for CompareAllBBChipHWID, AUTH_IsReady, SOC_Verification | Stub — scans for xrefs but no byte modification |
| `dll_proxy_template.c` | VERSION.dll proxy | Complete proxy DLL with payload entry for runtime MetaCore patching | Compilable — full implementation |

Next step: implement actual byte patching in the Python scripts using the found offsets, or use the DLL proxy approach at runtime.

## Key Recommendations for License Bypass

1. **DNS redirect** `node.octoplusbox.cloud` + `node.octoplusbox.club` → local HTTPS server
2. **Patch MetaCore.dll** at offset 0x938274 (NOP the CompareAllBBChipHWID failure path)
3. **Registry pre-seed** HKLM\SOFTWARE\OCTOPLUS\ with dummy license entries
4. **Test in Windows VM** — real Windows needed for DLM dongle checks and SIM installer file copy
