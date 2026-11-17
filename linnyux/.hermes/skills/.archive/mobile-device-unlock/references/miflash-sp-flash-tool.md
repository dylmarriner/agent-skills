# SP Flash Tool & Mi Flash for MediaTek SLA Bypass

## When to Try

Dimensity 6080+ SLA blocks free mtkclient. Xiaomi's official Mi Flash tool has the SLA key in its auth/DA files and native DLLs. This reference covers using those tools on Linux.

## Mi Flash 20220507 Package Structure

Path: `MiFlash20220507/`

| Directory | Purpose |
|-----------|---------|
| `SP_Download_tool/` | SP Flash Tool (SP_download_tool.exe) + Authentication.dll |
| `da/` | Generic auth_sv5.auth + 14MB MTK_AllInOne_DA.bin |
| `mi/` | Xiaomi LoginPro, account_auth, cef browser |
| `Source/` | Google USB drivers, ADB, fastboot |
| `flash_all_lock.bat` | Batch script for full flash |

**Key files for SLA bypass:**
- `da/auth_sv5.auth` — generic auth file (MD5: 0191491e615d39792fca6579a2d24274)
- `da/MTK_AllInOne_DA.bin` — Download Agent (14MB, handles SLA auth)
- `SP_Download_tool/Authentication.dll` — exports sec_init_key, sec_auth_challenge, sec_hash, sec_verify

The firmware tgz (gold_global_images_V14.0.3.0.TNQMIXM_13.0/) contains its OWN auth_sv5.auth (MD5: 94e8fa9921b4450159d7e8bc2488d776) and a smaller MTK_AllInOne_DA.bin (746KB). The da/ versions are TOOL-GENERIC and the firmware versions are DEVICE-SPECIFIC. They differ starting at byte 1744 — different RSA keys.

## auth_sv5.auth Format

MMM\x01 container format:
```
[MMM\x01][4-byte LE size][8-byte type string][payload]
```

Two containers per file:
1. `FILE_INFO` — 56 bytes, device metadata
2. `MTK` — 2184 bytes, RSA key data (mostly zero-padded)

The MTK section stores the RSA key used by sec_init_key in Authentication.dll. The key data is sparse — most of the 2184 bytes are zeros with key material concentrated in specific regions.

## Wine Compatibility

**SP Flash Tool under Wine:** ❌ Does NOT work for raw MTK USB access.

SP_download_tool.exe launches under Wine, loads the scatter file, and reads the DA binary. It even reports "Loading Da OK!" — but then fails at "Download Fail!" because Wine cannot pass raw USB control/bulk transfers to the MT65xx Preloader (0e8d:2000). Wine's USB support is limited to WinUSB/COM-port emulation, which the MediaTek flashing protocol doesn't use.

**Result:** Need native Windows (VM or bare metal) to use SP Flash Tool for SLA bypass on MediaTek.

**Authentication.dll under Wine:** sec_init_key exports are accessible but extracting the key requires a compiled Windows binary calling these functions. mingw-w64 toolchain needed, not available on stock Ubuntu.

## Scatter File for FRP-Only Format

A minimal scatter file for SP Flash Tool format operations:

```
- general: MTK_PLATFORM_CFG
  info:
    - config_version: V1.1.2
    platform: MT6833
    project: gold
    storage: UFS

- partition_index: SYS0
  partition_name: frp
  file_name: NONE
  is_download: false
  type: NORMAL_ROM
  partition_size: 0x100000
  region: EMMC_USER
  operation_type: UPDATE
```

Command: `SP_download_tool.exe -scatter scatter.txt -format frp`

## SP Flash Tool CLI

```
SP_download_tool.exe -scatter <path> -format <partition_name>
SP_download_tool.exe -scatter <path> -download <partition_name>
```

The tool auto-loads auth_sv5.auth and MTK_AllInOne_DA.bin from the current working directory. No explicit --auth or --da flags exist in the 20220507 version.

## Pitfalls

- **Wine USB failure is silent**: SP Flash Tool says "Download Fail!" with no USB-level diagnostics. The actual error is that Wine's WinUSB layer can't enumerate or claim the MT65xx Preloader device.
- **Firmware auth ≠ tool auth**: Copying the firmware's auth_sv5.auth into SP_Download_tool/ will give a different key than the da/ version. Use the da/ version for SP Flash Tool, firmware version for custom tools.
- **Scatter file must match platform**: If the platform field doesn't match (e.g., MT6833 for Dimensity 6080), the tool may reject the scatter entirely or use wrong parameters.
