---
name: production-audit-remediation
description: |
  Full-production audit and remediation workflow for web applications.
  Multi-tool parallel investigation (security, frontend, code health, SEO, AIEO)
  followed by systematic multi-phase fix orchestration with subagents,
  build-fix-verify iteration, and final report generation.
version: 1.0.0
tags: [audit, security, seo, production, remediation, quality, aieo]
triggers:
  - "audit this project"
  - "make this production ready"
  - "fix everything"
  - "audit and fix [project]"
  - "production audit"
  - "$50k website"
  - "check if this is ready to deploy"
---

# Production Audit & Remediation

A multi-phase framework for auditing web applications against production-grade
standards and fixing all identified issues systematically.

---

## Phase 0: Discovery

1. **Understand the project** — read package.json, explore directory structure,
   check the existing tech stack (Next.js, Payload CMS, etc.)

2. **Check for existing audit reports** — look for `PRODUCTION_AUDIT_REPORT.md`
   or similar files. Understand what's been done before.

3. **Load relevant skills** from all available sources:
   - Hermes (skills_list + skill_view)
   - skills.sh (`npx skills find <query>`)
   - ClawHub (`clawhub search <query>`)

---

## Phase 1: Multi-Tool Parallel Audit

Spawn up to 3 subagents in parallel, each covering a different audit dimension:

### Investigator A: Security & Infrastructure
- **squirrelscan** live site audit (`squirrel audit <url> --format llm`)
- Security headers check (HSTS, CSP, XFO, Permissions-Policy)
- robots.txt + sitemap.xml validation
- Rate limiting test on all API endpoints (hit each 10x, look for 429)
- Form submission security (Zod validation, honeypot fields, XSS vectors)
- Stripe webhook signature verification testing
- Secrets exposure check (.env in git, hardcoded API keys)
- CSP production vs dev mode analysis

### Investigator B: Frontend & UX
- Accessibility (WCAG 2.2 AA): skip links, keyboard nav, color contrast, aria attributes, error/loading/not-found pages
- Mobile responsiveness of all components
- Loading states, error boundaries, empty states
- Form validation UX (field-level errors, aria-invalid, focus management)
- Image optimization (next/image vs img tags, lazy loading)
- Component reusability and pattern consistency
- Tailwind CSS version compatibility (v3 vs v4 configs)
- JSON-LD schema quality (duplicates, URL construction, @id linking)
- Console warnings and hydration issues

### Investigator C: Code Health
- Pending issue verification from previous audit reports
- TypeScript type safety (`any` usage count)
- Error handling patterns (catch block consistency, silent catches)
- Logging adoption (console.log vs structured logger migration %)
- Unused dependencies or SDKs (e.g., Sentry installed but not imported)
- Dead code and TODO comments
- Request ID tracing / middleware
- Bundle size concerns (large components needing splitting)

### Investigator D: SEO & AIEO (if applicable)
- Traditional SEO: meta titles/descriptions, OG tags, core web vitals
- AIEO: llms.txt, pricing.md, AI bot access in robots.txt
- Content extractability: FAQ schema, comparison tables, definition blocks
- E-E-A-T signals: author attribution, last-updated dates, expert sourcing
- Competitor citation analysis (who gets cited in AI answers vs you)

---

## Phase 2: Evidence Consolidation

Collect all findings into a structured master list grouped by severity:

| Severity | Meaning | Action |
|----------|---------|--------|
| **CRITICAL** | Blocks launch, breaks core functionality | Fix immediately |
| **HIGH** | Hurts quality, security, or UX significantly | Fix before deploy |
| **MEDIUM** | Code quality / maintainability | Fix post-launch |

For each issue record:
- ID (C1, H1, M1, etc.)
- Title
- Severity
- Location (file path)
- Root cause
- Fix instructions

---

## Phase 3: Systematic Fix Orchestration

Organize fixes into 5 phases, executing parallel batches via subagents:

