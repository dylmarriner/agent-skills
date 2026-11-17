# Medusa Box / Octoplus JTAG — RE Reference

## Product Identity
- Medusa Box Software and Octoplus JTAG are sibling brands by GSMServer
- The same installer payload can ship under either name
- USB VID_025F&PID_0001 — custom vendor ID for the Medusa JTAG box

## Key Binaries

| File | Typical Size | Role |
|------|-------------|------|
| Medusa.exe | ~8.3 MB | Main GUI + business logic (VMProtect 2.x) |
| Updater.exe | ~7.8 MB | Update/activation/license check (VMProtect 2.x) |
| libmedusa.dll | ~235 KB | JTAG protocol library (VMProtect 2.x) |

## Protection
All three binaries are **VMProtect 2.x** packed. Evidence:
- Section names `.vmp0`/`.vmp1` (self-modifying, executable, writable)
- Entropy ~7.89
- Zero-length `.text` section
- Expected compile timestamps: 2020 (Medusa.exe: Oct 2020, Updater.exe: Sep 2020)

## Data Sources That Survive Packing

### 1. Medusa.ini (UTF-16)
This is the complete feature surface. Not obfuscated. Contains:
- All modes: EasyRepair, Advanced, Debug, ECC
- All UI strings (read/write/erase flash, IMEI repair, unlock codes, RepairCard)
- Error codes ERROR[007]-ERROR[046] with full descriptions
- Debug log strings DEBUG[000]-DEBUG[003]
- Emergency mode key combos for every supported phone family
- Support forum URLs: forum.gsmhosting.com, forum.gsmserver.com

### 2. Driver INF files → USB VID/PID
```
app/Driver/Box/Medusa.inf → VID_025F&PID_0001
```

### 3. libmedusa.dll exports (82 functions)
The DLL's export table survives VMProtect. Full JTAG API documented below.

## JTAG API (from libmedusa.dll)

### Core Operations
- `mdInit`, `mdOpen`, `mdClose` — session lifecycle
- `mdIrScan`, `mdIrScanEx` — Instruction Register scan
- `mdDrScan` — Data Register scan
- `mdJTAGTLR` — Test-Logic-Reset
- `mdJTAGRead`, `mdJTAGWrite`, `mdJTAGWriteRead` — raw JTAG I/O
- `mdSetSpeed`, `mdRTCKReactionTime` — clock speed control
- `mdSetTAPIrLen`, `mdGetTAPIrLen` — TAP IR length
- `mdShortTMSTableUsed`, `mdUseShortTMSTable` — TMS optimization

### TAP Management
- `mdTAPAdd`, `mdTAPAddHidden`, `mdTAPInsert` — chain config
- `mdGetTAPId`, `mdGetTargetTAPIndex` — identification
- `mdSelectTarget`, `mdCurrentTargetIndex` — multi-TAP selection

### ARM Core Debug (EmbeddedICE)
- `mdHalt`, `mdResume`, `mdResumeEx`, `mdStep`, `mdJStep`
- `mdReadReg`, `mdWriteReg`, `mdReadPC`, `mdWritePC`
- `mdReadMem`, `mdReadMemEx`, `mdWriteMem`, `mdWriteMemEx`
- `mdReadPhysMemEx`, `mdWritePhysMemEx` — bypass MMU
- `mdEnableDCC`, `mdReadDCC`, `mdWriteDCC`, `mdReadDCCStat`
- `mdSendDCC`, `mdRecvDCC` — Debug Communications Channel
- `mdReadEICEReg`, `mdWriteEICEReg`, `mdEICEVersion`

### ARM Co-Processor
- `mdArmMCR`, `mdArmMRC` — co-processor R/W
- `mdArm7ClockDataIn`, `mdArm7ClockOut`
- `mdArmJtagSetInstr`, `mdArmJtagAddDrOut`, `mdArmJtagFlush`

### Breakpoints
- `mdAddBreakpoint`, `mdRemoveBreakpoint`
- `mdAddWatchpoint`, `mdRemoveWatchpoint`
- `mdAddPoint`, `mdRemovePoint`, `mdEnumPoints`

### Flash & Target
- `mdSelectCore`, `mdSelectAp`
- `mdGetCoreId`, `mdGetTargetType`, `mdGetAdapterType`
- `mdGetAPIVersion`, `mdGetHWStatus`
- `mdReset`, `mdResetDelay`, `mdResetHalt`, `mdResetOnInit`, `mdSoftResetHalt`
- `mdSetReset`, `mdTRSTDelay`
- `mdSetFailCallback`, `mdSetLogFn`
- `mdTargetCreate`, `mdTargetSetSpecial`
- `mdAddWorkArea`, `mdArchState`
- `mdDebugRun`, `mdRunTest`
- `mdPoll`, `mdIsHalted`
- `mdUSBReset`, `mdUSleep`

## Supported Device Families (from help files)
Alcatel, Amoi, Asus, Cherry, Crius, Dell, Ever, FPT, Gigabyte, Haier,
HTC (~200 models: Desire/HD2/One/Diamond/Sensation/Wildfire/EVO/etc.),
Huawei (~60 models: E-series dongles, Android phones),
LG (~100 models: P/E/KU/SH/LU series, KP/KH),
Samsung (~300 models: SGH/GT/SCH/SHW/SPH series, bada/Android/WP),
Sony/Sony Ericsson, SKY (IM series), Pantech, Toshiba, Siemens,
Vodafone, ZTE, and more.
