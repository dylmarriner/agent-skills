# Self-Hosting Build Reference

## Prerequisites

- **Rust toolchain** — matches rust-toolchain.toml (nightly-2025-12-04, auto-installed by rustup)
- **Node.js** — v18+ (verified: v24.15.0)
- **pnpm** — v10+ (installed via `corepack enable`)

## Full Build Sequence (Linux x86_64)

```bash
# Clone
git clone https://github.com/BloopAI/vibe-kanban.git
cd vibe-kanban

# JS deps
pnpm i

# Frontend production build
pnpm --filter local-web build

# Rust server binary
cargo build --release --bin server
```

## Binary Locations

| Binary | Source | Build Command | Output |
|--------|--------|---------------|--------|
| Main server | `crates/server/` | `cargo build --release --bin server` | `target/release/server` |
| MCP server | `crates/server/` | `cargo build --release --bin vibe-kanban-mcp` | `target/release/vibe-kanban-mcp` |
| Review CLI | `crates/review/` | `cargo build --release --bin review` | `target/release/review` |

## Frontend Output

Built to `packages/local-web/dist/`. The server binary serves these static files — no separate web server needed.

## Running

```bash
# Default (localhost:3000, auto-assigns port if 3000 is taken)
./target/release/server

# Custom port + expose on LAN
PORT=3001 HOST=0.0.0.0 ./target/release/server
```

## Runtime Behaviour

- **Port auto-assign**: If `PORT` is not set or port 0, the OS assigns a free port. Check startup log for `Main server on :XXXX`.
- **Port conflicts**: When the specified port is in use, the server exits with `AddrInUse`. Use `ss -tlnp` or `lsof -i :PORT` to find the conflicting process.
- **First run**: No config found → auto-creates `config.json` and `profiles.json` under the asset directory. `VK_SHARED_API_BASE` unset → remote features disabled (local-only operation).
- **Data directory**: `~/.local/share/ai.bloop.vibe-kanban/` — contains SQLite DB (`db.v2.sqlite`), config, profiles, credentials, and signing keys.
- **Health check**: `curl http://localhost:<port>/health` → `200` when the server is ready.
- **Runtime dependencies**: `git` — required for worktree operations (PR creation, branch management). The server reads from `.gitconfig` for user identity.
- **Graceful shutdown**: Ctrl+C or SIGTERM cleans up running agent processes and closes the SQLite connection.

## Docker Build

The `Dockerfile` in the repo root handles both frontend + Rust in a multi-stage build:

```bash
docker build -t vibe-kanban:selfhost .
docker run -p 3000:3000 vibe-kanban:selfhost
```

## Notes

- Rust nightly toolchain is required (pinned in `rust-toolchain.toml`) — rustup auto-downloads it
- Build takes **several minutes** first time (30+ workspace crates)
- SQLx uses offline mode — no DB connection needed at build time
- The server embeds an Axum HTTP stack + embedded assets — single binary deployment
