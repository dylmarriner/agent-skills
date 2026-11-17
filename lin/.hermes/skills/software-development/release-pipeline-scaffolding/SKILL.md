---
name: release-pipeline-scaffolding
description: Build or repair the release-pipeline surface of a long-lived engineering project — CLI command surface, regenerated artifacts, honest-status documentation, multi-track harness/boundary docs, and warning cleanup. Use after a canon-audit reveals the pipeline is incomplete or stale, or when bringing a project up to a "release-ready" gate per an authoritative checklist (e.g. Phase N release-readiness, v1.0 checklist).
metadata:
  category: software-development
---

# Release Pipeline Scaffolding

The post-audit follow-on. After `repo-canon-audit` (or any roadmap/blueprint audit) identifies what is missing, this skill is the construction playbook for closing the gap. Three pillars:

1. **CLI command surface** that the release gate actually requires
2. **Regenerated artifacts** that are honest, versioned, and consent-preserving
3. **Honest-status documentation** that separates "pipeline in place" from "engine passing"

A fourth, recurring pattern when a repo serves two parallel product tracks (world engine + human sim, frontend + backend, OSS + proprietary): the **HARNESS boundary doc** that locks which crate may import what.

---

## When to use

- A canon/roadmap audit (`repo-canon-audit`) found missing CLI commands, missing artifacts, missing docs
- A "release-readiness" or "v1.0" gate document enumerates a checklist and most of it is unmet
- The repo has a stale `artifacts/` dir with values that no longer match the current source
- Two product tracks share one repo and people keep conflating them
- The build emits warnings that the gate doc says must be zero

**Do not** use this skill for:
- Routine feature work that doesn't touch the release surface
- Audit-only work (use `repo-canon-audit` for that)
- Performance work unrelated to the release gate

---

## Pillar 1: CLI command surface

### Find the spec, don't invent

Before writing any CLI code, locate the authoritative command spec. For Rust projects, this is usually in `docs/roadmap/`, a `*RELEASE_READINESS*` doc, or a `*_EXECUTION_ROADMAP*` doc. **Read the spec verbatim** — don't paraphrase the command list from memory. Phase 7 §3.1 of a real project looked like:

```rust
pub enum Command {
    Init { config_path: PathBuf },
    Run { ticks: u64, dt_seconds: u64 },
    Snapshot { path: PathBuf },
    Load { path: PathBuf },
    Verify { duration: VerificationDuration },
    Metrics { output_path: PathBuf },
}
```

That spec tells you the field names, the types, and the order. Mirror it.

### Scaffold shape

For a Rust `app/` crate that fronts engine work, this is the proven shape:

```
apps/mk_cli/
├── Cargo.toml              # mk_engine, mk_core, blake3, bincode, serde, tracing
├── src/
│   ├── main.rs             # arg dispatch, --json global flag, exit codes 0/1/2
│   ├── output.rs           # print_human, print_human_err, print_json
│   ├── commands/
│   │   ├── mod.rs          # pub mod list
│   │   ├── shared.rs       # parse_path_arg shared across all flag-taking commands
│   │   ├── validate_canon.rs
│   │   ├── audit.rs
│   │   ├── replay.rs
│   │   ├── bench.rs
│   │   ├── init.rs
│   │   ├── run.rs
│   │   ├── snapshot.rs
│   │   ├── load.rs
│   │   ├── verify.rs
│   │   ├── metrics.rs
│   │   └── version.rs
│   └── tests/
│       └── cli.rs          # integration tests via env!("CARGO_BIN_EXE_mk")
```

### Arg parser — hand-rolled is fine

Clap is recommended in most release-readiness docs but a hand-rolled parser is acceptable **if** it:

- Strips `--json` from subcommand args (global flag must not appear in sub-arg parse)
- Honors `--key VALUE` and `--key=VALUE` for path-like args
- Returns `Result<u8, u8>` from each command (0=pass, 1=halt/fail, 2=usage error)
- Has `--help` that lists every command and `--version` for the binary version

Put `--json` filtering in `main.rs` and a single `parse_path_arg(args, "--flag")` helper in `commands/shared.rs`. The shared helper is mandatory — copying it into each command module guarantees one will be wrong and break the rest.

### Panic-catching is required for engine-facing commands

Any command that calls into the engine must wrap calls in `catch_unwind(AssertUnwindSafe(...))`. The engine can panic on bad state, and a CLI that panics gives the user no recourse. The pattern:

```rust
let result = catch_unwind(AssertUnwindSafe(|| world.step_world(dt)));
match result {
    Ok(Ok(())) => { /* tick ok */ }
    Ok(Err(e)) => { halt_msg = Some(format!("step_world returned error at tick {}: {}", t, e)); break; }
    Err(pe) => { halt_msg = Some(format!("step_world panicked at tick {}: {}", t, panic_message(&pe))); break; }
}
```

