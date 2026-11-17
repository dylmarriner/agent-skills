# S24 (SM-S921B, Exynos 2400) — Live ODIN PIT Read, Verified 2026-08-30

Source: live S24 serial R5CW90M2ZQH in download mode (`04e8:685d`), read via
the `protocol.py` library in `universal-unlock-suite/backend/exploits/exynos/`.
Raw PIT committed to `universal-unlock-suite/dumps/S921B_pit_2026-08-30.bin`.

## The critical technique: ZLP / empty-send after every request

The single thing that turned "PIT read fails / state machine wedges" into a
clean 8192-byte PIT dump is the **zero-length packet (empty-send)** after each
request. Modern Exynos bootloaders (S21+/Exynos 2200+) require a bulk ZLP
(0-length OUT) after each control request. Hand-rolled bulk probes that skip it
fail AND wedge the device state machine.

Use the library's `send_empty()` / `_send_packet_zlp()` — do NOT hand-roll raw
bulk probes for modern Exynos.

## Wire framing (all 8-byte {u32 type, u32 value} unless noted)

- **Handshake:** send `ODIN`, expect `LOKE` (bytes `4c4f4b45`). `handshake()`
  does a USB bus reset first to clear stale state — a wedged device returns
  `0x67` instead of `LOKE`.
- **Session begin (0x64):** value `0x28000` = 163840.
- **PIT dump request:** `0x65` sub `0x01` (kRequestDump=1) → declares 8192 bytes
  (0x2000). Empty-send AFTER.
- **PIT part request:** `0x65` sub `0x02` (kRequestPart=2), partIndex at offset 8.
  Empty-send AFTER.
- **PIT end:** `0x65` sub `0x03` (kRequestEndTransfer=3).
- **Part size = 500 bytes** (0x1f4) — confirmed from sboot map + live read.

## Correct PIT sub-commands (matter — wrong ones return the error format)

| sub | meaning |
|-----|---------|
| `0x00` | flash-pit-begin |
| `0x01` | **dump-pit-begin** (returns declared size) |
| `0x02` | **dump-pit-data** (per-part) |
| `0x03` | end-transfer |
| `>0x03` | **error path** |

**Pitfall:** a sub-command >3 returns the error response
`{FF FF FF FF FF 00 00 00}` (8 bytes: `ffffffff00000000`) — this is the device's
error format, NOT a PIT payload and NOT the device being broken. `ffffffff00000000`
= you used a bad sub-command.

## PIT entry layout — 132 bytes, NOT the classic 128

Verified live. Samsung PIT entries on modern devices (S24) are **132 bytes**
(classic 128 + 4 extra). `parse_pit()` in protocol.py was patched to
`entry_size = 132`.

- Header (32 bytes): magic `0x12349876` @0, entry count @4, 24-byte board string @8.
- Entry fields: u32 binary_type/device_type/identifier/attributes/update/
  block_size/block_count/file_offset at offsets 0–28; partition name @+0x20;
  flash .img @+0x40; fota @+0x60.

## Live results
- Board `COM_TAR2S5E9945`, 49 partitions, magic `0x12349876`, 8192 bytes.

## S24 partition table (49 entries, from live dump)
FLD, UL_KEYS, BOOTLOADER2, DDI, PIT, MD5HDR, EFS, SEC_EFS, STEADY,
BOOTLOADER(sboot.bin), EPBL, PARAM, UP_PARAM, KEYSTORAGE, BOTA, HARX,
DRM_PLUGIN, UH, UHCFG, DTBO, BLCMD, BOOT, INIT_BOOT, VENDOR_BOOT, RECOVERY,
PVMFW, RADIO(modem.bin), CP_DEBUG, NAD_REFER, PERSISTENT, MISC, VBMETA,
VBMETA_SYSTEM, METADATA, DEBUG, SUPER, PRISM, OPTICS, CACHE, OMR, USERDATA,
CPEFS, LDFW, TZSW, TZAR, SSP, SVM.

FRP/security-relevant partitions:
- **PERSISTENT** (dtype 23) — where the FRP flag/state lives.
- **KEYSTORAGE** — keystorage.bin, device key material.
- **EFS / SEC_EFS** — IMEI/calibration.
- **METADATA** — dynamic-partition metadata.
- **VBMETA / VBMETA_SYSTEM** — verified boot.

## Working driver (use this, not the old probes)
`backend/exploits/exynos/run_s24_pit.py`:
find_device → find_bulk_interface → claim_interface → handshake →
begin_session → read_pit → end_session → release_interface. Use it as the
template for any live-ODIN read.

## Probe history (why the hand-rolled ones failed)
- `probe_s24_v3.py`: no ZLP → PIT part requests returned error; Method C then
  wedged the device (bulk write timeout, end-session never sent).
- `probe_s24_v4.py`: used WRONG sub-commands (0x02 for dump-begin, 0x03 for
  parts) → error. Correct: 0x01 dump, 0x02 part, 0x03 end.
- `run_s24_pit.py`: uses the protocol.py library (ZLP-correct) → SUCCESS.
