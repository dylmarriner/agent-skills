---
name: mealify-canon-cleanup-playbook
description: Autonomous workflow for aligning the Mealify codebase with canonical UI/spec docs by fixing navigation bugs, removing legacy dashboard/admin copy, and verifying each pass with lint and targeted searches.
metadata:
  category: software-development
---

# Mealify Canon Cleanup Playbook

Use this when Mealify needs to be brought back in line with its active canon (`UI_SPECIFICATION.md`, blueprint docs, and current app shell), especially when the repo still contains legacy dashboard/admin/ops language or route mismatches.

## When to use
- The user asks to continue Mealify work autonomously.
- The app still exposes legacy dashboard/admin/ops framing.
- Navigation targets or screen names no longer match the canonical five-tab surface.
- You need to clean up copy drift after bigger functional fixes are already in place.

## Workflow

1. Read the authoritative docs first.
   - `UI_SPECIFICATION.md`
   - active blueprint / lock docs if present
   - any docs that declare hierarchy or legacy status

2. Inspect the real app shell and navigation entrypoints early.
   - Check bottom tabs, stack screens, and any routes used by the screens themselves.
   - Confirm the live route/component mapping, not just filenames.
   - Look for invalid navigation targets before changing copy.

3. Search for legacy vocabulary at scale.
   - dashboard
   - admin console / super admin
   - growth / platform / analytics engine / ops / tactical
   - generic SaaS / enterprise framing
   - screen names that conflict with the canonical surface

4. Prioritize fixes in this order.
   1. Broken or invalid navigation targets
   2. Canon-breaking visible UI copy on active screens
   3. Screen names or labels that imply the wrong mental model
   4. Legacy tooling surfaces that leak into the user-facing flow

5. Make minimal, behavior-preserving patches first.
   - Prefer copy changes over structural rewrites when the screen already functions.
   - If a route mismatch is found, fix the route rather than papering over it in copy.
   - Avoid renaming files or routes unless the implementation truly needs it.
   - When renaming a stack/route label, update every caller in the same batch so navigation stays consistent.
   - For auth/sign-up flow, prefer auth-state-driven navigation over manually pushing a post-signup screen.
   - If signup/login already sets user state correctly, remove any extra navigation that jumps to non-canonical surfaces.

6. Special-case the Week screen to the canonical blank-start flow.
   - Do not auto-generate the week on mount if the spec says Week starts blank.
   - Expose a visible Auto-Generate Week action and keep the empty state explicit until the user taps it.
   - Remove non-canonical sub-tabs or secondary meal modes that conflict with the single Week surface unless the spec explicitly requires them.

7. Verify after every meaningful patch batch.
   - Run the mobile lint gate (`npm run lint` in the mobile app)
   - Re-scan for removed legacy phrases or invalid route targets
   - If a verification command is invalid for the current directory, correct the working directory or command before retrying
   - Use targeted searches after patching to confirm the old phrases and bad route names are actually gone, not just visually changed in one file.
   - Prefer lint/search for React Native screen verification; do not use `node require()` on JSX files as a health check because it will fail on legitimate component syntax.
   - For auth/end-to-end checks, verify the backend contract as well as the mobile UI: JWT env, password reset `FRONTEND_URL`, and `/auth/validate` behavior can affect the mobile experience.
   - When testing on-device or in browser, confirm the mobile API base URL is actually set for that environment (`EXPO_PUBLIC_API_URL`, `API_URL`, window/meta override, or a known-safe fallback) before blaming auth code.

8. If a JSX patch starts corrupting a screen, stop broad replacement attempts immediately.
   - Re-read the file and reconstruct the component cleanly, or replace the full file with a known-good version.
   - Avoid stacking more broad text replacements onto a file that already has partial patch damage.
   - After recovery, re-run lint and a targeted content search to ensure the file is structurally sound.

9. Continue autonomously until the biggest remaining drift is reduced.
   - Do not stop after the first cosmetic improvement if a stronger canon mismatch remains.
   - Keep scanning for the next highest-value mismatch until the surface is materially aligned.
   - If the app cannot be fully exercised in the current environment, report the exact blocker with evidence instead of guessing.

## Common patterns found in Mealify cleanup
- A screen is named like a dashboard but should read as Home, Week, Grocery, Pantry, or Insights.
- Household selection still navigates to an old route name that no longer exists.
- Analytics/admin screens use product/platform language that fights the canonical household-first framing.
- Screens already function correctly, but the visible labels still suggest the legacy product shape.

## Pitfalls
- Treating copy drift as harmless when it changes the product mental model.
- Renaming components before checking whether the real bug is a route target mismatch.
- Running the wrong verification command from the wrong directory.
- Fixing one screen while leaving the next obvious legacy surface untouched.

## Verification checklist
- Lint passes with no errors.
- Searches for the removed legacy phrases return no hits in the targeted files.
- Navigation targets point to real stack/tab screens.
- The visible app surface uses canonical Mealify language.

## Mealify-specific lessons learned
- The canonical five tabs are Home, Week, Grocery, Pantry, Insights; do not rename these labels unless the spec changes.
- Home copy should feel time-aware and prioritization-focused rather than dashboard/ops-oriented.
- Insights should not reuse Home's current-need framing unless the spec explicitly says so.
- Grocery copy should describe the actual action, e.g. comparing store prices, rather than legacy “basket”/admin language.
- When verifying mobile cleanup, run lint from the mobile app root so ESLint resolves the correct project config; path mistakes can make a healthy screen look broken.
- Prefer copy-only changes on already-working screens; avoid route/structure changes unless a real mismatch is verified.

## Why it works
Mealify cleanup is most effective when you fix the concrete route bugs first, then remove legacy mental models in the UI copy, and keep iterating with search-plus-lint verification until the active surface matches the spec.