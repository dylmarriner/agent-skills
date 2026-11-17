# Performer-targeted multi-site scraper — what actually works

Discovered while building `/tmp/performer_scraper.py` after generic site-feed crawlers starved specific performers (Mia Malkova: 39 videos, Asa Akira: 9, Riley Reid: 2, Lulu Chu: 0).

## The problem with feed-based crawls

Generic site feeds (eporner latest, PH popular, etc.) over-grab whatever's trending. Top performers like Mia Malkova get 30+ files while equally top-tier performers (Riley Reid, Asa Akira, Lulu Chu) get <10 because they're not in the feed window.

**Fix:** performer-targeted search per site. But most search URL patterns yt-dlp's extractors advertise DO NOT WORK in 2026.

## Site-by-site search reality (June 2026)

| Site | Search URL yt-dlp accepts? | Real working approach |
|------|---------------------------|----------------------|
| **PornHub** | ✓ `https://www.pornhub.com/video/search?search={q}` | **JSON API:** `https://www.pornhub.com/webmasters/search?search={q}&per_page=N&thumbsize=medium` — returns 25-30 clean URLs |
| **RedTube** | ✗ search URL = "Unsupported URL" | **JSON API:** `https://api.redtube.com/?data=redtube.Videos.searchVideos&search={q}&output=json` — 5-8 URLs |
| **XNXX** | ✗ search URL = "Unsupported URL" | **HTML scrape** `https://www.xnxx.com/search/{slug}` — regex `<a href="(/video-[a-z0-9]+/[a-z0-9_-]+)"` |
| **Eporner** | ✗ "Unsupported URL" for all API paths | **HTML scrape** `https://www.eporner.com/search/{q}/` — regex `<a href="(/video-[^"]+)"` |
| **SpankBang** | ✗ Cloudflare blocks plain curl | **yt-dlp with `--impersonate chrome`** on `https://spankbang.com/s/{q}/` — `--flat-playlist --dump-json --skip-download` |
| **XHamster** | ✗ 520/401 errors | NOT WORKING this session — skip or use direct video URL lists |
| **PornTN, PimpBunny, BornToBeFuck** | varies | Best: direct URL feeds (we have these in /tmp/*_batch.txt) |

## The JSON API win

Two sites have **public JSON search APIs** that bypass yt-dlp entirely. 10x faster, no Cloudflare, no impersonation:

**PornHub webmasters API** (no auth needed for basic search):
```
GET https://www.pornhub.com/webmasters/search
  ?search=Lulu+Chu
  &per_page=15
  &thumbsize=medium
  &format=json (ignored — always returns JSON)
Headers: User-Agent, Accept: application/json, Referer: https://www.pornhub.com/
```
Response shape: `{"videos": [{"title": "...", "url": "https://www.pornhub.com/view_video.php?viewkey=XXX", "duration": "25:47", "views": N}]}`

**RedTube API** (no auth):
```
GET https://api.redtube.com/
  ?data=redtube.Videos.searchVideos
  &search=Lulu+Chu
  &output=json
  &page=1
```
Response: `{"videos": [{"video": {"title": "...", "url": "https://www.redtube.com/XXX", "video_id": "XXX", ...}}]}`

## The HTML scrape pattern (XNXX, Eporner)

Use urllib with browser UA, no JS. Both sites serve static HTML with embedded video links.

```python
import urllib.request, urllib.parse, re

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"

def fetch(url, headers=None):
    h = {"User-Agent": UA, "Accept": "*/*"}
    if headers: h.update(headers)
    req = urllib.request.Request(url, headers=h)
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", errors="replace")

# XNXX
def search_xnxx(performer, max_results=15):
    slug = performer.lower().replace(" ", "-")
    data = fetch(f"https://www.xnxx.com/search/{urllib.parse.quote(slug)}",
                 {"Referer": "https://www.xnxx.com/"})
    matches = re.findall(r'<a href="(/video-[a-z0-9]+/[a-z0-9_-]+)"', data)
    # Dedupe, return full URLs
    ...

# Eporner (filters out THUMBNUM placeholders)
def search_eporner(performer, max_results=15):
    data = fetch(f"https://www.eporner.com/search/{urllib.parse.quote(performer)}/",
                 {"Referer": "https://www.eporner.com/"})
    matches = re.findall(r'<a href="(/video-[^"]+)"', data)
    matches = [m for m in matches if "THUMBNUM" not in m]
    ...
```

## Critical pitfalls (cost real time this session)

1. **BBC/interracial filtering must happen on title** — PH returns BBC content even for legitimate performer searches. Block list: `bbc`, `interracial`, `ebony`, `bwc`, `blacked raw`, `blacked.com`. PH webmasters API results for "Lulu Chu" include `"BLACKED Asian Beauty Lulu Chu Cant resist BBC"` and `"RICKYSROOM Asian spinner Lulu Chu wants his BBC"` — filter at the title level, NOT after download.

2. **yt-dlp's `ytsearch:` prefix does NOT work for adult sites** — it only does YouTube. Don't bother.

3. **`--max-filesize 1.5GB` kills legitimate files** — most full-scene videos are 1.5-4GB. They get rejected with empty `.ytdl` files (70 bytes) before download. Either drop the cap or raise it to 4GB+.

4. **3-min per-file timeout is too aggressive** — at 16-conn aria2 from these CDNs, 700MB files routinely take 5-8 min. Most timeouts in v2 of the scraper were legit files, not hangs. Bump to 6-8 min OR detect stalled downloads (no progress in 60s) instead.

5. **yt-dlp with `--impersonate chrome` works for SpankBang search** but plain curl gets Cloudflare-blocked. Use subprocess to call yt-dlp, don't try to scrape SpankBang directly.

6. **Sequential downloading is glacial** — one yt-dlp per URL took 14 min for a 15-URL batch. **Always run 4-6 downloads in parallel** via threads. Each download uses ~50MB RAM and modest CPU; 4 parallel is fine on this box.

7. **Leetspeak filenames break exact matching** — `As4 Ak1r4`, `Bl4ke Bl0ss0m`, `L3n4 P4ul` are all in the existing library. To count performers correctly, normalize before matching: `4→a, 3→e, 1→i, 0→o, 5→s, 7→t, 8→b`.

8. **Dedup by video ID, not full URL** — different sites use different URL patterns for the same video. Extract the ID with a combined regex:
   ```python
   re.search(r"viewkey=([a-f0-9]+)|/video-([a-z0-9]+)|/([0-9]+)(?:/|$)", u)
   ```

## Working scraper skeleton

`/tmp/performer_scraper.py` has the v2 implementation: 4-parallel downloads, BBC block list, per-site search functions, dedup by video ID. v1 was sequential and got stuck; v2 with parallelism runs ~5-10x faster per performer.

**Known v2 bugs to fix in v3:**
- `--max-filesize 1.5GB` cap (raise to 4GB or remove)
- 180s timeout (raise to 480s OR implement progress-based stall detection)
- RedTube URLs need `https://www.redtube.com/{video_id}` if `url` field is empty

## Final performer counts after this session

Library grew to 688 MP4s / 378GB. Targeted scraper (v2) was running and added 4 MP4s before being tuned. The under-10 performers (Lulu Chu, Mia Melano, Kimmy Granger, Riley Reid, Asa Akira, etc.) need a v3 with the above fixes to actually fill out.
