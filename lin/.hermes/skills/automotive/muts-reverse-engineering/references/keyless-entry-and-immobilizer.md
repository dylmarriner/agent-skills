# Keyless entry, RKE and the immobilizer — the radio side

Depth for "code a new key", "unlock/start it from outside", and "what is the fob
algorithm". Separate workstream from the `0x27` diagnostic unlock: nothing here
inherits that evidence, and none of it touches the ECM's security access.

## Three systems inside one key, three different problems

| layer | physics | part / protocol | what it permits |
|---|---|---|---|
| transponder (immobilizer) | 125 kHz inductive, powered *by* the coil field (~2–5 cm) | ID46 / Philips **Crypto-2**, PCF7936AS; MAZ24 or MAZ13 blade | possession only — see below |
| RKE (lock/unlock/trunk) | 433.92 MHz (NZ/EU/JP) or 315 MHz (NA) | fixed code **or** hopping (KeeLoq/HCS-class) — must be measured | replay or one-shot capture |
| diagnostic enrollment | CAN `0x7E0`/`0x7E8` | the solved `0x27` seed/key **plus** an unidentified write-key-slot service | add-key / AKL |

**Crypto-2 is possess, not compute.** The secret lives inside the chip and the
module stores only an ID; no capture of the exchange yields a computable
response. So "reverse engineer the fob algorithm" has no useful endpoint — the
endpoint is *enrolling or cloning a chip*. Naming which of the three layers a
question is about is the first thing to do; conflating them is how a session
gets spent on the wrong subsystem.

## What each layer actually allows, at range

- **Unlock**: yes, radio is the whole point. Fixed code → replay forever.
  Rolling counter → blind replay works **once**; the remaining option is
  jam-and-capture (hold the receiver deaf while the owner presses, capture N and
  N+1, replay N inside the window). Hopping payload with no monotonic byte → **no
  radio route at all**; go to enrollment.
- **Start**: needs a valid transponder answer, i.e. a chip inside the coil field.
  That is possession, a clone, or a relay — never computation. On a blade-ignition
  car the barrel also has to be turned, so "start from outside" closes there.
  On a push-start car the button and brake pedal are still physical: a relay gets
  the car to *believe* the key is inside, it does not press anything.
- **No-telematics cars** (BL-era Mazda) have no modem, no OTA, no keyless-go
  network. "Zero physical access" is an absent attack surface, not a policy line
  — the only real remote surface is an aftermarket remote-start/alarm cloud app,
  and that is an app-security problem on the owner's account.

## The measurement that decides everything

Five presses, compared byte-for-byte, settle the design before any hardware is
bought:

- identical every press → fixed, replayable forever;
- one byte incrementing by 1 → rolling counter, single-use replay;
- all bytes varying → hopping/encrypted, no radio plan.

`tools/rke_capture_analyze.py <capture>` takes hex-per-line or `rtl_433 -F json`
lines, reports `fixed` / `counter` / `hopping` / `inconclusive` with the counter
byte offset, and **exits 2 on an inconclusive capture** so a thin capture cannot
be read as a verdict. Self-test: `--self-test`.

## Relay geometry, and the push-start constraint

- Car side: LF antennas in the door handles and in the cabin; the fob answers on
  UHF. Two channels near the car, or one multiplexed — a handle coil will not
  cover the cabin.
- Forward **raw baseband**, CC1101 in ASYNC mode both ends. Every implementation
  that decodes and re-encodes the LF frame dies on jitter; pipe the waveform.
- Far end must sit within centimetres of the fob: the range exists on the *car*
  side only, because the transponder is powered by the field.
- Push-start timeline: brake-pedal switch **before** the button pulse, and the LF
  link held open **past button release**, because the cabin antenna re-challenges
  during crank. Dropping it then reads as an immobilizer fault, not a relay fault.
- Feasibility is arithmetic, not enthusiasm:
  `slack = window − (fob_delay + 2·link + 2·jitter)` and
  `frame_slack = frame − 2·link`. ESP-NOW on two ESP32 fits typical windows;
  LoRa-SF9 does not; walkie-talkie audio is marginal. `tools/keyless_relay_plan.py
  --mode budget` computes both and `--mode start --hold N` **exits 1** when the
  hold is shorter than `200 + crank + poll` ms.

## Body-side facts worth not re-learning

- BL (2010–2013) Mazda3: ID46 Crypto-2 transponder, remote-head key, MAZ24/MAZ13
  blade. Trim and market decide whether it is blade or smart-key push-start —
  confirm on the car, not from a forum thread about another market.
- Add-key with two known keys is an on-board sequence on many of these; add-key
  with one key needs a tool; all-keys-lost needs the PIN read or decoded. A
  half-written keyless module needs bench recovery, so add-key before AKL, always.
- Cloning writes a **duplicate ID** (car sees the same key). Enrollment writes a
  **new ID**. They are not interchangeable, and a cloned chip is what a bypass
  module wants.

## Where this lives in the repo

`tools/rke_capture_analyze.py`, `tools/keyless_relay_plan.py`,
`tests/test_keyless_tools.py`, and the "Keyless entry: measurement and planning
only" section of `docs/ecu_reads/security_tools.md`. Measurement and planning
only: no transmit, jam, or actuator code is implemented, and the doc states that
this workstream does not extend the ECU programme's scope.
