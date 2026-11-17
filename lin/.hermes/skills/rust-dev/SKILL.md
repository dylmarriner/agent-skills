# Rust Development

Use for Rust apps, CLIs, services, workers, crates, MCP tools, and performance-sensitive code.

Rules:
- Prefer safe Rust.
- Do not introduce unsafe unless explicitly approved.
- Do not clone just to silence the borrow checker.
- Avoid unwrap/expect in production paths.
- Do not add crates unless justified.
- Preserve public APIs unless the task requires changing them.
- Check trait bounds, lifetimes, Send/Sync, and async boundaries.

Validation:
- cargo fmt --check
- cargo check --all-targets --all-features
- cargo clippy --all-targets --all-features -- -D warnings
- cargo nextest run, or cargo test
- cargo audit / cargo deny check when dependencies change
