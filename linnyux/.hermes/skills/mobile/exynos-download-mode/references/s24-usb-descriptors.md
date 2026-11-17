# S24 SM-S921B USB Descriptors — Download Mode

Captured 2026-07-14 from `lsusb` + pyusb enumeration.

## Device Info
```
Bus 001 Device 027: ID 04e8:685d Samsung Electronics Co., Ltd GT-I9100 Phone [Galaxy S II] (Download mode)
Manufacturer string: garbled / empty
Product string: garbled / empty
```

Note: despite the `lsusb` label "Galaxy S II", this is the S24 SM-S921B. The `lsusb` USB ID database hasn't been updated for Exynos 2400 devices, so it falls back to the first Samsung download-mode entry (Galaxy S II). Ignore the label — PID 0x685D is the correct identifier for modern Exynos download mode.

## Configuration
```
bConfigurationValue = 1
bNumInterfaces = 2
```

## Interface 0 — CDC Communications (Control)
```
bInterfaceClass = 0x02  (CDC Communications)
bInterfaceSubClass = 0x02 (ACM — Abstract Control Model)
bInterfaceProtocol = 0x01 (AT-commands V.250)
bNumEndpoints = 1

Endpoint 0x82 IN
  bEndpointAddress = 0x82  (IN, endpoint 2)
  wMaxPacketSize = 10
  bmAttributes = 0x03  (Interrupt)
  bInterval = 10
```

This is NOT standard CDC ACM class (0x0A). It's Communications Device Class (0x02) with the ACM subclass. The interrupt endpoint is small (10 bytes) — used for control/status notifications, not Odin protocol data.

## Interface 1 — CDC Data (Bulk — Odin Protocol)
```
bInterfaceClass = 0x0A  (CDC Data)
bInterfaceSubClass = 0x00
bInterfaceProtocol = 0x00
bNumEndpoints = 2

Endpoint 0x81 IN
  bEndpointAddress = 0x81  (IN, endpoint 1)
  wMaxPacketSize = 512
  bmAttributes = 0x02  (Bulk)
  bInterval = 0

Endpoint 0x01 OUT
  bEndpointAddress = 0x01  (OUT, endpoint 1)
  wMaxPacketSize = 512
  bmAttributes = 0x02  (Bulk)
  bInterval = 0
```

512-byte max packet size confirms USB 2.0 high-speed (480 Mbps). Not USB 3.x (which would have 1024-byte packets).

## Kernel Driver State
```
Interface 0: driver = [none]
Interface 1: driver = [none]
```
No kernel driver claims either interface on this system. `cdc_acm` driver would normally bind interface 0, but the device is in download mode so it presents a different descriptor layout than normal mode.

## Protocol Session Log (First Run — Successful ODIN/LOKE)

```
[01:05:57] Found device: PID 0x685d bus=1 addr=27
[01:05:57] Interface[0] class=0x02 endpoints=1
[01:05:57] Interface[1] class=0x0a endpoints=2
[01:05:57] Found bulk interface[1]: IN=0x81 OUT=0x01
[01:05:57] Claimed interface 1
[01:05:57] Sending ODIN handshake...
[01:05:57] ODIN/LOKE handshake successful
[01:05:57] Beginning session...
[01:05:57] Device packet size: 100
[01:05:57] Device supports large packets, setting 1MiB...
[01:06:00] File part size response: 100
[01:06:00] Session begun
[01:06:00] Reading PIT...
[01:06:00] PIT file size: 101 bytes
[01:06:30] PIT read: 8 bytes
[01:06:30] ERROR: PIT data too short
```

## Protocol Session Log (Second Run — Stuck State Machine)

```
[01:08:24] Found device: PID 0x685d bus=1 addr=27  <-- same address!
[01:08:24] Claimed interface 1
[01:08:24] Sending ODIN handshake...
[01:08:25] DEBUG: Bulk read error: [Errno 110] Operation timed out
[01:08:25] ERROR: No handshake response
```

Device address didn't change despite `usbreset` and kernel unbind attempts. The download mode state machine on Exynos 2400 remains stuck in session mode after a partial session.

## Key Differences from Heimdall's Expected Protocol

| Aspect | Heimdall (older Exynos) | S24 (Exynos 2400) |
|--------|------------------------|-------------------|
| PIDs supported | 0x6601, 0x6850, 0x6810 | 0x685D |
| Interface 0 class | 0x0A CDC Data? | 0x02 CDC Communications |
| Interface 1 class | 0x0A CDC Data | 0x0A CDC Data |
| Max packet size | 64 (USB 1.1) | 512 (USB 2.0 HS) |
| Begin session response | 0 (no negotiation) | 100 (packet size) |
| PIT response size | ~2-8 KB | 101 bytes declared, 8 actual |
| State machine reset | USB reset works | Physical power cycle required |
