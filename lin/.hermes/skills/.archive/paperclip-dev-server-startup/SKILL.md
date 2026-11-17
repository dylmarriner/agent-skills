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

## Procedure

1. Inspect the current state first.
   - Check listeners on port 3100.
   - Check for existing Paperclip dev processes.
   - If an instance is already healthy and matches the requested mode, verify it instead of starting another.

2. Remove stale or duplicate Paperclip instances.
   - Kill only Paperclip-related dev processes that are holding the port or causing duplicate launches.
   - Recheck port 3100 after cleanup.

3. Start the dev server in the correct mode.
   - From the repo root, run:
     - `pnpm dev --tailscale-auth`
   - This should produce authenticated/private mode with `HOST=0.0.0.0` so it is reachable over Tailscale/private networking.

4. Wait for the real server to come up.
   - Startup may include plugin SDK build, workspace preflight, and embedded Postgres initialization.
   - Do not treat the launch as complete until the actual server is listening on port 3100.

5. Verify health and mode.
   - Confirm the port is listening on `0.0.0.0:3100`.
   - Confirm `curl http://127.0.0.1:3100/api/health` returns JSON with:
     - `status: "ok"`
     - `deploymentMode: "authenticated"`
     - `deploymentExposure: "private"`
     - `authReady: true`
     - `bootstrapStatus: "ready"`

6. Ensure singleton state.
   - Re-run process checks to confirm there is only one live Paperclip dev instance.
   - If more than one remains, stop the extras and re-verify.

## Useful checks

- Listener check:
  - `ss -ltnp '( sport = :3100 )'`
- Process check:
  - `ps -ef | grep -E '[p]npm dev --tailscale-auth|[t]sx .*dev-runner|[n]ode .*src/index.ts'`
- Health check:
  - `curl -fsS http://127.0.0.1:3100/api/health`

## Pitfalls

- The dev runner may spawn multiple wrapper processes during startup; focus on the actual server process bound to port 3100.
- A healthy health endpoint is the real completion signal, not merely a running npm command.
- If the server is still building or initializing embedded Postgres, wait and re-check before concluding failure.
- Better Auth may warn about base URL auto-detection even when the service is otherwise healthy; verify the health endpoint and mode rather than stopping on that warning alone.
- If an older instance is already listening, prefer cleanup and a single fresh instance over launching yet another wrapper.

## Completion criteria

Treat the task as done only when all are true:

- Paperclip is listening on port 3100
- `/api/health` returns OK
- The deployment is authenticated/private
- Tailscale-friendly/private access is enabled via the startup mode
- Only one live Paperclip dev instance remains
