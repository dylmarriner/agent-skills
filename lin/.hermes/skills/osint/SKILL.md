---
name: osint
version: 1.2.0
description: Open-source intelligence on people, companies, domains, and B2B accounts. Use when the user wants to investigate, vet, research, or build a dossier on a target — phrases like "OSINT", "due diligence", "background check", "research this person", "look into [company/domain]", "vet this prospect/vendor", "what does X do", "is this account worth pursuing", "find me a contact at", "who's the buyer for", or any open-source investigation task. Disambiguates identities before reporting and grades every claim by independent source count.
---

# OSINT

Open-source intelligence gathering with disambiguation discipline, confidence grading, and tiered depth. Public sources only. No breach data. No social engineering. Scope-respecting.

This skill is the orchestrator. You do the thinking. Tools and scripts are workers — they fetch, you decide.

---

## How to use this skill

1. **Classify the target.** Person, company, domain/IP, B2B account, due-diligence subject, or threat entity. If ambiguous, ask the user.
2. **Pick a depth.** Quick (≤5 min, web search only) → Standard (15–30 min, multi-tool) → Deep (full dossier, may take an hour). Default to Standard unless the user signals otherwise.
3. **Run the gates** below — every investigation, every time.
4. **Route to a workflow.** See the routing table.
5. **Produce the output contract** — a markdown dossier plus a `findings.json` sidecar.

---

## The Four Gates

Run these in order. Skipping any of them is how OSINT goes wrong.

### Gate 1 — Scope & Authorization

Before a single query, confirm:

- **Lawful basis.** Public information about a public-facing target (executive, company, public domain) is fine. Private individuals investigated for stalking, harassment, or unauthorized vetting are **not**. If the request smells like that, decline and say why.
- **No prohibited methods.** No paid breach databases. No social engineering. No accessing accounts you don't own. No bypassing paywalls or platform ToS. No active probing of infrastructure (port scans, vuln scans) without explicit authorization.
- **Scope statement.** Write one sentence: *"I am researching [target] for [purpose] using [public sources]."* If you can't write that sentence cleanly, stop.

See `references/ethics-and-scope.md` for full rules and the decline-it list.

### Gate 2 — Disambiguation

The single biggest OSINT failure mode is conflating two people (or two companies) with the same name. Before reporting **anything** about a target:

1. Identify all plausible candidates that match the name/handle.
2. Pick a **discriminator** — employer, location, age range, domain, industry, photo.
3. Confirm the discriminator from a primary source (LinkedIn, corporate bio, company website, official registry).
4. State which candidate you're tracking and which ones you're explicitly **not**.

If you can't disambiguate, say so. Don't guess.

**Gang/criminal targets:** When investigating individuals with known gang affiliations (Black Power, Manu Kaha, Mongrel Mob, Comancheros, Head Hunters, Hells Angels, King Cobras, etc.), the gang name IS the discriminator. Common names like "Daniels" will have dozens of non-criminal matches — always include the gang name in every search query. Also:

- Gang members often appear in news under street names/nicknames, not legal names
- Search the SURNAME + gang name (not full name) to catch family members and associates
- NZ Herald topics/gangs page has rich JSON data (`Fusion.globalContent`) — parse it directly
- Many gang members with extensive criminal records have ZERO indexed news presence — non-indexed court databases (District Court, Youth Court) hold the bulk
- If web search returns nothing, that's a finding worth reporting but not proof of clean record

See `references/disambiguation.md` for the full protocol.

### Gate 3 — Source Independence

A "fact" repeated by ten content-farm sites that all copied one LinkedIn bio is **one source**, not ten. Before grading a finding:

- Trace each claim to a primary source (the entity itself, an authoritative registry, a first-hand account).
- Two sources owned by the same parent, or two articles citing each other, count as one.
- Self-published claims (the target's own LinkedIn, bio, website) are useful for *what they claim* but not independent confirmation of the underlying fact.

### Gate 4 — Confidence Grading

Every finding gets a letter grade in the dossier:

- **A** — Three or more independent sources, including at least one primary or authoritative.
- **B** — Two independent sources.
- **C** — One source, or multiple non-independent sources.
- **D** — Inferred, likely-but-unconfirmed, or single self-published source.

If a finding can only get a D, either drop it or label it as inference.

See `references/confidence-grading.md` for the rubric and edge cases.

---

## Routing table

Match the user's intent to a workflow. If unclear, ask.

| User intent / phrasing | Workflow |
|---|---|
| "Research this person", "background check on", "who is X" | `workflows/person.md` |
| "Look into this company", "what does X do", "is X legit" | `workflows/company.md` |
| "B2B account intel", "is this prospect worth pursuing", "find the buyer at", "what's their stack", "who's their MSP" | `workflows/b2b-account.md` |
| "Check this domain/IP", "tech footprint", "what's running on", "subdomains of" | `workflows/domain.md` |
| "Due diligence", "investment-grade research", "vet this vendor/partner" | `workflows/due-diligence.md` |

For multi-target investigations (e.g., a person at a company), run the relevant workflows in sequence and merge the outputs.

---

## Phase model

Pick a depth at the start. Tell the user the depth and the rough budget so they can adjust.

### Quick (≤5 min, web_search only)

- 3–5 targeted searches.
- Read 1–2 primary sources.
- Output: 2–3 paragraph summary + 3–5 cited findings + confidence grades.
- Use for: triage, "do I care about this", before-a-meeting prep.

### Standard (15–30 min, multi-tool)

- 8–15 targeted searches across general web, LinkedIn, corporate registries.
- Read 5–10 primary sources, including the target's own properties.
- Cross-check at least three claims for source independence.
- Output: full dossier per `templates/dossier.md` + `findings.json` sidecar.
- Use for: most B2B account work, prospect research, person research.

### Deep (60+ min, all available tools)

- Iterative search with progressive narrowing.
- DNS/WHOIS/cert transparency for domain targets.
- Multiple platforms cross-referenced.
- Historical data (Wayback) where it changes the picture.
- Output: full dossier, findings.json, plus a one-page executive summary.
- Use for: due diligence, investment decisions, big-account work.

If you're going to exceed the budget you stated, stop and tell the user before continuing.

---

## Output contract

Every Standard or Deep investigation produces two artifacts:

1. **`<target-slug>-dossier.md`** — human-readable, follows `templates/dossier.md`. Section headers, confidence grades on every claim, source URLs collected at the bottom.
2. **`<target-slug>-findings.json`** — machine-readable, follows `templates/findings.schema.json`. Each finding has `claim`, `confidence`, `sources[]`, `category`, `extracted_at`.

For Quick investigations, the markdown summary is enough. JSON is optional.

Save outputs to a folder named `osint/<target-slug>/` in the working directory unless the user specifies otherwise.

---

## Tool usage

**Required minimum:** web search + ability to fetch URLs. The skill works with just these.

**Strongly helpful (graceful degradation):**
- LinkedIn search (via web search operators or scraper)
- WHOIS / DNS / certificate transparency for domain work
- GitHub search (free API tier is plenty)
- Wayback Machine (`web.archive.org`) for historical
- Apify or Bright Data actors for social platform extraction (if API keys present)

**Search operator reference:** `references/search-operators.md` — Google dorks, LinkedIn X-ray, GitHub search syntax, Wayback usage.

**Search engine limitations:** `references/search-limitations-and-fallbacks.md` — bot-detection landscape for OSINT: 11-layer fallback ladder, query limits per engine, critical pitfalls (DDG HTML empty body IS a false negative, not evidence of zero results), when to stop and pivot. Read before any investigation.

**NZ-specific sources:** `references/nz-osint-sources.md` — direct URLs for NZ court databases, corrections, companies office, news archives, OIA paths, Fusion API access, and gang intelligence. For any NZ target, read this first.

**NZ genealogy & founding families:** `references/nz-genealogy.md` — Kerr Taylor family pattern for tracing NZ founding families through Wikipedia + Heritage NZ property pages. Replicable for any descendant of a historic NZ family (Taylor, Logan Campbell, Dilworth, Bucklands, etc.). Use when the target mentions descent from a known NZ family, landowner, or early settler.

**API key check** (do this once at the start of any Standard or Deep investigation, silently):

```bash
[ -n "$GITHUB_TOKEN" ]   && echo "github: yes"   || echo "github: no"
[ -n "$BRAVE_API_KEY" ]  && echo "brave: yes"    || echo "brave: no"
[ -n "$APIFY_TOKEN" ]    && echo "apify: yes"    || echo "apify: no"
[ -n "$SHODAN_API_KEY" ] && echo "shodan: yes"   || echo "shodan: no"
```

If a key is missing, fall back to web search. Never tell the user "I can't do this" without first trying the fallback.

---

## Anti-patterns to avoid

- **Don't open with the dossier.** State the depth, scope, and disambiguation result first; produce the dossier at the end.
- **Don't manufacture confidence.** A C-grade finding labeled C is useful. A C-grade finding labeled A poisons the rest of the report.
- **Don't pad with noise.** Five well-sourced findings beat fifty drive-by mentions.
- **Don't assume the most prominent match is the right one.** The CEO is famous; the IT director you're actually trying to reach is not.
- **Don't write speculative biography.** If a source doesn't say it, you don't either.
- **Don't keep mining after the question is answered.** Quick means quick.
- **Don't conclude "not found" from search-engine failures.** DDG HTML returns "no results" after rate-limit kicks in. Bing returns junk. "Zero results from search engines" is a methodology gap, not a factual negative. Always report what was tried and what was blocked. See `references/search-limitations-and-fallbacks.md` for the full landscape.
- **Don't keep searching with wrong names.** This is the #1 time-waster in gang/criminal OSINT. Gang members with extensive records often have ZERO internet footprint under their street names. If 10+ queries across 5+ engines return nothing, stop and tell the user: "These names don't exist on any network I can reach. Are these legal names or street monikers? I need legal names or DOB to continue." Pushing past this point wastes time and burns search-engine goodwill. See `references/nz-osint-sources.md` for which NZ databases are actually accessible.
- **Don't report walls, go around them.** The user doesn't want a list of what's blocked. Use Tor to bypass geo-restrictions, try alternative search engines (Mojeek, SearXNG, DDG HTML, Brave, Ecosia), parse site JSON directly, and use the browser on sites without Cloudflare. Only report a source as dead after trying it from at least two different access paths.
- **Don't tunnel-vision on one angle.** This is a critical anti-pattern. Searching only criminal/court records while ignoring education, business, property, vehicle registrations, insolvency, charities, tenancy tribunal, professional licenses, social media, and electoral rolls will miss the target entirely. Go WIDE first — hit every database class in parallel — before going deep on any single angle. A target with zero criminal search results may have a registered company, a tenancy tribunal order, or a LinkedIn profile.
- **Stop searching wrong names — pivot to associates immediately.** The #1 time-waster in gang/criminal OSINT. When 10+ queries across 5+ engines return nothing for the primary target, STOP. Don't keep burning search-engine goodwill. Instead, ask the user for known associates: girlfriend, mother, siblings, cousins, employers. Associates with legal names and DOBs have real digital footprints. Search THEM and work backward to the target. See the Pivot-to-Associates workflow below.

---

---

## Pivot-to-Associates Workflow

When the primary target has zero digital footprint (common for gang members, pre-internet offenders, or people using street names), immediately pivot to known associates. This is the highest-leverage OSINT technique for hard targets.

### When to pivot

Pivot when ALL of these are true:
- 10+ queries across 5+ engines/sources return zero results for the primary target
- The user has confirmed the names are correct but you still can't find them
- At least 30 minutes have been spent on the primary target

### How to pivot

1. **Ask for associates.** Request from the user: girlfriend/boyfriend name and DOB, mother's name, father's name, siblings, known addresses, employers, schools attended. Any ONE of these with a legal name + rough DOB is enough.

2. **Search the associate first.** Associates with legal names and DOBs have real digital footprints — birth records, school enrollments, social media, employment, property records. Find them in every available database.

3. **Work backward to the target.** From the associate's data, find: shared addresses, tagged photos, relationship status, joint tenancy applications, co-directorships, court cases naming both parties, family connections.

4. **Cross-pollinate.** Once you find the associate on one platform, search that platform for the target using the associate's network. Example: find Kirsty on Instagram → search her follows/tagged photos for "Ben."

### Associate data that unlocks targets

| Associate data | What it unlocks |
|---|---|
| Legal name + DOB | BDM records, electoral roll, credit history |
| Current address | Property records, neighbours, local news |
| Employer | LinkedIn network, company directory, colleagues |
| Mother's name | Birth records, family tree, siblings |
| Phone number | WhatsApp/Telegram/Signal, reverse lookup |
| Email address | Account recovery, social media, data breaches |
| Vehicle registration | NZTA records, parking tickets, traffic cameras |

### NZ-specific associate databases

- **BDM Historical Records** (`dia.govt.nz`) — accessible via browser, no Cloudflare. Post-1976 births blocked for living people, but marriages pre-1950 and deaths are searchable. Mother's name field works.
- **Companies Office** (`app.companiesoffice.govt.nz`) — their Angular SPA errors on parameterized URLs. Use the browser search form directly, not API/query-string access.
- **NZ Herald gangs page** (`nzherald.co.nz/topic/gangs/`) — returns `Fusion.globalContent` JSON in page source. Parse with regex: `Fusion\.globalContent=({.*?});`. Contains article headlines, URLs, descriptions, dates.
- **NZ Police media releases** — Drupal-based, no Cloudflare. Search by district + keyword. No JSON API — scrape HTML links.

---

## Agentic OS Integration

If the current project root contains an `.agent/` directory, this skill MUST participate in the Agentic OS shared-memory model.

At the end of your execution, check for `.agent/state/last-run.json`. If it exists, append or update the file using its required schema to log your run. Ensure you capture your runtime (`agent_id`), `assigned_skill`, a concise `description`, `decision_log`, and `outcome`. Use `python3 ~/.agents/skills/heartbeat/scripts/heartbeat.py complete <task_id> ...` if completing a task from the queue.

## Optional: PAI / OpenCode integration

If running inside PAI or PAI-OpenCode, the following are honored automatically:

- User customizations at `~/.opencode/skills/PAI/USER/SKILLCUSTOMIZATIONS/OSINT/PREFERENCES.md` override defaults.
- Apify actors via `~/.opencode/skills/Apify/` are used when present.
- Memory/context loading from `~/.opencode/skills/PAI/SKILL.md` runs first if the file exists.

If those paths don't exist, ignore them. The skill is fully functional standalone.

---

## Quick-start example

User: *"Look into Jason Gurash at Avenir Senior Living for me — B2B prospect, infrastructure consulting angle."*

Your turn 1 (don't dossier yet):

> Setting up a B2B account intel investigation. Routing to `workflows/b2b-account.md`. Depth: Standard (~20 min). Disambiguation target: Jason Gurash, VP Operations, Avenir Senior Living. I'll confirm that match before reporting any details about him personally. Scope: public sources for sales discovery — corporate site, LinkedIn, news, tech footprint. I'll skip personal-life angles since they're not relevant to the consulting use case. Starting now.

Then run the workflow. Then produce the dossier with grades.