### Phase A: Critical Fixes
**Pattern**: The blockers — broken phone numbers, unauthenticated APIs, missing error pages, broken schema, build-breaking type errors.

**Approach**: Fix each independently via parallel subagents. Each subagent handles a distinct fix area.

### Phase B: Security Hardening
**Pattern**: CSP directives, rate limiting on all endpoints, authentication guards, robots.txt conflicts, missing headers.

**Approach**: One subagent fixing next.config.ts + all API routes. Verify with build after.

### Phase C: UX Polish
**Pattern**: Accessibility fixes, keyboard handlers, form validation UX, OG images, color contrast, hiding admin features from non-admins.

**Approach**: One subagent per major fix area. Submit all changes, verify with build.

### Phase D: Code Quality
**Pattern**: Component consolidation (remove duplicates), delete dead config files, add middleware, fix import paths.

**Approach**: Clean up structural issues. Run build after to catch any broken imports.

### Phase E: AIEO + SEO
**Pattern**: Create llms.txt, pricing.md, update robots.ts for AI crawlers, enhance schema with @id, add OG metadata.

**Approach**: Create files and update configs. Verify with build.

---

## Phase 4: Build-Fix-Verify Loop

After each phase:
```
1. Run `npx next build` (or equivalent)
2. If build fails, fix the specific error:
   - Import path mismatches
   - API type mismatches (zod v3 vs v4, payload version changes)
   - Missing `notFound()` imports (Next.js 15+ requires proper import)
   - Missing `from` field in email send calls
   - Migration type import paths
3. Rebuild
4. Repeat until clean
```

**Common build traps in Next.js 16 + Payload CMS 3:**
- `return { notFound: true }` must be `notFound()` (from `next/navigation`)
- `redirect()` must be imported from `next/navigation`
- `z.literal(true, { errorMap })` → Zod v4: `z.literal(true, { message })`
- Migration imports: `from 'payload/database'` → local type alias
- Email calls need `from:` field matching EmailParams interface

---

## Phase 5: Report Generation

Write a comprehensive audit report:
```
PRODUCTION_AUDIT_REPORT_v2.md
```

Cover:
- Executive summary with score estimates
- What was fixed in each phase
- What remains (user-actionable items)
- Build verification status
- Final verdict (production ready or not)

---

## Anti-Hallucination Guardrails

1. **Evidence-First**: Every audit finding must cite specific file paths and line numbers.
2. **Verify Before Claiming**: Check build output yourself, don't trust "subagent said it compiled".
3. **Source-Level Verification**: When checking if a previous issue was "resolved", read the actual source file — don't trust the report.
4. **Subagent Output Validation**: Subagent summaries are self-reports. Verify critical changes (auth guards, rate limiting, non-public deletions) by reading the modified files yourself.

---

## Parallel Subagent Pattern

```
Phase A: Critical Fixes
┌─────────────────────────────┐
│ Subagent 1: Phone numbers   │  → Independent find+replace
├─────────────────────────────┤
│ Subagent 2: Error pages     │  → Create error/loading/not-found
├─────────────────────────────┤
│ Subagent 3: Schema cleanup  │  → Delete duplicates, fix imports
├─────────────────────────────┤
│ Subagent 4: RichText keys   │  → Fix React reconciliation
└─────────────────────────────┘
         ↓
    BUILD VERIFY
         ↓
Phase B: Security Hardening (parallel subagents)
         ↓
    BUILD VERIFY
         ↓
... continue through all phases
```

Each subagent gets:
- `goal`: the specific fix to apply
- `context`: project root, file paths, brand colors, existing patterns
- `toolsets`: `["terminal", "file"]`

---

## User Preference Embedding

- Dylan prefers comprehensive "fix everything in one pass" — don't ask for phased approval
- Skip overviews/comparisons when installing skills — load, check, test, report
- Direct correction language = firm rules, not rudeness
- Production code must be placeholders/stubs/TODO-free
