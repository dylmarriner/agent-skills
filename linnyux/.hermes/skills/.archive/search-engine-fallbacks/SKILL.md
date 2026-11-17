---
name: search-engine-fallbacks
description: "Use when search engines block or return zero hits."
metadata:
  tags: web-search, search-engine, bing, duckduckgo, google, captcha, absence-verification, osint, curl
  version: 1.0.0
---

# Search Engine Fallbacks — When Engines Block or Return Nothing

## When to Use

- curl to a search engine returns a captcha, HTTP 202, or empty output
- You need to verify whether a term EXISTS on the web (exact-phrase quoted search)
- A search returns HTTP 200 but zero organic results — need to distinguish genuine absence from a block
- The term is cryptic, user-specific, or a part number with no web footprint — need to pivot to user context before answering

## Engine Access Table (tested from lin, Aug 2026)

| Engine | curl works | Block signature if not | Result parser |
|--------|-----------|------------------------|---------------|
| Bing | ✅ | — | `grep -c 'b_algo'` on the HTML; 0 count + HTTP 200 = genuine zero results |
| AliExpress search | ✅ | — | `grep -oP '"subject":"[^"]{5,120}"'` on the page |
| DuckDuckGo html/lite | ❌ | HTTP 202 "anomaly" page | — |
| Google | ❌ | redirect to /sorry/ captcha | — |
| Ecosia | ❌ | Cloudflare "Just a moment..." | — |
| Mojeek / Brave | ⚠️ unreliable | empty/parseable-nothing output — treat as NO signal | — |
| eBay search | ⚠️ | error page | — |

Notes:
- Bing via `curl -A "Mozilla/5.0 (X11; Linux x86_64) ... Chrome/120"` returns parseable HTML.
- The Hermes browser does NOT dodge Google/Ecosia/DDG captchas without residential proxies — the browser hits the same walls (Google /sorry/, Cloudflare challenge). Don't waste time browser-navigating to captcha-walled engines.
- When an exact phrase has no hits, engines that work (Bing, AliExpress) returning only generic/adjacent results is itself useful evidence.

## Zero Results vs Blocked — Critical Distinction

- **Genuine absence signal:** HTTP 200 + `grep -c 'b_algo' file.html` → 0 on Bing. This is real and meaningful.
- **Blocked (says NOTHING about existence):** HTTP 202 (DDG anomaly), /sorry/ captcha redirect (Google), "Just a moment..." (Ecosia), empty body (Mojeek/Brave).
- **Never report "not found" from a blocked page.** Only claim absence after ≥2 independent engines returned real non-blocked zero-result pages, plus targeted site searches (e.g. AliExpress for part numbers, eBay, repair-parts vendors).

## Absence-Verification Protocol (exact phrase)

1. `curl -s -A <UA> "https://www.bing.com/search?q=%22<phrase>%22"` → count `b_algo`.
2. If zero, run a site-specific search that works via curl (AliExpress `https://www.aliexpress.com/w/wholesale-<phrase>.html`, vendor search endpoints).
3. Only then, optionally, try the browser on one captcha-walled engine — usually not worth it.
4. If absence is confirmed → pivot to user context BEFORE composing the answer.

## Pivot to User Context (cryptic / zero-footprint terms)

1. `session_search(query)` — the term may appear in past sessions. Watch for false positives (e.g. "zebra" matched only a Monero wordlist).
2. Targeted filesystem grep — ALWAYS with `timeout 20-25` and NARROW paths (`~/Documents`, `~/CascadeProjects`, the specific project root). Full-recursive greps over home dirs or /mnt/* time out at 60s and return nothing.
3. Exclude noise before grepping: `.next/`, `node_modules/`, `venv/`, `site-packages/` — build artifacts and pip's rich emoji lists match animal words like "zebra" and pollute results.
4. If nothing in user context → answer with the most probable interpretation, state the uncertainty, and ask where they saw the term (listing URL, auction, label, manual page).

## Reporting Rules (Dylan-specific)

- Never "none found" from partial data. State exactly which sources were checked and their status: e.g. "Bing returned zero organic results, Google was captcha-walled, AliExpress had no match".
- Give the best-reasoned interpretation with the confidence level stated (e.g. "almost certainly a zebra connector strip, 5C6 = variant code").
- Don't keep hammering captcha-walled engines — two independent confirmations is enough, then pivot.
- End with ONE targeted question that would pin it down, not a menu of options.

## Pitfalls

- Grepping a 322KB AliExpress page for `"subject"` fails silently if the page is a challenge/redirect — check the `<title>` first.
- `curl --resolve` tricks (see browser-data-extraction skill) apply to page access, not to search-engine result pages — engines block by IP/UA fingerprint, not DNS.
- Bing may serve region-specific results; zero hits in one region is still strong absence evidence for an exact quoted phrase.

## References

- [zebra-5c6-search](./references/zebra-5c6-search.md) — Session record: cryptic phone-part term with zero web footprint → zebra (elastomeric) connector interpretation; the search run and the domain fact bank.
