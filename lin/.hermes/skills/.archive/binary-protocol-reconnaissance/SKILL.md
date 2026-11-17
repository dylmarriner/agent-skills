---
name: binary-protocol-reconnaissance
description: Extract protocol information, device identification patterns, and communication layer architecture from binaries via systematic strings analysis. Covers cross-referencing DLL exports/imports across a software suite, identifying chipset-specific protocols, USB/device enumeration logic, and building layered architecture maps — all from static string artifacts.
---

# Binary Protocol Reconnaissance

Extract USB/device communication protocols, command/response formats, and chipset-specific protocol implementations from binary executables and DLLs using systematic strings analysis. This is the first pass before dynamic analysis — it maps the protocol surface area.

## Core Principle: Analyze the Suite, Not Just the File

When told a specific binary is "the device communication engine" (e.g., `rd.exe`), **do NOT analyze it in isolation.** The named file may be a small utility in a larger toolchain. Always survey the entire directory for companion binaries:

```bash
ls -la <directory>/
file <directory>/*.exe <directory>/*.dll
```

Identify:
- Qt/GUI applications (large EXEs) — these are typically the orchestrators
- DLLs with chipset/vendor names in their filenames (e.g., `libnvflash.dll`, `libnvusbhost.dll`)
- Transport/DLLs (e.g., `libusb-1.0.dll`, `AdbWinApi.dll`)
- Database files (`.db`, `.oct` models)
- Command-line tools (smaller EXEs for specific operations)

## Phase 1: Systematic Strings Extraction

### Per-Binary String Dump
Get ALL strings with file offsets from every relevant binary:

```bash
# All strings with hex offsets, numeric sort
strings -a -t x <binary>.exe | sort -k1 -n

# Save to file for later searching
strings -a -t x <binary>.exe > <binary>_strings.txt
```

### Targeted Protocol Searches
Search across ALL binaries simultaneously — do not assume a protocol lives in one binary:

```bash
# Search all EXEs + DLLs in directory
for f in *.exe *.dll; do
    strings -a "$f" | grep -iE '(pattern1|pattern2|pattern3)' | while read line; do
        echo "  [$f] $line"
    done
done

# Key search categories (run in parallel):
strings <all-binaries> | grep -iE '(usb|vid|pid|device|interface|descriptor)'
strings <all-binaries> | grep -iE '(chipset|samsung|exynos|qualcomm|mtk|nvidia|tegra)'
strings <all-binaries> | grep -iE '(boot|download|protocol|cmd|opcode|frame|packet|sync|ack|nack)'
strings <all-binaries> | grep -iE '(error|failed|success|timeout|status|version)'
strings <all-binaries> | grep -iE '(serial|com[0-9]|baud|tty|acm|diag)'
```

### Count String Hits per Binary
Identify which binary contains the most protocol strings:

```bash
for f in *.exe *.dll; do
    count=$(strings -a "$f" 2>/dev/null | grep -ciE '(protocol|chipset|pattern)')
    echo "$count $f"
done | sort -rn
```

## Phase 2: DLL Export/Import Cross-Referencing

### Extract Exported Function Names
DLL exports reveal the API surface of each protocol layer:

```bash
# Use strings filtered for known export patterns
strings -a <binary>.dll | grep -E '^[A-Z][a-z]+[A-Z]' | grep -E '(^Nv[A-Z]|^Adb[A-Z]|^libusb_)'
```

### Build Layer Dependency Graph
Map which DLLs depend on which others by looking at import references:

```bash
for dll in *.dll; do
    echo "=== $dll imports ==="
    strings -a "$dll" | grep -i 'lib.*\.dll'
done
```

### Identify Naming Conventions
Protocol layers follow predictable naming:
- `Nv*` → NVIDIA Tegra related (e.g., `Nv3p*`, `NvBoot*`, `NvFlash*`, `NvUsb*`)
- `Adb*` → ADB transport (e.g., `AdbEndpointObject`, `AdbInterfaceObject`)
- `Mtk*` → MediaTek (e.g., `MtkDevice`, `MtkLibUsb`)
- `WinUsb_*` → Windows USB API
- `SetupDi*` → Windows device enumeration

## Phase 3: USB/Device Enumeration Analysis

### Identify USB Transport Stack
Look for Windows USB API usage:

| API String | Meaning |
|------------|---------|
| `SetupDiEnumDeviceInterfaces` | Device enumeration via SetupAPI |
| `WinUsb_Initialize` | WinUSB device initialization |
| `WinUsb_ReadPipe` / `WinUsb_WritePipe` | Bulk transfer |
| `WinUsb_GetDescriptor` | Descriptor retrieval |
| `libusb_init` / `libusb_open` | libusb-based transport |
| `CreateFileW` + `DeviceIoControl` | Legacy driver I/O |

