# L3CE / MZR seed→key: tiers, material, and evidence classes

Depth for "is the key solved", "retest the unlock", and "is it ready live".
The always-on rules are in SKILL.md; this file is the detail you need when you
are actually re-deriving, re-testing or answering a status question.

## Two tiers, two materials — never one answer

| | Level 1 | Level 2 |
|---|---|---|
| `0x27` subfunctions | `01` seed / `02` key | `03` seed / `04` key |
| internal selector value | `2` | `4` |
| state transition | 1 → 2 | 2 → 4 (requires L1 first) |
| 5-byte material | `IvfeR` @ ROM `0x21065` | `MazdA` @ ROM `0x2106A` |
| provider | `l3ce-level-1` | `l3ce-level-2` |

Seed subfunction is `2L-1`, key `2L`. Both materials live in one Ghidra string
object `ds "IvfeRMazdA"`, contiguous, which is why address arithmetic and an
off-by-five are the two ways this goes wrong.

**A key is only meaningful with its tier named.** Same seed, two answers:
`43 62 50` → `6B 8A 22` (IvfeR, Level 1) and `4C CE 0B` (MazdA, Level 2).
Answering a `27 01` seed with Level 2 material is a guaranteed `0x35` and a spent
attempt. `tools/ecu_security.py calculate` defaults `--suffix` to `MazdA`, so
its bare output is Level 2 material — read the `suffix` field before using a
candidate. "tier 2" in the firmware documents means *Level 1*; do not carry that
word into a Level 2 conversation.

## The transform, in its reduced form

```python
state = 0xC541A9                      # 24-bit
for byte in seed + material:          # 3 + 5 bytes, in that order
    for bit in range(8):              # LSB first
        feedback = (state & 1) ^ ((byte >> bit) & 1)
        state >>= 1
        if feedback:
            state |= 0x800000         # feedback injected at bit 23
            state ^= 0x109028
        state &= 0xFFFFFF
# 24-bit result -> three wire bytes, little-endian
```

Right-shifting, feedback injected at the top. The **published Mazda GLFSR shape**
used by the common open-source implementations (left-shifting, mask XORed onto
the shifted state) reproduces **0 of 5** known vectors on this calibration. Start
from the reduced form above, not from "Mazda seed/key is the public LFSR".

When a from-scratch implementation fails the known vectors, that is only a
finding if a known-good implementation passes them **in the same run** — otherwise
the guess and the instrument are indistinguishable. Put both in one script.

## Known vectors (ground truth for any re-derivation)

| seed | material | key | class |
|---|---|---|---|
| `F3 50 77` | `IvfeR` | `F1 99 2D` | live acceptance, raw CAN capture in `.hermes/l3ce_accepted_capture_*.json` |
| `DF EA 19` | `IvfeR` | `2D 8F FB` | live acceptance, ledger-reported, no raw capture |
| `01 02 03` | `IvfeR` | `17 1A 5A` | offline, firmware comparison |
| `01 02 03` | `MazdA` | `30 5E 73` | offline, firmware comparison |

Any candidate implementation must reproduce all four, then agree with
`mazda_protocols.mps_seed_key` over ~1,024 random seeds per tier before it is
worth a sentence.

## The nine providers — "all levels" is a provenance table, not a count

`KeyProviderRegistry()` enumerates them; never hardcode the list in a probe, or a
new provider is silently untested.

| provider | seed | provenance |
|---|---|---|
| `l3ce-level-1` | 3 B | ROM-confirmed, live-accepted |
| `l3ce-level-2` | 3 B | ROM-confirmed, never sent |
| `mzr-standard`, `mzr-enhanced`, `mzr-bcm` | 4 B | **dead placeholder in this repo's own legacy tree**, never recovered, module refuses to run it |
| `mzr-tcm` | 2 B | same dead placeholder |
| `mazda-calibration` | 6 B | mixes caller-supplied `additional_data` (≥4 B); the real key is a proprietary VIN KDF |
| `mazda-immobilizer` | 8 B | 3DES under a caller-supplied 24-byte key, standing in for that VIN KDF |
| `mazda-manufacturer` | 8 B | AES under a caller-supplied 16/24/32-byte master key; none public |

