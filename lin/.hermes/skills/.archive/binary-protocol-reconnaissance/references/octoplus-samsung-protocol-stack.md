# Real-World Example: Octoplus Samsung Protocol Suite

## Context

This is a documented case study of reverse-engineering the Octoplus Samsung software toolset to map its complete protocol stack. The analysis covered 18+ binaries totaling multiple GB.

## Key Discovery

The file described as "the device communication engine" (`rd.exe`, 298KB) was actually a **standalone ext4 partition manipulation utility** compiled from `D:\work\VS_Projects\Project1__lwext4\Work_ext4\main.cpp`. The actual device communication engine was distributed across multiple DLLs and a 135MB Qt GUI application.

## Directory Layout

```
app/
├── OctoplusSamsungNew.exe    ← MAIN ENGINE (135MB, Qt5 GUI + exploit orchestrator)
├── OctoplusSamsung.exe       ← Legacy GUI (245MB)
├── SamsungUpdater.exe        ← Update tool
├── SDB/sdb.exe               ← Samsung Development Bridge (custom ADB-like protocol)
├── rd.exe                    ← ext4 IMEI writer (NOT the comms engine)
├── libnv3p.dll               ← NVIDIA 3P protocol (ACK/NACK command/response)
├── libnvusbhost.dll          ← NVIDIA USB host (WinUSB + SetupAPI)
├── libnvflash.dll            ← NVIDIA flash operations
├── libnvboothost.dll         ← NVIDIA RCM boot protocol
├── libnvdioconverter.dll     ← DIO boot image converter
├── libnvaes_ref.dll          ← AES-CMAC for RCM signing
├── libnvapputil.dll          ← Utilities + comprehensive error codes
├── libnvos.dll               ← OS abstraction
├── libusb-1.0.dll            ← Generic USB (libusb)
├── AdbWinApi.dll             ← ADB transport
├── AdbWinUsbApi.dll          ← ADB WinUSB transport
├── 7z.dll                    ← Archive support
├── lz4.dll                   ← LZ4 compression
├── sqlite3.dll               ← SQLite
├── libeay32.dll              ← OpenSSL
├── SAM_ALL.db                ← 1000s of Samsung model names (SQLite)
├── SamsungModels.oct         ← Encrypted model config (OCTOPUS_v.1.0 header)
└── Drivers/                  ← USB drivers (FTDI, MTK, Samsung, Spreadtrum)
```

## Chipset Protocol Summary

### 1. Exynos (Samsung SoC)
- **Transport:** NVIDIA 3P via libnvusbhost.dll (WinUSB/SetupAPI)
- **Boot Protocol:** NVIDIA RCM via libnvboothost.dll
- **Flash Protocol:** NVIDIA Tegra flash via libnvflash.dll
- **Exploit Layer:** DWC3 USB 3.0 controller exploitation + CPDN (Compelson privileged agent)
- **Key Classes:** `ExynosRuntime::Dwc3::Dwc3ExploitState`, `ExynosRuntime::FinalFlow`, `OdinExploitWorker`

### 2. MediaTek
- **Transport:** libusb-1.0.dll (VID 0E8D)
- **Boot Protocol:** BROM (BootROM) exploit
- **Flash Protocol:** DA (Download Agent) with checksummed writes
- **Key Operations:** `sendPing`, `sendHaccLoader`, `readMem32`, `writeChecksumAndData`, `readPitAndWriteCrashGpt`

### 3. Qualcomm
- **Transport:** Serial/DIAG + custom USB
- **Boot Protocol:** EDL (Emergency Download Mode)
- **Flash Protocol:** Sahara streaming + Firehose XML commands
- **Loaders:** `QualcommLoaders/config.ini` + programmer ELF files

### 4. Spreadtrum/Unisoc
- **Transport:** Serial port (virtual COM)
- **Boot Protocol:** Test point → DIAG mode
- **Protocol:** `SerialExyDiagSender`, `SerialQlcDiagSender`, `DiagExyCommandBox`

## Protocol String Catalog

### USB Transport (libnvusbhost.dll)
```
WinUsb_GetDescriptor, WinUsb_AbortPipe, WinUsb_SetPipePolicy
WinUsb_WritePipe, WinUsb_ReadPipe, WinUsb_QueryPipe
WinUsb_QueryDeviceInformation, WinUsb_QueryInterfaceSettings
WinUsb_Free, WinUsb_Initialize
SetupDiEnumDeviceInterfaces, SetupDiGetDeviceInterfaceDetailA
"Make sure that the Nvidia recovery mode driver is installed on this system"
```

### 3P Protocol (libnv3p.dll)
```
Nv3pAck, Nv3pNack, Nv3pCommandComplete
Nv3pCommandReceive, Nv3pCommandSend
Nv3pDataReceive, Nv3pDataSend
Nv3pGetLastNackCode, Nv3pTransferFail
Nv3pTransportOpen, Nv3pTransportClose
Nv3pTransportSend, Nv3pTransportReceive
Nv3pTransportReopen
```

### RCM Boot (libnvboothost.dll)
```
NvBootHostCryptoEncryptSignBuffer
NvBootHostRcmCreateMsgFromBuffer
NvBootHostRcmCreateMsgFromFile
NvBootHostRcmCreateMsgFromFileHandle
NvBootHostRcmGetMsgBufferLength
NvBootHostRcmGetMsgLength
NvBootHostRcmGetMsgPayloadBuffer
NvBootHostRcmInitMsg
NvBootHostRcmSignMsg
"EncryptAndSign: begin encryption"
"EncryptAndSign: end encryption"
"EncryptAndSign: begin signing"
"EncryptAndSign: end signing"
"AES(key, nonce)"
```

