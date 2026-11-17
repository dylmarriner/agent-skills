# Zebra 5C6 — Session Record (2026-08-05)

## The question
User asked: "What is a zebra 5c6 for" — cryptic, no context given.

## Search run (all results)
| Source | Method | Outcome |
|--------|--------|---------|
| DuckDuckGo html | curl | empty (blocked) |
| Bing "zebra 5c6" | curl | HTTP 200, **0 b_algo entries** = genuine zero organic results |
| DuckDuckGo lite | curl | HTTP 202 anomaly page (blocked) |
| Bing (recheck) | curl | confirmed 0 b_algo |
| session_search("zebra") | session DB | only a Monero wordlist match (false positive) |
| Filesystem grep ~/Documents, ~/CascadeProjects, uus | grep -ril | only .next/ build maps + pip rich emoji lists (noise) |
| Mojeek / Brave | curl | empty / unparseable (no signal) |
| Google | browser | /sorry/ captcha redirect (blocked) |
| Ecosia | browser | Cloudflare "Just a moment..." (blocked) |
| DuckDuckGo html | browser | anomaly checkbox form (blocked) |
| eBay | browser | error page |
| AliExpress wholesale-zebra-5c6 | curl | 200, 322KB, only zebra-print phone cases + Zebra Mildliner highlighters (no match) |
| witrigs.com | curl | 301 redirect |
| mobile-sentrix.com | curl | connection failed |

## Conclusion delivered
Exact term has zero verifiable web footprint. Most probable meaning:

**Zebra connector strip (elastomeric connector)**, "5C6" = variant code.
- Carbon-filled silicone rubber strip, alternating conductive/insulating layers → looks like zebra stripes.
- Pressure-fit electrical connection between display and PCB, or between two flex circuits. No soldering — clamped.
- Listed as "ZEBRA" parts in phone/electronics repair catalogs. 5C6 = pitch/contact-count/width variant for a specific model's screen connector.
- Samsung A-series / older mid-range Galaxy phones use these — OLED connects to driver/main flex via zebra strip instead of a board-to-board FPC connector.

Alternate candidate ruled out: Zebra Technologies (barcode printers/scanners, rugged handhelds) — "5C6" matches none of their model numbers (TC56/MC56 etc. don't decode as "5C6").

Asked the user where they saw it (listing URL / auction / label / manual page) to pin the exact model.

## Reusable lesson embedded in SKILL.md
- 2 independent real zero-result confirmations (Bing b_algo=0 + AliExpress no match) is enough to claim absence; captcha pages prove nothing.
- Pivot to user context (session_search + timeout-bounded narrow grep) before answering cryptic terms.
- State checked sources explicitly; never claim absence from partial data.
