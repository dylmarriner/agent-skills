---
name: hostile-production-audit
description: Full-stack production readiness audit with hostile mindset. Covers security, frontend/UX, backend/infrastructure, code quality, and deployment/CI-CD. Uses parallel subagents for maximum coverage. Produces prioritized findings report with $NZD value context, orchestrates batch fixes across all severity levels.
platforms: [linux, macos]
category: security
triggers:
  - "audit this project for production readiness"
  - "hostile audit"
  - "review this codebase for a \\$50K standard"
  - "tear this apart"
  - "full stack audit"
  - "production review"
  - "pre-deployment audit"
  - "security audit"
related_skills: [security-auditor, audit-website, oss-forensics, ai-seo, qa-expert]
---

# Hostile Production Audit

A multi-agent full-stack audit framework for assessing web applications against production-grade standards. Assumes a "hostile auditor" mindset — maximum scrutiny, minimum mercy. Produces prioritized issue reports and orchestrates batch fixes.

## When to Use

Use this skill when the user asks to:
- "Audit this project" — any full-stack web app
- "Make this production ready"
- "Review for $X standard" (e.g., "make this worth $50K")
- "Tear this apart" / "hostile audit" — wants brutal honesty
- "Pre-deployment checklist" / "production review"
- Full-stack security, quality, or architecture review

Do NOT use for:
- Quick code review of a single PR — use `requesting-code-review` or `github-code-review`
- Single-layer audits (e.g., just SEO, just security) — use the dedicated skill
- Supply chain forensics — use `oss-forensics`

## Methodology

The audit runs in **parallel tracks** using `delegate_task`. Each subagent is a "hostile" specialist focused on one layer. They share no tools and mix no sources.

### Phase 0: Project Reconnaissance (before subagents)

Before spawning subagents, understand the project:
1. Read package.json, next.config.ts, tsconfig.json, and key config files
2. Check src/ directory structure
3. Check for existing audit reports (PRODUCTION_AUDIT_REPORT.md, etc.)
4. Note the tech stack (Next.js, React, Payload CMS, etc.)

### Phase 1: Parallel Hostile Audit Tracks

Spawn up to 3 subagents in parallel. Each gets the full project context and the instruction to be "MAXIMUM HOSTILE — no mercy."

**Track A: Backend & Infrastructure**
- Configuration files (next.config, tsconfig, payload.config, env-validation)
- Library code (rate-limit, email, logger, stripe, pricing engine, validation schemas)
- RBAC, access control, authentication
- Payload CMS collections and globals (missing fields, wrong types, access control gaps)
- Package.json (unused/incorrectly-placed dependencies)
- Middleware, migration files
- Tests (e2e and unit — do they actually test anything?)
- CI/CD workflows

**Track B: Frontend & UX**
- All page components — check for consistency, missing metadata, copy-paste
- Component library — find dead components, duplicate implementations
- Accessibility (aria attributes, keyboard navigation, skip links, color contrast)
- Responsive design and mobile behavior
- Form validation UX
- Loading/error/empty states
- Design token consistency (CSS variables vs hardcoded values)
- SEO metadata and schema markup

**Track C: Security & Business Logic**
- API routes — error response consistency, validation holes, hardcoded values
- Authentication/authorization on sensitive endpoints
- CSP and security headers
- Payment/webhook handling (idempotency, rate limiting, replay protection)
- PII handling and data leaks
- XSS vectors in CMS fields
- Third-party service integration issues

### Phase 2: Findings Compilation

Each subagent returns a structured summary. Compile into a single report with:

**Severity classification:**
- **CRITICAL (Production Collapse)** — will break in production within first week
- **CRITICAL (Security)** — actively exploitable vulnerability
- **HIGH** — significant quality/security/UX defect
- **MEDIUM** — code debt, inconsistency, missed feature
- **LOW** — polish, best practice

For each finding: file path, line number, description, fix recommendation.

Include a **$NZD context** — e.g., "This is a $15K project pretending to be $50K."

