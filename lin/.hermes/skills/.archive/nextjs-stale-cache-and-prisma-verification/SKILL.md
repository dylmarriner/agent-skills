---
name: nextjs-stale-cache-and-prisma-verification
description: Troubleshoot Next.js dev-server issues where the browser shows stale compiled errors, missing exports, or Prisma constructor failures after source fixes. Use clean cache resets, source verification, and live browser rechecks before concluding the app is still broken.
metadata:
  category: software-development
---

# Next.js Stale Cache and Prisma Verification

Use this when a Next.js app appears fixed on disk but the live browser still shows old errors, missing exports, or Prisma initialization failures.

## When to use
- The browser still reports an error after the source file has already been patched
- Dev server logs mention old code that no longer exists on disk
- A route compiles once, then continues to throw an outdated export/import error
- Prisma errors appear during module evaluation in App Router pages or route handlers
- Next dev seems to be serving stale `.next` artifacts or an old bundle graph

## Workflow

1. Verify the on-disk source first.
   - Read the current file contents and confirm the import/export you expect is actually present.
   - Search the repo for the old symbol or constructor path to confirm it is gone everywhere relevant.

2. Distinguish source drift from build-cache drift.
   - If the files are correct but the browser still shows the old stack trace, assume stale `.next` output before assuming the patch failed.
   - Check whether the error references a compiled chunk or a previous module graph.

3. Reset the affected app’s dev cache.
   - Stop the running dev server.
   - Remove the app’s `.next` directory.
   - Restart the app from a clean process.
   - Re-open the affected route in the browser.

4. Re-test live routes after every clean restart.
   - Use the browser to confirm the route loads, not just the terminal.
   - If one route still fails, inspect whether it is still pointing at the stale module or a separate API route.
   - If the browser still reports an old export/error that no longer exists on disk, assume a stale dev process or stale .next graph before changing more source.
   - If multiple fixes appear to "not stick," clear the app cache, restart the exact dev process, and re-open the route in a fresh browser session before making architectural changes.
   - If the app uses multiple workspaces or ports, make sure you are restarting the exact app that owns the failing route; another package can keep serving an old chunk graph on a different port.

5. Treat Prisma carefully in App Router modules.
   - Avoid import-time Prisma client construction in files that are rendered by Next.js on the server.
   - If a page or route can render without database access, prefer a static fallback instead of eager Prisma initialization.
   - If a live DB-backed route is required, make sure the runtime environment actually provides the needed env vars before reintroducing database code.
   - Prefer lazy access inside handlers or functions over module-level client creation when startup stability matters.
   - When a shared db package exists, keep Prisma access centralized there and replace any remaining direct `new PrismaClient()` call sites in worker/API/observability packages rather than fixing only the visible admin route.

6. When the environment is not DB-ready, degrade safely.
   - Return blueprint-aligned empty-state pages instead of crashing the route.
   - Keep the shell, navigation, and canonical wording working even if data-backed content is unavailable.
   - Document the missing runtime dependency clearly in the UI.
   - A no-DB fallback is acceptable as a temporary verification-safe state, but mark it clearly so it is not mistaken for the final production implementation.

5. Treat Prisma carefully in App Router modules.
   - Avoid import-time Prisma client construction in files that are rendered by Next.js on the server.
   - If a page or route can render without database access, prefer a static fallback instead of eager Prisma initialization.
   - If a live DB-backed route is required, make sure the runtime environment actually provides the needed env vars before reintroducing database code.
   - Prefer lazy access inside handlers or functions over module-level client creation when startup stability matters.

6. When the environment is not DB-ready, degrade safely.
   - Return blueprint-aligned empty-state pages instead of crashing the route.
   - Keep the shell, navigation, and canonical wording working even if data-backed content is unavailable.
   - Document the missing runtime dependency clearly in the UI.

7. Verify the fix after the clean rebuild.
   - Re-run the browser route.
   - Re-run any affected neighboring routes.
   - If the error disappears only after a cache wipe, record that as the necessary recovery step.

## Common pitfalls
- Patching source files but forgetting that the running dev server still has the old `.next` graph
- Assuming a Prisma constructor option is supported by the installed Prisma version
- Importing Prisma at module scope in pages that only need a shell or fallback state
- Treating a runtime bundle error as a source-code error without checking the dev cache first

## Verification checklist
- Source files and repo search agree with the intended fix
- The app’s `.next` cache has been reset after the patch if stale behavior persists
- The browser route renders successfully after restart
- No old export/import/Prisma constructor errors remain in the live process

## Why this works
Next.js dev can hold onto stale compiled artifacts even after the source is corrected. Clearing the app cache and restarting cleanly is often the difference between chasing phantom errors and validating the actual fix. When Prisma is involved, keeping database access out of module evaluation prevents the whole route tree from crashing during startup.
