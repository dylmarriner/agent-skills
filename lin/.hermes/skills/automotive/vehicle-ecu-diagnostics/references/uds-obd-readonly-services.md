# Read-only diagnostic services

## Allowlist to transmit (reads)

| service | meaning | notes |
|---|---|---|
| `01` | OBD-II current data | chase `0100/0120/0140` bitmaps first |
| `02` | OBD-II freeze frame | needs the frame that triggered it |
| `03` | stored DTCs (read) | `04` is the **clear** — never |
| `06` | on-board monitoring | MIDs from `0600` pages |
| `07` / `0A` | pending / permanent DTCs | |
| `09` | vehicle information | `0902` VIN, `0904` CALID, `0906` CVN, `090A` ECU name, `0908` IPT |
| `19` | ReadDTCInformation | sub-functions below |
| `22` | ReadDataByIdentifier | the workhorse |
| `23` | ReadMemoryByAddress | read, but usually session/security gated |
| `27` **odd sub-functions only** | SecurityAccess requestSeed | sampling only; even sub-function sends the key |
| `1A` / `21` | KWP2000 local identification | K-line / legacy CAN modules |
| `3E` | TesterPresent | keeps an open session alive; harmless, not a read of data |

## Never transmit unless explicitly authorised (state changes / writes)

`10` session control · `11` ECU reset · `14` clear DTC · `2E`/`2F` write · `27` even sub-function
(send key) · `28` communication control · `31` routine control · `34`/`35`/`36`/`37` download/
transfer · `38`/`3B`/`3D` file services · `83`/`85`/`86`/`87` (ODX/coding, DTC setting off, etc.).

## Negative response codes worth naming in a report

`0x11` serviceNotSupported · `0x12` subFunctionNotSupported · `0x13` incorrectMessageLength
(the ECU wanted a DTC number / more bytes) · `0x21` busyRepeatRequest · `0x22` conditionsNotCorrect ·
`0x24` requestSequenceError · `0x31` requestOutOfRange (a swept DID does not exist) ·
`0x33` securityAccessDenied · `0x35` invalidKey · `0x36` exceedNumberOfAttempts ·
`0x37` requiredTimeDelayNotExpired · `0x7E`/`0x7F` service/sub-function not supported **in the
active session** — the last two are the signature of a seed hidden behind a session switch.

## DID ranges worth sweeping (UDS `0x22`)

| range | content |
|---|---|
| `F180-F19F` | standardised identification: `F187` spare part number, `F188` ECU hardware/part number, `F18A` supplier, `F18C` serial, `F190` VIN, `F191`/`F192` hardware versions, `F194`/`F195` software version, `F197` system name, `F199` programming date |
| `F100-F17F` | supply/manufacturer strategy + part-number variants (Mazda-style part numbers show here) |
| `F200-F2FF`, `F000-F0FF`, `F300-F3FF` | manufacturer specific, often short binary config/version blocks |
| `FD00-FEFF` | manufacturer specific per ISO 14229 |

Expect most DIDs to answer `0x31`; the sweep is what turns "which DIDs exist" from a guess into a
counted result. `0x22` responses are `62 <did_hi> <did_lo> <data…>` — strip three bytes, then try the
payload as ASCII and keep the hex either way.

## DTC reads (UDS `0x19`)

`01` countByStatusMask · `02` byStatusMask · `04` snapshotRecordByDTCNumber · `06` extDataRecord ·
`0A` supportedDTC · `14` faultDetectionCounter. `04`/`06` need the 3-byte DTC in the request or the
ECU answers `0x13 incorrectMessageLength`. Cross-check the count field of `01` against the record
count of `02` — a mismatch means the module's table is synthetic or corrupt.

## OBD-II identification decode

- Mode 09 replies: `49 <pid> <count> <ascii…>`, NUL padded — trim NULs and spaces for VIN/CALID/name;
  `0906` is a 4-byte CVN, report it as hex, not text.
- Mode 01 singles: `41 <pid> <data>`; supporting-PID replies are `41 <pid> <4-byte bitmap>`.
- Bitmaps: 32 bits map to IDs `pid+1 … pid+0x20`; the bit for `pid+0x20` is the "next page exists"
  marker and is not itself a supported identifier.

## Seed-probe recipe (read-only)

```text
for level in 1..16:                 # sub-function = 2*level - 1  (odd => requestSeed)
    send 27 <sub>
    3 samples, ~200 ms apart         # one sample cannot tell constant from rolling
    record full response + NRC
    stop the level's probing on 0x36 / 0x37 and report the module as locked
```

Interpretation to include in the report: a non-zero seed is a real seed (for a later, explicitly
authorised algorithm study); `00 00…` means the level is already unlocked;
`7F 27 7E/7F` means the service is not available in the default session — a seed will only appear
after `10 02`/`10 03`, which is a state change the operator has to authorise.
