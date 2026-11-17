# Papatoetoe Funeral Cottage — Production Audit Session

## Project Specs
- **Stack:** Next.js 16.2.6 + Payload CMS 3.84.1 + React 19.2.4 + Tailwind CSS v4
- **Target:** Complete production audit + fix of a $50K NZD funeral home website
- **Live site (old):** Wix.com at `papatoetoefuneralcottage.co.nz`
- **New build:** Payload CMS + Next.js at same domain
- **Team size:** Solo developer

## Key Findings That Apply Broadly

### Tooling Discoveries
- **squirrelscan CLI** binary is `squirrel` from `github.com/squirrelscan/squirrelscan/releases` (not `github.com/squirrelscan/squirrel` — dead repo). Install: `sudo curl -sL -o /usr/local/bin/squirrel "https://github.com/squirrelscan/squirrelscan/releases/download/v0.0.38/squirrel-0.0.38-linux-x64" && sudo chmod +x /usr/local/bin/squirrel`
- **ClawHub CLI** (`clawhub`) is installed and works for skill discovery. Skills install to `~/.openclaw/workspace/skills/` not `~/.hermes/skills/`
- **skills.sh CLI** (`npx skills`) installs to `~/.agents/skills/` — separate from Hermes skills. Use `-g -y` flags for silent global install.

### Tailwind v4 Quirks
- `tailwind.config.ts` is NOT used when `@import "tailwindcss"` is the CSS entry point. All theme tokens must be in `@theme` block in `globals.css`.
- `@tailwindcss/typography` must be installed as a dependency and added via `@plugin "@tailwindcss/typography"` in CSS.
- Deleting `tailwind.config.ts` is correct for v4 migration, but verify the `@theme` block has ALL needed tokens first.
- Common tokens that are easy to forget: `--color-brand-gold`, `--color-surface`, `--color-border-soft`, `--font-mono`

### Tailscale Hostname Leak
- The dev config had `allowedDevOrigins: ['lin-hp-pavilion-laptop-15-cs0xxx-1.tail2c15c8.ts.net']` — machine hostname + Tailscale network fingerprint in source control. Flag as potential internal recon vector.

### Payload CMS v3 Specifics
- Admin sessions use cookie `payload-token`. Verified via REST: `GET /api/admins/me` with `credentials: 'include'`.
- Globals default to public read access unless `access` is explicitly configured.
- Migrations use `push: false` by default — schema drift is silent.
- `payload-types.ts` auto-generated types have 12 unavoidable `any` fields (Lexical editor children). This is an upstream limitation.

## Multi-Agent Fix Orchestration (Tested Pattern)

This pattern completed ~50 fixes in under 2 hours of agent time:

1. **Audit phase:** 3 parallel subagents (backend/lib, frontend/components, collections/API/tests/CI)
2. **Fix phase:** 4 parallel batches of ~10 issues each (critical, security, frontend, quality)
3. **Verify:** Single build after all fixes + browser smoke test

Each batch subagent received: exact file paths + line numbers, "Read each file first. Build after."
