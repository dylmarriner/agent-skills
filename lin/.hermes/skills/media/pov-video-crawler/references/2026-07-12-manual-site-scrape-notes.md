# Manual site-scrape notes — 2026-07-12

This session expanded the POV crawler by manually scraping the sites we already use, plus Redtube.

## What worked
- PornHub: webmasters JSON API
- Redtube: JSON API
- XNXX: HTML scrape
- Eporner: HTML scrape
- xHamster: partial/spotty HTML scrape, but did return usable results on some performer queries
- SpankBang: search probe returned no usable results in this session

## Practical lessons
- Search-engine results alone were not enough; many valid URLs only surfaced after site-specific scraping.
- Keep the filter strict: explicit POV only, no BBC/interracial, and reject obvious non-POV studio titles unless the page title explicitly contains POV.
- Prefer site-native APIs/HTML over broad web search when the performer count is already known.
- When a site yields zero results repeatedly, skip it for the current pass and move to the next site instead of spending the whole session there.

## Outcome snapshot
- The manual site scrape found usable URLs for some performers that the web-search pass missed.
- The strongest sources in this pass were Eporner, XNXX, PornHub, and Redtube.
- A few performers topped out at 15 from the combined library + previous searches + this pass.
