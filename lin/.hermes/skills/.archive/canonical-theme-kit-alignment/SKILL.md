---
name: canonical-theme-kit-alignment
description: Align a Next.js monorepo to one shared theme kit across website/admin surfaces, centralize CSS variables in a shared package, avoid client-only helpers in server layouts, and verify the live UI after cache clears and restarts.
metadata:
  category: software-development
---

# Canonical Theme Kit Alignment

Use this skill when the user wants one theme system applied consistently across a multi-app stack, especially a Next.js monorepo with website/admin shells and a shared UI package.

## Goal

Make the website and app/admin surfaces consume one canonical token system for:
- typography
- spacing
- radii
- shadows
- transitions
- semantic colors
- theme variants
- density modifiers

The outcome should be a single source of truth for theme variables and a live browser-verifiable result.

## Workflow

1. Identify the canonical theme source.
   - Prefer a shared package over app-local inline CSS.
   - Confirm the token names used by the docs and components.
   - If the repo already has a shared UI package, treat it as the owner of theme CSS generation.

2. Map the required theme contract.
   - Define base tokens in `:root`.
   - Define theme variants via `[data-theme="..."]`.
   - Define app density modifiers like `.app-website` and `.app-admin`.
   - Keep semantic tokens stable across themes.

3. Apply the theme in root layouts only.
   - Set `data-theme` on the `<html>` element.
   - Attach a density class to the app root (`app-website`, `app-admin`).
   - Inject the shared CSS string or shared stylesheet once.
   - Avoid duplicating theme definitions inside each app layout.

4. Make the shared CSS generator server-safe.
   - The theme helper must be a pure function that returns a CSS string.
   - Do not rely on React hooks, browser-only APIs, or a `use client` boundary in the helper.
   - If a layout calls the helper during server render, the helper must be importable from server code.
   - If the build complains about client/server boundaries, move the helper logic into a pure module and keep interactive UI components separate.

5. Normalize component tokens.
   - Prefer shared token names such as `--bg-primary`, `--bg-secondary`, `--text-primary`, `--border-default`, `--accent`.
   - If older components use `--color-*` aliases, map them in the shared CSS rather than rewriting every page.
   - Avoid hardcoded hex values in page-level components unless they are truly local exceptions.

6. Verify density and theme behavior.
   - Website should feel roomier and more marketing-oriented.
   - Admin should feel denser and more operational.
   - Confirm cards, tables, buttons, badges, and headings read correctly in both surfaces.

7. Verify live in the browser.
   - Start or restart the dev servers.
   - Clear stale `.next` artifacts if the browser still shows old behavior.
   - Check the live website and admin shells in a fresh browser session.
   - If the browser shows a runtime error after a source fix, inspect whether the dev server is serving stale compiled code before changing more files.

8. Fix stale cache or port issues when needed.
   - Kill old `next dev` processes if ports are occupied.
   - Remove app `.next` folders when a restart does not reflect source changes.
   - Re-run the browser check after the cleanup.

## Important rules

- One theme kit, one canonical contract.
- Never leave duplicated app-local theme CSS once the shared package is available.
- Never call a client-only theme helper from a server layout.
- Keep theme values stable enough that components can rely on them.
- Treat theme alignment as a source-of-truth problem, not a page-by-page styling problem.

## Common pitfalls

- Duplicating the same token set in multiple app layouts.
- Using a `use client` theme helper from a server component.
- Forgetting to add app density classes, causing website/admin to look identical.
- Replacing tokens with page-level hardcoded colors instead of updating the shared theme.
- Assuming the browser reflects source changes without clearing stale dev artifacts.
- Verifying only by source inspection and not by live browser render.

## Verification checklist

- Shared theme CSS lives in one canonical package.
- Website and admin layouts both consume that shared CSS.
- Theme variants are selected through `data-theme`.
- Website and admin density modifiers are present.
- Browser rendering matches the intended theme in both apps.
- No client/server boundary error is thrown during layout render.
- Stale dev server artifacts were cleared if needed.