### Extract USB VID/PID References
USB Vendor/Product IDs may appear as hex strings or as part of INF/driver references:

```bash
# Known USB vendor IDs
strings *.exe *.dll | grep -iE '(04e8|05c6|0e8d|0a5c|18d1|2717|10c4)'
# 04E8 = Samsung, 05C6 = Qualcomm, 0E8D = MediaTek, 18D1 = Google/ADB
```

### Find Driver Install Requirements
User-facing driver instructions reveal expected USB modes:

```bash
strings OctoplusSamsung*.exe | grep -iE '(driver|install|usb.*driver|com port|test point|brom mode|download mode)'
```

## Phase 4: Chipset Protocol Identification

### Protocol Keywords by Chipset

| Chipset | Search Keywords | Expected Protocols |
|---------|----------------|-------------------|
| **Exynos** (Samsung) | `exynos`, `odin`, `cpdn`, `compelson`, `dwc3`, `pit`, `sboot`, `sbl`, `appsbl` | ODIN download mode, CPDN (Compelson), DWC3 USB 3.0 exploits |
| **NVIDIA Tegra** | `nvflash`, `nvboot`, `nv3p`, `rcm`, `tegra`, `bct`, `sbk` | RCM recovery, 3P command/response, BCT boot config table |
| **MediaTek** | `mtk`, `brom`, `preloader`, `da`, `scatter`, `hacc`, `rpmb` | BROM/DA protocol, HACC encrypted loader, scatter-based flashing |
| **Qualcomm** | `qualcomm`, `edl`, `sahara`, `firehose`, `qdloader`, `qhsusb`, `9008` | EDL emergency download, Sahara streaming protocol, Firehose XML |
| **Spreadtrum** | `spreadtrum`, `sprd`, `sc[0-9]`, `sharkl`, `ums`, `diag` | Serial/DIAG protocol, test point mode |
| **Broadcom** | `broadcom`, `bcm` | Vendor-specific |

### Protocol-Specific String Patterns
Look for these in strings output:

```bash
# ACK/NACK protocol
grep -iE '(nv3p|ack|nack|packet.*nack|command.*send|command.*receive|data.*send|data.*receive)'

# Boot protocol handshake
grep -iE '(rcm|boot.*msg|sign.*msg|encrypt.*sign|boot.*host)'

# Flash commands
grep -iE '(--download|--setboot|--getbct|--getpartitiontable|--format_partition|--sbk|--odmdata)'

# Partition types
grep -iE '(boot_config_table|extended_boot_record|master_boot_record|partition_table|bootloader|nand|emmc)'

# Exploit state machines
grep -iE '(ExploitState|FinalFlow|StartPrefix|IExploitMemoryAccess|IByteStream)'
```

## Phase 5: Command/Response Protocol Mapping

### Identify Command Strings
Protocol commands often appear as:
- Short strings with namespaced prefixes: `Nv3p*`, `Mtk*`, `Diag*`
- Method/function class names in C++ mangled symbols: `N13ExynosRuntime4Cpdn12ExploitStateE`
- Error messages with format specifiers: `writeChecksumAndData Error: wait %08x after writing [0x%1]`
- Help text: `--download`, `--setboot`, `--odmdata`

### Decode C++ Mangled Names
Demangle to get full class hierarchy and function names:

```bash
# The itanium demangler can decode MSVC-style names too
python3 -c "
import re, subprocess
with open('strings_output.txt') as f:
    for line in f:
        if line.startswith('?'):
            # MSVC mangled names
            print(line.strip())
        elif line.startswith('_Z') or line.startswith('_ZN'):
            # Itanium mangled names
            try:
                result = subprocess.run(['c++filt', line.strip()], capture_output=True, text=True)
                print(result.stdout.strip())
            except:
                pass
"
```

### Identify Protocol State Machine
Look for:
- `*State` class names → state machine stages
- `*Worker` class names → worker threads
- `*Failed` / `*Error` / `*Success` → status codes
- Version strings: `Jul2022`, `Aug2022`, `S20S21` → exploit version targeting

## Phase 6: Error Code Database Extraction

Error code enumerations are a goldmine for protocol understanding. Look for contiguous groups of error strings:

```bash
strings -a -t x library.dll | sort -k1 -n | grep -E '(Failed|Error|Success|Timeout|Invalid|NotFound|Busy|NotSupported|Bad)'
```

