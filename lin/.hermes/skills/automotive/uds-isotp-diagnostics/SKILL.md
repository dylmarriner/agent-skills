---
name: uds-isotp-diagnostics
description: "Use when writing UDS/ISO-TP ECU diagnostic clients."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [automotive, can, iso-tp, uds, security-access, j2534]
---

# UDS / ISO-TP diagnostic clients

Procedure and pitfalls for ECU diagnostic work: the transport contract, the security-access state
machine, attempt/delay accounting, key providers, and the bench harness that proves all of it without
a car. Covers UDS (ISO 14229) security access, session control, DID/DTC reads, ISO-TP (ISO 15765-2)
framing and J2534/SocketCAN transports.

## When to Use

- Implementing or debugging a client for service `0x27` (seed/key), `0x10`/`0x11`/`0x22`/`0x2E`,
  `0x19`/`0x14`, `0x31`, `0x34`/`0x36`/`0x37`, or `0x3E`.
- Wiring a client to a J2534 pass-thru device or a SocketCAN `CAN_ISOTP` socket.
- A security-access attempt is refused, locks out, or returns a negative response you cannot read.
- Building a bench ECU / simulator so protocol work can be tested with no vehicle attached.
- Turning a refusal-only security module into a working, provider-backed one without inventing an
  algorithm.

## 1. Transport contract (decide this first)

A transport is any object exposing **`request(payload: bytes) -> bytes`** returning the *complete*
response PDU (positive `0x6X…` or negative `0x7F <sid> <nrc>`). Keep every client and service
written against that one shape so J2534 and SocketCAN backends are interchangeable.

- **Call it with one positional argument and let defaults apply.** Transports spell their second
  parameter differently (`request(payload, timeout_ms)` vs `request(payload, timeout=<seconds>)`),
  so passing it positionally either mis-scales the timeout by 1000x or raises. Consumers that need a
  deadline should own it, not forward it blind.
- **Surfaces that already exist are the surfaces to use.** Before writing framing, check for the
  kernel `CAN_ISOTP` socket and a J2534 driver that segment/reassemble for you; only hand-roll ISO-TP
  (SF/FF/CF/FC, BS/STmin, sequence wrap, N_Cs/N_Cr) when you are on raw CAN frames.
- **Response-pending (`0x7F <sid> 0x78`) is not a result.** Either the transport consumes it and keeps
  reading, or the client raises a typed `ResponsePendingError` telling the caller the exchange did not
  complete. Never let it fall through as a success or as a generic error.

## 2. Security access (service 0x27)

Sub-functions are paired: request seed = **odd** `2 * level - 1`, send key = **even** `2 * level`.
Validate the mapping in both directions so an echoed sub-function can be checked against what was asked.

State machine, in order:

1. **Refuse before any traffic** if the level has no registered key provider. Asking an ECU for a seed
   you cannot answer wastes an exchange and, on modules that count failures, moves it toward lockout.
   Raise a typed error that names the level and how to register a provider.
2. **Request the seed.** Require the response sub-function to echo the request; treat an **all-zero
   seed as "already unlocked"** and return success *without* sending a key (this is standard, not a
   shortcut).
3. **Derive the key** through a named provider (see §3).
4. **Send the key** only if a seed for that level is pending; otherwise it is a local sequence error
   (NRC 0x24 semantics) — do not put it on the bus.
5. **Mark the level unlocked** only on a positive response, and clear the pending seed either way.

Negative responses map to typed exceptions so a refusal can never be mistaken for progress:

| NRC | Meaning | Client action |
|---|---|---|
| `0x13` | incorrect length/format | malformed request built locally |
| `0x22` | conditions not correct | wrong session/vehicle state |
| `0x24` | request sequence error | key without seed, or out of order |
| `0x31` | request out of range | unsupported level/format |
| `0x33` | security access denied | session/level not permitted |
| `0x35` | invalid key | count an attempt, clear the pending seed |
| `0x36` | exceed number of attempts | start the required-delay window, stop trying |
| `0x37` | required time delay not expired | start/extend the delay window |
| `0x78` | response pending | see §1 — surface it |

**Account for attempts and delays client-side, and refuse locally before transmitting.** Track
attempts per level, set a delay deadline on `0x36`/`0x37`, and raise the delay error from the local
clock instead of spending an exchange to be told again. While a delay is outstanding, hold the
session open with TesterPresent (`0x3E 00`) roughly every `S3/2` — with `S3 = 5000 ms`, a 2.5 s slice.
Make the clock and the sleeper injectable so the state machine is testable without real sleeps.

