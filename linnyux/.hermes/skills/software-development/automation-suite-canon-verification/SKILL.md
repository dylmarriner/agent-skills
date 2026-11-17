---
name: automation-suite-canon-verification
description: Audit and physically verify Automation Suite against its governing docs, then fix route/UI drift with live browser checks on separate website/admin servers.
metadata:
  category: software-development
---

# Automation Suite Canon Verification

Use this when the user asks to align or verify the Automation Suite against `docs/technical-blueprint.md`, `docs/ui-theme-blueprint.md`, and the executable roadmap.

## When to use
- The user wants the repo aligned to the governing docs.
- You need to verify the live website and admin surfaces in a browser.
- Route loops, legacy redirects, or stale dev-server behavior are suspected.
- Admin/data-backed pages may fail because of environment or Prisma initialization issues.

## Workflow

1. Read the governing docs first.
   - `docs/technical-blueprint.md`
   - `docs/ui-theme-blueprint.md`
   - `automation_suite_executable_roadmap.md`

2. Establish the canonical hierarchy.
   - The technical blueprint wins over older roadmap language.
   - Treat the UI theme doc as the source of truth for shell/theme behavior.
   - Treat the roadmap as execution sequencing, not a separate canon.

3. Inspect the live app surfaces separately.
   - Website and admin may run on different local ports.
   - Verify the website shell, product routes, bundles, pricing, demo, signup, and legal pages.
   - Verify the admin shell and its operational routes separately.

4. Validate with the browser, not just file scans.
   - Confirm route rendering, redirects, and actual page content.
   - Don't rely only on file existence or route registration.
   - If a route looks wrong, test it directly in the browser.

5. Treat stale Next dev logs cautiously.
   - Old 307/500 output may reflect a prior run, not the current code.
   - Trust fresh browser/curl responses over old log spam when reconciling live state.
   - Restart the relevant dev server after route or build-critical changes.

6. Fix common drift patterns.
   - Collapse redirect loops by replacing alias redirects with stable content or canonical route targets.
   - Remove parallel source-of-truth splits.
   - Align public pages with the registry-driven product model.
   - Convert broader-than-canon landing pages into canonical content or thin wrappers.

7. Handle admin/data-backed pages carefully.
   - If Prisma or other startup-time data access fails, check whether the environment has the needed vars before changing business logic.
   - If a page fails during module evaluation, avoid eager data access at import time.
   - Prefer a stable route shell over a hard crash in verification environments.
   
   **Prisma 7 note:** Prisma 7 moved datasource URLs from `schema.prisma` into `prisma.config.ts`. Do not add `url = env("DATABASE_URL")` to `schema.prisma` - that causes P1012 error. The configuration should be:
   ```prisma
   datasource db {
     provider = "postgresql"
   }
   ```
   And `packages/db/prisma.config.ts` should contain:
   ```ts
   import 'dotenv/config';
   import { defineConfig } from 'prisma/config';
   
   export default defineConfig({
     datasource: {
       url: process.env.DATABASE_URL,
     },
   });
   ```
   
   This applies to all database operations in the suite. See `references/prisma-7-config-issues.md` for additional context.

8. Verify after each meaningful fix batch.
   - Re-open the live pages in the browser.
   - Re-run direct route checks for the affected surfaces.
   - Confirm the current server instance reflects the changed files.

## Verification checklist
- Governing docs were actually read.
- Website routes render without loops.
- Admin routes render or fail with a clearly understood environment limitation.
- No stale-redirect confusion remains after restart.
- Live browser/curl responses match the expected canonical surface.

## Notes
- The website/admin apps are commonly verified as separate local servers.
- Browser verification is part of the task, not optional polish.
- If route or data surface drift exists, fix the live behavior first, then clean the surrounding copy and docs.