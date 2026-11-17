# Manual site scraping notes (2026-07-12)

Session learning:
- Broad search-engine queries often return zero or junk for specific performers even when the performer has many POV videos.
- Site-by-site manual scraping produced the real wins.
- Useful site targets in this session: Pornhub webmasters API, RedTube API, XNXX HTML search, Eporner HTML search, xHamster search pages.
- SpankBang search returned no useful explicit POV URLs in this pass.

Working pattern:
1. Search each performer on each site separately.
2. Keep only titles that explicitly contain `POV` (or `point of view` when the title is trustworthy).
3. Exclude BBC / interracial / BWC / ebony / blacked / blackedraw.
4. Combine all results into one pool.
5. Deduplicate by exact URL first.
6. Run a second title-key dedupe to collapse near-identical entries across sites.
7. Write a plain URL-only file for the downloader.

Observed source behavior:
- Pornhub webmasters API returned many usable explicit-POV hits for Payton Preslee and Natasha Nice.
- RedTube returned some usable explicit-POV hits, but also a lot of non-POV junk that had to be filtered.
- XNXX and Eporner produced the best long-tail explicit POV hits for performers that search engines missed.
- xHamster search pages sometimes yielded useful explicit POV hits, but not consistently.

Use this as the default workflow before trying to pad counts with broader search results.