---
name: vehicle-ecu-diagnostics
description: Use when reading an ECU over J2534/CAN adapters.
version: 1.0.0
author: Hermes Curator
license: MIT
metadata:
  hermes:
    tags: [automotive, can, j2534, iso15765, uds, obd2, kwp2000, ecu, read-only, hardware]
    related_skills: []
---

# Vehicle ECU diagnostics (read-first)

## When to Use

- A user asks to "read", "extract", "dump", "identify" or "talk to" an ECU, module, car computer
  or OBD-II/CAN device — especially when they add a constraint like "read-only" or "no writes".
- An adapter is (or may be) attached: Tactrix OpenPort 2.0, generic J2534 passthru, SocketCAN/`can0`,
  ELM327, or a vendor tuning tool that proxies one of these.
- The goal is identification (VIN, CALID, CVN, part numbers), DTCs, live data, seed/security
  reconnaissance, a memory/coding read, or working out which modules are on a bus.

## Scope

Applies to any session where an ECU sits behind a USB/CAN adapter and the goal is identification,
DTCs, live data, seed reconnaissance or a memory/coding read.

## Hard rules

- **"Read mode" is a boundary the user sets, and it is absolute.** Transmit only explicitly permitted read services; do not treat the user's adapter connection or a broad goal like "read the ECU" as permission to change diagnostic state. Enforce the boundary in code *before the frame is built*: allowlist read service IDs and constrain mixed-purpose services by sub-function (`0x27` odd requestSeed only; `0x29` configuration query `0x08` only, when verified for this ECU/protocol). Never send session control, reset, clear-DTC, write, routine, download, transfer, certificate, proof, or de-authentication requests. Exercise the guard offline first, then verify the raw capture contains no disallowed service.
- **Exercise the guard before the bus, not after.** Call it against the write-service list and confirm
  it raises — no adapter, no vehicle, no session. A read-only claim that has never been executed is a
  comment, and the guard is the one place a later edit quietly widens the allowlist.
  `scripts/verify_readonly_guard.py <collector.py>` does this offline and exits non-zero on a leak.
- **A raw command-string tool is a write primitive.** Any interface that takes free text and hands it
  to the adapter unfiltered — an agent tool, an MCP server, a vendor SDK wrapper — has no boundary:
  the allowlist becomes whatever the model was told, which is nothing. Audit that surface before
  trusting a "read-only" label, and put the filter server-side per command, where the adapter is
  spoken to.
- **A session switch is a state change, not a read.** `0x10 DiagnosticSessionControl` is what unlocks
  seeds, security levels and most manufacturer DIDs. When the only way forward is a session change
  (or `0x11` reset, `0x14` clear DTC, `0x2E` write, `0x31` routines, `0x34-0x37` download), STOP,
  report exactly what is gated and by which service, and offer the one command — do not run it
  silently to get a nicer result.
- **Never send the key-send half of security access** (even sub-function of `0x27`) unless the user
  explicitly asked for an unlock attempt. Requesting a seed (odd sub-function) is a read of ECU state
  and consumes no attempt counters; sending a key burns an attempt and can lock the module.
- **Report negatives as results.** A swept space with no answers (NRC histogram, addresses silent,
  service unsupported) is evidence and belongs in the report; do not bury it.
- **Distrust tidy answers from firmware.** Cross-check derived fields against their own payload
  (DTC count field vs list length) and say when the module contradicts itself instead of presenting
  the answer as ground truth. Decode each UDS DTC status byte before calling it active: a returned
  record with `testFailed` and `confirmedDTC` clear is not a confirmed active fault; report the raw
  code/status and the OBD Mode 03/07 results alongside it.

## Procedure

1. **Identify what is actually plugged in** before writing any protocol code:
   `lsusb`, `/sys/bus/usb/devices/*/` (idVendor/idProduct/product/serial), `dmesg | tail`,
   `ip -br link show type can`, `ls /dev/ttyACM* /dev/ttyUSB*`, `ss -tlnp`. Record VID:PID and
   firmware — the report starts with the adapter, not the ECU. If nothing enumerates, that is the
   lead: say the adapter is absent, show the empty probe commands, and hand over the exact
   attach → unbind → run lines plus the previous run's artifacts. Never sweep against an absent
   adapter, and never report its absence as a task failure.
2. **Reuse the project's existing transport stack.** If the repo already has a driver wrapper and
   transport (`comms/j2534_device.py`, `iso15765_transport.py`, `j2534_manager.py`, a bundled
   `drivers/linux/j2534.so`, an ELM327 interface), call them. Writing a second ISO-TP implementation
   next to a working one is the most expensive mistake in this task class. Also run the repo's own
   read-only evidence collector first if one exists — it is the cheapest proof the transport works.
3. **Prove the read-only guard first, with nothing plugged in.** Import the collector and drive its
   guard with the write-service list; every one must raise before a frame is built. Offline, instant,
   and the only evidence the boundary exists.
