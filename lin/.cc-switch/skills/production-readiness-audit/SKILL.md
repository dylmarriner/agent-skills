---
name: production-readiness-audit
description: |
  Multi-track production readiness audit. Orchestrates parallel subagents for
  security, frontend/UI/UX, code quality, SEO/AIEO, and infrastructure analysis.
  Compiles findings into a unified report with severity-graded issues and phased
  fix plans. Designed for high-value ($50K+) production deployments.
version: 1.0.0
toolsets: [delegation, terminal, file]
platforms: [linux, macos]
---

# Production Readiness Audit

Orchestrate a comprehensive multi-track audit of a web application codebase for
production deployment. Spawns parallel specialist subagents, then compiles their
findings into a unified severity-graded report with phased fix plans.

## When to Use

Use this skill when:

- The user asks to "make this production ready" or "audit for production"
- The user says a site needs to meet a specific dollar-value standard ($10K, $50K, etc.)
- Deploying a new application and need a comprehensive pre-launch checklist
- The user asks for a "full audit" or "everything check" of their codebase
- A previous audit existed and needs verification + extension

Do NOT use this skill for:
- Quick CI/CD pipeline checks (use `audit-website` with `--coverage quick` directly)
- Single-aspect reviews like "check my SEO" or "review my security headers" alone
- Code review on a single PR (use `code-reviewer` instead)

## Audit Tracks

Spawn up to 4 parallel subagents. Each runs independently and returns a structured
summary. Pass the project root path and relevant context.

### Track 1: Security & Infrastructure
**Context to pass**: Project root, .env path (without secrets), next.config.ts path,
playwright config, package.json.

**Checks**:
- Security headers (HSTS, CSP, XFO, XSS, Referrer-Policy, Permissions-Policy)
- CSRF/XSS protections (CSP directives, input sanitization, DOMPurify usage)
- Rate limiting on all POST endpoints
- Authentication on admin/API routes
- Secrets exposure in source code
- robots.txt and sitemap.xml (no conflicting static+dynamic files)
- HTTPS redirect configuration
- CAPTCHA on public forms
- Stripe webhook signature verification
- Database connection configuration
- Request timeout configuration
- Error logging (structured logging vs console.log)

### Track 2: Frontend / UI / UX
**Context to pass**: src/components/ path, src/app/ path, package.json.

**Checks**:
- Accessibility (WCAG 2.2 AA): skip links, keyboard nav, aria attributes, color contrast
- Error boundaries: error.tsx, loading.tsx, not-found.tsx presence
- Form validation UX: field-level errors, aria-invalid, focus management
- Mobile responsiveness across all pages
- Image optimization: next/image usage, lazy loading, sizes attributes
- React patterns: stable keys (no key={Math.random()}), component splitting
- Component duplication: multiple implementations of same concept
- Tailwind/CSS: no undeclared theme classes, proper plugin usage
- Empty states for all data-fetching components
- Console warnings and hydration mismatches

### Track 3: Code Quality & Architecture
**Context to pass**: Full src/ tree, package.json, tsconfig.json, existing test files.

**Checks**:
- TypeScript any usage count and locations
- Code splitting: components over 500 lines flagged
- Duplicate implementations (meta functions, schema components, button components)
- Lint suppression patterns (eslint-disable frequency)
- Dead code: unused imports, unreachable code paths
- Error handling patterns: unknown vs any, silent catches, empty catch blocks
- Import organization and tree-shaking capability
- Migration compatibility (e.g. Tailwind v3 config coexisting with v4)
- Test coverage gaps

### Track 4: SEO / AIEO / Content
**Context to pass**: src/app/ pages tree, next.config.ts, any existing SEO docs.

**Checks**:
- Meta titles (50-60 chars), descriptions (150-160 chars), unique per page
- og:image / twitter card presence on all pages
- JSON-LD schema: single implementation, no duplicates, proper @id linking
- AIEO readiness: llms.txt, pricing.md, robots.txt allowing AI crawlers
- Author attribution and last-updated dates on content
- Content thickness (300+ word minimum per page)
- E-E-A-T signals: named authors, cited sources, contact page, privacy policy
- URL structure: clean, keyword-inclusive
- Core Web Vitals: LCP, CLS, INP baseline from lighthouse or PageSpeed
- Canonical URLs and hreflang tags