Helper:
```rust
fn panic_message(payload: &Box<dyn std::any::Any + Send>) -> String {
    if let Some(s) = payload.downcast_ref::<&'static str>() { s.to_string() }
    else if let Some(s) = payload.downcast_ref::<String>() { s.clone() }
    else { "<non-string panic payload>".to_string() }
}
```

### Tests for CLI commands

Use Rust's `env!("CARGO_BIN_EXE_<bin>")` so the test binary spawns the actual built binary, not a re-build. The standard smoke-test template:

```rust
fn mk() -> Command { Command::new(env!("CARGO_BIN_EXE_mk")) }

fn tmp_path(name: &str) -> std::path::PathBuf {
    let mut p = std::env::temp_dir();
    p.push(format!("test_{}_{}_{}", std::process::id(), name,
        std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()));
    p
}

#[test]
fn verify_smoke_emits_files() {
    let out_dir = tmp_path("verify");
    let out = mk().args(["verify", "--out"]).arg(&out_dir).args(["--horizons", "100kyr"]).output().expect("spawn");
    assert!(out.status.success(), "verify must exit 0; got {:?}", out);
    let entries: Vec<_> = std::fs::read_dir(&out_dir).unwrap().filter_map(|e| e.ok()).collect();
    assert!(entries.len() >= 4, "expected >=4 files, got {}", entries.len());
    let _ = std::fs::remove_dir_all(&out_dir);
}
```

Every command needs at minimum: a passing-path test, a bad-arg-exits-2 test, a missing-required-flag test.

---

## Pillar 2: Regenerated artifacts with consent-preserving archival

### The wrong move

The user has committed artifacts. You run your new emitter and it produces a slightly different file. You overwrite. The user has now lost the historical record. **This will get you blocked.**

### The right move

1. **Detect committed artifacts** before regenerating: `ls artifacts/`, `git ls-files artifacts/`
2. **If they exist, move them to an archive subdir first**: `mkdir -p artifacts/archive-<date>/ && mv artifacts/<files> artifacts/archive-<date>/`
3. **Then** regenerate into `artifacts/`
4. **Document the archive** in the relevant doc (`VERIFICATION_REPORTS.md`, etc.) so the next session knows it exists

The date stamp in the archive dir name matters — when this happens again in 6 months, you want to know which archive is which.

### Honest-status discipline

The artifact file's content reflects engine state, which may be broken. Do not paper over:

- `verification_100kyr.json` reports `success: false`? **Write that** in the docs, don't hide it
- Energy drift is 3.3e36? Write that
- 0 extinctions? Write that

The release pipeline can be **complete** while the engine is **not yet release-ready**. These are different claims. Conflating them is a release-readiness lie.

### Artifacts you should NOT commit

If artifacts are fully regenerable from source (bincode snapshots, derived JSON), keep them out of git and put a `make artifacts` / `mk verify` instruction in the README. If they encode results of a specific expensive run (compliance proof, signed release), keep them in.

---

## Pillar 3: Honest-status documentation

### The pattern

Every release-pipeline doc should answer **three questions** explicitly:

1. What is the pipeline state? (CLI ✓, artifacts ✓, docs ✓)
2. What is the engine state? (Phase 6 gate ✗ — energy drift 3.3e36)
3. What is the next unit of work? (Fix the energy ledger closure)

The first two are different. A doc that says "release pipeline complete" but also "engine not yet passing" is **not** contradictory — it's accurate. A doc that says "release complete" without the engine caveat is dishonest.

### What to update

When you finish a release-pipeline pass, the docs to write or update:

- `docs/VERIFICATION_REPORTS.md` (or equivalent) — pipeline state + engine state + next step
- `docs/MK_<VERSION>_RELEASE_STATUS_<DATE>.md` (or equivalent) — section-by-section checklist of the gate
- `README.md` — only the status line and the regenerate command; do not duplicate
- A **dated status note** in the repo, not the README, so the next session has a timestamp anchor

### A 2026-04-02 archive proves this matters

A real-world consequence: a project's `artifacts/canon_digest.txt` changed value between two emitter runs (different canon-derivation paths). If the old value had been overwritten without archival, there would be no record that the canon-derivation path ever differed. The archive subdir is the audit trail.

---

## Pillar 4: HARNESS boundary docs (for two-track repos)

When a repo serves two products (e.g. world engine + human sim, frontend + backend, OSS core + commercial plugin), and they share crates, the boundary must be **explicit and locked**, not implicit.

### Template

A HARNESS.md has:

