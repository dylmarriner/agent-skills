# Multi-Track Production Readiness Audit

A systematic approach to auditing a codebase for production readiness, designed to catch issues that standard QA misses. Uses parallel subagents running independent deep-dives, followed by a hostile pass that attacks the code from every angle.

## When to Use This

Use when the user asks for:
- "production audit of this project"
- "is this production ready?"
- "make sure everything is to the highest standard"
- "hostile audit" / "rip it apart"
- "is this worth $X?"
- A comprehensive go/no-go assessment before deployment

## Methodology

The audit runs in two waves:

### Wave 1: Three Parallel Deep-Dives

Spawn 3 subagents via `delegate_task` (batch mode, parallel). Each gets a different slice of the codebase and is instructed to be thorough but constructive. Each subagent should:

1. Read actual files — not summaries, not directory listings. Read function bodies, schemas, configs.
2. Report specific file paths and line numbers for every issue.
3. Classify each issue: Critical / High / Medium / Low.
4. Suggest a concrete fix for each.

**Subagent 1: Backend, lib, and infrastructure**
Files to inspect:
- `src/lib/` — all utilities, validators, email, rate limiting, pricing, Stripe, logger, RBAC
- `src/payload.config.ts` — CMS config
- `next.config.ts` — CSP, security headers, image config
- `tsconfig.json`, `package.json` — dependency audit
- `src/middleware.ts` — if it exists
- `src/app/api/` — every API route handler

Look for: in-memory state that doesn't scale, empty secret fallbacks, mock functions used in production, unmigrated console.log, CSS class names that don't exist in the theme, unused dead code paths, race conditions, hardcoded values, wrong domain names, CSP directives that block legitimate services, env vars validated but not used.

**Subagent 2: Frontend, components, pages, and UX**
Files to inspect:
- `src/app/(site)/` — every page
- `src/components/` — all components, forms, layouts, sections
- `src/app/layout.tsx` — root layout
- `src/app/globals.css` — theme tokens

Look for: missing `generateMetadata` on SEO-critical pages, components using CSS vars that don't exist in the theme, dead components (imported by zero files), duplicated implementations (two buttons, two FAQ renders, two metadata builders), suppressHydrationWarning without root cause fix, eslint-disable at file scope, `as unknown as X` type casts, `<img>` instead of `next/image`, missing `error.tsx`/`loading.tsx`/`not-found.tsx`, hardcoded data that should come from CMS, inline email templates that look amateurish.

**Subagent 3: Collections, tests, docs, and CI/CD**
Files to inspect:
- `src/collections/` — all Payload CMS collections
- `src/globals/` — all Payload CMS globals
- `src/migrations/` — migration files
- `tests/` — all test files
- `docs/` — documentation
- `scripts/` — seed scripts
- `.github/workflows/` — CI/CD pipelines

Look for: missing unique constraints, wrong access control on collections/globals, missing timestamps, migrations that don't exist, tests that test the wrong thing (test data mismatched from API schema), tests that never run for the reason claimed, documentation that describes non-existent infrastructure, CI/CD workflows that trigger on the wrong branch, AI-generated boilerplate committed as real pipelines, seed scripts that leak info or produce broken data.

### Wave 2: Hostile Pass

After the three constructive deep-dives complete, compile their findings. Then spawn a **single hostile auditor** subagent that reads the compiled report AND the key offending files directly. Instruct it to be brutal:

> "You are a HOSTILE AUDITOR. Show NO mercy. Mock bad patterns. Find everything wrong. Specific file paths and line numbers. For a $X project, this is embarrassing."

The hostile auditor should:
- Tear apart the worst patterns found in Wave 1
- Look for additional issues the constructive reviews missed
- Identify "theater" — code that looks secure/functional but isn't
- Calculate what the project is actually worth vs what was paid
- Produce a ranked list: production collapses > security > quality > cosmetic

## Phase 4: Batch Remediation

Organize fixes into parallel batches of 10-12 items each. Each batch runs as a delegate_task subagent with clear file ownership to avoid overlap.

1. Prioritize fixes by severity — production collapses first, then critical security, then high, then medium
2. Batch independent fixes into parallel subagents
3. After each batch, run the production build to verify nothing broke
4. For build errors that surface (common when fixing dormant issues), fix them immediately
5. Re-audit by running the build and checking that all routes compile

## Pitfalls

- **Dev server stale cache after batch edits.** When many files are edited via subagents while a dev server is running, HMR applies client-side changes but the server-side compiled HTML may be from an older build. Symptoms: hydration mismatches (different class names, different content between server and client), unstyled pages (Times New Roman font renders because Tailwind CSS wasn't re-processed), missing CSS. **Fix**: Kill all dev server processes, delete `.next/`, run `npx next build`, restart.
- **Subagents can't see what other subagents changed.** If two sub-agents modify the same file, the second one's changes overwrite the first. Track file ownership and avoid delegating fixes for overlapping files to separate agents.
- **Stripe webhook rate limiting.** Never apply IP-based rate limiting to Stripe webhooks — Stripe sends from its own infrastructure IPs. Additionally, CSP `form-action 'self'` blocks Stripe Checkout redirects — add `https://checkout.stripe.com` and `https://api.stripe.com` to form-action.
- **Token-based auth checks against non-existent fields.** If you query a collection for a field that doesn't exist in its schema, the query returns empty and the "auth passed" guard always passes. Verify the field exists in the collection definition.
- **Build errors after fixing are often pre-existing issues that were masked by broken imports or dead code paths.** Fixing the imports (for self-heal modules, for example) can surface errors that were hidden. Treat these as legitimate build fixes, not regressions from the audit.
- **The "timing middleware" trap.** `Date.now()` before and after `NextResponse.next()` called synchronously always measures ~0ms. True request timing requires a `Server-Timing` header or a wrapper around the response.
- **Mock functions in production.** Search for "mock", "fake", "stub", "placeholder" in function and variable names. Developers leave these in production more often than they admit.
