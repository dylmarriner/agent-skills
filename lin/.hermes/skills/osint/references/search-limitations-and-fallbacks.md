# Search Engine Limitations & Fallback Strategies

When conducting OSINT programmatically (via agent tools, curl, or scripts), search engines aggressively block non-browser traffic. This document catalogs what works, what doesn't, and the fallback order.

## The landscape (tested 2026-07-19)

| Engine | Endpoint | Works via curl? | Works via browser tool? | Notes |
|---|---|---|---|---|
| DuckDuckGo | `html.duckduckgo.com/html/` | Yes (4-6 queries) | N/A | Fastest fallback. Rate-limited after ~6 queries → CAPTCHA |
| DuckDuckGo | `duckduckgo.com` (JS) | No (JS required) | Sometimes | Browser tool gets past JS wall but still CAPTCHA after rate-limit |
| Google | `google.com/search` | No (JS required) | No | Aggressive bot detection, hard-blocked everywhere |
| Bing | `bing.com/search` | No (JS required) | Sometimes | Browser tool can load the page; results may be empty/junk |
| Brave | `search.brave.com` | Sometimes | Untested | Browser renders but often CAPTCHA; curl with User-Agent sometimes works |
| NZLII | `nzlii.org` | No (Cloudflare) | Untested | Cloudflare JS challenge blocks curl |

## Fallback strategy (in order)

1. **DDG HTML endpoint** — `https://html.duckduckgo.com/html/?q=...` — use FIRST, before any other search tool. You get ~4-6 queries before rate-limit. Batch independent queries together in one turn.
2. **Bing via browser** — when DDG is CAPTCHA'd, try Bing in the browser. Navigate + scroll to see results. Unreliable — often returns 0-1 irrelevant results even for valid queries.
3. **Direct government/source databases** — bypass search engines entirely. Hit registries, court databases, and news sites directly via their own search endpoints or APIs. See `references/nz-osint-sources.md` for NZ-specific ones.
4. **`web_search` tool** — when Firecrawl credits are available, this is the best option. When credits are exhausted, it fails silently.

## Pitfalls

- **DDG HTML gives 4-6 queries, then CAPTCHA.** Plan your query order — most important queries first. Don't waste queries on broad checks you can do elsewhere.
- **"No results" ≠ not indexed.** DDG HTML returns "No more results found" for terms it can't match. Bing returns irrelevant Chinese results. Neither means the person doesn't exist — just that the search path is broken.
- **Browser tool is slow.** Each navigate + snapshot + scroll is 3-5 seconds. Use curl for DDG HTML first, browser only as fallback.
- **`execute_code` with Python + `urllib` inherits the same rate-limits as curl.** The CAPTCHA is IP/session-based, not tool-specific.
- **Never conclude "not found / doesn't exist" from search-engine failures alone.** Always report the methodology gap: "No results found across X search engines — this could mean the records aren't indexed, or the search path was blocked."
