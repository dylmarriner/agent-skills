---
name: usb-firmware-development
description: USB device firmware and host-side application development. C for USB descriptors, Rust for host applications and device firmware, Assembly for bootloaders and timing-critical routines. CDC ACM virtual serial and vendor-specific bulk transfer protocols.
---

# USB Firmware Development

## Language Choice

### Device Firmware

| Language | Domain | When |
|----------|--------|------|
| **C** | Default firmware language | Vendor SDKs (STM32, PIC, AVR, ESP32, Nordic), maximum hardware compatibility, mature drivers/examples/debuggers, modifying existing firmware. LUFA, libopencm3, STM32 HAL for USB descriptors. |
| **Rust** | Modern alternative | New projects on well-supported MCUs, memory safety, safer concurrency. Embassy framework for async USB. Produces native machine code. Trade-off: ecosystem maturity varies by chip. |
| **Assembly** | Specialist tool only | Startup code, interrupt entry/exit, bootloaders, timing-critical routines, tiny MCUs, context switching. Not the default for the whole system. |

### Host-Side USB Application

Good choices: Rust, C, C++, Python, C#, Go. Assembly makes no sense here.

Rust is particularly good for:
- USB discovery (`rusb` / `libusb`)
- Serial communication (`serialport` crate)
- Binary protocols (CBOR, custom framing, CRC32)
- Firmware updates (DFU)
- Cross-platform CLI tools
- Safe parsing of device responses

### Recommended Designs

| Scenario | Firmware | Host Software | Assembly |
|----------|----------|---------------|----------|
| Maximum compatibility, lowest risk | **C** | **Rust** | Only startup/low-level |
| New project on well-supported hardware | **Rust** | **Rust** | Almost none |
| Existing vendor project | **C** | **Rust** | Only where needed |

### The Blunt Answer

- **C** is the most universal firmware language.
- **Rust** is often the better language for a new, safety-conscious firmware project.
- **Assembly** is a specialist tool, not the default for the whole system.
- **Rust** is an excellent choice for the computer-to-device USB application.

## USB Protocol Variants

| Approach | Crate | Use Case |
|----------|-------|----------|
| CDC ACM (virtual serial) | `serialport` | Commands, config, logs, modest data. Appears as `/dev/ttyACM0`, `COM3`, `/dev/cu.usbmodem...` |
| Vendor-specific bulk | `rusb` | Higher throughput, binary commands, firmware flashing, large transfers, precise packet control |

## Composite Device Layout

Recommended composite USB device for a production hardware tool:
```
USB Device
├── Interface 0: Vendor-specific bulk protocol
│   ├── Bulk OUT (EP 0x01): command packets
│   └── Bulk IN  (EP 0x81): response packets
├── Interface 1: CDC ACM diagnostics
│   ├── Serial IN  (EP 0x82): debug output
│   └── Serial OUT (EP 0x02): shell input
└── Interface 2: DFU (firmware updates)
    └── DFU endpoints for signed firmware flashing
```

## Command Frame Protocol

Use framed binary messages, not unstructured text:

```
┌─────────┬─────────┬──────────┬────────────┬───────┐
│ Version │ Command │ Sequence │ Payload    │ CRC32 │
│ (1 byte)│ (1 byte)│ (2 bytes)│ (variable) │(4 bytes)
└─────────┴─────────┴──────────┴────────────┴───────┘
```

CBOR is a good payload format. CRC32 per packet for integrity.

## Host-Side Rust Skeleton

**CDC ACM (serialport):**
```rust
use std::io::{Read, Write};
use std::time::Duration;
let mut port = serialport::new("/dev/ttyACM0", 115_200)
    .timeout(Duration::from_secs(1)).open()?;
port.write_all(b"GET_STATUS\n")?;
let mut buffer = [0u8; 256];
let count = port.read(&mut buffer)?;
```

**Vendor bulk (rusb):**
```rust
let mut device = rusb::open_device_with_vid_pid(0x1234, 0x5678)
    .ok_or("USB device not found")?;
device.claim_interface(0)?;
device.write_bulk(0x01, &command, Duration::from_secs(1))?;
let count = device.read_bulk(0x81, &mut response, Duration::from_secs(1))?;
```

## Update System

- Cryptographic firmware signatures
- Version checking
- Rollback protection
- Recovery bootloader
- Power-loss-safe installation
- A/B firmware layout (where storage permits)

## Mobile Platform Integration

- **Android**: Kotlin + `UsbManager` APIs. Vendor-specific bulk endpoints for main protocol, CDC ACM for diagnostics.
- **iPhone**: BLE for everyday control (USB restricted without MFi). Wi-Fi for high-bandwidth operations. MFi process required for direct USB access.

## Full Reference

See `docs/USB_FIRMWARE_ARCHITECTURE.md` in the project for the complete architecture document with detailed diagrams and examples.
