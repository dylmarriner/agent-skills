# Session Log: 2026-07-08b — Pimpbunny crack + project restructure

## What changed

**Project restructure:** The old `backend/extractors.py` was replaced with a modular `backend/extractors/` Python package:

- `backend/extractors/__init__.py` — `@register` decorator pattern, site dispatch, pimpbunny extractor
- Each site has its own `async` function decorated with `@register(r"sitename\.com")`
- Returns `{url, title, ext, source, cookie_file?, referer?}` or `None`

**browser_bypass.py** gained `extract_page()` — calls new `/extract-page` endpoint on the Puppeteer service, returns full page HTML + cookies after JS execution.

**node_service/index.js** gained `/extract-page` endpoint that:
1. Launches Puppeteer (headless new)
2. Sets stealth UA + viewport + webdriver override
3. Navigates to URL, waits for network idle + 3s
4. Waits up to 8s for `contentUrl`, `get_file`, or `<video>` elements
5. Returns full HTML, cookies, final URL

## Pimpbunny extraction pipeline

The working chain is:

1. `browser_bypass.extract_page(url)` → Puppeteer loads page, returns HTML + cookies
2. Extractors parse JSON-LD from HTML: `<script type="application/ld+json">` contains `contentUrl`
3. The video URL is like: `https://pimpbunny.com/get_file/<num>/<hash>/<id>/<id>_720p.mp4/`
4. Cookies + Referer header are needed to bypass anti-hotlink (returns 1x1 GIF without them)
5. Download via curl with cookie file

**Important:** The URL hash/`rnd` token is session-tied. Must extract fresh per download.

## Puppeteer-extra build issue

`puppeteer-extra@3.3.6` installed without built `dist/` directory — `package.json` points to `dist/index.cjs.js` which doesn't exist. Package is published as source and needs `tsc` + `rollup` build.

**Fix:** Switched `index.js` to use plain `puppeteer`:
```javascript
const puppeteer = require('puppeteer');
```
Stealth plugin is optional — manual UA + viewport + `evaluateOnNewDocument` to hide webdriver is sufficient.

## Direct yt-dlp workflow (most sites)

For ad-hoc downloads (not through VideoSnap), the reliable pattern is:

```bash
~/.local/bin/yt-dlp --impersonate chrome \
  --format "bestvideo[height<=1080]+bestaudio/best[height<=1080]" \
  --merge-output-format mp4 \
  --output "/mnt/storage/videos/%(title)s [%(id)s].%(ext)s" \
  --no-playlist --socket-timeout 30 \
  "URL"
```

This works for: pornhub (bypasses 474), xhamster, xnxx, youporn, eporner.

Use Hermes `terminal(background=True, notify_on_complete=True)` for non-blocking execution.
