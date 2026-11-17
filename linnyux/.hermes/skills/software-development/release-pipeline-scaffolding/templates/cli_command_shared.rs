//! Shared helpers for subcommand arg parsing.
//!
//! Put shared helpers in `commands/shared.rs`, not in one command module
//! that siblings import. Rust will tell you the function is private and
//! you'll waste a compile cycle.

use std::path::PathBuf;

/// Parse `--flag VALUE` or `--flag=VALUE` from the args slice.
/// Returns the first match as a PathBuf.
pub fn parse_path_arg(args: &[&str], flag: &str) -> Option<PathBuf> {
    let mut i = 0;
    while i < args.len() {
        if args[i] == flag && i + 1 < args.len() {
            return Some(PathBuf::from(args[i + 1]));
        }
        if args[i].starts_with(&format!("{}=", flag)) {
            return Some(PathBuf::from(&args[i][flag.len() + 1..]));
        }
        i += 1;
    }
    None
}

/// Reconstruct a panic message from `catch_unwind`'s opaque payload.
/// Catches both `&'static str` and `String` payloads; falls back to a marker.
pub fn panic_message(payload: &Box<dyn std::any::Any + Send>) -> String {
    if let Some(s) = payload.downcast_ref::<&'static str>() {
        s.to_string()
    } else if let Some(s) = payload.downcast_ref::<String>() {
        s.clone()
    } else {
        "<non-string panic payload>".to_string()
    }
}
