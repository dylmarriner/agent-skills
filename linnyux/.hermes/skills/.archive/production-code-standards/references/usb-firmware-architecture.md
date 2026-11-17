# USB Firmware Architecture Reference

Language stack for USB device firmware projects, synthesized from user guidance.

## Language Choice

| Layer | Language | Why |
|-------|----------|-----|
| USB device firmware | C | Industry standard. LUFA, libopencm3, STM32 HAL. Vendor SDKs, max compatibility. |
| Desktop USB app | Rust | `serialport` for CDC ACM, `rusb` for vendor bulk. Cross-platform CLI. |
| Bootloaders/timing-critical | Assembly | Startup code, interrupts, context switching. Not the main language. |

### Recommended Designs

| Scenario | Firmware | PC Software | Assembly |
|----------|----------|-------------|----------|
| Max compatibility, lowest risk | C | Rust | Only startup |
| New project, well-supported MCU | Rust | Rust | Almost none |
| Existing vendor project | C | Rust | Where needed |

## USB Protocol Variants

| Approach | Rust Crate | Use Case |
|----------|-----------|----------|
| CDC ACM (virtual serial) | `serialport` | Commands, config, logs. Appears as `/dev/ttyACM0`, `COM3` |
| Vendor-specific bulk | `rusb` | Higher throughput, binary commands, firmware flashing, precise packet control |

## Composite Device Layout

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

## Command Frame Format

```
┌─────────┬─────────┬──────────┬────────────┬───────┐
│ Version │ Command │ Sequence │ Payload    │ CRC32 │
│ (1 byte)│ (1 byte)│ (2 bytes)│ (variable) │(4 bytes)
└─────────┴─────────┴──────────┴────────────┴───────┘
```

Payload format: CBOR (compact binary). Integrity: CRC32 per packet. Security: Signed commands where necessary. Updates: Signed A/B firmware.

## Blunt Answer

- C is the most universal firmware language
- Rust is better for new safety-conscious projects on supported MCUs
- Assembly is a specialist tool, not the default for the whole system
- Rust is excellent for the computer-to-device USB application
