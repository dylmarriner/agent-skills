---
name: usb-firmware-flashing
description: Flash firmware to USB-connected devices on Linux — identify the device, understand the protocol, obtain firmware, and apply it via native tools, Wine, libusb, or the device's official update path.
trigger: user asks to flash, update, or upgrade firmware on a USB-connected hardware device (radar detector, dash cam, IoT gadget, etc.)
---

# USB Firmware Flashing on Linux

Flash firmware to a USB-connected device. The approach depends on how the device communicates (serial, HID, bulk) and how the vendor distributes firmware (standalone file, tools app, cloud API).

## Phase 1: Identify the Device

1. **Find it** — `lsusb` to list all USB devices. Look for your vendor name or a recognizable product string.
2. **Get USB details** — `sudo lsusb -v -d <VID:PID>` (or without sudo if world-readable) to see:
   - Interface class (vendor-specific = custom protocol, CDC ACM = serial, HID = human interface)
   - Endpoint types (bulk, interrupt, isochronous)
   - Max packet sizes
3. **Check for serial port** — `ls -la /dev/ttyUSB* /dev/ttyACM*` — if the device appears here, it uses a standard serial protocol
4. **Check for kernel driver** — `lsmod | grep <driver>` — some devices need `usbserial`, `cdc_acm`, or a vendor-specific kernel module

## Phase 2: Understand the Protocol

- **Standard serial (ttyUSB/ttyACM)**: Use `screen`, `minicom`, or `picocom` to connect. Try AT commands or standard firmware update protocols (XMODEM, YMODEM, DFU)
- **WinUSB / vendor bulk**: The device uses bulk endpoints (like our Escort example). `libusb` is the tool. Write a Python/pyusb probe script to read endpoints
- **HID**: Use `hidapi` or Python `hid` library
- **DFU (Device Firmware Update)**: Try `dfu-util`
- **Mass storage**: Some devices mount as a USB drive — just copy the firmware `.bin` file to it

