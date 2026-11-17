# Samsung USB Protocol Reverse Engineering — Session Notes

## Devices Tested
- SM-S921B (S24 Exynos 2400, OneUI 6.x / Android 14)
- SM-A546E (A54 Exynos 1380, A546EXXU5CXK3, OneUI 6.x / Android 14)

## Host Environment
- Linux 6.17.0-35-generic, pyusb 1.2.1, libusb 1.0.26, heimdall 1.4.2

## Download Mode Endpoint Discovery

Using pyusb endpoint dump on PID 685d (both devices identical):

### Configuration descriptor
```
bLength: 9
bDescriptorType: 2
wTotalLength: 67
bNumInterfaces: 2
bConfigurationValue: 1
iConfiguration: 0
bmAttributes: 0xC0 (Self-powered)
MaxPower: 100mA
```

### Interface 0 — CDC ACM (Control)
```
bInterfaceNumber: 0
bNumEndpoints: 1
bInterfaceClass: 0x02 (Communications)
bInterfaceSubClass: 0x02 (Abstract Control Model)
bInterfaceProtocol: 0x01 (AT-Commands / V.250 Modem)

Endpoint 0x82 IN Interrupt:
  wMaxPacketSize: 10
  bInterval: 8
  bmAttributes: 3 (Interrupt)
```

### Interface 1 — CDC Data (Bulk)
```
bInterfaceNumber: 1
bNumEndpoints: 2
bInterfaceClass: 0x0A (CDC Data)
bInterfaceSubClass: 0x00
bInterfaceProtocol: 0x00

Endpoint 0x81 IN Bulk:
  wMaxPacketSize: 512
  bInterval: 0
  bmAttributes: 2 (Bulk)

Endpoint 0x01 OUT Bulk:
  wMaxPacketSize: 512
  bInterval: 0
  bmAttributes: 2 (Bulk)
```

## Heimdall Protocol Analysis

Heimdall 1.4.2 protocol init sequence (from binary strings analysis):

1. **Claim Interface 0** — CDC ACM control
2. **SET_LINE_CODING** (0x21, 0x20) — 115200 baud, 8n1
3. **SET_CONTROL_LINE_STATE** (0x21, 0x22) — RTS=1, DTR=1
4. **Claim Interface 1** — CDC Data bulk
5. **Bulk OUT write** — Odin "begin session" packet (4 bytes command + 4 bytes flags + padding to 512)
6. **Bulk IN read** — Expect session setup response

Heimdall succeeds up to step 4, fails at step 5-6 with `LIBUSB_ERROR_TIMEOUT`.

## Odin Command Format Tested

All commands sent as `struct.pack('<II', command, flags)` + `\x00` * 504:

| Command | Name | Response |
|---------|------|----------|
| 0x01 | Platform info | Timeout |
| 0x03 | Begin download | Timeout |
| 0x64 | Read PIT | Timeout |

The bulk OUT write NEVER errors (USB stack accepts it). The bulk IN read ALWAYS times out after 5s. This means the device receives the request but either:
a) Doesn't recognize the command format and never sends a response
b) Requires a different framing or encryption layer

## Conclusion

The Samsung download protocol changed between the pre-2022 format (what heimdall 1.4.2 implements) and the post-2022 format (OneUI 6.x / Android 14+). The change likely involves:
- Different initial handshake packet structure
- Possible encrypted/authenticated command channel
- Possibly different endpoint allocation

Without access to a working Odin3 session with USB packet capture, the new protocol format cannot be reverse-engineered.