Three consequences. "All seed keys reverse engineered" is false for seven of the
nine, and the reason differs by group: the four `mzr-*` entries are placeholders
nobody ever recovered, while the last three are the wrong question — the real
secret is a caller-held key (immobiliser: a VIN-derived 3DES key; manufacturer: an
unpublished master key), so no firmware reversing produces it, and a brute force
over 16–32 bytes is not a finding. A
harness must synthesise context from `provider.required_context` rather than
passing one global dict: the 3DES provider rejects 16 bytes, and the immob/n
manufacturer providers raise `KeyProviderMissingError` naming the expected sizes.
And a matrix pass (9/9 accept, 9/9 reject) is evidence about the client's state
machine, not about any algorithm — say which of the two you measured.

### Gating an unverified provider — the pattern, once

An offline matrix pass must never promote a provider. The gate lives on the
data, not in callers: `KeyProvider.verified` (default `True`, `False` on the four
`mzr-*`-compat entries) is consulted by `SecurityAccessService._require_provider`,
which raises `UnsupportedSecurityLevelError` before any derivation or
transmission. Applied properly it touches four places at once:

1. the flag on the providers that have neither firmware nor a capture;
2. `SecurityAccessService(..., allow_unverified: bool = False)` — a per-call
   opt-in, never a module-level switch;
3. every wrapper that constructs the service or the facade (`SecurityAccess`,
   `quick_unlock`) taking the same flag, defaulting to closed;
4. the mechanics tests passing `allow_unverified=True` **explicitly**, because
   they test the protocol, not the verification status.

Then pin the new behaviour with two tests: an unverified provider raises **with
zero frames on the transport** (assert the captured request list is empty, not
just the exception), and a verified provider still reproduces a known vector
unchanged. Skipping step 3 leaves a product path that looks gated and is not —
`quick_unlock()` defaulted to the unconfirmed engine profile, which is exactly
how a fabricated key could still reach a car.

## Provenance: run the search, then read the module that owns the constants

A transform's origin is settled by two moves, in this order — and neither is
optional, because each one alone gives a wrong answer.

1. **`gh search code '<constant tuple>'` with a control that must hit.** Without
the control (`0x109028` is the standing one — it appears in `VolvoTools`,
`VBFlasher` and `FG-Falcon`) an empty result is indistinguishable from a broken
search. A tuple that hits *only* your own repository is not a port, a recovery,
or a leak from a vendor tool: it is this repo.
2. **Read the file that owns the constant, not just its presence.** The owning
module closes the question: `app/mds/security/security_algorithms.py` raises
`SecurityAlgorithmUnavailable` from every algorithm entry point, its transform
body's only comment is `# More complex algorithm with additional steps`, and
`_derive_immobilizer_key` raises "VIN key derivation is proprietary and no
verified provider is configured". Code below those raises is unreachable. That is
a placeholder that was disabled, later lifted into `mazda_protocols/security.py`
and given a description as if it were recovered.

The search pays a second dividend when the control does hit: `daftracing/VBFlasher`
`ford/uds.py` is a public Ford/Mazda UDS keygen on the same `0xC541A9` /
`0x109028` core, and feeding it `reverse(seed || material)` reproduces
`mps_seed_key` for 2,048/2,048 seeds including every known vector. That settles
the byte ordering the per-byte reduction leaves implicit, and it is the
strongest provenance the two L3CE tiers have short of the car.

What the search cannot settle: the VIN→key KDF and the manufacturer master key.
Both are firmware/lockdown workstreams with a VIN or a dump as input. Stop
searching once the control hits and the owning module has been read — continuing
to search for a secret that is defined by the caller looks identical to failure
and produces "not found" claims that mean nothing.

A VIN is not that input on its own. Ran against the 1 MiB payload image, with
`IvfeRMazdA` at `0x21065` as the control that must hit: the VIN (full, prefix,
last-eight) is **absent**, there is **no DES S-box row** anywhere, `0xC541A9` /
`0x109028` never appear in either byte order, and the mask is not built by an
`oris ..,0x1090` / `ori ..,0x0028` pair. Two conclusions, both instrumented: the
PCM does not own the immobiliser crypto (so the KDF needs a KCM/immobiliser
dump, which this repo has never held), and a constant-grep over this ROM cannot
falsify any algorithm in it. Say "the artefact that consumes the VIN is not
here" rather than "the VIN does not work".

## Evidence classes — keep them in separate columns

| class | proves | does not prove |
|---|---|---|
| live ECU acceptance | the ECM's own comparison accepted that key for that level | memory-read permission, other seeds, other tiers |
| original-firmware P-code / static decode | the algorithm and selector mapping in the shipped image | live acceptance, hardware attempt limits, timing |
| initialized firmware simulation | the original dispatcher, comparison and state transition execute and accept | cold boot, real peripherals, the car |
| synthetic UDS model (`comms/synthetic_ecu.py`) | MUTS's client, state handling and ledger behave | anything about the ECM; the model's rules are MUTS's parameters |

