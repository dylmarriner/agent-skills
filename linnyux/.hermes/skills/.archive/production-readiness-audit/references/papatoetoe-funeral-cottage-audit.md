# Reference: Papatoetoe Funeral Cottage Audit (2026-05-20)

## Target
- **Codebase**: `/home/lin/Documents/funeral-cottage-website/`
- **Stack**: Next.js 16 + Payload CMS 3 + React 19 + Tailwind CSS v4
- **Live domain**: `papatoetoefuneralcottage.co.nz` (currently a Wix site — the Next.js build replaces it)
- **Previous audit**: `PRODUCTION_AUDIT_REPORT.md` (2026-05-16, claimed 63% resolved)
- **Standard**: $50K NZD production website

## Audit Tracks Executed

### Track 1: Security & Infrastructure (subagent)
- 6/7 security headers present — missing Permissions-Policy
- robots.txt HTTP 500 (conflicting static file + dynamic route handler)
- CSP missing `base-uri`, `form-action`, `frame-ancestors` directives
- 6/11 API endpoints lack rate limiting (webhook, checkout, analytics, health, inline-update, cron)
- In-memory rate limiter — single-process Map, not production-scalable
- Live Resend API key exposed in .env on disk
- Production CSP removes `'unsafe-inline'` from `style-src` — will break Next.js CSS
- Stripe webhook properly verifies signatures with idempotency ✅
- Form inputs pass through unsanitized at API boundary (but Payload CMS sanitizes on render)
- **Key finding**: inline-update API has zero authentication

### Track 2: Frontend / UI / UX (subagent)
- Phone number `+649****9098` with literal asterisks in 16 files — every "Call Now" link broken
- No `error.tsx`, `loading.tsx`, or `not-found.tsx` in any route
- `key={Math.random()}` in RichText destroys React reconciliation
- Duplicate JSON-LD schema implementations (`seo/` vs `schema/` directories)
- `prose` class used but `@tailwindcss/typography` not installed
- SkipLink uses undefined CSS classes (`bg-primary` doesn't exist in brand theme)
- Color contrast: `text-brand-plum/75` on `bg-brand-ivory` fails WCAG AA (4.0:1)
- Tailwind v3 `tailwind.config.ts` coexists with v4 `@theme` in globals.css
- InlineEditMode toggle visible to all visitors, not just admins
- Full report written to `FRONTEND_UX_AUDIT.md`

### Track 3: Code Quality / Previous Audit Verification (subagent)
- Previous report claimed 63% (17/27) resolved — actual is ~52% (14/27)
  - Console.log adoption only 33% (4/12 routes)
  - Error context: 7 routes use `catch (error: unknown)` but only 4 forward to pino logger
  - 41 `any` type instances in 19 files (12 unavoidable in payload-types.ts)
  - Unused Sentry SDK: `@sentry/nextjs` installed but zero imports
  - Analytics endpoint is a no-op: `console.log` + `catch {}` — no persistence
  - 3 distinct error handling patterns coexist

### Track 4: Squirrelscan (live Wix site)
- Overall score: **59/100 (Grade F)** — baseline for the replacement build
- No CSP, no clickjacking protection, no privacy policy detected
- No E-E-A-T signals, no structured data, thin content (117-227 words)
- Forms without labels, color contrast issues
- Key insight: domain still points to Wix, not the Next.js build

## AIEO Readiness
- No `llms.txt` or `pricing.md` for AI agent consumption
- Schema broken (duplicate blocks) — Google ignores
- No author attribution on content
- No visible last-updated dates
- No og:image on any page

## Final Verdict
**NOT PRODUCTION READY** — 23 issues across 5 phases
- Phase 1 (critical fixes): 7 items — ~1-2 days
- Phase 2 (security hardening): 6 items — ~1 day
- Phase 3 (UX polish): 6 items — ~1-2 days
- Phase 4 (code quality): 8 items — ~1 week
- Phase 5 (AIEO/SEO): 7 items — ~1 week
