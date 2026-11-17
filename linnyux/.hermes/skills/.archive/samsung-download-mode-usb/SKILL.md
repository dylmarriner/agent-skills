---
name: samsung-download-mode-usb
description: "USB endpoint layout, pyusb communication, and Odin/heimdall protocol behavior for post-2022 Samsung devices in download mode (S24, A54, Exynos). Covers endpoint detection fixes, CDC ACM init, and protocol reverse-engineering gaps."
version: 1.0.0
author: agent
tags: [samsung, usb, pyusb, odin, heimdall, download-mode, endpoint]
---

# Samsung Download Mode USB Protocol

## When to use
- Device is detected in download mode (PID 0x685d) but heimdall fails
- You need to write or fix pyusb code for Samsung download mode communication
- You're trying to debug why bulk writes/reads aren't working on a post-2022 Samsung

## USB Endpoint Layout

Post-2022 Samsung devices in download mode (S24 SM-S921B, A54 SM-A546E):

| Interface | Class/Sub/Proto | Endpoints | Purpose |
|-----------|-----------------|-----------|---------|
| 0 | CDC ACM (0x02/0x02/0x01) | EP 0x82 IN (interrupt, 10B) | AT command / modem control |
| 1 | CDC Data (0x0A/0x00/0x00) | EP 0x01 OUT (bulk, 512B), EP 0x81 IN (bulk, 512B) | Odin protocol data |

## Correct PyUSB Endpoint Detection

```python
import usb.core, usb.util

dev = usb.core.find(idVendor=0x04E8, idProduct=0x685D)
if dev is None:
    raise RuntimeError("Device not found in download mode")

# Detach kernel drivers
for iface in [0, 1]:
    try:
        if dev.is_kernel_driver_active(iface):
            dev.detach_kernel_driver(iface)
    except:
        pass

dev.set_configuration()
cfg = dev.get_active_configuration()

# Interface 1 = bulk data (NOT interface 0!)
intf = cfg[(1, 0)]
ep_out = usb.util.find_descriptor(intf, custom_match=lambda e:
    usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
ep_in = usb.util.find_descriptor(intf, custom_match=lambda e:
    usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)

if ep_out is None or ep_in is None:
    raise RuntimeError("Failed to find bulk endpoints on interface 1")
```

**Critical:** Use `cfg[(1, 0)]` NOT `cfg[(0, 0)]`. Interface 0 has no bulk OUT endpoint — trying to use it returns None and causes `'NoneType' object cannot be interpreted as an integer`.

## CDC ACM Init in Download Mode

```python
# SET_LINE_CODING — will fail with EPIPE (expected in download mode)
try:
    line_coding = struct.pack('<IBBBB', 115200, 0, 0, 8, 0)
    dev.ctrl_transfer(0x21, 0x20, 0, 0, line_coding, timeout=5000)
except:
    pass  # EPIPE is normal here

# SET_CONTROL_LINE_STATE — succeeds
dev.ctrl_transfer(0x21, 0x22, 0x3, 0, None, timeout=5000)
```

## Heimdall Behavior on Post-2022 Devices

### What succeeds
- Device detection (finds VID:PID)
- Interface claiming
- Protocol initialisation (control handshake)
- CDC ACM init

### What fails
```
Beginning session...
ERROR: libusb error -7 whilst sending bulk transfer.
ERROR: Failed to begin session!
```
**Root cause:** The Odin protocol command format changed. Heimdall 1.4.2 (2017) sends the old `<II>` format which the new bootloader ignores.

### Old Odin Format (broken on post-2022)
```python
# 4-byte command + 4-byte length + 504 bytes padding = 512 total
packet = struct.pack('<II', 0x64, 0x00) + b'\x00' * 504
ep_out.write(packet, 5000)  # Write succeeds silently
data = ep_in.read(1024, 5000)  # Read times out — no response
```

## Tools That Actually Work

