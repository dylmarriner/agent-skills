# Hostile Audit Patterns — Concrete Reference

Findings taxonomy from production hardening audits, categorized by severity and subsystem.

## Production Collapse Patterns (Fix These First)

### Auth That Doesn't Actually Auth
- **Pattern:** Querying a non-existent field on a CMS collection for token verification. The query always returns empty, making the "auth check" always pass.
- **Fix:** Replace with shared-secret pattern (env var + header check) or use the CMS's built-in session verification API.
- **Example:** `payload.find({ collection: 'admins', where: { token: { equals: sessionToken } } })` when the Admins collection has no `token` field.

### Missing Module Imports
- **Pattern:** Route imports 8 modules that don't exist. The route crashes on every invocation.
- **Fix:** Create stub modules with actual health-check logic, or remove the imports.
- **Example:** Self-heal cron importing `@/lib/self-heal/{database,cache,images,cdn,ssl,performance,seo,security}` when none of those files exist.

### Mock Functions in Production
- **Pattern:** Function named `calculateMockEstimate` used as the primary production pricing function while the real `calculateQuoteEstimate` sits unused.
- **Fix:** Swap to the real function. Delete or deprecate the mock.
- **Signal:** Function name containing "mock", "stub", "fake", "placeholder", "demo".

### Rate Limiting on Payment Webhooks
- **Pattern:** Stripe webhooks rate-limited by IP to 5 requests per 10 minutes. Stripe's own IPs hit this limit, causing webhooks to be dropped. Stripe stops retrying after 3 days.
- **Fix:** Never rate-limit payment webhooks. Rely on signature verification for security.
- **Corollary:** Any endpoint called by a trusted third-party infrastructure (Stripe, GitHub, AWS) should not have IP-based rate limiting.

### CI/CD That Never Runs
- **Pattern:** Workflow watches `main` but repo uses `master`. The second workflow file is broken YAML (mixed tabs/spaces).
- **Fix:** Match branch names to actual repo default branch. Delete non-functional workflow files.

### Empty Secret Fallbacks
- **Pattern:** `secret: process.env.SECRET || ''` — empty string used as encryption/JWT signing key. Token forgery for anyone who notices.
- **Fix:** Throw a meaningful startup error: `if (!process.env.SECRET) throw new Error(...)`.

## Common Security Gaps

### CSP Blocks Own Functionality
- **Pattern:** `form-action 'self'` blocks CSP-compliant browsers from redirecting to Stripe Checkout (`checkout.stripe.com`).
- **Fix:** `form-action 'self' https://checkout.stripe.com https://api.stripe.com`.

### Obituaries/Records Leak via Bulk Read
- **Pattern:** CMS collection `read` access: `if (!data) return true` — bulk list queries get ALL records including unpublished/draft.
- **Fix:** Return a query constraint for unauthenticated users: `{ visibility: { equals: 'public' }, approved: { equals: true } }`.

### Globals Without Access Control
- **Pattern:** CMS globals (Navigation, Footer, EmergencyBanner, QuoteSettings, SeoDefaults, SiteSettings) have zero access control defined. Payload defaults to public read.
- **Fix:** Add `access: { read: () => true, update: (req) => hasRole(req.user, 'editor') }` to every global.

### Stored XSS in CMS Fields
- **Pattern:** `ctaDestination` is plain text with no validation. Staff can set `javascript:alert(1)`.
- **Fix:** Add a `validate` hook that rejects values not starting with `/`, `http://`, `https://`, or `mailto:`.

## Frontend/UX Production Gaps

### Pages Without Metadata
- **Pattern:** Dynamic pages (obituary detail, location pages) have no `generateMetadata()` function. Every page gets the root template title.
- **Fix:** Add `generateMetadata()` with page-specific title, description, and OG image.

### Dual Design Systems
- **Pattern:** One page type uses classes like `bg-primary`, `text-primary-foreground`, `bg-muted` while the rest of the site uses `bg-brand-charcoal`, `bg-brand-ivory`. Two different frameworks on one site.
- **Signal:** Classes from shadcn/ui, Tailwind UI, or other framework defaults that don't exist in the project's `@theme` block.

### Dead Components
- **Pattern:** Components exist in `src/components/ui/` but are imported by zero files. Built for a design iteration that was abandoned.
- **Fix:** Search for imports before deleting. Cross-reference against the design system's current token set.

### Missing Sitemap Entries
- **Pattern:** Dynamic pages (obituaries, locations) not included in `sitemap.ts`. Critical SEO pages invisible to crawlers.
- **Fix:** Fetch from CMS in the sitemap function. Add per-page-type `changeFrequency`.

### 404/Error Pages Show Default
- **Pattern:** No custom `not-found.tsx` or `error.tsx`. Users see Next.js's default white error page.
- **Fix:** Create branded versions with navigation suggestions and contact info.

## Code Quality Patterns

### RBAC Without Hierarchy
- **Pattern:** Every access function manually checks `user.roles?.includes(...)` — 12 redundant functions with copy-paste role lists.
- **Fix:** Create a `ROLE_HIERARCHY` map and a single `hasRole(user, requiredRole)` helper.

### In-Memory State Not Production-Scalable
- **Pattern:** Rate limiter is a plain `Map<string, Entry>` — evaporates between serverless invocations, O(n) per request cleanup.
- **Fix:** Document upgrade path explicitly in comments. Don't pretend in-memory is production.

### Duplicate Implementations
- **Pattern:** Two schema directories (`seo/` and `schema/`), two Button components, two metadata builders, two FAQ rendering patterns.
- **Signal:** Files that do the same thing with different params. Always keep the one that's actually imported.

### API Response Patterns
- **Pattern:** Hardcoded fallback domains that don't match the actual production domain (`funeralcottage.co.nz` vs `papatoetoefuneralcottage.co.nz`).
- **Pattern:** Double JSON serialization (`JSON.stringify()` on a field that's already `json` type).
- **Pattern:** `catch {}` swallowing all errors silently (especially in analytics endpoints that do nothing but `console.log`).

## Live Site Cross-Reference Checklist

When replacing an existing live site, always verify these details match:

- [ ] Phone number (check formatting: spaces vs hyphens vs country code)
- [ ] Email address
- [ ] Physical address (street, city, postcode, country)
- [ ] Business name (exact legal name)
- [ ] All service/page names listed in the live navigation
- [ ] Testimonials/quotes from live site
- [ ] Social media links (Facebook, Instagram, etc.)
- [ ] Copyright notice format and year
- [ ] Pricing (if publicly visible)
- [ ] Opening hours / availability
- [ ] Any unique terminology the business uses (e.g., "Cottage" vs "Chapel")
