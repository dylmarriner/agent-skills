# USB Unlock Dongle Architecture

Applied from Universal Unlock Suite project docs. Composite USB device design.

## Language Choice — The Complete Framework

### For Device Firmware

| Language | Domain | Why |
|----------|--------|-----|
| **C** | Default firmware language | Vendor SDKs (STM32, PIC, AVR, ESP32, Nordic), maximum hardware compatibility, mature drivers/examples/debuggers/bootloaders, direct hardware access. Downside: memory corruption, buffer overruns. |
| **Rust** | Modern alternative | New projects on well-supported MCUs, memory safety, safer concurrency, register/interrupt/DMA/USB access. Produces native machine code — not "less direct" than C. Trade-off: ecosystem maturity varies by chip. |
| **Assembly** | Specialist tool only | Startup code, interrupt entry/exit, bootloaders, timing-critical routines, tiny MCUs, context switching, special CPU instructions. Not the default for the whole system. |

C is the safest practical choice when the chip vendor supplies a C SDK, you need maximum compatibility, or other engineers need to maintain it. Rust is good when starting a new project on supported hardware and memory safety matters. Assembly for an entire modern firmware project is unnecessary and painful.

### For the Computer-Side USB Application

Good choices: Rust, C, C++, Python, C#, Go. Rust is particularly good for:
- USB discovery (`rusb` / `libusb`)
- Serial communication (`serialport` crate)
- Binary protocols (CBOR, custom framing, CRC32)
- Firmware updates (DFU)
- Cross-platform CLI tools

### Recommended Designs

| Scenario | Firmware | PC Software | Assembly |
|----------|----------|-------------|----------|
| Maximum compatibility, lowest risk | **C** | **Rust** | Only startup/low-level |
| New project on well-supported hardware | **Rust** | **Rust** | Almost none |
| Existing vendor project | **C** | **Rust** | Only where needed |

### USB Protocol Variants

| Approach | Crate | Use Case |
|----------|-------|----------|
| CDC ACM (virtual serial) | `serialport` | Commands, config, logs, modest data. Appears as /dev/ttyACM0, COM3, /dev/cu.usbmodem |
| Vendor-specific bulk | `rusb` | Higher throughput, binary commands, firmware flashing, large transfers, precise packet control |

### Rut Desktop Skeleton — CDC ACM
```
use std::io::{Read, Write};
use std::time::Duration;
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut port = serialport::new("/dev/ttyACM0", 115_200)
        .timeout(Duration::from_secs(1)).open()?;
    port.write_all(b"GET_STATUS\n")?;
    let mut buffer = [0u8; 256];
    let count = port.read(&mut buffer)?;
    println!("{}", String::from_utf8_lossy(&buffer[..count]));
    Ok(())
}
```

### Rust Desktop Skeleton — Vendor Bulk
```
use std::time::Duration;
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut device = rusb::open_device_with_vid_pid(0x1234, 0x5678)
        .ok_or("USB device not found")?;
    device.claim_interface(0)?;
    let command = [0x01, 0x00, 0x00, 0x00];
    device.write_bulk(0x01, &command, Duration::from_secs(1))?;
    let mut response = [0u8; 64];
    let count = device.read_bulk(0x81, &mut response, Duration::from_secs(1))?;
    println!("Response: {:02X?}", &response[..count]);
    Ok(())
}
```

### The Blunt Answer

- **C is the most universal firmware language.**
- **Rust is often the better language for a new, safety-conscious firmware project.**
- **Assembly is a specialist tool, not the default for the whole system.**
- **Rust is an excellent choice for the computer-to-device USB application.**

## Target Hardware

- MCU: STM32, RP2040, nRF52840, or ESP32-S3
- Firmware: C (LUFA, libopencm3, STM32 HAL, TinyUSB)
- Bootloader: Assembly (timing-critical entry)

## Composite USB Device

```
USB Device
├── Interface 0: Vendor-specific bulk protocol
│   ├── Bulk OUT (EP 0x01): command packets
│   └── Bulk IN  (EP 0x81): response packets
├── Interface 1: CDC ACM diagnostics
│   ├── Serial IN  (EP 0x82): debug output
│   └── Serial OUT (EP 0x02): shell input
└── Interface 2: DFU (firmware updates)
    └── Signed firmware flashing
```

## Command Protocol

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0      | 1    | Version | Protocol version |
| 1      | 1    | Command | Opcode |
| 2      | 2    | Sequence | Request/response pairing |
| 4      | var  | Payload | CBOR-encoded data |
| end-4  | 4    | CRC32 | Integrity check |

Example commands: GET_STATUS, SET_MODE, UNLOCK, READ_PARTITION, ENTER_BOOTLOADER.

## Platform Integration

- **Android**: Kotlin + UsbManager (vendor-specific bulk endpoints)
- **iPhone**: BLE + Wi-Fi (USB restricted without MFi)
- **Desktop**: Rust/Python + libusb

## Firmware Update

- Signed images (crypto signature per release)
- Version checking + anti-rollback
- Recovery bootloader partition
- A/B slot layout
- Power-loss-safe: complete slot verification before marking active
