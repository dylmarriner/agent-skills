---
name: url2video-download
description: Download videos from pimpbunny.com, borntobefuck.com, spankbang.com and other protected sites
---

# URL2Video Download Patterns

## url2video service (preferred for all sites)

The url2video service on port 8800 is the primary downloader. Queue URLs to it via:
```bash
curl -s -X POST http://localhost:8800/q \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://...","quality":"1080p"}'
```

It handles yt-dlp, proxy rotation, browser bypass, and persistence automatically. See `references/url2video-api.md` for full API.

**Known hang:** url2video can become unresponsive under load (high CPU, port open but no response). Recovery: kill the hung PID, restart as background process. DB persists — no jobs lost.

## pimpbunny.com

**Custom extractor (recommended):** The VideoSnap project at `~/Documents/video-downloader/` has a custom pimpbunny extractor in `backend/extractors/__init__.py`. Uses Puppeteer node service (port 3001) to load page → extract JSON-LD `contentUrl` → yt-dlp with cookies + referer.

**via standalone script (bypasses videosnap circular import):**
```bash
# Ensure Puppeteer node service is running first
cd /media/kubuntux/DEVELOPMENT1/video-downloader/backend/node_service
NODE_PATH=$(pwd)/node_modules node index.js &
# Extract & download
python3 /tmp/pimp_dl.py <pimpbunny_url>
```
The script at `/tmp/pimp_dl.py` calls the node service directly via `urllib.request` (no `backend/` imports — avoids the circular import), extracts JSON-LD contentUrl, writes cookies to Netscape format, and downloads with yt-dlp.

**Manual fallback (Puppeteer direct):**
1. Start node service: `cd /media/kubuntux/DEVELOPMENT1/video-downloader/backend/node_service && NODE_PATH=$(pwd)/node_modules node index.js`
2. Extract page: `curl -s http://localhost:3001/extract-page -X POST -H "Content-Type: application/json" -d '{"url":"<url>"}'`
3. Parse JSON-LD for `contentUrl` field, save cookies
4. Download: `yt-dlp --cookies cookies.txt --referer <url> --impersonate chrome --format "bestvideo[height<=1080]+bestaudio..." <contentUrl>`

**Note:** JSON-LD contentUrl is usually 720p (`_720p.mp4`). Better-quality `_source.mp4` variants exist in the HTML get_file URLs but require session-signed tokens.

**Known issue:** yt-dlp's generic extractor can't handle pimpbunny (flashvars). Don't attempt `--force-generic-extractor` — always use the Puppeteer pipeline.

## borntobefuck.com

**Three methods — Puppeteer click-and-capture preferred (see `scripts/bornto_sniff.cjs`), then simple Puppeteer load, lastly curl fallback.**

### Background: two CDN backends

Borntobefuck uses two different CDN backends depending on video age:
- **Zavastream** (`content.zavastream.com/{content_id}/{uuid}/index.m3u8`) — Older videos; HLS URL is directly in the player HTML after Puppeteer rendering. Player page is ~17KB.
- **Bunny CDN** (`vz-*.b-cdn.net/{uuid}/playlist.m3u8`) — Newer videos; HLS URL only appears AFTER clicking play (network request interception). Player page is ~9KB — no video URLs in static HTML.

### Method 1: Puppeteer Click-and-Capture (most reliable — works for both CDNs)

Use the `bornto_sniff.cjs` script (in `scripts/` of this skill) which launches Puppeteer, loads the player page, clicks the play area, and captures `.m3u8` URLs via network request interception:

```bash
cd /media/kubuntux/DEVELOPMENT1/video-downloader/backend/node_service
node <path>/bornto_sniff.cjs <video_id>
```

The script navigates to `https://borntobefuck.com/videos/{id}/player?lang=en`, registers a `.m3u8` request listener, then clicks selectors in order: `.active-video-player`, `.player-container`, `.video-player`, `#player`, `video`, play buttons, then center of page. Waits 8s for HLS manifest, returns JSON with `m3u8s[]`:

```json
{"success":true,"m3u8s":["https://vz-0c578c5b-997.b-cdn.net/{uuid}/playlist.m3u8",".../720p/video.m3u8"]}
```

Download with descriptive output name (raw HLS URLs have no title metadata):

```bash
yt-dlp \
  --referer "https://borntobefuck.com" \
  --add-header "Origin:https://borntobefuck.com" \
  --output "/mnt/storage/videos/borntobefuck_{video_id}.mp4" \
  --merge-output-format mp4 \
  "https://vz-0c578c5b-997.b-cdn.net/{uuid}/720p/video.m3u8"
```

### Method 2: Puppeteer → Player Iframe → HLS page load (Zavastream only)

1. Ensure Puppeteer node service running on :3001: `cd /media/kubuntux/DEVELOPMENT1/video-downloader/backend/node_service && NODE_PATH=$(pwd)/node_modules node index.js`
2. Extract watch page via Puppeteer `/extract-page` to find player iframe (`/videos/{id}/player?lang=en`)
3. Load player iframe via `/extract-page` — HTML contains `content.zavastream.com/{content_id}/{uuid}/index.m3u8`
4. Download with yt-dlp `--referer` + `--add-header "Origin:..."`

### Method 3: curl player page directly (least reliable)
```bash
curl -sL -H "Referer: https://borntobefuck.com/" \
  "https://borntobefuck.com/videos/{id}/player?lang=en" | \
  grep -oP 'https?://[^"'"'"'\\\\s]+\\.m3u8[^"'"'"'\\\\s]*'
```

### Known issues:
- `/watch/NNNNN` format NOT supported by yt-dlp — must extract player iframe first
- videosnap queue add accepts URLs but serve does NOT reliably process for this site
- curl returns ~5KB (incomplete); Puppeteer returns 9-17KB
- Quality cap: 720p most videos; some 480p only (check variant in m3u8s array: `480p/video.m3u8` vs `720p/`)
- **Filenames from raw HLS are useless** — yt-dlp saves as `index [index].mp4`. Always use `--output borntobefuck_{id}.mp4`
- **Dead videos** — `/watch/{id}` returns empty (0-byte) from Puppeteer. Skip these.
- Content ID and UUID vary per video — extract from player page thumbnail reference or m3u8 in captured URLs

## spankbang.com
**Known issue (2026-06):** Returns 403 Forbidden to yt-dlp even with custom User-Agent and Referer headers. The page also blocks curl (returns tiny 5KB block page).

**Possible workaround:**
```bash
yt-dlp --cookies-from-browser chromium <url>
```
This uses browser cookies which may bypass the 403. If that also fails, the site requires a logged-in browser session or is using CDN-level blocking that can't be bypassed.

## xhamster.com
Works well with standard yt-dlp + aria2c. Better encode quality than eporner.com.

## porntn.com
Works with yt-dlp generic extractor. Album pages are valid batch sources. Extraction is slow but downloads once started.

## General rules
- The user sends URLs and expects silent action. No explanations, no questions.
- Confirm only: DONE: filename or FAILED: reason
- Run downloads in background so the user can keep sending URLs
- `--impersonate chrome` is ESSENTIAL for pornhub.com (returns HTTP 474 without it)
- For protected sites, use the VideoSnap project at `/media/kubuntux/DEVELOPMENT1/video-downloader/`:
  - `backend/extractors/` — Python extractors with `@register` decorator pattern
  - `backend/node_service/index.js` — Puppeteer microservice on port 3001
  - `backend/browser_bypass.py` — Client for the Node service
  - **puppeteer-extra is broken** on Node v22 (missing dist/ build). Edit index.js to use `require('puppeteer')` directly instead.
  - **`backend/queue.py` shadows Python stdlib `queue`** — rename to `download_queue.py` if you see circular import errors.
