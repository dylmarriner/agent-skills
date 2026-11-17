---
name: video-extraction
description: Extract video URLs from protected adult sites using a fallback chain — yt-dlp impersonation, custom extractors (JSON-LD/Puppeteer), and ad-gated HLS capture.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [video, download, extraction, puppeteer, yt-dlp, scraping, hls, adult-sites]
    related_skills: []
---

# Video Extraction Pipeline

Extract video URLs from protected adult sites using a fallback chain. Handles anti-bot measures, JS-loaded players, ad-gated content, and session-signed URLs.

## Trigger

Use when the user provides a video URL from: pornhub, eporner, xnxx, xhamster, pimpbunny, borntobefuck, spankbang, youporn. Also when standard yt-dlp returns HTTP 474, "Unsupported URL", or generic extraction errors.

## Fallback Chain

For any video URL, try in order:

1. **Direct yt-dlp** with `--impersonate chrome`
2. **Custom extractors** (VideoSnap project — JSON-LD/Puppeteer)
3. **Puppeteer service** (full page extraction via `/extract-page`)
4. **Direct Puppeteer script** (iframe click + HLS capture)

## Per-Site Methods

### pornhub
```bash
~/.local/bin/yt-dlp --impersonate chrome \
  --format "bestvideo[height<=1080]+bestaudio/best[height<=1080]" \
  --merge-output-format mp4 \
  --output "/mnt/storage/videos/%(title)s [%(id)s].%(ext)s" \
  --no-playlist --socket-timeout 30 "<URL>"
```
Without `--impersonate chrome`, pornhub returns HTTP 474 (anti-bot).

### eporner / xnxx / xhamster / youporn
Same command as pornhub above. Direct yt-dlp with `--impersonate chrome` works reliably.

### pimpbunny
Requires full Puppeteer → JSON-LD → cookies → curl pipeline.

Project extractor at `/media/kubuntux/DEVELOPMENT1/video-downloader/backend/extractors/__init__.py`:
1. Puppeteer loads page (stealth)
2. Parse JSON-LD `contentUrl` from `<script type="application/ld+json">`
3. Fallback: find `get_file` URLs in HTML
4. Extract cookies from browser session
5. Return direct URL with cookie file + referer
6. Download via curl with cookies and proper referer headers

### borntobefuck
Ad-gated — video behind "4 clicks left" wall. HLS via zavastream CDN.

Pipeline:
1. Navigate main page with Puppeteer
2. Find iframe (src = `/videos/NNNNN/player?lang=en`)
3. Navigate to iframe URL
4. Click Play button via page.evaluate
5. Capture `.m3u8` URLs from network requests (request interception)
6. Extract unique `index.m3u8` URL
7. Download via yt-dlp with referer + origin headers:
```bash
yt-dlp --impersonate chrome \
  --output "/mnt/storage/videos/%(title)s [id].%(ext)s" \
  --no-playlist --socket-timeout 30 \
  --referer "https://borntobefuck.com/" \
  --add-header "Origin:https://borntobefuck.com" \
  "<HLS_URL>"
```
8. Rename "index.mp4" to proper title (lookup with web_extract)

BTBF master playlists max out at 720p (no 1080p source).

## Node Service Setup

Service at `/media/kubuntux/DEVELOPMENT1/video-downloader/backend/node_service/`

**Pitfall:** `puppeteer-extra` has unbuilt `dist/`. Patch `index.js` to use plain `puppeteer`:
```
- const puppeteer = require('puppeteer-extra');
+ const puppeteer = require('puppeteer');
```
Then `npm install` and `node index.js` (port 3001).

For standalone Puppeteer scripts:
```
NODE_PATH=/media/kubuntux/DEVELOPMENT1/video-downloader/backend/node_service/node_modules node /tmp/script.js
```

## HLS Download

```bash
yt-dlp --impersonate chrome \
  --output "/mnt/storage/videos/<Title> [<id>].%(ext)s" \
  --no-playlist --socket-timeout 30 \
  --referer "https://originsite.com/" \
  --add-header "Origin:https://originsite.com" \
  "<HLS_URL>"
```

## Known Pitfalls

- **Circular import:** `backend/queue.py` shadows Python stdlib `queue` (used by urllib3). Rename to `download_queue.py`, update all 3 import sites (`cli.py`, `main.py`, `cli_impl.py`).
- **HLS filenames:** Raw HLS URLs save as "index.mp4". Always rename post-download.
- **Partials cleanup:** Interrupted HLS leaves `.part` and `.part-FragN.part` files. Delete before retry.
- **EADDRINUSE:** Port 3001 may be busy. `fuser -k 3001/tcp` before restarting Node service.

## Output

All videos → `/mnt/storage/videos/` (SMB share `[videos]` on kubuntux).