| Tool | Platform | Notes |
|------|----------|-------|
| samloader-rs (topjohnwu) | Rust, any OS | **THE reference.** Full Odin stack for post-2022: ODIN/LOKE + ZLP framing, begin-session v2 negotiation, PIT, flash, LZ4. Release binaries on GitHub. Also downloads/decrypts firmware from FUS (v1 samloader's BinaryInform is dead — 401; Inform2 in samloader-rs works). |
| Odin3 v3.14.4+ | Windows | Gold standard for post-2022 |
| SamFW FRP Tool | Windows | Free, works on S24/A54 |
| jodin3 | Linux/Mac | Wraps heimdall — same limitation |

## S24 Protocol Diffs vs Heimdall 1.4.2 (from samloader-rs source, verified 2026-08-28)

1. **ZLP after every control packet** (`EmptySendKind::After`) — zero-length bulk OUT
   after each 1024B request. Heimdall never sends these → S24 ignores the request → bulk
   read timeout. This is THE root cause.
2. **ZLP BEFORE** sequence start/end packets and before every file part except part 0
   (`EmptySendKind::BeforeAndAfter` in send_one_sequence).
3. **Begin session payload**: `[0x64, 0, 0x05]` (protocol_version=5 at offset 8). Old code
   sent 0 → bootloader treated it as v1. Response VALUE = (proto_ver << 16) | flags;
   flags bit 0x8000 = LZ4 supported. v2+ → negotiate part size (0x64,5,1048576), expect 0.
4. **Part responses**: (0x00, part_index) 8-byte responses during file transfer.
5. **Sequence framing**: ≤30 MiB per sequence (30 × 1 MiB parts), sequence end timeout 120s.
6. **End packet fields**: [0x66, 4=phone|5=modem, seq_len, binary_type(0=AP,1=CP),
   device_type(2=MMC), partition_id, is_last]. Old code sent device_type as the
   AP/BL/CP/CSC group constant — wrong; it's the storage medium enum.
7. **Handshake**: USB device reset FIRST, then ODIN/LOKE.
8. **TotalBytes**: (0x64, 2, u64 total) progress hint before flashing.
9. **PIT dump**: ZLP after dump request; part request + ZLP after; recv_empty after
   last part; ZLP after end-transfer. PIT data in 500-byte chunks, size at offset 4.

Ported into `universal-unlock-suite/backend/exploits/exynos/protocol.py` (begin_session,
read_pit, end_session, flash_file all follow samloader-rs semantics now).

## sboot.bin S921BXXSGDZG1 static verification (2026-08-28, /tmp/s921fw/ODIN_PROTOCOL_MAP.md)

Full dispatch reconstructed from the ZG1 bootloader:
- **Main command dispatcher** @VA-file 0x2e1560: command = packet[4], valid range 0x00–0x0C,
  jump table @0x3bb586 (u16 offsets, base 0x2e15c0). cmd>0xC → error handler.
- **Response builder** @0x2e0390: writes (w0=type, w1=value) as LE32 pair into the session
  buffer, sends 8 bytes via bulk @0x230450. Confirms all responses = 8-byte (type,value).
- **Error responses**: {FF FF FF FF FF 00 00 00} pattern from 0x2e1460.
- **PIT dump**: sub-dispatch @0x2e2308 (table @0x3bb5a0, subs 0–3 = flash-begin/flash-data/
  dump-begin/dump-data). Part indexing uses `madd x0, x2, 0x1f4, x14` — **0x1f4 = 500-byte
  parts, matching samloader-rs PitDataPacket::SIZE=500**. Dump total size global @0x93bd90.
- **Type bytes seen in code**: 0x67 end-session ack, 0x69 devinfo/cmd4 reject, 0x6a
  file-size-over reject. End-transfer matcher @0x2e0928: field==4 → phone-end path,
  ==1 → modem-end path (matches samloader-rs end-phone=4/end-modem=5 sub-codes with
  binary_type 0=AP/1=CP).
- **'Odin protocol version error!'** fires from the cmd 5 handler @0x2e1ae0 when the
  protocol byte [x21+3] is nonzero-negative (sign-extended check @0x2e18fc) — the version
  gate is in cmd 5, not the ODIN/LOKE handshake.
- Bulk RX max = 0x400 (1024) everywhere; file-part engine @0x2a9d80; DDP (dynamic
  partition) metadata gate @0x2e13f0 via 0x281b4c(4) bits[4..11].
- Runtime globals: session ptr @0x93bb76, TFLASH flag @0x93bb3e, PIT size @0x93bd90.

## LAYER 2: V3_SMP packet engine (also in S921B_ODIN_PROTOCOL_MAP.md)

- **Packet framer** @0x286a80: accumulates into a 0x400 buffer (fill counter @0x6e4a30),
  dispatches to 0x2e0878 when full. Last type/value cached @0x6e4a34/0x6e4a38.
- **Short acks are strings, not (type,value)**: `'OK'` @0x413dfe, `'OKAY'` @0x413df4,
  `'LOKE'` @0x413df9. V3_SMP replies OKAY/OK on success paths; LOKE string is legacy.
- **Wire semantics**: Loke packet = `[type][subcmd][payload...]`; subcmd picks a table.
  Three verified tables: MAIN (u16 @0x3bb586, base 0x2e15c0, cmds 0x0–0xC),
  PARAM (u16 @0x3bb578, base 0x2e08e0, subcmds 0–6), PIT (u8 @0x3bb5a0, base 0x2e2360, 0–3).
  PARAM[1]→PIT, PARAM[3]→end-transfer matcher (4=phone, 1=modem), PARAM[5]→per-part
  transfer, PARAM[6]→reject ('prb is null!').
- **Devinfo response** = the odininfo format string
  `@#MODEL=%s;UN=%s;CAPA=%s;VENDOR=%s;FWVER=%s;PRODUCT=%s;PROV=%s;SALES=%s;VER=%s;DID=%s;...@#`
  — variable-length text blob, not fixed fields.
- **Protocol-version gate**: cmd5 handler chain, version byte = packet[8+3],
  accepted value 0 (sign-ext check @0x2e18fc).
- **'change protocol..'** (@0x3a419c) is printed by the phone-end path after successful
  end-of-transfer — Odin 3.14 logs the same, useful as a live-progress marker.
- File-part ACKs: (0x00, part_index) 8-byte pairs generated @0x286b18 with part counter
  @0x6e4a14, stride @0x6e4a08, max-outstanding @0x6e49f8.

## Pitfalls

- **Heimdall 1.4.2** is too old. Protocol init succeeds but PIT read fails. NOT a connection problem.
- **cfg[(0, 0)]** has no bulk OUT. Always use `cfg[(1, 0)]` for bulk communication.
- **Endpoint objects vs integers** — `dev.write(endpoint, data)` accepts both, but `endpoint` must be the Endpoint object, not the bEndpointAddress integer. Use `ep_out.write(data)` method on the object, not `dev.write(0x01, data)`.
- **AI-generated exploit code** is often simulated — it prints "Bootloader unlocked!" without any actual USB writes. Check for `ep_out.write()` or `dev.write()` calls.
- **USB device state** — after a failed heimdall or pyusb attempt, the device may need physical replug to recover (USB reset alone doesn't clear endpoint stalls).
- **Exynos != Qualcomm** — EDL firehose only works on Snapdragon variants. Exynos (S24 international, A54) needs Odin protocol.
- **Kernel addresses > 32-bit** — `struct.pack('<I', ...)` fails on ARM64 addresses. Use `'<Q'` (64-bit) for kernel addresses.
- **samloader (Python v1) is dead for downloads** — NF_DownloadBinaryInform.do returns 401 even for valid versions (server moved to Inform2 with CHIPSET field). Use samloader-rs.
- **libusb ZLP writes may raise** — pyusb can throw on zero-length writes on some backends; the ZLP may still have been delivered. Treat exception as non-fatal. |

## Pitfalls

- **Heimdall 1.4.2** is too old. Protocol init succeeds but PIT read fails. NOT a connection problem.
- **cfg[(0, 0)]** has no bulk OUT. Always use `cfg[(1, 0)]` for bulk communication.
- **Endpoint objects vs integers** — `dev.write(endpoint, data)` accepts both, but `endpoint` must be the Endpoint object, not the bEndpointAddress integer. Use `ep_out.write(data)` method on the object, not `dev.write(0x01, data)`.
- **AI-generated exploit code** is often simulated — it prints "Bootloader unlocked!" without any actual USB writes. Check for `ep_out.write()` or `dev.write()` calls.
- **USB device state** — after a failed heimdall or pyusb attempt, the device may need physical replug to recover (USB reset alone doesn't clear endpoint stalls).
- **Exynos != Qualcomm** — EDL firehose only works on Snapdragon variants. Exynos (S24 international, A54) needs Odin protocol.
- **Kernel addresses > 32-bit** — `struct.pack('<I', ...)` fails on ARM64 addresses. Use `'<Q'` (64-bit) for kernel addresses.
