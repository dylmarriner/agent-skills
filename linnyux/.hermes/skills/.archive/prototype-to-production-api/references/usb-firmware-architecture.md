# USB Firmware Architecture — Language & Protocol Decision Guide

## Language Choice: The Complete Picture

### Device Firmware

| Language | Domain | When to Use |
|----------|--------|-------------|
| **C** | Default firmware lang | Chip vendor supplies C SDK, maximum HW compatibility, STM32/PIC/AVR/ESP32/Nordic, mature tooling, other engineers maintain it |
| **Rust** | Modern alternative | New project on supported MCU (Embassy), memory safety matters, safer concurrency. NOT "less direct" than C. Ecosystem varies by chip. |
| **Assembly** | Specialist tool only | Startup code, interrupt entry/exit, bootloaders, timing-critical routines, tiny MCUs, context switching. NOT the default for the whole system. |

**Blunt rule:** Assembly for an entire firmware project is like building a house with tweezers.

### Computer-Side USB Application

Assembly makes no sense here. Good choices: Rust, C, C++, Python, C#, Go.

Rust is particularly good for: USB discovery (`rusb`), serial comms (`serialport`), binary protocols (CBOR, custom framing, CRC32), firmware updates (DFU), cross-platform CLI, safe response parsing.

### Recommended Configurations

| Scenario | Firmware | PC Software | Assembly |
|----------|----------|-------------|----------|
| Max compatibility, lowest risk | C | Rust | Only startup/low-level |
| New project, supported HW | Rust | Rust | Almost none |
| Existing vendor project | C | Rust | Only where needed |

## USB Protocol Choice

| Approach | Crate | Use Case |
|----------|-------|----------|
| CDC ACM (virtual serial) | `serialport` | Commands, config, logs, modest data. Appears as `/dev/ttyACM0`, `COM3`, `/dev/cu.usbmodem...` |
| Vendor-specific bulk | `rusb` | Higher throughput, binary commands, firmware flashing, large transfers, precise packet control |

**Basic control device:** Rust + CDC ACM + `serialport`
**Production hardware tool:** Rust + vendor USB bulk + `rusb`
**Firmware updates:** Rust desktop updater + USB DFU bootloader

## Recommended Program Structure

```
Rust desktop program
├── Device discovery
├── USB connection
├── Command protocol (CBOR framing + CRC32)
├── Firmware updater
└── Logging / diagnostics

Rust device firmware
├── USB device stack
├── Command parser
├── Hardware drivers
├── Bootloader
└── Signed firmware updates

Composite USB device
├── Interface 0: Vendor-specific bulk protocol (Bulk OUT 0x01, Bulk IN 0x81)
├── Interface 1: CDC ACM diagnostics (Serial IN 0x82, Serial OUT 0x02)
└── Interface 2: DFU (firmware updates)
```

## Command Frame Format

```
┌─────────┬─────────┬──────────┬────────────┬───────┐
│ Version │ Command │ Sequence │ Payload    │ CRC32 │
│ (1 byte)│ (1 byte)│ (2 bytes)│ (variable) │(4 bytes)
└─────────┴─────────┴──────────┴────────────┴───────┘
```

## Reference Code Snippets

### CDC ACM (serialport crate)
```rust
let mut port = serialport::new("/dev/ttyACM0", 115_200)
    .timeout(Duration::from_secs(1))
    .open()?;
port.write_all(b"GET_STATUS\n")?;
```

### Vendor Bulk (rusb crate)
```rust
let mut device = rusb::open_device_with_vid_pid(0x1234, 0x5678)
    .ok_or("USB device not found")?;
device.claim_interface(0)?;
device.write_bulk(0x01, &command, Duration::from_secs(1))?;
```

## Update System Requirements

- Cryptographic firmware signatures
- Version checking
- Rollback protection
- Recovery bootloader
- Power-loss-safe installation
- A/B firmware layout (where storage permits)
