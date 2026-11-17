//! <Project> Phase N CLI entry point.
//!
//! Invariants:
//! - Read-only against <core>/<engine>, except for run/snapshot/load which
//!   exercise the engine through its public surface.
//! - Every command returns a stable exit code: 0 = pass, 1 = fail, 2 = usage error.
//! - --json is a global flag, stripped from subcommand args before they parse.
//!
//! Failure modes:
//! - Any halt condition -> exit 1, error printed to stderr.
//! - Engine panic during run -> caught, reported as exit 1, never propagated.

use std::process::ExitCode;

mod commands;
mod output;

use commands::{audit, bench, init as init_cmd, load as load_cmd, metrics as metrics_cmd,
               replay, run as run_cmd, snapshot as snapshot_cmd, validate_canon,
               verify as verify_cmd, version};

const USAGE: &str = "\
<bin_name> — <Project> Phase N CLI

USAGE:
    <bin_name> <COMMAND> [OPTIONS]

COMMANDS:
    validate-canon    Validate the locked canon profile
    audit             Run conservation / nonnegativity / NaN-Inf checks
    replay            Replay a saved tick log and verify determinism
    bench             Micro-benchmark the deterministic core
    init              Write a starter config to --out PATH
    run               Step the world for --ticks N at --dt seconds
    snapshot          Save a world snapshot to --out PATH
    load              Load a world snapshot from --in PATH and validate
    verify            Run verification horizons and emit artifacts under --out DIR
    metrics           Export run metrics to --out PATH as JSON
    version           Print versions and build info

GLOBAL OPTIONS:
    --json            Emit machine-readable JSON output
    -h, --help        Print this help
    -V, --version     Print this CLI's version

EXIT CODES:
    0  success
    1  command failed (canon mismatch, audit halt, replay divergence, engine halt)
    2  usage error (unknown command or bad arguments)
";

fn main() -> ExitCode {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info")),
        )
        .with_writer(std::io::stderr)
        .init();

    let args: Vec<String> = std::env::args().skip(1).collect();
    let json_mode = args.iter().any(|a| a == "--json");

    if args.iter().any(|a| a == "-h" || a == "--help") {
        println!("{}", USAGE);
        return ExitCode::SUCCESS;
    }
    if args.iter().any(|a| a == "-V" || a == "--version") {
        return version::run(json_mode);
    }

    let cmd = match args.first().map(|s| s.as_str()) {
        Some(c) => c,
        None => { eprintln!("{}", USAGE); return ExitCode::from(2); }
    };
    // --json is global; strip it from subcommand args so they don't see it as unknown
    let sub_args: Vec<&str> = args.iter().skip(1)
        .filter(|a| a.as_str() != "--json")
        .map(|s| s.as_str())
        .collect();

    let result: Result<i32, i32> = match cmd {
        "validate-canon" => validate_canon::run(json_mode).map(|c| c as i32).map_err(|e| e as i32),
        "audit"          => audit::run(json_mode, &sub_args).map(|c| c as i32).map_err(|e| e as i32),
        "replay"         => replay::run(json_mode, &sub_args).map(|c| c as i32).map_err(|e| e as i32),
        "bench"          => bench::run(json_mode, &sub_args).map(|c| c as i32).map_err(|e| e as i32),
        "init"           => init_cmd::run(json_mode, &sub_args).map(|c| c as i32).map_err(|e| e as i32),
        "run"            => run_cmd::run(json_mode, &sub_args).map(|c| c as i32).map_err(|e| e as i32),
        "snapshot"       => snapshot_cmd::run(json_mode, &sub_args).map(|c| c as i32).map_err(|e| e as i32),
        "load"           => load_cmd::run(json_mode, &sub_args).map(|c| c as i32).map_err(|e| e as i32),
        "verify"         => verify_cmd::run(json_mode, &sub_args).map(|c| c as i32).map_err(|e| e as i32),
        "metrics"        => metrics_cmd::run(json_mode, &sub_args).map(|c| c as i32).map_err(|e| e as i32),
        "version"        => { version::run(json_mode); Ok(0) }
        other => { eprintln!("error: unknown command '{}'\n\n{}", other, USAGE); return ExitCode::from(2); }
    };

    match result {
        Ok(code)  => ExitCode::from(code as u8),
        Err(code) => ExitCode::from(code as u8),
    }
}
