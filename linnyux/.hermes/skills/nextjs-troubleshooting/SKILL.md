---
name: nextjs-troubleshooting
description: 'Fix Next.js build and runtime issues: monorepo theme kit problems, stale cache/Prisma, and Tailwind build failures.'
---

# Next.js Troubleshooting

Diagnose and fix common Next.js build and runtime issues.

## When to Use

Triggers:
- Next.js monorepo has theme runtime issues after dependency changes
- Browser shows stale content after schema/index changes
- Tailwind v4/PostCSS build fails

## Workflows

### 1. Monorepo Theme Runtime Stabilization
See: `references/monorepo-theme-runtime-stabilization.md`
Fix shared theme kit runtime across workspace packages.

### 2. Stale Cache and Prisma Verification
See: `references/stale-cache-and-prisma-verification.md`
Fix browser showing stale content after schema/index changes.

### 3. Tailwind Build Stabilization
See: `references/tailwind-build-stabilization.md`
Fix Next.js app using Tailwind v4/PostCSS after config changes.

### 4. Canonical Theme Kit Alignment
See: `references/canonical-theme-kit-alignment.md`
Align a multi-app Next.js monorepo to one shared theme kit, centralize CSS variables, avoid client-only helpers in server layouts.
