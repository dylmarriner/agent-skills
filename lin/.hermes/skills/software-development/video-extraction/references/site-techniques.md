# Site-Specific Extraction Details

## pimpbunny.com

**Anti-bot measures:** JS-blob video (MediaSource), session-signed `get_file` URLs with rotating hash + `rnd` parameter, Cloudflare, anti-hotlink (returns 1x1 GIF without cookies).

**Working extraction:**

1. Puppeteer loads page with stealth, waits 3s
2. Parse `<script type="application/ld+json">` for `contentUrl` field
3. Fallback: regex for `get_file` URLs in HTML
4. Cookies from `page.cookies()` → Netscape format cookie file
5. Download: `curl -L -o output.mp4 -b "$COOKIE_FILE" -H "Referer: https://pimpbunny.com/" -H "User-Agent: ..." "$VIDEO_URL"`

**Cookie format:**
```
# Netscape HTTP Cookie File
.pimpbunny.com	TRUE	/	FALSE	0	PHPSESSID	xxxxx
```

## borntobefuck.com

**Anti-bot measures:** Ad-gated (click-to-play overlay), canvas-based player, iframe-based player page, HLS via two CDN backends:
- **Zavastream** (`content.zavastream.com/{content_id}/{uuid}/...`) — older videos; m3u8 visible directly in player HTML
- **Bunny CDN** (`vz-*.b-cdn.net/{uuid}/...`) — newer videos; m3u8 only appears AFTER clicking play

**Player page size tells you which CDN:** ~17KB = Zavastream (static HLS in HTML). ~9KB = Bunny CDN (needs click-and-capture).

**Working extraction:**

Use Puppeteer click-and-capture. Load the player directly at `https://borntobefuck.com/videos/{id}/player?lang=en` (NOT the watch page — yt-dlp doesn't support `/watch/NNNNN`).

**Method 1 — Single video (recommended):**
```bash
cd /media/kubuntux/DEVELOPMENT1/video-downloader/backend/node_service
NODE_PATH=$(pwd)/node_modules node /path/to/bornto_sniff.cjs <video_id>
```
Outputs JSON: `{success, m3u8s: [HLS URLs]}`

**Method 2 — Batch (multiple videos, reuses browser):**
```bash
cd /media/kubuntux/DEVELOPMENT1/video-downloader/backend/node_service
NODE_PATH=$(pwd)/node_modules node /path/to/btbf_batch_extract.cjs <id1> <id2> ...
```
Outputs JSON array.

Both scripts:
1. Launch headless Chromium via `require('puppeteer')` (NOT puppeteer-extra — it's broken)
2. Navigate to player iframe page
3. Register `.m3u8` network request listener
4. Click CSS selectors: `.active-video-player` → `.player-container` → `video`
5. Fallback: click center of page
6. Wait 10-13s total for HLS streams to resolve

Download with explicit naming (raw HLS saves as "index.mp4"):
```bash
yt-dlp --referer "https://borntobefuck.com" \
       --add-header "Origin:https://borntobefuck.com" \
       --output "/mnt/storage/videos/borntobefuck_{video_id}.mp4" \
       --merge-output-format mp4 \
       "<720p_video_m3u8_URL>"
```

**BTBF info:**
- Quality varies: most Bunny CDN vids max at 480p; Zavastream usually has 720p
- Dead videos return 0-byte HTML from Puppeteer
- The m3u8s array typically has the master playlist first, quality variant second
- `--impersonate chrome` is NOT enough — yt-dlp returns "Unsupported URL" for borntobefuck

## VideoSnap Project Extractors

Located at `/media/kubuntux/DEVELOPMENT1/video-downloader/backend/extractors/`

**Architecture:** Package with `__init__.py` using `@register(r"domain\.com")` decorator pattern.

**BrowserBypass class** (`browser_bypass.py`):
- `extract_page(url)` → POST `/extract-page` → returns `{html, cookies, headers, url}`
- `get_context(url)` → POST `/extract-cookies` → returns `{cookies, headers}`
- `write_cookie_file(cookies)` → writes Netscape-format temp file

**Node service** (`node_service/index.js`):
- POST `/health` → `{status: "ok"}`
- POST `/extract-cookies` → `{cookies, headers}`
- POST `/extract-page` → `{html, cookies, headers, url}` — waits for contentUrl/get_file/video in DOM

## Common Error Patterns

| Error | Cause | Fix |
|-------|-------|-----|
| HTTP 474 | Pornhub anti-bot | Add `--impersonate chrome` |
| Unsupported URL | No yt-dlp extractor | Use custom extractors or Puppeteer |
| Unable to extract flashvars | pimpbunny generic extractor | Use JSON-LD approach |
| Requested format not available | HLS format mismatch | Omit `--format` flag for HLS URLs |
| EADDRINUSE :3001 | Previous Node service still running | `fuser -k 3001/tcp` |
| Module not found puppeteer-extra | Unbuilt dist/ | Replace with plain `puppeteer` in index.js |
| 404 on 720p/video.m3u8 | Source only has 480p (Bunny CDN) | Use 480p/video.m3u8 instead |
| tcsetattr: Inappropriate ioctl | curl with background process issues | Use yt-dlp or foreground curl |
| Content does not exist (gofile) | File removed/expired | Cannot recover |
| Downloads temporarily restricted (filesters) | Service down across .si/.me/.gg domains | Bookmark and retry later |
