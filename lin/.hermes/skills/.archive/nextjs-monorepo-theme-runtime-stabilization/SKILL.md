---
name: nextjs-monorepo-theme-runtime-stabilization
description: Stabilize Next.js monorepos that use a shared theme kit and persistent dev processes. Use when app layouts must share one canonical theme package, when Turbopack/cache corruption causes ENOENT or empty-browser failures, or when the root dev orchestrator fails due to workspace concurrency.
metadata:
  category: software-development
---

# Next.js Monorepo Theme + Runtime Stabilization

Use this skill when working in a multi-app Next.js monorepo where:
- website/admin must share one canonical theme kit
- root layouts are drifting into app-local inline CSS
- dev servers show empty pages, manifest ENOENTs, or stale Turbo/Turbopack cache errors
- `pnpm dev` fails because the workspace has more persistent tasks than Turbo concurrency allows

## Goals

1. Centralize theme tokens and CSS generation in one shared package.
2. Make app layouts consume that shared theme kit instead of duplicating inline theme CSS.
3. Detect and eliminate stale dev runtime state before blaming source code.
4. Verify the live UI in a fresh browser session after every restart.

## Canonical theme workflow

1. Identify the theme source of truth.
   - Prefer one shared UI package or theme package.
   - Do not let website/admin each define their own token sets.

2. Normalize the token contract.
   - Keep shared semantic variables like background, text, border, accent, spacing, radii, shadows, and transitions.
   - Add app-density modifiers as classes, not as separate theme systems.

3. Wire layouts to the shared theme.
   - Import the shared CSS helper from a server-safe module.
   - Set `data-theme` on `<html>`.
   - Add app-scoped density classes such as `.app-website` and `.app-admin`.
   - Avoid client-only theme helpers inside server layouts.
   - If the shared UI package root also exports client components/hooks, do not import the root into server layouts just to get theme CSS; split the theme CSS into a dedicated server-safe file and export it separately.
   - Watch for package `exports` maps: a subpath import may be blocked even if the file exists on disk. Add an explicit export or use a package-safe root re-export for the server-safe helper.

4. Keep theme variants limited and intentional.
   - Canonical themes should have clear roles, e.g. website default vs admin control plane.
   - If a theme is renamed, update the shared source first and then the app layouts.

## Runtime stabilization workflow

1. Treat empty pages and manifest ENOENTs as stale runtime until proven otherwise.
   - Common signs:
     - `build-manifest.json` missing
     - `pages-manifest.json` missing
     - Turbopack SST / meta / compaction errors
     - browser snapshot says “Empty page”
     - runtime error overlay appears after a clean source change

2. Inspect live processes before changing code.
   - Find existing `next dev` listeners.
   - Kill the actual listener PIDs, not just wrapper shells.
   - Remove the relevant `.next` directories for each app.

3. Restart narrowly.
   - Prefer starting the affected app(s) directly first.
   - Use `pnpm -C apps/website dev` and `pnpm -C apps/admin dev` when root orchestration is polluted.
   - Recheck after restart in a fresh browser session.

4. If `pnpm dev` fails because of workspace task count.
   - Check Turbo concurrency.
   - Increase `--concurrency` to cover all persistent tasks.
   - If the root orchestrator still fails because unrelated apps are broken, verify the target apps individually instead of assuming the theme change is wrong.

5. If Turbopack cache corruption persists.
   - Switch app dev scripts to `next dev --webpack` temporarily for stability.
   - Verify that the source still loads correctly under the safer dev mode.
   - If needed, reintroduce faster dev tooling only after the runtime is healthy.

## Practical sequence

1. Read the relevant app layouts and the shared theme package.
2. Patch the shared theme package first.
3. Patch website/admin layouts to import and use the shared helper.
4. Kill stale dev processes.
5. Remove `.next` for the affected apps.
6. Restart the smallest possible scope.
7. Verify in a fresh browser session.
8. Only then judge whether there is a code problem.

## Verification gates

Before declaring success, confirm:
- website/admin layouts reference the shared theme kit
- the browser no longer shows runtime overlay or empty page
- routes render after a clean restart
- no stale manifest or SST errors appear in logs
- the root dev command is not blocked by concurrency settings

## Common pitfalls

- Editing layouts without fixing the shared theme source
- Calling client-only helpers from server layouts
- Assuming `pnpm dev` failure means the theme code is wrong
- Killing the wrong listener because another project already owns that port; verify the exact PID/command before terminating anything, and treat explicitly user-owned ports as off-limits
- Leaving stale `next-server` listeners on ports 3000/3001
- Forgetting that workspace orchestrators can fail because unrelated packages have broken dev scripts
- Verifying in an old browser session after restarting the server

## When to use

Use this skill for:
- theme kit rollouts across website/admin
- Next.js 16 / Turbopack cache corruption
- stale `.next` recovery
- monorepo dev orchestration failures
- browser verification after runtime repair