4. **Inspect USB interface binding before touching it.** Check the OpenPort's exact VID:PID, serial, USB node permissions, and each `/sys/bus/usb/devices/<device>:<interface>/driver` link. If `cdc_acm` actually owns the interface, unbind that exact interface for libusb; if the interface is already unbound, do not issue an unnecessary unbind. Do not rebind while the J2534 session is open. Details and commands in `references/j2534-openport-linux.md`.
5. **Prove the bus answers before sweeping**: one `01 00` (OBD) or `22 F1 90` (VIN by DID) exchange
   at the default request/response pair (`0x7E0`/`0x7E8`). If that times out, fix the physical layer
   before adding phases.
6. **Extract in phases, cheapest and most valuable first**: adapter/firmware info → OBD-II
   identification (Mode 09: VIN, CALID, CVN, ECU name) → UDS DIDs → DTC services → seed probe →
   protocol-specific identification (KWP `0x1A`/`0x21`) → memory reads → module scan. Service lists,
   DID ranges and NRC meanings: `references/uds-obd-readonly-services.md`.
7. **Chase the "supported" bitmaps instead of assuming.** `0100`/`0120`/`0140`, `0900`, `0600` pages
   tell you which PIDs/MIDs exist and which next page to request; the last bit of each page is the
   next-page marker, not an identifier. Record every request/response pair — the raw log is the
   deliverable, the decode is commentary.
8. **Enumerate modules by address pair.** A J2534 ISO15765 channel has a flow-control filter for one
   response ID, so a functional broadcast is not collected: iterate `0x7E0+i` / `0x7E8+i` and
   reconnect per pair to find which modules are present.
9. **Write the artifacts**: raw JSON (every exchange, hex, status, elapsed), a markdown report with
   decoded values beside raw hex, and a short findings file with the plain-language answer.

## Pitfalls that cost real time

- **A crash in a late phase must not lose earlier data.** Wrap each phase in its own try/except and
  write the output in `finally`; one unhandled overflow after 16 s of harvesting throws away the whole
  run otherwise.
- **Validate widths before packing.** `0x23`/`0x34` requests mix an address-length format byte with
  address and size fields; a probe address that does not fit the chosen address width raises at pack
  time. Skip the incompatible combination, don't crash.
- **Received ISO15765 payloads may carry `ProtocolID == 0`** with this class of driver. Filtering
  responses on `ProtocolID == ISO15765` alone silently drops every answer; accept both and rely on
  the CAN-ID prefix.
- **Skip driver indications, not just errors.** `RxStatus` carries TX echo / start-of-message bits and
  frames shorter than the 4-byte CAN-ID prefix + 1 payload byte are indications, not ECU data.
- **Sample a seed at least three times** with ~200 ms spacing: one sample cannot distinguish a
  constant seed from a rolling one. Abort the probe on NRC `0x36`/`0x37` and say the module is in a
  delay window.
- **K-line and CAN services differ per module.** A module answering `0x22`/`0x19` on CAN may return
  `0x11 serviceNotSupported` to every KWP2000 request; that is a finding, not a transport fault.
- **A negative response is not a timeout.** Separate `NO_RESPONSE`/timeout from `NEGATIVE`+NRC in the
  log; they point at different problems (wiring/baud vs session/security gating).
- **Timing discipline is cheap**: a small inter-request gap plus a bounded per-request timeout keeps a
  ~1800-DID sweep under a minute on a live bus. Do not over-throttle to the point of hiding
  completeness, and do not omit the gap on modules with a delay-after-attempt timer.

## Output shape for this user

- Lead with the answer: adapter + bus line, then a compact table of the extractable identifiers
  (VIN, CALID, CVN, ECU name, part numbers, DIDs that answered, DTC status, live-data highlights).
- State the seed/security reality explicitly, including the exact NRC observed and which service
  would be needed to go further.
- Give absolute paths for the raw dump, the decoded report and the findings file; keep the tool that
  produced them in the repo next to the other scripts.
- Flag data-quality doubts in one short paragraph at the end rather than decorating the table.
- Asked to evaluate an outside stack (bare repo URL, vendor tool, another agent) the deliverable is a
  verdict, not an install: what it is, what it actually speaks, the one part worth taking, the one
  part to refuse, and the read on its tool surface. Recipe: `references/third-party-stack-review.md`.

## References

- `references/j2534-openport-linux.md` — bringing an OpenPort 2.0 (and similar passthru) up on Linux:
  udev/permissions, the cdc_acm unbind, driver build, message layout, filters, channel per module.
- `references/uds-obd-readonly-services.md` — read-service allowlist vs write set, NRC table, DID
  ranges worth sweeping, OBD mode/PID map, seed-probe recipe.
- `references/third-party-stack-review.md` — reviewing an outside diagnostic stack: read order,
  the raw-command-string write-primitive audit, verdict table shape, what to refuse.
- `scripts/verify_readonly_guard.py` — offline probe: imports a read-only collector and proves its
  guard refuses every write service (and still permits declared reads). Exit non-zero on a leak.