### Tegra Flash (libnvflash.dll)
```
--setbct, --setbootdevconfig, --setbootdevtype
--odmdata, --sbk, --bct, --odm
--getbct, --getpartitiontable
--download, --delete_partition, --format_partition, --setboot
"master_boot_record", "extended_boot_record"
"boot_config_table", "bootloader", "partition_table"
"mobilelbanand", "muxonenand", "nand"
```

### Boot Image Converter (libnvdioconverter.dll)
```
"MSFLSH50"
"converting dio image: %s"
"BootBinFormatStoreSegmentHeader:"
"BootBinFormatStoreRecordHeader:"
"Segment type is %x", "Sectors is %x", "infoSize is %x"
```

### MTK BROM Protocol (from OctoplusSamsungNew.exe)
```
MtkDevice::daReadWrite readMem32 error
MtkDevice::writeChecksumAndData Error: write checksum
MtkDevice::writeChecksumAndData Error: wait 00000000 after writing [0x%1] at pos [0x%2]
MtkDevice::writeDataOnly Error: buffer write failed
MtkDevice::writeFlashData Error: buffer overrun
MtkLibUsb::MtkDevice sendHaccLoader failed
MtkLibUsb::MtkDevice sendHaccNvLoader failed
MtkLibUsb::MtkDevice sendPing failed
MtkLibUsb::MtkDevice readRpmbBlock failed
MtkLibUsb::MtkDevice writeRpmbBlock failed
```

### Exynos CPDN/Compelson Protocol
```
[CPDN] endSession(4) failed
[CPDN] findPitAddress failed
[CPDN] findV3Privdata failed
[CPDN] loadDevinfoLeakFromDevice failed
[CPDN] stealCdBufferList failed
[CPDN] FinalFlow failed
[CPDN] reinitialize failed
compelson.manufacturer=exynos
compelson.adbd=ready
compelson.decrypt.fstab=/%s
/compelson_root/data, /compelson_root/dev, /compelson_root/proc, /compelson_root/sys
```

### Error Code Enumerations (from libnvapputil.dll)
Comprehensive error catalog spanning USB, eMMC, NAND, UART, MIPI-HSI, AES crypto, bootloader, display, and I²C subsystems. Full list: ~120 error codes organized by hardware domain.

### USB Vendor IDs (from string context)
| VID | Vendor |
|-----|--------|
| 04E8 | Samsung |
| 05C6 | Qualcomm |
| 0E8D | MediaTek |

### Model Databases
- `SAM_ALL.db` (SQLite): 1000s of Samsung model numbers (GT-E*, GT-B*, GT-C*, GT-I*, SM-*, SPH-*)
- `SamsungModels.oct` (custom binary): `OCTOPUS_v.1.0` magic + encrypted payload

## Architecture Map

```
OctoplusSamsungNew.exe (Qt5 Orchestrator)
│
├── Model Layer
│   ├── General_Exynos → DWC3 + CPDN exploits
│   ├── General_MTK    → BROM/DA + libusb
│   ├── General_Qualcomm → EDL + DiagSender
│   └── General_Spreadtrum → Serial/Diag + Test Point
│
├── Worker Layer (Exynos Exploit Timeline)
│   ├── ReadCodesExploitExynos (patchModemProtection)
│   ├── ReadCodesExyUploadS20S21 (makeUploadTwist)
│   ├── ReadCodesExyUploadExtractSha256
│   ├── ReadCodesExyExploitWrite_RootRfs
│   └── RemovePleaseCallMeExynosEUB
│
├── Worker Layer (MTK Exploit Timeline)
│   ├── resetFrpBromExploit
│   ├── UnlockMtkBromExploit
│   ├── UnlockMtkJul2022
│   └── UnlockMtkJul2022Restore
│
├── Transport Layer
│   ├── libnv3p.dll + libnvusbhost.dll (Exynos USB)
│   ├── libusb-1.0.dll (MTK USB)
│   ├── AdbWinApi/UsbApi (ADB)
│   └── QSerialPort (Diag/Serial)
│
└── Low-Level
    ├── libnvflash.dll (flash commands)
    ├── libnvboothost.dll (RCM boot)
    ├── libnvdioconverter.dll (DIO convert)
    ├── libnvaes_ref.dll (AES-CMAC)
    ├── SDB/sdb.exe (Samsung FB)
    └── rd.exe (ext4 IMEI writer)
```

## Key Lessons

1. **The named file is rarely the complete story** — always survey the full directory.
2. **DLL filenames reveal chipset protocols** — `libnv*.dll` = NVIDIA/Exynos, `libusb` = MTK
3. **C++ mangled names expose exploit internals** — demangled `ExynosRuntime::FinalFlow::runWithArtifacts(...)` with 6+ lambda instantiations reveals complex exploit pipelines.
4. **Error code enumerations are protocol documentation** — `EmmcCommandFailed`, `NandReadFailed`, `UsbInvalidEndpoint` directly reveal hardware interfaces.
5. **Qt orchestrators are common** — many repair/exploit tools build on Qt5 for cross-platform GUI, with C++ worker classes implementing chipset-specific protocols.
