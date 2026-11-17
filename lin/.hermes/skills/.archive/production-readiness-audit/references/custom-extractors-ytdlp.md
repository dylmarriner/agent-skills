# Custom yt-dlp Extractors for Blocked Sites

## When to Build

yt-dlp can't handle a site when:
- It returns "Unsupported URL" — no extractor registered
- The site requires JavaScript rendering + cookies for video URL extraction
- The site blocks yt-dlp's User-Agent or HTTP client fingerprint
- The direct video URL requires specific cookies + Referer to download

## Architecture

User URL → extractors/__init__.py (pattern match → extractor fn)
         → browser_bypass.extract_page() → Puppeteer (full JS + stealth)
         → Parse HTML for video URL
         → Return {url, title, ext, source, cookie_file, referer}
         → downloader.py passes to yt-dlp with cookies + Referer

## Implementation Steps

### 1. Create extractors package

backend/extractors/__init__.py with a @register(pattern) decorator that maps URL
regex patterns to async extraction functions, and a top-level extract(url) that
iterates registered extractors and returns the first match.

### 2. Add Puppeteer endpoint

The Node.js microservice needs a POST /extract-page endpoint that:
- Launches Chrome with stealth plugins (puppeteer-extra-plugin-stealth)
- Navigates to the URL with waitUntil: networkidle2 + 3s delay
- Waits for video-related content (JSON-LD, get_file, video elements)
- Returns { html, cookies, headers, url }

Use sleep(ms) not page.waitForTimeout(ms) — removed in Puppeteer v23+.

### 3. Extraction methods (priority order)

1. JSON-LD contentUrl — Parse script type=application/ld+json for contentUrl
   (check both top-level and data.video.contentUrl)
2. get_file URLs — Regex for get_file endpoint with quality suffixes
   (_1080p.mp4, _720p.mp4, _src.mp4)
3. video tag src — Parse video tag's src attribute
4. Generic mp4 URL — Look for /videos/N, /dl/N, /media/N patterns

### 4. Integrate into download pipeline

In downloader.py, before running yt-dlp:
  custom = await self.resolve_url(url)
  if custom:
      ydl_opts["cookiefile"] = custom.get("cookie_file")
      ydl_opts["http_headers"]["Referer"] = custom.get("referer")

## yt-dlp Format Fallback Chain

Try in order:
1. bestvideo[height<=N]+bestaudio/best[height<=N]
2. bestvideo+bestaudio/best
3. best

Catch each error, continue to next, raise last error if all fail.
