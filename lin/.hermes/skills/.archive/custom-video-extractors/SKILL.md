---
name: custom-video-extractors
description: Build per-site video URL extractors for sites yt-dlp can't handle. Uses a registry pattern with Puppeteer stealth for page extraction, JSON-LD and regex parsing for video URL discovery, and cookie generation for authenticated downloads.
trigger: user wants to download from a site that blocks yt-dlp, extract video URLs from JavaScript-rendered pages, or add a new site to a downloader's custom extractor system.
---

# Custom Video Extractors

Framework for extracting video download URLs from websites that block yt-dlp, require JavaScript execution, or have anti-bot protections.

## Architecture

```
User URL → extract() [registry dispatcher]
  → Pattern match against registered extractors
    → Puppeteer stealth loads page (JS, cookies)
      → Extract video URL from HTML (JSON-LD, get_file, video tag)
        → Return {url, title, cookie_file, referer}
          → yt-dlp downloads with cookies + Referer
```

## Registry Pattern

### Decorator-based registration

```python
import re
_extractors: list[tuple[re.Pattern, callable]] = []

def register(pattern: str):
    """Decorator: register an extractor for URLs matching *pattern*."""
    def wrap(fn):
        _extractors.append((re.compile(pattern, re.IGNORECASE), fn))
        return fn
    return wrap

async def extract(url: str) -> dict | None:
    """Try all registered extractors in order, return first match."""
    for pat, fn in _extractors:
        if pat.search(url):
            try:
                result = await fn(url)
                if result:
                    return result
            except Exception as e:
                logger.warning("Extractor %s failed: %s", fn.__name__, e)
    return None
```

### Registration example

```python
@register(r"pimpbunny\.com")
async def extract_pimpbunny(url: str) -> dict | None:
    ...
```

## Puppeteer Microservice (Node.js)

### Endpoints

| Endpoint | Purpose | Returns |
|----------|---------|---------|
| `POST /health` | Health check | `{status: "ok"}` |
| `POST /extract-cookies` | Get cookies only | `{cookies[], headers, success}` |
| `POST /extract-page` | Full page HTML + cookies | `{html, cookies[], headers, success, url}` |

### Key patterns

- **Stealth plugin** — `puppeteer-extra` + `puppeteer-extra-plugin-stealth` to avoid bot detection
- **Chrome path** — Set via `CHROMIUM_PATH` env var (e.g. `/usr/bin/chromium-browser`)
- **No `waitForTimeout`** — Use `const sleep = (ms) => new Promise(r => setTimeout(r, ms))` instead (removed in Puppeteer v23+)
- **Wait for video elements** — Use `page.waitForFunction()` with a timeout (not required to succeed — catch the timeout and use whatever HTML loaded)
- **Proxy support** — Pass `--proxy-server` via launch args

### Request format

```javascript
// POST /extract-page
{ "url": "https://pimpbunny.com/videos/123", "proxy": "http://1.2.3.4:8080" }
```

### Running the service

```bash
CHROMIUM_PATH=/usr/bin/chromium-browser node index.js
# Listens on port 3001 by default
```

## Page Extraction Strategy

The `/extract-page` endpoint loads the page with full JavaScript execution, waits for video-related content, and returns the rendered HTML.

### Content extraction methods (tried in order):

1. **JSON-LD structured data**: `<script type="application/ld+json">` → parse `contentUrl` field
2. **get_file URLs**: Common on adult tube sites — search for URLs containing `get_file`, `_1080p.mp4`, `_720p.mp4`, `_src.mp4`
3. **Video tag src**: `<video src="...">`
4. **Generic .mp4 URLs**: `/videos/N/...mp4`, `/dl/N/...mp4`, `/media/...mp4`

### Python extractor structure

```python
@register(r"example\.com")
async def extract_example(url: str) -> dict | None:
    from browser_bypass import BrowserBypass
    bb = BrowserBypass()
    result = await bb.extract_page(url)
    html = result.get("html", "")
    if not html:
        return None

    # ▸ Method 1: JSON-LD
    for m in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
                         html, re.DOTALL | re.IGNORECASE):
        data = json.loads(m.group(1))
        cu = data.get("contentUrl") or data.get("video", {}).get("contentUrl")
        if cu:
            video_url = cu
            break

    # ▸ Method 2: get_file URLs
    if not video_url:
        for pat in [r'get_file[^"\']*_1080p\.mp4', r'get_file[^"\']*_720p\.mp4']:
            m = re.search(pat, html)
            if m:
                video_url = m.group(0)
                break

    if not video_url:
        return None

    # Return format expected by the downloader
    cookies = result.get("cookies", [])
    cookie_file = bb.write_cookie_file(cookies)
    return {
        "url": video_url,
        "title": safe_title,
        "ext": "mp4",
        "source": "example",
        "cookie_file": cookie_file,
        "referer": url,
    }
```

## Integration with Downloader

The downloader's `download()` method:
1. Calls `resolve_url()` which invokes the extractor registry
2. If a custom extractor returns a direct URL, passes it to yt-dlp as a raw file download
3. Injects `cookiefile` and `Referer` header into yt-dlp options

```python
# In downloader.py:
custom = await self.resolve_url(url)
if custom:
    direct_url = custom.get("url")
    ext_cookie_file = custom.get("cookie_file")
    ext_referer = custom.get("referer")
    if direct_url:
        ydl_opts["format"] = "best"
        download_url = direct_url
        if ext_cookie_file:
            ydl_opts["cookiefile"] = ext_cookie_file
        if ext_referer:
            ydl_opts.setdefault("http_headers", {})["Referer"] = ext_referer
```

## Pitfalls

- **Puppeteer version** — `waitForTimeout` removed in v23+. Use `sleep()` helper instead.
- **Chrome not found** — Set `CHROMIUM_PATH=/usr/bin/chromium-browser` or whatever path for the installed browser. The puppeteer bundled Chrome may not match the system version.
- **JSON-LD parsing** — The JSON-LD script tag may be nested or have extra whitespace. Use `re.DOTALL` flag.
- **get_file URL escaping** — URLs in page HTML often have escaped backslashes: `\\/` → `/`. Clean with `.replace("\\", "")`.
- **Cookie expiry** — Puppeteer session cookies may expire. The cookie file is written once at extraction time and should be used within a reasonable timeframe.
- **page.waitForFunction timeout** — Use a catch on the timeout. The page may have loaded enough content before the timeout fires. Log the timeout but use whatever HTML was captured.
- **Port conflicts** — Node service on port 3001. Kill with `fuser -k 3001/tcp`.
- **Referer required** — Some CDNs check the Referer header. Always pass the original page URL as Referer when downloading the extracted video URL.
