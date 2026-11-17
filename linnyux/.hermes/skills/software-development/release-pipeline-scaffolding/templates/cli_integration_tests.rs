//! Integration tests for the CLI binary.
//!
//! Shell out to the compiled binary via env!("CARGO_BIN_EXE_<bin>").
//! Every command needs at minimum: a passing-path test, a bad-arg-exits-2
//! test, and a missing-required-flag test.

use std::process::Command;

fn mk() -> Command {
    Command::new(env!("CARGO_BIN_EXE_mk"))
}

/// Unique temp path per test invocation (PID + name + nanos).
/// Stops two concurrent tests from clobbering each other.
fn tmp_path(name: &str) -> std::path::PathBuf {
    let mut p = std::env::temp_dir();
    p.push(format!(
        "cli_test_{}_{}_{}",
        std::process::id(),
        name,
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    p
}

#[test]
fn help_exits_zero() {
    let out = mk().arg("--help").output().expect("spawn --help");
    assert!(out.status.success());
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(stdout.contains("Phase N CLI"));
}

#[test]
fn unknown_command_exits_two() {
    let out = mk().arg("nosuch").output().expect("spawn nosuch");
    assert_eq!(out.status.code(), Some(2), "unknown command must exit 2");
}

#[test]
fn bad_arg_exits_two() {
    let out = mk()
        .args(["replay", "--ticks", "abc"])
        .output()
        .expect("spawn bad arg");
    assert_eq!(out.status.code(), Some(2));
}

#[test]
fn verify_smoke_emits_files() {
    let out_dir = tmp_path("verify");
    let out = mk()
        .args(["verify", "--out"])
        .arg(&out_dir)
        .args(["--horizons", "100kyr"])
        .output()
        .expect("spawn verify");
    assert!(out.status.success(), "verify must exit 0; got {:?}", out);
    let entries: Vec<_> = std::fs::read_dir(&out_dir)
        .unwrap()
        .filter_map(|e| e.ok())
        .collect();
    assert!(
        entries.len() >= 4,
        "expected >=4 files, got {}",
        entries.len()
    );
    let _ = std::fs::remove_dir_all(&out_dir);
}

#[test]
fn snapshot_and_load_roundtrip() {
    let snap = tmp_path("roundtrip");
    let snap_out = mk()
        .args(["snapshot", "--out"])
        .arg(&snap)
        .args(["--ticks", "5"])
        .output()
        .expect("spawn snapshot");
    assert!(snap_out.status.success());

    let load_out = mk()
        .args(["load", "--in"])
        .arg(&snap)
        .output()
        .expect("spawn load");
    assert!(load_out.status.success(), "load must exit 0");
    let _ = std::fs::remove_file(snap);
}
