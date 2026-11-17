# Unknown identifier search — zebra 5c6 case study (2026-08-05)

User asked: "What is a zebra 5c6 for" — a terse identifier with no context, and the exact phrase
has essentially zero web footprint.

## Per-endpoint outcomes (what actually happened)

| Endpoint | Method | Outcome |
|----------|--------|---------|
| Bing `?q=%22zebra+5c6%22` | curl | 200, ZERO organic results (`b_algo` empty) — genuine zero-footprint signal. After ~4 queries Bing started serving empty pages entirely (bot rate-limit). |
| DuckDuckGo html/lite | curl | HTTP 202 anomaly |
| DuckDuckGo html | browser | captcha form ("Select all squares containing a duck") |
| DuckDuckGo main | browser | results below fold; body shows captcha |
| Google | browser | `/sorry` captcha (no residential proxies) |
| Ecosia | browser | Cloudflare "Just a moment..." |
| eBay | browser | "Error Page" |
| Startpage | curl | anomaly page (10KB) |
| Yandex | curl | 302 redirect |
| Mojeek / Brave | curl | empty |
| AliExpress `wholesale-zebra-5c6` | curl | 200; only generic "zebra" products (phone cases, Mildliner pens) — nothing named 5C6 |
| Amazon `s?k=zebra+5c6` | curl | bot page, zero hits |
| zebra.com site search `?q=5C6` | curl | 200; only generic category boilerplate — no 5C6 product |
| witrigs / mobile-sentrix | curl | 301 / connection fail |
| TradeMe `search_string=zebra+5c6` | curl | JS shell, zero data |
| TradeMe same | **browser** | definitive: "Showing 0 results for 'zebra 5c6'" |

## Resolution

- Zebra = **Zebra Technologies** (enterprise barcode scanners/printers/rugged handhelds) — confirmed
  when user followed up: "it's a barcode scannee thing for businesses".
- "5C6" is NOT an official Zebra model (zebra.com search proves it).
- Ranked interpretation: (1) typo for **Zebra TC56** — rugged Android handheld with integrated
  barcode scanner, the classic business scanner; (2) config/region block in a longer DS-series SKU;
  (3) marketplace listing code.
- Ended with one clarifying question ("where did you see it — label/box/listing?") — the user's
  one-word follow-up confirmed the family instantly.

## Reusable commands

```bash
# Bing exact phrase — check for b_algo organic results (zero = signal)
curl -s -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120" \
  "https://www.bing.com/search?q=%22zebra+5c6%22" | grep -c 'b_algo'

# AliExpress marketplace
curl -s -A "Mozilla/5.0 ..." "https://www.aliexpress.com/w/wholesale-zebra-5c6.html" \
  | grep -oP '"subject":"[^"]{5,120}"' | head -15

# TradeMe — MUST use browser (JS-rendered); curl gets an empty shell
# browser_navigate https://www.trademe.co.nz/a/marketplace/search?search_string=zebra+5c6

# Vendor site search
curl -s -A "Mozilla/5.0 ..." "https://www.zebra.com/us/en/search.html?q=5C6"
```

## Notes for future runs

- Marketplaces + vendor search are the high-value checks; engine captchas are a distraction — skip
  past them after Bing confirms zero footprint.
- session_search + narrow filesystem grep (NOT broad — big trees time out) for user-local references.
- The user will correct aggressively if you claim definitive absence from partial data — phrase the
  negative as "zero footprint across [list of sources]", then give the ranked interpretation.
