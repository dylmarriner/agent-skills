# Paperclip + OpenCode Adapter Setup (kubuntux@100.93.75.87)

Captured from 2026-05-10 setup session. This covers getting Paperclip AI server running on a remote Ubuntu machine with OpenCode adapter, accessible via Tailscale.

## Environment

- Machine: kubuntux (100.93.75.87, x86_64, Ubuntu 24.04)
- Repo: `github.com/paperclipai/paperclip` at `~/paperclip/`
- OpenCode: `v1.14.43` at `~/.npm-global/bin/opencode`
- Embedded PostgreSQL (PGlite mode)

## Embedded PostgreSQL: ICU60 Library Fix

Paperclip's embedded PostgreSQL binary requires `libicui18n.so.60`, which is not available on Ubuntu 24.04 (it ships libicu74). Workaround:

```bash
# Download libicu60 from Ubuntu 20.04 archive
cd /tmp
wget http://archive.ubuntu.com/ubuntu/pool/main/i/icu/libicu60_60.2-3ubuntu3.2_amd64.deb
mkdir -p icu60-extract
dpkg-deb -x libicu60_60.2-3ubuntu3.2_amd64.deb icu60-extract/
cp icu60-extract/usr/lib/x86_64-linux-gnu/*.so.60.2 ~/.local/lib/
cd ~/.local/lib
for f in *.60.2; do ln -sf "$f" "${f%.60.2}.60"; done
```

Then run with: `LD_LIBRARY_PATH=/home/$USER/.local/lib pnpm dev:once`

## Tailscale Binding (No socat Needed)

Paperclip only listens on `127.0.0.1` by default. To make it accessible via Tailscale:

```bash
cd ~/paperclip
pnpm dev:once -- --tailscale-auth
```

This flag auto-detects the Tailscale IP via `tailscale ip -4` and binds to it. The server will listen on `0.0.0.0:3100`.

**Do NOT use socat** to forward ports — the `--tailscale-auth` flag handles it natively. The dev-runner code at `scripts/dev-runner.ts` line 149-170 handles this.

## Hostname Authorization

When accessing via Tailscale IP for the first time, Paperclip returns:

```json
{"error":"Hostname 'X.X.X.X' is not allowed for this Paperclip instance."}
```

Fix:
```bash
cd ~/paperclip
pnpm paperclipai allowed-hostname <TAILSCALE_IP>
# Restart paperclip for the change to take effect
```

## Result

Access at `http://<TAILSCALE_IP>:3100` — serves both API and UI:
- API health: `/api/health` → `{"status":"ok","version":"0.3.1"}`
- UI: `/` → Paperclip board interface

## Running in Background

The `pnpm dev:once` command runs as a foreground process. For persistent background operation:

```bash
nohup pnpm dev:once -- --tailscale-auth > ~/paperclip.log 2>&1 &
```

Or use a systemd user service if available.

## Paperclip + OpenCode Adapter

Paperclip auto-detects OpenCode for its `opencode-local` adapter. It runs heartbeat checks that execute `opencode` commands. If OpenCode isn't in the PATH when Paperclip runs, heartbeats fail with:

```
Error: Command not found in PATH: "opencode"
```

Fix: ensure `~/.npm-global/bin` is in the PATH, or start Paperclip with the full PATH.

## Common Pitfalls

- **Multiple Paperclip instances:** The dev-runner checks for existing processes before starting. If a previous run didn't clean up, `kill` the leftover node processes first.
- **pnpm dev:once exiting immediately:** Usually means the embedded postgres failed (check LD_LIBRARY_PATH) or the server port is already in use.
- **Hostname not allowed after restart:** The `allowed-hostname` setting persists in the database. Actual issue is usually wrong port or Tailscale not running on the client side.
- **Port 3100 vs 3101 confusion:** Paperclip defaults to 3100. If socat was used previously on 3101, the user may try the wrong port.
