# Site Search URL Patterns (2026-06-28 update)

Working methods to discover performer-targeted video URLs. The previous doc said "yt-dlp doesn't accept search URLs" — that's wrong. Most sites DO accept search URLs, but **the format yt-dlp's extractor recognizes differs from what you might guess**, and several sites also have JSON APIs that work cleanly.

## Quick reference: which approach per site

| Site | Best method | yt-dlp direct? | Notes |
|------|-------------|----------------|-------|
| pornhub | JSON API | Yes (but TIMEOUT-prone) | `pornhub.com/webmasters/search` returns clean JSON; prefer this over yt-dlp search which Cloudflare-times out at 60-90s |
| spankbang | yt-dlp + impersonate | Yes | Use `--impersonate chrome --flat-playlist --dump-json --skip-download` on `/s/{q}/` |
| xhamster | HTML scrape | **No** | yt-dlp rejects `/search/` URLs. curl + regex on the search page works |
| xnxx | HTML scrape | **No** | yt-dlp rejects `/search/` URLs. curl + regex works perfectly — extracts clean video page URLs |
| redtube | JSON API | No | `api.redtube.com/?data=redtube.Videos.searchVideos&search={q}` returns JSON |
| eporner | HTML scrape | **No** | yt-dlp rejects `/search/` and `/tag/` URLs. curl + regex on the search page works |
| porntn | yt-dlp | Yes | Direct video page URLs work fine |
| pimpbunny | Puppeteer sniff | No | yt-dlp can't extract flashvars; use Puppeteer node_service |
| borntobefuck | Puppeteer sniff | No | `/watch/` URLs unsupported; sniff for m3u8 |

## Working: PornHub Webmasters JSON API

PornHub has a clean JSON API. Use it instead of yt-dlp's search (which Cloudflare-times out):

```python
import urllib.request, json
import urllib.parse

def search_pornhub(performer, max_results=15):
    q = urllib.parse.quote(performer)
    url = f"https://www.pornhub.com/webmasters/search?search={q}&per_page={max_results}&thumbsize=medium"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 ...",
        "Accept": "application/json",
        "Referer": "https://www.pornhub.com/",
    })
    data = urllib.request.urlopen(req, timeout=20).read()
    d = json.loads(data)
    return [v["url"] for v in d.get("videos", []) if v.get("url")]
```

Returns: `{"videos": [{"url": "https://www.pornhub.com/view_video.php?viewkey=...", "title": "...", "duration": "MM:SS", "views": N, ...}, ...]}`

## Working: RedTube JSON API

```python
def search_redtube(performer, max_results=15):
    q = urllib.parse.quote(performer)
    url = f"https://api.redtube.com/?data=redtube.Videos.searchVideos&search={q}&output=json&page=1"
    data = fetch(url, {"Accept": "application/json"})
    d = json.loads(data)
    urls = []
    for item in d.get("videos", [])[:max_results]:
        v = item.get("video", {})
        u = v.get("url", "")
        if not u.startswith("http"):
            u = f"https://www.redtube.com/{v.get('video_id', '')}"
        urls.append(u)
    return urls
```

## Working: XNXX HTML scrape

yt-dlp's XNXX extractor rejects `/search/` URLs. But XNXX's search HTML is regular, parsable HTML with `<a href="/video-XXX/slug">` links:

```python
import urllib.request, re

def search_xnxx(performer, max_results=15):
    q = urllib.parse.quote(performer.lower().replace(" ", "-"))
    url = f"https://www.xnxx.com/search/{q}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 ..."})
    data = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", errors="replace")
    matches = re.findall(r'<a href="(/video-[a-z0-9]+/[a-z0-9_-]+)"', data)
    seen, urls = set(), []
    for m in matches:
        if m in seen: continue
        seen.add(m)
        urls.append(f"https://www.xnxx.com{m}")
        if len(urls) >= max_results: break
    return urls
```

Returns 30-40 video URLs per performer search reliably.

## Working: Eporner HTML scrape

Same approach as XNXX — yt-dlp's extractor rejects search URLs but the HTML is scrapable:

```python
def search_eporner(performer, max_results=15):
    q = urllib.parse.quote(performer)
    url = f"https://www.eporner.com/search/{q}/"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 ..."})
    data = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", errors="replace")
    matches = re.findall(r'<a href="(/video-[^"]+)"', data)
    seen, urls = set(), []
    for m in matches:
        if m in seen or "THUMBNUM" in m: continue
        seen.add(m)
        urls.append(f"https://www.eporner.com{m}")
        if len(urls) >= max_results: break
    return urls
```

## Working: SpankBang with yt-dlp impersonate

SpankBang is Cloudflare-protected but yt-dlp with `--impersonate chrome` works:

```python
import subprocess, json

def search_spankbang(performer, max_results=15):
    q = urllib.parse.quote(performer)
    url = f"https://spankbang.com/s/{q}/"
    result = subprocess.run(
        ["/home/kubuntux/.local/bin/yt-dlp", "--impersonate", "chrome",
         "--flat-playlist", "--dump-json", "--skip-download",
         "--no-warnings", "--playlist-items", f"1-{max_results}", url],
        capture_output=True, text=True, timeout=60
    )
    urls = []
    for line in result.stdout.strip().split("\n"):
        if not line: continue
        try:
            d = json.loads(line)
            u = d.get("url") or d.get("webpage_url", "")
            if u and "spankbang.com" in u:
                urls.append(u)
        except: pass
    return urls[:max_results]
```

**WARNING:** SpankBang search results contain HTML5MediaEmbed generic.mp4 HLS fragments, not real video pages. If you pass them to yt-dlp as direct download URLs, format selection fails with "Requested format is not available". Use only as URL discovery, then construct the proper video page URL from the slug in the result.

## Pitfalls discovered this session

- **yt-dlp search URLs work for SOME sites, fail for others.** The earlier doc said "all search URLs fail" — that's wrong. PH and RT have JSON APIs that bypass the search URL problem entirely. SpankBang works with impersonation. XNXX and Eporner reject search URLs but their HTML is scrapable. Always have a fallback.
- **HTML scrape needs proper User-Agent** or the sites return 403/404. Use a recent Chrome UA string.
- **Some sites have undocumented search via their search path that yt-dlp does NOT recognize** — even when the URL is technically valid. xnxx.com/search/{q} redirects to xnxx.com but yt-dlp's extractor doesn't claim ownership.
- **PornHub webmasters API has no auth requirement** but does require a proper Referer header. Without it you get 403.
- **Cloudflare timeout on PornHub yt-dlp search is real.** 60-90s and it dies. Use the JSON API instead.

## When you don't know what works: test with one URL first

Before building the full pipeline, probe each site with a single known performer to see which approach works:

```python
import subprocess, json, urllib.request, re

test_perf = "Lulu Chu"
# Test JSON API
try:
    data = urllib.request.urlopen(f"https://www.pornhub.com/webmasters/search?search={test_perf}&per_page=3", timeout=15).read()
    d = json.loads(data)
    print(f"PH JSON: {len(d.get('videos',[]))} results")
except Exception as e:
    print(f"PH JSON failed: {e}")

# Test HTML scrape
try:
    data = urllib.request.urlopen(f"https://www.xnxx.com/search/{test_perf.lower().replace(' ','-')}", timeout=15).read().decode()
    matches = re.findall(r'/video-[a-z0-9]+/', data)
    print(f"XNXX HTML: {len(set(matches))} results")
except Exception as e:
    print(f"XNXX HTML failed: {e}")
```

See `scripts/performer_scraper.py` for the full per-site scraper implementation.