Typical error categories found in protocol stacks:
| Category | Examples |
|----------|----------|
| USB transport | `UsbInvalidEndpoint`, `UsbfTxfrFail`, `UsbfEpStalled`, `UsbfCableDisConnected` |
| MIPI/HSI | `MipiHsiBusy`, `MipiHsiTransmitError`, `MipiHsiRxFifoEmpty` |
| eMMC/NAND | `EmmcCommandFailed`, `NandReadFailed`, `NandBlockIsLocked` |
| Bootloader | `BLServerConnectionFailed`, `BLServerInvalidElfFile`, `BLServerMemoryLimitExceeded` |
| 3P Protocol | `Nv3pBadReceiveLength`, `Nv3pPacketNacked`, `Nv3pUnrecoverableProtocol` |
| AES/Crypto | `AesClearSbkFailed`, `AesKeyUnWrapFailed`, `AesPermissionDenied` |
| UART/Serial | `UartOverrun`, `UartParity`, `UartFraming`, `UartBreakReceived` |
| Storage | `BlockDriverIllegalPartId`, `BlockDriverWriteVerifyFailed` |

## Phase 7: Architecture Map Construction

Build a layered communication stack map:

```
┌─────────────────────────────────────────────┐
│           Orchestrator (main EXE)            │
│  (Qt GUI, worker classes, exploit logic)     │
├─────────────────────────────────────────────┤
│  Protocol/Chipset Layer                      │
│  ├─ ExynosRuntime::Dwc3 (DWC3 USB exploit)  │
│  ├─ MtkLibUsb::MtkDevice (BROM/DA protocol) │
│  ├─ QualcommLoader (EDL/Sahara protocol)    │
│  └─ SerialPort/DiagSender (SPRD DIAG)       │
├─────────────────────────────────────────────┤
│  Transport Layer                             │
│  ├─ libnv3p.dll (NVIDIA 3P ACK/NACK)        │
│  ├─ libusb-1.0.dll (generic USB)            │
│  ├─ AdbWinApi.dll (ADB)                     │
│  └─ WinUSB/SetupAPI (native Windows USB)    │
├─────────────────────────────────────────────┤
│  Low-Level / Boot Protocol                   │
│  ├─ libnvboothost.dll (RCM boot)            │
│  ├─ libnvflash.dll (Tegra flash commands)   │
│  └─ libnvdioconverter.dll (DIO boot img)    │
└─────────────────────────────────────────────┘
```

### Identify the Actual Purpose of Each Binary
Cross-check against source code paths found in strings:

```bash
strings *.exe *.dll | grep -E '^[A-Z]:\\\\(work|src|dev|home|projects)\\\\'
```

These reveal the original project structure and prove whether a binary is part of a larger suite.

## Phase 8: Database & Configuration Analysis

### Model/Device Databases
```bash
file *.db *.oct
# SQLite databases can be dumped directly:
sqlite3 models.db ".tables"
sqlite3 models.db "SELECT * FROM models LIMIT 5;"
```

### Proprietary Binary Formats
```bash
# Check for magic headers
for f in *.oct *.dat; do
    magic=$(xxd "$f" | head -1 | awk '{print $2,$3,$4}')
    echo "$f: $magic"
done
```

## Common Pitfalls

- **Not checking companion files** — `rd.exe` was described as the device engine but was actually an ext4 partition utility. Always survey the entire directory first.
- **Stopping at the named file** — The main protocol logic lives in the GUI app and DLLs, not in small command-line tools.
- **Missing DLL dependencies** — A DLL that exports `Nv3pCommandSend` depends on `libnvusbhost.dll` for transport and `libnvos.dll` for OS primitives. Trace the full dependency chain.
- **Ignoring C++ mangled names** — Demangled C++ symbols reveal class hierarchies, namespace structure, and inheritance that plain strings miss. `ExynosRuntime::Dwc3::Dwc3ExploitState` is far more informative than `dwc3_exploit_state`.
- **Treating all strings as equal** — Prioritize strings that form a protocol vocabulary (exported function names, class names, error enums, format-argument strings) over generic Boost/MSVC CRT strings.
- **Assuming one protocol per chipset** — Samsung Exynos devices use FOUR different protocol paths: ADB (normal mode), ODIN (download mode), DWC3 exploit (USB 3.0), and Compelson (privileged operations).
- **Not searching for USB VID/PID as hex** — `0E8D` won't be caught by a search for `MediaTek` or `MTK`. Search hex vendor IDs directly.
- **Missing error code enums** — Large contiguous blocks of error strings (e.g., 100+ entries in `libnvapputil.dll`) contain hardware-level protocol details. These are easy to skip but critical for understanding transport failures.