## Orchestration Workflow

### Phase 1: Project Recon (30 seconds)
```bash
find . -maxdepth 3 -type f | head -80  # Quick structure overview
cat package.json  # Identify stack
cat next.config.ts  # Check security headers
```

### Phase 2: Spawn Parallel Subagents
Spawn 3-4 subagents using `delegate_task` with the `tasks` array for parallelism.
Each task MUST specify:
- `goal`: what to audit (from the track checklists above)
- `context`: project root path, key files to check, stack info
- `toolsets`: ["terminal", "file"] for each

```javascript
tasks: [
  {
    goal: "Run Track 1: Security & Infrastructure audit",
    context: "Project at /path/to/project. Stack: Next.js 16 + Payload CMS 3. ...",
    toolsets: ["terminal", "file"]
  },
  {
    goal: "Run Track 2: Frontend / UI / UX audit",
    context: "...",
    toolsets: ["terminal", "file"]
  },
  // ... up to 4 parallel tasks
]
```

### Phase 3: Run Squirrelscan (if live URL exists)
This runs in parallel with the above subagents. If the site is deployed:
```bash
squirrel audit https://example.com --format llm --coverage surface -m 100
```

If the live URL points to a different platform (e.g. Wix placeholder), note it
as baseline but focus audit on the codebase.

### Phase 4: Compile Unified Report
Collect all subagent summaries and squirrelscan output. Structure the report:

1. **Executive Summary**: Overall grade, key score, verdict (production ready or not)
2. **CRITICAL issues**: Blocks deployment, must fix first
3. **HIGH issues**: Fix before launch
4. **MEDIUM issues**: Fix post-launch or first sprint
5. **Previous Audit Reconciliation**: If an earlier report exists, verify each claim
6. **AIEO / AI SEO section**: LLM citation readiness
7. **Phased Fix Plan**: Ordered by dependency, estimated effort per phase
8. **Appendices**: Full finding details, source file references

Write the report to `<project>/PRODUCTION_AUDIT_REPORT.md` (or create a v2 if one exists).

## Report Format Rules

- Every CRITICAL finding must have a specific file path and line number
- Severity rubric:
  - **CRITICAL**: Site won't function or is actively exploitable
  - **HIGH**: Won't pass a professional QA review or security audit
  - **MEDIUM**: Technical debt that compounds over time
  - **LOW**: Nice-to-have polish
- Each finding gets a unique ID (C1, C2, H1, H2, M1, M2, etc.)
- Phased fix plan must be ordered: fixes earlier phases unblock later ones
- Verdict must be explicit: "PRODUCTION READY", "NOT PRODUCTION READY", or "CONDITIONAL"
- If conditional, list the exact conditions for sign-off

## Pitfalls

- **Live site != codebase**: The production URL may be an old Wix/WordPress site
  while the audit target is a new Next.js build. Always verify what's live.
- **Previous audit overconfidence**: Always verify resolved claims by checking
  actual source files, not just trusting the report.
- **Parallel exhausts context**: Subagent summaries are self-reported. Always
  verify critical claims by checking source files yourself.
- **CSP prod vs dev**: Production CSP often removes unsafe-eval/unsafe-inline but
  may break Next.js CSS-in-JS or hot reload. Always validate both modes.
- **squirrelscan binary**: The GitHub release URL uses `squirrelscan/squirrelscan`
  org, not `squirrelscan/squirrel`. Download from the
  [download page](https://squirrelscan.com/download), not a guessed URL pattern.
- **Rate limiting gaps**: Form POST endpoints are often rate-limited but Stripe
  webhooks, health checks, and analytics endpoints are not. Check ALL POST routes.
- **Duplicate JSON-LD**: Common when two developers independently implement schema
  components. Check for `<script type="application/ld+json">` duplicates in the DOM.
- **tailwind.config.ts + globals.css @theme**: If both exist simultaneously in
  Tailwind v4 migration, theme tokens may not resolve. Delete the v3 config file.

## Related Skills

- `audit-website` — squirrelscan-based automated website scanning (230+ rules)
- `ai-seo` — AI search engine optimization / LLM citation strategy
- `website-seo` — Comprehensive on-page SEO system
- `seo-audit` — Traditional SEO audit methodology
- `qa-expert` — Testing strategies and quality assurance
- `security-review` — Codebase security scanning
