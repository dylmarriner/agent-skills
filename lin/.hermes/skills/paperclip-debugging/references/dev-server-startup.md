---
name: paperclip-dev-server-startup
description: Start Paperclip’s local dev server cleanly in authenticated/private Tailscale-friendly mode, eliminate stale duplicate instances, and verify it is listening and healthy on port 3100.
metadata:
  category: software-development
  tags: [paperclip, dev-server, tailscale, auth, port-3100, singleton-verification]
---

# Paperclip Dev Server Startup

Use this skill when the user wants Paperclip started locally and verified in authenticated/private mode, especially when prior launches left stale processes behind or port 3100 is already occupied.

## Goal

Bring Paperclip up on port 3100 in Tailscale-accessible private/authenticated mode, confirm the health endpoint returns OK, and ensure there is only one live instance.

## When to use

- User asks to start Paperclip cleanly
- User asks for Tailscale/private/authenticated mode
- Port 3100 may already be in use
- There may be multiple stale dev runner processes
- You need a verified live instance, not just a launch attempt

## Bind Modes

The dev runner supports these `--bind` modes (defined in `scripts/dev-runner.ts`):

| Mode      | Effect | Best For |
|-----------|--------|----------|
| `loopback` | Binds to 127.0.0.1 only, no auth | Local-only dev |
| `lan`      | Binds to 0.0.0.0, authenticated/private | LAN access |
| `tailnet`  | Binds to the Tailscale interface IP, authenticated/private | Tailscale-only access |
| `custom`   | Binds to a user-specified host via `--bind-host` | Advanced setups |

Legacy aliases:
- `--tailscale-auth` (or `--authenticated-private`) → aliases to `--bind lan`, NOT `tailnet`. Use `--bind tailnet` if you specifically want the Tailscale IP.

## Procedure

1. Inspect the current state first.
   - Check listeners on port 3100.
   - Check for existing Paperclip dev processes.
   - If an instance is already healthy and matches the requested mode, verify it instead of starting another.

2. Remove stale or duplicate Paperclip instances.
   - Kill Paperclip-related processes: `pkill -f "paperclip"; pkill -f "tsx.*index.ts"`
   - Recheck port 3100 after cleanup.

3. Start the dev server in the correct mode.
   - From the repo root, use one of:
     - **Tailnet (Tailscale IP):** `npm_config_bind=tailnet pnpm dev:once` (env var approach, works with pnpm arg passthrough)
     - **LAN (0.0.0.0):** `pnpm dev --tailscale-auth` (legacy alias for `--bind lan`)
   - The dev runner will print the bind mode on startup, e.g.:
     `[paperclip] dev mode: authenticated/private (bind=tailnet)`
   - After startup completes, the server banner shows the exact bind address:
     ```
     Bind             tailnet (100.x.x.x)
     API              http://100.x.x.x:3100/api
     ```

4. Wait for the real server to come up.
   - Startup may include plugin SDK build, workspace preflight, and embedded Postgres initialization.
   - On NTFS filesystems, server startup takes 30-60s. Do not treat the launch as complete until the actual server is listening.
   - Watch for the `Server listening on` log line.

5. Verify health and mode.
   - Health endpoint responds on the bind address (use the Tailscale IP, not localhost):
     `curl http://<TAILSCALE_IP>:3100/api/health`
   - Expected JSON:
     - `status: "ok"`
     - `deploymentMode: "authenticated"`
     - `bootstrapStatus: "ready"`
     - `bootstrapInviteActive`: (true/false)
   - The full UI is also served at the same address (HTML 200):
     `curl -s http://<TAILSCALE_IP>:3100/`

6. Ensure singleton state.
   - Re-run process checks to confirm there is only one live Paperclip dev instance.
   - If more than one remains, stop the extras and re-verify.

## Useful checks

- Listener check:
  - `ss -ltnp '( sport = :3100 )'`
- Process check:
  - `ps -ef | grep -E '[p]npm dev|[t]sx .*dev-runner|[n]ode .*src/index.ts'`
- Health check:
  - `curl -fsS http://<TAILSCALE_IP>:3100/api/health`
- Server logs:
  - The server prints a banner with bind address, mode, and all URLs on startup

## Pitfalls

