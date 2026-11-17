# 2026-07-10 Crawl Session — max-20 cap + Pornhub+XNXX combo

## Trigger
User wanted to fill each performer to 20 videos max, POV + big tits only, no BBC/interracial, no duplicates.

## Method
Used `scripts/pornhub_xnxx_crawl.py` (implemented as `/tmp/crawl_pov_v3.py` in session):
- **Pornhub:** `yt-dlp --flat-playlist --dump-json "https://www.pornhub.com/video/search?search=pov+PERFORMER+NAME"`
- **XNXX:** `curl` HTML scrape of `https://www.xnxx.com/search/pov+PERFORMER+NAME`, regex `href="/video-\w+/[^"]*"`
- **Scoring:** +3 POV, +2 big tits keywords, +1 name match, -5 compilations, -10 BBC/blocked
- **Dedup:** global viewkey set across all performers + existing disk viewkeys

## Results
- **450 new URLs** found across 37 performers (1 removed as already-downloaded duplicate)
- **0 duplicates within crawl**, **0 BBC detected** in titles
- ~7 min runtime for full crawl

## Performer fill status

| Performer | Had | Added | Now | Status |
|-----------|-----|-------|-----|--------|
| Mia Malkova | 18 | 2 | 20 | ✅ |
| Kali Roses | 18 | 2 | 20 | ✅ |
| Aleksa Mink | 15 | 5 | 20 | ✅ |
| Lena Paul | 12 | 8 | 20 | ✅ |
| Angela White | 12 | 8 | 20 | ✅ |
| Lana Rhoades | 21 | 0 | 21 | ✅ already over |
| Payton Preslee | 11 | 9 | 20 | ✅ |
| Lauren Phillips | 10 | 10 | 20 | ✅ |
| Karma RX | 10 | 10 | 20 | ✅ |
| Tru Kait | 9 | 11 | 20 | ✅ |
| Lexi Luna | 9 | 11 | 20 | ✅ |
| Asa Akira | 9 | 11 | 20 | ✅ |
| Blake Blossom | 9 | 11 | 20 | ✅ |
| Siri Dahl | 8 | 12 | 20 | ✅ |
| Nicole Doshi | 8 | 12 | 20 | ✅ |
| Violet Myers | 8 | 12 | 20 | ✅ |
| Richelle Ryan | 8 | 12 | 20 | ✅ |
| Angie Faith | 8 | 12 | 20 | ✅ |
| Blondie Fesser | 8 | 12 | 20 | ✅ |
| Alanna Pow | 7 | 13 | 20 | ✅ |
| Vivian Taylor | 7 | 13 | 20 | ✅ |
| Sky Bri | 7 | 13 | 20 | ✅ |
| Rissa May | 7 | 13 | 20 | ✅ |
| Riley Reid | 6 | 14 | 20 | ✅ |
| Natasha Nice | 5 | 15 | 20 | ✅ |
| Sharon Lee | 5 | 15 | 20 | ✅ |
| Kendra Sunderland | 5 | 15 | 20 | ✅ |
| Ava Addams | 5 | 15 | 20 | ✅ |
| Ava Nicks | 4 | 16 | 20 | ✅ |
| Ember Snow | 4 | 16 | 20 | ✅ |
| Jade Kush | 4 | 16 | 20 | ✅ |
| Mia Melano | 4 | 16 | 20 | ✅ |
| Kimmy Granger | 3 | 17 | 20 | ✅ |
| Sophie Dee | 2 | 18 | 20 | ✅ |
| Lulu Chu | 2 | 18 | 20 | ✅ |
| Eva Lovia | 1 | 19 | 20 | ✅ |
| Lily Lane | 1 | 19 | 20 | ✅ |

**Total: 37 performers filled to 20.**

## Verification
- Full dedup check confirmed 0 intra-crawl duplicates
- 0 URLs matched existing viewkeys on disk (after removing 1 pre-existing)
- 0 BBC/interracial matches in titles
- No further live verification done (user didn't request it for this crawl)

## Notes
- The path from `/tmp/crawl_pov_v3.py` is a direct implementation. For re-use, the `scripts/pornhub_xnxx_crawl.py` is the canonical version.
- Crawl saved to `/mnt/storage/videos/.queue/pov_crawl_1783599833.txt`
