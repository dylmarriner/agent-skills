# Papatoetoe Funeral Cottage — Audit Session Reference

**Date:** 2026-05-20
**Stack:** Next.js 16.2.6 + Payload CMS 3.84.1 + React 19.2.4 + Tailwind CSS v4
**Target Quality:** $50K NZD production standard
**Domain:** papatoetoefuneralcottage.co.nz (currently Wix, being replaced)

## Skills Deployed
- squirrelscan (`squirrel audit https://site.co.nz --format llm`)
- `ai-seo` (AIEO/GEO/LLMO optimization patterns)
- `audit-website` (squirrelscan framework)
- `website-seo` (on-page SEO system)
- Multiple security audit techniques

## Tools Used
- 4 parallel subagents for multi-tool audit
- 3 parallel subagents for fix phases
- squirrelscan CLI (v0.0.38)
- curl for API endpoint testing
- grep/search_files for code analysis

## Key Findings (23 issues across 5 dimensions)

### Security (6 fails)
- No CSP on live Wix site (Next.js build has it, just not deployed)
- robots.txt conflict (static file + route handler → HTTP 500)
- 6 API endpoints lacked rate limiting
- Inline-update API had zero authentication
- Missing CSP directives (base-uri, form-action, frame-ancestors, Permissions-Policy)
- Live Resend API key exposed in .env

### Frontend/UX (8 fails)
- Phone number with literal asterisks (`+649****9098`) — CRITICAL
- No error.tsx / loading.tsx / not-found.tsx
- `key={Math.random()}` in RichText (destroys React reconciliation)
- Duplicate JSON-LD schema implementations
- `prose` class used but @tailwindcss/typography not installed
- SkipLink used non-existent CSS classes
- Color contrast failures (plum/75 on ivory, 4.0:1)
- InlineEditMode visible to all visitors

### Code Health (5 fails)
- 41 `any` type instances (12 unavoidable in payload-types)
- Only 33% pino logging adoption (15 console.log/error remain)
- Unused Sentry SDK (installed but zero imports)
- No request ID tracing / middleware
- duplicate components (theme-kit/ui, two Button implementations)

### SEO/AIEO (4 fails)
- No llms.txt / pricing.md for AI agents
- Schema broken (duplicate blocks) → Google ignores
- No og:image on any page
- No author attribution or last-updated dates on content

## Fix Approach
All 23 issues fixed in 5 parallel phases via subagents, followed by iterative build-fix-verify (6 build cycles to clean compilation).

## Build Traps Hit
1. `return { notFound: true }` → `notFound()` (import from next/navigation)
2. Missing `redirect` import in checkout page
3. `z.literal(true, { errorMap })` → Zod v4: `z.literal(true, { message })`
4. Migration import `from 'payload/database'` → local type aliases
5. Missing `from:` field in email sendEmail() calls across 4 API routes
6. Tailwind v3 config coexisting with v4 @theme → delete tailwind.config.ts
7. middleware.ts deprecation warning in Next.js 16 (use proxy instead)

## Final Build Status
✅ Clean compile — 31 routes, zero application TypeScript errors.