- **`--tailscale-auth` is NOT the same as `--bind tailnet`.** The legacy flag aliases to `--bind lan` (binds 0.0.0.0, not the Tailscale IP). Use `--bind tailnet` or `npm_config_bind=tailnet` for true Tailscale-interface binding.
- The dev runner may spawn multiple wrapper processes during startup; focus on the actual server process bound to port 3100.
- A healthy health endpoint is the real completion signal, not merely a running npm command.
- If the server is still building or initializing embedded Postgres, wait and re-check before concluding failure.
- Better Auth may warn about base URL auto-detection; this is cosmetic when the bind address is set correctly.
- On NTFS: `npx vite build` hangs — use `node node_modules/vite/bin/vite.js build` instead. Server startup from NTFS takes 30-60s. Delete both `rm -rf ui/dist ui/node_modules/.vite` after clean builds.
- If you need to pass `--bind` through pnpm, set the env var `npm_config_bind=tailnet` instead — pnpm's `--` passthrough may not work reliably with the dev runner's arg parser.
- **Auto port fallback.** If port 3100 is busy (even by a non-Paperclip process), the dev runner does NOT fail — it logs `WARN: Requested port is busy; using next free port (requestedPort=3100, selectedPort=3101)` and binds to 3101 (or 3102, etc.). Always check the server banner's `Server` line (`HTTP_PORT` env var or the printed port) to confirm which port it actually chose. Do not assume 3100. If the old process on 3100 is a stale Paperclip, use `pkill -f "paperclip"; pkill -f "tsx.*dev-runner"` to free it — but if it's a non-Paperclip service, just use the fallback port.
- **Starting via `pnpm dev` (without `dev:once`).** This triggers watch mode and runs indefinitely. Use `background=true` in the terminal tool (not `&`) to keep it alive while you run health checks. `pnpm dev:once` is preferred for short experiments since it exits after the server starts.
- **Health checks on the wrong port are misleading.** If you curled 3100 but the server is on 3101, you'll get connection refused and incorrectly conclude the server is down. Always read the banner's `Server` line first.
- **pnpm install required after repo update.** Pulling latest master or switching branches breaks workspace symlinks. The `node_modules/@paperclipai/` directory won't contain the expected packages. Trying to start the server produces `ERR_MODULE_NOT_FOUND: Cannot find package '@paperclipai/adapter-acpx-local'` from `server/src/adapters/registry.ts`. Fix: run `pnpm install` from the repo root (~40s). The shared build step will also update opencode.json with latest adapter versions.
- **sqlite3 native module may not be compiled for the current Node version.** pnpm 9.x ignores build scripts by default for packages not in `pnpm.onlyBuiltDependencies`. The symptom: the dev-watch process crashes with `Error: Could not locate the bindings file. Tried: ...build/Release/node_sqlite3.node`. Fix: `cd node_modules/.pnpm/sqlite3@*/node_modules/sqlite3 && pnpm rebuild`. The compiled module appears at `build/Release/node_sqlite3.node` (~2.2MB). For permanence, add `sqlite3` to `pnpm.onlyBuiltDependencies` in root `package.json`.
- **Dev-runner silent exit on existing instance.** When you start `dev-runner.ts watch` and an instance is already registered, the dev-runner prints `[paperclip] paperclip-dev-watch already running (pid X, child Y)` and exits with code 0 — no error, no crash, just silence. Easy to miss when monitoring via the process tool. Fix: kill ALL Paperclip-related processes before starting fresh. Use `sudo pkill -9 -f "tsx.*paperclip"; sudo pkill -9 -f "tsx.*dev"` — a simple `pkill -f "paperclip"` is insufficient because it won't catch the tsx wrapper processes.
- **Background process log can show 0 lines even when the server is running.** The dev-runner's `spawn()` creates child processes (dev-watch, tsx watch, esbuild) whose stdout goes to separate fd chains. The foreground terminal session captures none of this. If the health endpoint returns 200 but the process log shows 0 lines, the server is fine — do not treat zero output as a failure.

## Completion criteria

Treat the task as done only when all are true:

- Paperclip is listening on port 3100 (verify with `ss`)
- `/api/health` returns OK (curl from the bind address)
- The deployment is authenticated/private
- The bind address matches the intended mode (Tailscale IP for `tailnet`, 0.0.0.0 for `lan`)
- Only one live Paperclip dev instance remains