## 3. Key providers: pluggable, never invented

A seed→key transform is vendor- and ECU-specific and normally proprietary. Structure that honestly:

- **A provider is a named callable plus its declared seed length(s)** and, optionally, the context
  keys it needs (`vin`, `immobilizer_key`, `manufacturer_key`, `additional_data`).
- **Compute only what you can verify.** Reuse transforms that already exist and are testable in the
  codebase (dead code that sits *after* a `raise` is a real implementation that was disabled — move it
  into a provider and test it rather than rewriting it from a description).
- **Refuse unknown levels with a typed error naming the level**, and expose a profile that maps
  levels → provider names plus a one-line extension path (e.g. `profile.with_levels({2: "my-provider"})`).
  Do not synthesise a key for a level nobody has implemented.
- **Providers needing material raise a typed "missing input" error naming the key**, not a generic
  failure and not a made-up KDF. Crypto output longer than the seed is **zero-padded to the block size
  on the way in and truncated back to the seed length on the way out** — the ECU expects key length ==
  seed length.

## 4. Timings and constants worth not guessing

ISO 14229-1 defaults: `P2 = 50 ms`, `P2* = 5000 ms`, `S3 = 5000 ms`. ISO 15765-2 network timeouts
`N_As/N_Ar/N_Bs/N_Cr = 1000 ms`.

ISO-TP **STmin is a grid, not a number**: `0x00`–`0x7F` = whole milliseconds, `0xF1`–`0xF9` =
100–900 µs in 100 µs steps; `0x80`–`0xF0` are reserved. Reject values that do not land on the grid
instead of silently rounding them — a rounded STmin is a timing bug that shows up as intermittent
lost frames.

## 5. Bench harness (prove it without a car)

`vcan0` + `python-can-isotp` + a threaded simulated ECU is enough to exercise the whole stack:

1. `sudo modprobe vcan && sudo ip link add dev vcan0 type vcan && sudo ip link set up vcan0`.
2. Two `isotp.socket()` endpoints with mirrored addresses (ECU: `rxid=0x7E0, txid=0x7E8`; tester the
   reverse), both `bind("vcan0", Address(Normal_11bits, …))`.
3. The ECU thread answers `0x27` from a known transform and `0x3E` with `0x7E`; the tester wraps its
   socket in a `request(payload) -> PDU` adapter.
4. **Skip the whole module when `vcan0` is absent** (`pytest.mark.skipif` on a probe of
   `ip link show vcan0`) so the suite still runs on machines without the interface — but keep the
   skip visible, never silently green.
5. Set a socket timeout so an idle ECU thread does not hang the run, and always assert the exact
   request sequence (sub-functions in order) — a passing unlock that sent the wrong order is a bug.

## 6. Test discipline for this class of code

- **Fake transports must answer TesterPresent too.** A scripted transport that only knows `0x27`
  raises on the first keep-alive and looks like a bug in the service.
- **Use tolerances on scheduler-bound waits** (`waited >= 0.29` for a 0.3 s window), never exact float
  equality.
- **Before blaming your change for a red test, hide the new package** (`mv new_pkg /tmp/hidden`),
  re-run, and compare: identical failures mean pre-existing and belong to whoever owns that module.
- **Keep old exception names as aliases** when a refusal-only module becomes a working one, so existing
  importers do not break on the rewrite.

## Pitfalls

- **Do not implement an invented seed→key algorithm.** A plausible-looking transform that nobody can
  verify against a real seed/key pair is worse than a typed refusal; leave the provider slot empty and
  documented until an algorithm can be reproduced against a captured pair.
- **Do not treat a seed response as success.** On the wire, success is a positive `0x67` echo of the
  *key* sub-function; a returned seed is not access.
- **Do not let a `0x78` fall through as an empty response** — an empty PDU is a parse error, not a
  timeout, and the two get debugged very differently.
- **Portability:** if a package claims Python ≥3.8, `class X(str, Enum)` + `from __future__ import
  annotations` rather than `StrEnum` / `X | Y`, and pass `maxmem` to `hashlib.scrypt` (modern OpenSSL
  rejects the default). Both bite at runtime, not at import.
