# rust-cli-scaffold — adding a CLI crate to an existing Cargo workspace

Use this scaffold when the audit reveals that a workspace needs a Phase 7-style
CLI surface (validate-canon, audit, replay, bench, version) but the workspace
doesn't have one. Tested against the `mk_cli` crate pattern from the Maer-Ken
workspace.

## What's in the box

```
src/
├── main.rs                # dispatcher — handles --help/--version/--json, routes to commands
├── output.rs              # human/JSON output helpers
└── commands/
    ├── mod.rs             # pub mod declarations
    ├── cmd_a.rs           # simple command, no args (e.g. validate-canon)
    ├── cmd_b.rs           # command with --flag <value> parsing
    └── version.rs         # version info
tests/
└── cli.rs                 # integration tests shelling out to the binary
```

## How to use

1. Copy this directory to `<workspace>/<crate_name>/`.
2. Rename `*.template` files (strip the `.template` suffix).
3. Find-and-replace `<crate_name>`, `<bin_name>`, `<cmd_a>`, `<cmd_b>`, `<dep_a>`, `<dep_b>`, `<dep_for_data>`, `<Type>` with your real values.
4. Add the crate path to the workspace's root `Cargo.toml` `members = [...]` list.
5. `cargo build -p <crate_name>` — verify it compiles.
6. `cargo test -p <crate_name>` — verify the integration tests pass.

## The gotchas the templates document (GOTCHA 1–4 in main.rs and cmd_b.rs)

These are the four issues that always cost a build cycle when adding a new CLI
crate. The templates inline the fixes so you don't have to rediscover them:

1. **`--json` is global — strip it from subcommand args.** If you pass `args` straight through, subcommand parsers see `--json` and reject it as an unknown flag.
2. **Subcommand `run()` returns `Result<u8, u8>`.** Normalize to `i32` for `ExitCode::from()`. Trying to keep `Result<(), i32>` and `.map_err` everything trips the borrow checker.
3. **Don't pre-filter flags out of the global positional slice.** Subcommands own their own flag parsing. If you strip `--ticks` in `main.rs`, the subcommand gets only `1000` and chokes.
4. **Flag-with-value parsers need `i += 2`.** `match args[i] { "--foo" => { use args[i+1]; ... } }` — forgetting the `i += 2` causes the value to be parsed as the next flag.
