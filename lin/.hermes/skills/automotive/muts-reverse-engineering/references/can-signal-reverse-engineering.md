# Identifying an unknown proprietary CAN signal

## When to use

A bus trace contains a signal with no DBC: unknown CAN ID, unknown bit position, unknown byte order,
unknown scale and offset. The question is "which bytes move with this physical value". That is a
different question from "what does this DID mean" — DIDs are UDS and go through the read-only ECU
route, not this one.

## Do not reimplement the pipeline

A working five-stage implementation exists and is worth cloning rather than rewriting:
`github.com/CSS-Electronics/can-bus-reverse-engineering-skills` (~7.4k LOC, `scripts/` under
`.claude/skills/cansub-reverse-engineering/`). Clone it into the git-ignored `reference/` and call
its scripts from the CLI; a bespoke correlator is the expensive mistake in this task class.

## The pipeline, and why each stage exists

1. **survey** — per-ID, per-bit flip-rate heatmap over the whole trace. Distinguishes constantly
   varying bits from static ones, and identifies rolling counters and checksums *before* anything is
   correlated. The mechanism is what makes it work: a bit that never changes is padding, a byte that
   jumps to a fresh value on every frame is a checksum, a bit ticking at a steady clock-like rhythm is
   a rolling counter. Excluding those first is what stops them dominating every later score.
   It also guesses field boundaries: inside a number the low bit flips fastest, so a spot where the
   flip rate suddenly speeds up is the start of the next field.
2. **correlate** — every candidate field (CAN ID, start byte, 1–2 byte width, byte order) read as a
   series and scored against the reference by **windowed Spearman rank correlation**, median across
   overlapping windows. Rank correlation is deliberate: scale and offset are still unknown, so a
   monotonic score is the only fair test. The reference is slid over a small lag range to absorb
   reaction delay, signed and unsigned readings are both tested, and sentinel "signal unavailable"
   values are masked on both sides — without that masking the extreme values win the ranking.
3. **bitsearch** — with the CAN ID known, exhaustively tests every start bit × length × Intel/Motorola
   × signed/unsigned, scored by straight-line fit (R²) against the reference. Skips stretches
   containing stuck bits, using stage 1. Ties go to the shorter field: when two candidates fit equally
   well the longer one has usually swallowed a few bits of a neighbouring value.
4. **calibrate** — fits `physical = offset + scale * raw`, checks residuals, anchors the result
   physically (a decoded speed must read 0 when the reference reads 0), and rounds scale/offset within
   a threshold.
5. **build_dbc / verify** — emits a single-signal DBC, verifies it, merges into an application DBC.
   Re-verify after merging, and feed the growing application DBC back in as an extra reference for the
   next signal: a known speed signal constrains every later decode.

## Decide the reference signal before writing anything

No reference signal, no reverse engineering. Best to worst:

* **CAN-based (best)** — log an OBD-II PID for the same quantity alongside the proprietary traffic so
  both land in one timesynced file. In MUTS the OBD-II half already has a producer:
  `scripts/ecu_readonly_dump.py`. Get the reference frequency right: OBD-II responses are
  request/response and spaced out, so ten PIDs can mean one reference sample every several seconds —
  fine for a scale/offset fit, useless for tracking fast transients.
* **External vision** — film the dashboard/gauge and OCR it into a digitized series. Noisier, but it
  works for values with no CAN equivalent.
* **Human input** — a small sync app mirroring the real value with timestamps, for signals that have
  no display at all (a latch, a knob position).

Quality gate, and the reason a short log can fail: the trace must contain a **diverse, full-range**
series. Standstill plus several distinct hold points decodes in ~5 min; a noisy many-ECU bus wants
~10 min. A single steady cruise decodes nothing — scale and offset are unidentifiable when the value
never changes.

## Triage the target first

Classify the signal, because the class decides where the work is:

* **stationary vs driving** — can it be reproduced parked (locks, wipers, knob positions, gauges) or
  does it need a real drive (speed, RPM, state of charge, temperatures).
* **discrete vs continuous** — discrete signals take a few states and usually end at `scale=1,
  offset=0` with the raw code being the state; the fit work is all in the continuous ones.

Length conventions to test first: booleans 1–2 bits, continuous values 1–2 bytes unless they need
high resolution, and OEMs usually align fields to clean borders rather than splitting a value across
two bytes.

## Input contracts (read off the scripts, not the README)

* **Trace CSV** — semicolon-separated, fixed 12-column header:
  `TimestampEpoch;BusChannel;ID;IDE;DLC;DataLength;Dir;EDL;BRS;ESI;RTR;DataBytes` with hex ID and hex
  `DataBytes`. A header mismatch raises, so generate the file rather than hand-writing it.
* **Sidecar CSV** — `epoch;kind;label;value` with `kind` in `value` (continuous reference), `event`
  (discrete markers) and `anchor` (known timestamp/physical-value pairs).
* Every entry point takes `--trace` and `--sidecar` and reads a log; only capture and bus-detection
  need hardware, and those go through `can.Bus(interface=..., channel=...)`.

## Traps

* **The analysis scripts import `python_can_cansub` at module level** (it registers the CSV codec), so
  `pip install python-can-cansub` is required even for the purely offline log workflow. Do not read
  that dependency as "this needs their hardware" — nothing off the bus touches the device.
* **Never trust one signal's resolution without a second reference.** Spearman survives unknown
  scale, so a decodable signal is not automatically an accurate one; cross-check the decoded series
  against an independent source before writing a resolution into a DBC.
* **Transmit is the write path.** Fuzzing, request sweeps and spoofing push frames; keep them on a
  bench or a sacrificial vehicle and never on a vehicle in motion. The survey/correlate/bitsearch/
  calibrate stages are passive and run list-listen-only.
* **A partial decode is not a decode.** A field that correlates but fails the physical anchor stays a
  candidate and does not go into a DBC — same rule as house rule 3.

## What this does not solve

No ROM image and no seed→key. Those two stay blocked (see SKILL.md), and a newly decoded CAN signal
must not be reported as progress on the flash workstream.

## Fit with the repo

MUTS already has `python-can`, `can-isotp`, `udsoncan` and `canmatrix` in `.venv` plus a `vcan0`
bench, so traces can be replayed with no car attached. The missing half is an **emitter**: whatever
produced the sniff (the J2534/OpenPort stack, `socketcan` on a Pi) has to write out the trace CSV in
contract format above before any stage will run.
