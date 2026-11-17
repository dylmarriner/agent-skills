---
name: cryptic-identifier-lookup
description: "Identify cryptic product codes, model numbers, part numbers."
version: 1.0.0
tags: [research, search, identification, lookup, user-preference]
---

# Cryptic Identifier Lookup

## Trigger Conditions

Use when the user asks:
- "What is X for" / "What is X" where X is an ambiguous code, model, part number, hex string, or listing fragment
- "What phone is IMEI ...", "what model is ...", "what part is ...", "what is this code"
- Identifying hardware, SKUs, error codes, or marketplace listings

The user often drops terse identifiers with no context (e.g. "what is a zebra 5c6 for"). The identifier may be a typo, a fragment, or an unofficial marketplace code — the job is to identify it, not to demand context first.

## Core Rule

An exact string with ZERO footprint across engines + marketplaces + vendor site is itself the finding: it is NOT an official product name. Never claim "it doesn't exist" from partial data — say exactly which sources returned zero, then give the best-ranked interpretation.

## Search Ladder (in order)

### 1. Exact-phrase curl searches (fast; batch 2-3 at once)
- **Bing**: `curl -s -A "<desktop UA>" "https://www.bing.com/search?q=%22<phrase>%22"` — accepts curl for the first few queries. A page with zero `b_algo` organic results = genuine zero-footprint signal. After ~4 queries Bing rate-limits and serves empty pages — switch away; don't read that as "no results".
- **DuckDuckGo** html/lite: often HTTP 202 anomaly for curl.
- **Mojeek / Brave**: curl-friendly but usually empty for cryptic strings.
- **Startpage**: anomaly page via curl. **Yandex**: 302 redirect.

### 2. Marketplaces (where unknown strings actually live)
- **AliExpress**: curl works (`https://www.aliexpress.com/w/wholesale-<term>.html`, grep `"subject":"..."`).
- **TradeMe (NZ)**: JS-rendered — curl gets an empty shell; MUST use the browser. Gives a definitive "Showing 0 results for 'X'" verdict.
- **Amazon**: bot-walled for curl.

### 3. Vendor's own site search
`https://www.<vendor>.com/.../search.html?q=<fragment>` — if the fragment isn't a model there, it's not an official model. (E.g. zebra.com for Zebra Technologies.)

### 4. Browser fallback for engines
Headless browser WITHOUT residential proxies gets captchas on Google (/sorry), Ecosia (Cloudflare), DuckDuckGo ("select all squares containing a duck"). Don't fight them — marketplaces + vendor search already gave the answer.

### 5. Local context
session_search for the term + targeted filesystem grep (narrow dirs only — broad greps time out on big trees) to catch user-specific references.

### 6. Calibrated answer + ONE clarifying question
State verified facts vs inference, rank candidate interpretations, then ask ONE tight question — where did the user see the string (device label / box / listing)? A single detail resolves it instantly.

## Interpretation Playbook (zero-footprint strings)

Rank by likelihood:
1. **Typo / misremembered real model** — e.g. "5c6" ← Zebra TC56 (rugged Android handheld with integrated barcode scanner — the classic "barcode scanner for businesses").
2. **SKU/config fragment** of a longer part number — enterprise vendors (Zebra, Cisco, etc.) use long config strings; a 3-char block may be a config/region code.
3. **Marketplace listing code** on cheap clones (Temu/AliExpress) — arbitrary codes on unbranded goods.
4. **Domain term that looks like a code** — e.g. "zebra" = elastomeric connector in phone repair ("zebra strip"): check the user's domain vocabulary before concluding it's a product code.

## Pitfalls

- **No definitive negatives from partial data.** Say "zero footprint across Bing/DDG/AliExpress/TradeMe/zebra.com" — not "that doesn't exist".
- **Don't tunnel on one engine.** When Bing rate-limits or a captcha appears, move down the ladder; marketplaces + vendor search are the high-value checks anyway.
- **Don't demand context first.** The terse-identifier question IS the prompt; do the ladder, then ask one clarifying question at the end if still ambiguous.
- **No negative tool claims** ("search engines don't work") — the ladder documents per-endpoint behavior, not broken tools.

## Reference files

| File | Contents |
|------|----------|
| `references/unknown-identifier-search.md` | Full zebra 5c6 case study: per-endpoint outcomes, exact commands, and the resolution path. |
