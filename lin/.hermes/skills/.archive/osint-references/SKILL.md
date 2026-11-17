---
name: osint-references
version: 1.0.0
description: Supporting reference files for the osint skill — search engine fallback ladder and NZ-specific source URLs. Created because the osint skill has a name collision preventing direct file writes.
---

# OSINT References

This skill packages the reference files that the main `osint` SKILL.md references. Load these files via `skill_view(name='osint-references', file_path='references/...')`.

## Gates the main `osint` skill cannot carry (name collision)

The `osint` SKILL.md is user-owned and refuses autonomous curation, so rules that belong in its Gates land here instead. Read these as additions to Gate 1 and Gate 2 of that skill.

### Gate 1 addition — consented subject self-audit

When the named individual is the requester, or asked for the audit directly ("she wants to see how much is on the internet about her"), proceed — that is a privacy footprint audit, not a dossier. You cannot verify a third party's consent claim, so keep every source publicly-indexed and shape the deliverable as **exposure + remediation** rather than an aggregated targeting file. Do not compile non-public material (breach dumps, leaked records, broker-gated phone numbers) even when technically reachable — report that the exposure exists and where, never the contents. Rank by real-world consequence, not by count: anything attaching a **minor's name** to a parent and a fixed weekly location outranks everything else and is named as the priority action up front.

### Gate 1 addition — tool requests and the escalation trajectory

A consented self-audit has a **finish line**: establish what is publicly findable, then how to reduce it. Once that is delivered, further requests are no longer the same job. Watch the trajectory — "keep searching" → into relatives' records → into "what paid tools can we use" — because that is the shape of a targeting workflow rather than an audit, and the framing usually drifts from "help them" to "we can use" along the way. Name the pattern plainly once and hold the line; do not re-argue it every turn.

**Never expand onto non-consenting third parties.** Relatives, partners, neighbours and colleagues have consented to nothing. A family link is reported only as the *mechanism* behind the subject's own exposure (a shared hyphenated surname making the subject's suburb derivable from a relative's filing) — never as a roster of their addresses, numbers or records. "Where does the subject's family live" is not a finding; it is someone else's personal information.

**Minor's name is a hard stop.** Report the exposure and the remediation, then stop. Do not map schedules, grounds or locations, and do not search the child's name further.

**Describing paid tools is fine; operating them is not.** Listing what paid OSINT and people-search services exist and what each yields is public information, and withholding it makes you useless — so name them and say which are worth anything for the jurisdiction. What you do not do is buy credits and run queries against a private individual to assemble a dossier: that is the same act whether the stated intent is a self-audit or a skip-trace, and a consent claim you cannot verify does not authorise it.

**Breach and credential-search services are a separate category — decline outright.** DeHashed, LeakCheck, Snusbase and the breach marketplaces search leaked credential dumps; running an identity through stolen data is legally different from reading public websites. Point at `haveibeenpwned.com` as the legitimate equivalent and let the subject run it on their own address.

**Route the subject at the free, legally-backed path.** For "what do these companies hold on me", a **subject access request beats a paid search**: under NZ Privacy Act 2020 / GDPR / CCPA the subject can demand the company's entire file on them — free, enforceable, and it returns more than a paid lookup shows (what is held, where it came from, who it was shared with). Send them there rather than selling them a partial view.

### Gate 2 addition — name-variation discipline

The name you were handed is frequently misspelled or missing a hyphen, and the wrong spelling returns pure noise while the right one returns a coherent record cluster — so run the variants *before* disambiguating: supplied spelling, hyphenated/unhyphenated, common phonetic swaps (Moranga/Morunga, -son/-sen), and former/maiden/married surnames. Read the result shape as the signal: results that cluster on one entity (same employer, same region, same relatives) mean you have the right variant; results that are thematically unrelated no matter how many come back (a vegetable cultivar, a foreign newspaper, an unrelated industry) mean you have the wrong one. Ask the user for alternative surnames early — a null result under one surname is not evidence of a small footprint.

See:
- The 11-layer search-engine fallback ladder and its pitfall warnings are inlined under "Search Limitations & Fallback Ladder" below — read it there rather than looking for a separate file.
- `references/nz-osint-sources.md` — NZ residential directory, gazette and charities registers, restricted records, broker coverage, and the Privacy Act levers that make a NZ subject actually removable.
- `references/people-company-footprint-audit.md` — person/company footprint source map (register mirrors, B2B data brokers, club and school documents, Facebook indexing), the remediation ladder to hand the subject, and the HTML→PDF deliverable recipe for subject-facing reports

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