The habitual failure is collapsing two rows into "Level 2 is solved". Report
them apart: algorithm solved, firmware-confirmed, never live-accepted, ROM read
still unanswered.

**A synthetic model proves your client, not the ECU's rules.** The synthetic ECU
accepts `27 03` on a fresh instance — it does not enforce Level 1 before Level 2,
and its attempt counter, cooldown and session expiry are MUTS's numbers. Assert
that gap as a *passing* check in the retest script, so a later reader cannot
mistake it for coverage.

## Retest recipe

`scripts/l3ce_sim_unlock_retest.py` (`OPERATOR_MODE=dev .venv/bin/python`, exits
non-zero on failure). Phases: read both materials out of the factory HEX;
cross-check the reduced transform against the shipped one and every known
vector; assert the tier separation; drive `SecurityAccessService` +
`L3CE_ENGINE_PROFILE` through accept/reject paths on the synthetic ECU with the
ECU's expected keys computed by the *re-derived* transform; then the same
exchanges through `RomReader` + `UnlockLedger`. `--with-matrix` adds the nine
provider rows above. Extend it rather than writing a new probe — the
two-implementation shape is the point, and a single-implementation test passes
even when both sides share a bug.

## Verifying a transform when there is no firmware to compare against

For the seven providers with no L3CE image behind them, the only honest offline
evidence is about **shape**, not provenance. Each check rules out one specific
way a ported transform can be wrong:

| property | what it rules out |
|---|---|
| deterministic for one seed | a transform that depends on a counter, clock or call order |
| per-byte map is a permutation over all 256 values | a lossy scramble that collapses distinct seeds onto one key |
| no cross-byte diffusion | pins it as a byte-wise scramble rather than a cipher, which is why a matrix pass says nothing about the ECB providers and vice versa |
| LFSR tier: every single-bit seed flip moves every key byte | a per-byte substitute masquerading as the LFSR |
| caller-key cipher: output equals an independent ECB of the zero-padded seed, truncated | padding, block size, key use and truncation — the only parts left once the primitive is a library call |
| no two comparable providers collide on one seed | a copy-paste duplicate transform, which would make one tier's key silently valid at another |

**Classify the transform before choosing the check.** Byte-wise scrambles
(`mzr-*`, `mazda-calibration`) are per-byte permutations and *fail* a diffusion
test by construction; the 3DES/AES providers *fail* a permutation test. Grouping
them wrong yields a batch of "failures" that are the harness's fault, and the fix
is the grouping, not the code under test. `mazda-calibration` takes a context
(`additional_data`) but is still byte-wise — `required_context` is not a signal
that a cipher is inside; only `mazda-immobilizer` and `mazda-manufacturer` are.

Block size follows the cipher, not the seed: 8 for 3DES, 16 for AES, zero-pad
the seed to the block and truncate back to seed length. A 6-byte seed padded to 8
raises "length of the provided data is not a multiple of the block length" from
AES. Context sizes are enforced: the immobiliser wants 24 bytes (3-key 3DES EDE),
manufacturer 16/24/32 — synthesise each from `provider.required_context`.

`--with-providers` runs all of this (~29 checks on top of `--with-matrix`). These
checks say a transform is a well-formed bijection of the right shape; they do not
say the ECM computes it, so never present them as provenance.

## Ledger semantics that change what you may say

- `UnlockLedger.spent` is `len(attempts)`: **successes are counted too, by
  design.** This is fail-closed pessimism, asserted by `tools/rom_read.py
  --self-test` and `tests/test_rom_read.py`. Report it as "N sends recorded, X of
  them failures" — never as "the ECM has X attempts left", and never "fix" it by
  patching `spent`. The only lever is an explicit `--attempt-budget` raise, which
  is a reviewed decision.
- `budget` is assumed (`budget_is_assumed: true`). The ECM's real limit and
  reset policy are unmeasured.
- Each entry's `at` is when the record was **written**. Migrated history carries
  the migration date. Take the real exchange time from the contemporaneous
  capture beside it, and treat a session whose preflight shows
  `PassThruOpen failed` / `ecu_responded: false` as having sent nothing.
- `0x27` requestSeed is free (48 in one session, no lockout). Only the key send
  costs.
