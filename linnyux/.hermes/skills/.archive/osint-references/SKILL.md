---
name: osint-references
version: 1.0.0
description: Supporting reference files for the osint skill — search engine fallback ladder and NZ-specific source URLs. Created because the osint skill has a name collision preventing direct file writes.
---

# OSINT References

This skill packages the reference files that the main `osint` SKILL.md references. Load these files via `skill_view(name='osint-references', file_path='references/...')`.

See:
- `references/search-limitations-and-fallbacks.md` — 11-layer search engine fallback ladder with query limits and pitfall warnings
- `references/nz-osint-sources.md` — NZ government database URLs, OIA paths, and gang intelligence sources

## Search Limitations & Fallback Ladder

Real-world bot-detection landscape. Last updated: 2026-07-19.

### The Fallback Ladder

When one layer fails, drop to the next immediately. Do NOT retry the same engine.

| Layer | Engine/Method | Typical Limit | Failure Signal |
|---|---|---|---|
| 1 | `web_search` (Firecrawl) | Credit-dependent | "Payment Required" |
| 2 | DDG HTML (`html.duckduckgo.com/html/`) | ~6-8 queries | Empty body OR CAPTCHA |
| 3 | Bing browser (`browser_navigate` to bing.com) | ~2-3 queries | Cloudflare "Verify you are human" |
| 4 | DDG JS browser | ~2 queries | "Select squares with duck" |
| 5 | Brave Search browser | ~1-2 queries | Cloudflare challenge |
| 6 | Ecosia browser | ~1 query | Cloudflare "robot" |
| 7 | Mojeek (`mojeek.com`) | ~1-5 queries | 403 or empty |
| 8 | SearXNG public instances | Varies | 429 |
| 9 | Tor-based (`torsocks curl`) | Harder to block | Bypasses most CF |
| 10 | Ahmia dark web (Tor) | Very slow | Limited NZ coverage |
| 11 | Direct API to target site | Fragile | JSON/API changes |

### Critical Pitfalls

**DDG HTML empty body = false negative.** DDG returns empty body when rate-limited — identical to genuine zero results. After ~6 queries, every subsequent query is empty regardless. Never report this as a factual negative.

**Bing "About 1 results" with junk = block in progress.** Bing returns a single irrelevant foreign domain result when bot detection is ramping up. Not real.

**Google via curl = JS wall.** Returns JS challenge. Unusable without browser.

### When to Stop

After layers 1-10 exhausted with zero results across name variants:
1. Report what was tried and what was blocked
2. State "not on publicly indexed web" — NOT "doesn't exist"
3. Note absence from indexes IS intel (sealed records, aliases, pre-digital era)
4. Suggest: OIA requests, Police NIA, Corrections internal, data brokers

### NZ-Specific Search Patterns

- **NZ Herald topic pages** (`/topic/gangs/`): Return `Fusion.globalContent` JSON with full article metadata. Parse directly.
- **Stuff.co.nz**: `?q=` redirects silently — does NOT search
- **Police media**: `police.govt.nz/news?search=<query>` (Drupal HTML)
- **Parliament Hansard**: `parliament.nz/en/pb/hansard-debates/rhr/search?criteria.Keyword=<query>`
- **NZ Gazette**: `gazette.govt.nz/search/Search/?SearchText=<query>`
- **Companies Office**: `app.companiesoffice.govt.nz/companies/app/ui/pages/companies/search?q=<query>`
- **NZLII court judgments**: Cloudflare-protected. Use `torsocks curl`.
- **MOJ Judicial Decisions**: `forms.justice.govt.nz/jdo/Search.jsp` — Cloudflare, needs Tor
- **Corrections OIA**: `corrections.govt.nz` — file OIA for custodial records
- **Police vetting**: `police.govt.nz/advice-services/business-and-organisations/vetting` — $8.50 per name

## Gang Investigation Methodology

When targets have known gang affiliations (Black Power, Manu Kaha, Mongrel Mob, Comancheros, etc.):

1. **Gang name IS the discriminator.** Common surnames like "Daniels" have dozens of non-criminal matches. Always include gang name in every query.
2. **Search SURNAME + gang** not just full name — catches family/associates
3. **Gang members appear under street names**, not legal names, in news
4. **Many gang members with extensive records have ZERO web presence** — non-indexed District/Youth Court databases hold the bulk
5. **NZ Herald Fusion.globalContent** on `/topic/gangs/` is the richest NZ gang news source
6. **Police operations** (Operation Fantail, Operation Highwater, etc.) name arrestees in press releases — search by operation name
