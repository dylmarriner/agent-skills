---
name: nextjs-tailwind-build-stabilization
description: Stabilize a Next.js app that uses Tailwind v4/PostCSS after branding or shell updates, including build failures from PostCSS config, missing plugins, and @apply utility drift.
metadata:
  category: software-development
---

# Next.js + Tailwind Build Stabilization

Use this skill when a Next.js app builds locally but fails after changing the app shell, theme, or global CSS, especially with Tailwind v4 / PostCSS / Turbopack.

## When to use
- Next.js build fails after editing `app/layout.tsx`, `app/page.tsx`, or `globals.css`
- Tailwind v4 complains about PostCSS plugin setup
- Build errors mention unknown utilities like `border-border`
- The app has starter-shell content that needs replacing with a branded landing page
- The repo has lockfile/root warnings or a stale Next config setup
- The repo contains both `app/` and `src/app/` trees and the build is reading the other one

## Workflow

### 1) Verify the real failure first
- Run the production build in the frontend package directory.
- Read the exact error, especially the first CSS/PostCSS/Turbopack failure.
- Do not guess from source alone.
- If the repo has both `app/` and `src/app/`, verify which tree the build is actually using before editing more files.
- Watch for duplicated globals/theme files in both trees; the build may be failing on the non-primary `app/` path even when most source lives under `src/app/`.
- If `@apply border-border` or similar unknown utility errors persist after fixing `src/app/globals.css`, inspect the root `app/globals.css` too.

### 2) Fix PostCSS for Tailwind v4
If the build says Tailwind is being used directly as a PostCSS plugin:
- Update `postcss.config.js` to use `@tailwindcss/postcss`
- Remove `tailwindcss` from the PostCSS plugin list
- Remove `autoprefixer` if it is missing and not already installed

Example:
```js
module.exports = {
  plugins: {
    '@tailwindcss/postcss': {},
  },
}
```

### 3) Remove brittle `@apply` usage from globals if needed
If build errors mention unknown utilities like `border-border`:
- Search `app/globals.css` for `@apply` rules
- Replace Tailwind utility application with plain CSS variables where possible
- Prefer:
  - `background: hsl(var(--background));`
  - `color: hsl(var(--foreground));`
  - `outline-color: hsl(var(--ring));`
- Avoid relying on utility classes that Tailwind no longer resolves in the build path

### 4) Keep the theme tokens and usage aligned
- Ensure `:root` defines the CSS variables consumed by UI components
- Make sure component classes reference tokens that actually exist
- If custom colors such as `border-border` are used widely, verify the Tailwind config exports the corresponding theme tokens

### 5) Brand the shell without placeholders
- Replace starter metadata in `app/layout.tsx`
- Replace the starter home page in `app/page.tsx`
- Do not leave placeholder copy, mock data, FIXMEs, or TODOs in production code

### 6) Rebuild after each fix
- Re-run the frontend build after each meaningful change
- Keep going until build succeeds
- Treat warnings separately from build failures
- Warnings like next.config `eslint` deprecations or multiple-lockfile root inference are not blockers unless they break the build

## Verification checklist
- `npm run build` succeeds in the frontend package
- The root route renders the branded shell
- No starter Next.js content remains
- No CSS/PostCSS/Turbopack errors remain
- Any warnings are documented separately and do not block the build

## Common pitfalls
- Leaving `tailwindcss` in PostCSS config while using Tailwind v4
- Leaving `autoprefixer` in config when it is not installed
- Keeping `@apply` rules that depend on unavailable utilities
- Fixing CSS tokens but forgetting the actual `:root` variable definitions
- Assuming a successful compile means the app shell is acceptable visually

## Practical lesson
In Tailwind v4 / Next.js 16 builds, the smallest safe fix is often to replace fragile global `@apply` rules with plain CSS variables and keep PostCSS minimal.
