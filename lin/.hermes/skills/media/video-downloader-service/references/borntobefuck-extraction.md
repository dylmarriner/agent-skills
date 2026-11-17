# borntobefuck.com Extraction Pattern

## Two Methods

### Method 1: Puppeteer → Player Iframe → HLS (PREFERRED — VERIFIED 2026-07-12)

The page renders the video player dynamically. Use the Puppeteer node service on port 3001 to get the full rendered HTML:

1. **Start Puppeteer service** (if not running):
   ```bash
   cd /media/kubuntux/DEVELOPMENT1/video-downloader/backend/node_service
   NODE_PATH=$(pwd)/node_modules node index.js
   ```

2. **Extract page via Puppeteer** — this loads the full JS-rendered page including the player iframe content:
   ```bash
   curl -s -X POST http://localhost:3001/extract-page \
     -H 'Content-Type: application/json' \
     -d '{"url":"https://borntobefuck.com/watch/34798"}'
   ```
   The response HTML contains:
   - Player iframe at `https://borntobefuck.com/videos/{id}/player?lang=en`
   - Thumbnail URL showing the content path: `content.zavastream.com/{content_id}/{uuid}/thumbnail.jpg`

3. **Extract player iframe HTML** — load the player iframe via Puppeteer (NOT curl, curl returns incomplete HTML):
   ```bash
   curl -s -X POST http://localhost:3001/extract-page \
     -H 'Content-Type: application/json' \
     -d '{"url":"https://borntobefuck.com/videos/34798/player?lang=en"}'
   ```
   The rendered HTML directly contains the `index.m3u8` URL:
   ```
   content.zavastream.com/{content_id}/{uuid}/index.m3u8
   ```

4. **Download with yt-dlp** using Referer + Origin headers:
   ```bash
   yt-dlp \
     --referer "https://borntobefuck.com" \
     --add-header "Origin:https://borntobefuck.com" \
     --output "/mnt/storage/videos/%(title)s [%(id)s].%(ext)s" \
     --merge-output-format mp4 \
     "https://content.zavastream.com/{content_id}/{uuid}/index.m3u8"
   ```

### Method 2: Curl Player Page (fallback when Puppeteer unavailable)

If the node service is not running, try direct curl with Referer:
```bash
curl -sL -H "Referer: https://borntobefuck.com/" \
  "https://borntobefuck.com/videos/33467/player?lang=en" | \
  grep -oP 'https?://[^"'"'"'\\s]+\.m3u8[^"'"'"'\\s]*'
```

## URLs: /watch/NNNNN vs /videos/NNNNN

- **`/watch/NNNNN`** — the main page URL format. Not supported by yt-dlp. Must extract the player iframe.
- **`/videos/NNNNN/player?lang=en`** — the player iframe. Contains the HLS stream URL but only when loaded with JS (Puppeteer) or with correct Referer (limited curl support).

The video ID maps to a content ID on zavastream. Example from verified session:
- Watch URL: `https://borntobefuck.com/watch/34798`
- Player iframe: `https://borntobefuck.com/videos/34798/player?lang=en`
- HLS: `https://content.zavastream.com/{zavastream_content_id}/{uuid}/index.m3u8`

## Download Parameters

- `--referer https://borntobefuck.com` — REQUIRED
- `--add-header "Origin:https://borntobefuck.com"` — REQUIRED
- Quality: max 720p (borntobefuck doesn't serve higher on the HLS stream)
- Merge: mp4 (HLS segments need merging)

## Videosnap Integration

`videosnap queue add` accepts borntobefuck URLs and assigns a job ID, but:
- The **serve command** (API server) does NOT reliably process the queue for this site
- videosnap dl returns "Unsupported URL" for borntobefuck
- Use the Puppeteer → yt-dlp pipeline (Method 1) as the primary download path

## Pitfalls

- **Puppeteer service must be running** — without it, the player page HTML is incomplete and won't contain the m3u8 URL
- The player page returns ~17KB JS-rendered HTML via Puppeteer vs ~5KB via curl
- Always set BOTH `--referer` and `--add-header Origin` for yt-dlp HLS downloads
- The zavastream content ID (e.g. `621742`) and UUID are unique per video — extract from thumbnail URL or player HTML
- Quality ceiling is 720p on this site's HLS output