### Phase 3: Fix Orchestration

When the user says "fix everything," organize fixes into 4-5 parallel batches:

**Batch 1 — Production Collapses** (usually 5-8 items):
- Broken auth (e.g., inline-update API with missing token field)
- Missing files (e.g., self-heal modules that don't exist)
- Pricing engines using "mock" functions in production
- Rate limiting on critical endpoints (webhooks)
- CI/CD pointing at wrong branches
- CSP/security header gaps that break functionality

**Batch 2 — Security & API** (usually 8-10 items):
- Analytics endpoints that are no-ops
- Commented-out customer notifications
- Data access leaks (bulk reads returning unpublished data)
- Wrong email domains in routes
- Duplicate payment records on refunds
- XSS vectors in CMS globals
- Globals missing access control
- Environment validation gaps

**Batch 3 — Frontend & UX** (usually 8-10 items):
- Pages using wrong design system or template
- Dead components and duplicate implementations
- Missing metadata for SEO-critical pages
- Sitemap gaps
- Footer/components ignoring CMS data
- Lint suppressions and hydration warnings
- Accessibility fixes

**Batch 4 — Code Quality & Polish** (usually 8-10 items):
- RBAC hierarchy helpers
- Collection schema improvements (uniques, timestamps)
- Seed scripts fixing
- Environment variable docs
- Test fixes
- Quote rules misalignment

Each batch goes to a `delegate_task` subagent that reads files, applies fixes, and submits a build. After all batches complete, run a final production build to verify.

### Report Template

The final report should have:

```
## AUDIT SUMMARY
**Total issues found: X** (Critical: X, High: X, Medium: X, Low: X)

## TOP 5 FIRES THAT WILL BURN PRODUCTION DOWN
1. ...
2. ...
3. ...
4. ...
5. ...

## WHAT NEEDS YOUR ACTION (before deploy)
- openssl commands for secrets
- Third-party service registrations
- .env var updates

## BUILD STATUS
✅ / ❌
```

## Pitfalls

- **Don't run all 3 audit tracks in one subagent** — they must be separate delegate_task calls for source isolation
- **The hostile tone is part of the output** — the user expects brutal honesty, not polite suggestions
- **Don't skip the build at the end** — always verify fixes compile
- **Check for dead components by searching for imports** — never delete files without confirming zero references
- **When fixing, always read files first** before modifying — subagents that modify files may conflict with other subagents' changes
- **Copy error/loading/not-found pages to root AND route group** — Next.js needs them at `src/app/` level, not inside `(route-group)/`
- **Check default branch name** in .git/config before fixing CI/CD workflows — repo might use `master` not `main`
- **SQLAlchemy asyncpg JSONB serialization** — raw SQL `INSERT` with `CAST(:param AS jsonb)` in asyncpg needs the Python value to be a `str`, not a `list`/`dict`. Always `json.dumps()` Python lists/dicts before passing to the params dict. Also, `jsonb_build_object('key', :val)` with parameterized placeholders fails under asyncpg with `IndeterminateDatatypeError` — build the full JSON object in Python as a single `json.dumps()` string and pass it as `CAST(:metadata AS jsonb)`. See `references/asyncpg-jsonb-patterns.md`.
- **gen_random_uuid() for SQLAlchemy ORM tables** — When models define `id: Mapped[uuid.UUID] = mapped_column(UUID(...), primary_key=True, default=uuid.uuid4)`, raw SQL `INSERT` statements must explicitly specify `id` with `gen_random_uuid()`. The Python-level `default=uuid.uuid4` does NOT translate to a database-level default — Postgres will reject `NULL` for the `id` column. Either add `DEFAULT gen_random_uuid()` at the DB level or include `id` + `gen_random_uuid()` in every raw INSERT.

## Related Skills

- `security-auditor` — dedicated security code review (narrower scope)
- `audit-website` — squirrelscan-based live site audit
- `oss-forensics` — supply chain and GitHub forensics
- `qa-expert` — testing strategy and quality assurance