**To identify Windows driver model** (if it's a Windows-only device):
- Check `.inf` files in the vendor's software installer (extract with `7z` or Wine)
- `WinUSB` driver = `libusb` compatible
- `usbser.sys` = standard serial
- Custom driver = reverse-engineering needed

## Phase 3: Obtain the Firmware

| Source | How to get it |
|--------|---------------|
| Vendor website | Check support/downloads page for firmware files or update tool |
| Software installer | Extract with `7z` or run via Wine, search for `.fw`, `.bin`, `.hex`, `.s19` files |
| Update tool that downloads it | Intercept network traffic or decompile the .NET app (see below) |
| Mobile app OTA | Some devices (e.g. Escort MAX 360c) update over Bluetooth/WiFi via a companion app |
| Reverse-engineer | SOAP/REST API calls from the vendor's app may reveal download URLs |

**If the firmware is delivered through an app:**
1. Check if the app is a .NET assembly — `strings` on the exe will show web service URLs
2. Try probing the web service — ASMX endpoints accept SOAP POST requests
3. Look for product IDs or device type identifiers in the binary's strings
4. If the API is authenticated, you'll need to decompile the app (mono, ILSpy, dnSpy) to find the auth mechanism

## Phase 4: Apply the Firmware

### Via Wine (if vendor provides a Windows tool)

1. **Install Wine** — `wine --version` (winehq-stable recommended)
2. **Install the vendor tool** — `wine setup.exe /VERYSILENT /DIR=C:\\tools`
3. **Make USB device accessible** — `sudo chmod 666 /dev/bus/usb/XXX/YYY`
4. **Handle Device Detection** — If the app uses WinUSB, it won't see the device through Wine's SetupAPI. Workarounds:
   - Add registry entries under `HKEY_LOCAL_MACHINE\System\CurrentControlSet\Enum\USB\VID_XXXX&PID_YYYY\` (may not help — Wine doesn't implement WinUSB kernel driver)
   - Run under a Windows VM with USB passthrough (reliable)
   - Dual-boot Windows (guaranteed)
5. **Run with virtual display** — `Xvfb :99 -screen 0 1024x768x24 & DISPLAY=:99 wine tool.exe`

### Via libusb (native Linux tool)

Only viable if you know (or can reverse-engineer) the USB protocol.

1. Install pyusb: `pip3 install --user --break-system-packages pyusb`
2. Probe the device — send/receive on bulk endpoints to discover commands
3. Reverse-engineer protocol from the vendor's .NET app or Windows driver captures
4. Write a Python script to read firmware file and push it via bulk transfers

### Via the device's own OTA mechanism

Some devices (WiFi/Bluetooth-capable) can update from a mobile companion app. This is often the path of least resistance.

## Developing USB Firmware (for unlock dongles / USB accessories)

When writing firmware for a USB device (unlock dongle, hardware debug tool, etc.):

### Language Choices

| Layer | Language | Why |
|-------|----------|-----|
| USB device firmware | **C** | Industry standard. LUFA, libopencm3, STM32 HAL. Direct memory mapping, bitwise ops for USB descriptors. Modify VID/PID, craft custom HID payloads. |
| Bootloaders / timing-critical | **Assembly** | Bit-banging, processor-specific init, minimal C overhead. |
| Desktop utilities | **Rust or Python** | libusb bindings, CBOR framing, high-level protocol logic. |

C is the backbone of USB device controllers. Assembly handles the edge cases (timing-critical bit-banging, bootloader entry where C overhead is too slow).

### Recommended Composite USB Device Layout

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

### Command Protocol Format

Use framed binary messages, not unstructured text. CBOR is a good payload format.

```
┌─────────┬─────────┬──────────┬────────────┬───────┐
│ Version │ Command │ Sequence │ Payload    │ CRC32 │
│ (1 byte)│ (1 byte)│ (2 bytes)│ (variable) │(4 bytes)
└─────────┴─────────┴──────────┴────────────┴───────┘
```

### USB Class Stacks

- **LUFA** (C, AVR): Mature, well-documented, good for ATmega32U4 / AT90USB
- **libopencm3** (C, ARM): STM32, open-source USB peripheral driver
- **STM32 HAL** (C, ARM): Vendor USB device library, comprehensive but heavy
- **TinyUSB** (C, multi-platform): Modern, supports many MCUs, good DFU support

### Android Integration

Kotlin + `UsbManager` APIs: match VID/PID, request permission, claim interface, bulk IN/OUT via vendor-specific endpoints.

### iPhone Integration

USB-C on iPhone does NOT give unrestricted raw USB access. MFi process required for direct USB. For iPhone, use BLE for everyday control and Wi-Fi for high-bandwidth operations.

### Updates

- Cryptographic firmware signatures
- Version checking + rollback protection
- Recovery bootloader
- Power-loss-safe installation
- A/B firmware layout (where storage permits)

## Common Pitfalls

- **USB device node permissions** — `/dev/bus/usb/` nodes are owned by root. Set a udev rule: `SUBSYSTEM=="usb", ATTR{idVendor}=="XXXX", ATTR{idProduct}=="YYYY", MODE="0666"`
- **Wine cannot use WinUSB devices** — WinUSB is a kernel driver that Wine doesn't implement. Even if the app runs, it won't see the device. A Windows VM or dual-boot is the reliable path
- **Firmware is not a standalone file** — many modern devices download firmware dynamically from an authenticated web API. You need to capture the app's network traffic or decompile it
- **Device re-enumerates during firmware update** — some devices switch VID/PID after entering bootloader mode. Watch with `lsusb` in a loop
- **Bricking risk** — firmware update protocols often have device-specific bootloader modes. Interrupting a flash can brick the device. Prefer the official tool path where possible

## References

See `references/` for per-device protocol details and session logs.
- **[references/usb-unlock-dongle-arch.md](references/usb-unlock-dongle-arch.md)** — Composite USB unlock dongle architecture (C firmware, CBOR protocol, DFU updates)