1. **The boundary** — which crate/file belongs to which track, in a table
2. **The authority** — point to the locked roadmap doc for each track
3. **Naming rules** — if the gate doc has them (e.g. "Maer'Ken = world, Marr'Kena = planet, never reversed")
4. **Directory contract** — the canonical layout, with which dirs are shared vs track-specific
5. **Forbidden imports** — list the imports that will fail the build guard
6. **Allowed imports** — list the imports that are fine
7. **Cross-track work** — how to handle a change that legitimately touches both
8. **When in doubt** — default to the authority doc, file a cross-track note, don't pretend

### Where to put it

`HARNESS.md` at the repo root, OR `docs/HARNESS.md`. Root is more visible but `docs/` is more discoverable. Pick the one that matches the rest of the doc layout.

### The "do not pretend they agree" rule

If a roadmap doc (track A authority) and a canon doc (track B authority) disagree, the HARNESS must say so. The wrong move is to silently harmonize. The right move is to file a cross-track note and ask.

---

## Slow builds: offload to background

Any `cargo build --workspace --release` on a non-trivial Rust project takes 5+ minutes. Run it in the background and keep working:

```bash
# In foreground, but backgrounded via the terminal tool:
cargo build --workspace --release 2>&1 | tee /tmp/release_build.log &
# Or use the background terminal tool with notify_on_complete=true
```

Patterns:
- **Always `tee` to a log file** so the output is recoverable if the pipe gets SIGTERM'd
- **Use `head -60` of warnings**, don't try to read all 90 in the chat
- **Fix warnings incrementally** by file/crate, not by line — the fix path is the unit
- **Do a focused subset build** (`cargo build -p mk_core -p mk_engine -p mk_cli`) to verify engine-path fixes don't regress while the full build runs

### Output of a release build

You will see a line like:
```
cargo build: 0 errors, 90 warnings (5 crates)
```

This is the gate signal. **0 errors with warnings ≥ 0 is the only state you can ship from.** Warnings count breakdown by crate tells you which surface to focus on.

---

## Common pitfalls

- **Inventing CLI commands** instead of reading the spec — you'll add commands the gate doc doesn't require and miss the ones it does
- **Putting shared helpers in one command module** then importing from siblings — Rust will tell you the function is private. Put shared helpers in a `commands/shared.rs` from the start
- **Overwriting committed artifacts** without archival — user will block you. Move to `archive-<date>/` first
- **Writing "release complete"** when only the pipeline is complete — dishonest. Use the three-question structure
- **Treating zero-warning as easy** — 90 warnings across 5 crates takes an hour of focused work. Plan for it
- **Failing the long-horizon test** and claiming it doesn't count — it counts. Surface it as an untested blocker per `repo-canon-audit`'s phase-gate workflow
- **Skipping the panic catcher** on engine calls — the engine will panic, the CLI will die, the user will be angry
- **Committing derived artifacts** when the source can regenerate them — bloats git history, makes the next regenerate a force-push
- **Forgetting to wire the new CLI command in main.rs** — the command exists, the test passes, but `mk <cmd>` returns "unknown command". Re-read main.rs after adding a new file

---

## Verification

Before claiming the work complete:

- [ ] All commands in the spec are implemented and listed in `--help`
- [ ] All commands have at least one passing-path test, one bad-arg test, one missing-flag test
- [ ] `cargo build --workspace --release` exits 0 (engine path zero warnings; frontend warnings are out of scope if HARNESS says so)
- [ ] All non-archived committed artifacts are regenerable from a single command
- [ ] `docs/VERIFICATION_REPORTS.md` (or equivalent) explicitly states pipeline state AND engine state
- [ ] A dated status note exists in the repo for this pass
- [ ] HARNESS.md (if applicable) lists forbidden and allowed imports
- [ ] No `_ = var` or `let _unused = ...` workarounds in commands/* to silence real warnings

---

## Related skills

- `repo-canon-audit` — run this first to find what's missing
- `simplify-code` — after the pass, parallel 3-agent cleanup of the new code
- `test-driven-development` — if the spec gives clear test cases, use RED-GREEN-REFACTOR for new commands
- `requesting-code-review` — before committing the new CLI surface

## Support files

- `templates/cli_crate_Cargo.toml` — Cargo.toml skeleton for an `app/` crate
- `templates/cli_main_rs.rs` — `src/main.rs` skeleton with global `--json` flag, exit codes, and command dispatch
- `templates/cli_command_shared.rs` — `parse_path_arg` and `panic_message` helpers (put these in `commands/shared.rs` from the start, not after a compile error)
- `templates/cli_integration_tests.rs` — `tests/cli.rs` skeleton with the unique-temp-path pattern
- `references/artifact_archive_workflow.md` — step-by-step consent-preserving archive workflow with the real `canon_digest.txt` story
