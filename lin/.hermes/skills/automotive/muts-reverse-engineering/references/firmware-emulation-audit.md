# Offline firmware-emulation audit — full procedure

Depth for "resume / start the full stack", auditing a reconstructed ECU runtime,
and answering "is it ready to use live" from emulation evidence. The always-on
rules are in SKILL.md; this is the long form.

## Resolving the task first

For any request to resume or "start the full stack", resolve the task from the
repo's program-of-record plan and latest evidence before acting. Distinguish an
ECU firmware/emulation workstream from launching the MUTS desktop application,
and do not guess when those interpretations imply different actions. Inspect
`git status --short --branch` first and preserve dirty work; do not reset, clean,
stash, overwrite, or stage user changes. Report the active branch and the
concrete blocker briefly when execution cannot safely proceed.

## Auditing a reconstructed runtime

First identify the exact original firmware, emulator/harness revision, scenario
and saved evidence; distinguish a rebuilt/modified image from original-firmware
execution with reconstructed services. Inspect the scenario implementation, the
independent auditor, fixture address ranges and the evidence JSON before
trusting a status report.

Then, in this order:

1. Authenticate the actual mapped source bytes — not just the project name.
2. Prove every fixture region lies wholly within synthetic RAM and intersects no
   mapped program-memory block.
3. Validate every modeled-helper return against a decoded direct call, LR
   fall-through, and the intended helper target.
4. Give each substituted service/peripheral explicit provenance, a bounded
   contract, and a fail-closed path for unknown callers or operations.
5. Bind transcripts to the SHA-256 of the explicitly selected harness revision.
6. Test primary and reopened-export tampering independently, so one rejected
   input cannot mask a missing check on the other.

Re-running saved-evidence auditors is **transcript verification**, not fresh
emulator execution — label it that way. When a harness changes, run fresh
headless emulation with new private output paths, capture console output only
into ignored/private evidence, and derive follow-up inputs from that evidence
without printing security material into public logs or docs.

Report initialized execution, reconstructed startup, and complete cold boot as
separate milestones. Do not infer full ECU correctness from a successful
diagnostic path. Save findings, exact commands, source/artifact hashes, limits,
test outcomes and evidence class in the domain documentation and index,
following repository policy.

## Seed→key confirmation on original firmware

Exercise the original firmware's fresh-seed path, calculate each response
independently, and require the original dispatcher/comparison and completion path
to accept it; pair valid cases with mutated-key rejections and same-instance
valid-key recovery. Authenticate firmware ranges and synthetic-RAM boundaries
before each run, and keep exact tuples in private evidence. Replaying a
saved-sequence driver is a useful fresh emulator check; re-running a transcript
auditor alone only verifies recorded evidence.

State the conclusion narrowly: the tested transform is confirmed for the
authenticated application path and modeled helper boundary — not for cold boot,
physical timing, hardware attempt limits, or live ECU acceptance.

## Answering "is it ready to use live"

Answer in two halves — what the offline evidence establishes, then the gates that
remain closed — taken from the newest `docs/ecu_reads/l3ce_live_test_readiness_*.md`
and its machine-readable readiness JSON, rather than inferred from the algorithms.
Keep the two halves from bleeding into one verdict.

## Pitfalls

- Zeroing a fixture range based at a RAM subregion can still cross into mapped
  ROM or outside the declared RAM window; validate the full half-open range
  before writing.
- A transcript hash field is not provenance unless the auditor compares it with
  the selected source revision.
- Corrupt and test each transcript input separately, because a single early
  failure can hide a missing validation on a later input.
- Do not call a saved-transcript audit a fresh firmware run; it only checks
  existing outputs.
- Keep exact firmware-derived security material in protected evidence; public
  reports state case counts, outcomes, source offsets and private evidence
  references without raw tuples.

## REA-assisted review

First inspect the ELF/provenance and verify it is a derived analysis container
with sparse source mappings — not a rebuilt or flashable image. Use the
project-specific launcher so its processor profile and seed file are applied:
`tools/rea_l3ce.sh inspect-artifact <analysis.elf> --format json`, then
`tools/rea_l3ce.sh function <analysis.elf> <address> --provider ghidra
--snapshot <snapshot.json> --format json` on the algorithm entry, material
selector, transform, and the relevant dispatcher/comparison functions. Filter the
output to the procedure, pseudocode/assembly, callers, callees and provenance
fields instead of dumping the full evidence envelope — the large value-flow
sections otherwise obscure the finding.

Trace selector return values into the material-table offset and length, then
trace transform output into the original comparison and the accepted-state
transition before summarising the algorithm.

- `inspect-artifact` inventories the container; it performs no
  firmware-semantic analysis.
- Confirm the ELF header, Ghidra-selected language, source-range provenance and
  seed-import outcome separately: a generic architecture label plus a configured
  VLE profile does not prove the header declares VLE, and seeded function starts
  are analyst assertions, not discoveries.
- Treat a broad `rea doctor` failure by individual provider check; unrelated
  missing engines do not negate a healthy Ghidra provider, and a healthy provider
  does not certify the ECU model.
- REA deepens targeted static review; it is not a claim that every function,
  peripheral, startup path or runtime behaviour has been checked.

## Interpreting the request

When the active plan and surrounding evidence clearly refer to UDS seed→key, use
that as the default reading of a misspelled "seek key". Do not derail the task
with a question about key fobs unless the request actually points at immobilizer
enrollment or remote-key behaviour — that is a distinct workstream, documented in
`references/keyless-entry-and-immobilizer.md`.
