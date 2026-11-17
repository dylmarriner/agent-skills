# Borntobefuck Extraction

## Architecture

borntobefuck uses a canvas-based player where the HLS stream URL is loaded dynamically by JavaScript after clicking play. Two CDN backends:

- **Zavastream** (`content.zavastream.com/{contentId}/{uuid}/index.m3u8`) — older videos, m3u8 sometimes visible in initial HTML
- **Bunny CDN** (`vz-0c578c5b-997.b-cdn.net/{uuid}/playlist.m3u8`) — newer videos, requires click-to-play

## Extraction Pipeline

### Step 1: Load watch page, find player iframe
POST to `http://localhost:3001/extract-page` with `{"url":"https://borntobefuck.com/watch/{ID}"}`. Look for iframe src containing `/videos/{ID}/player?lang=en`. Some IDs return empty HTML (dead/deleted).

### Step 2: Puppeteer sniff-and-capture
Navigate to `https://borntobefuck.com/videos/{ID}/player?lang=en`. Register `page.on('request', ...)` filtering for `.m3u8`. Click player selectors in order: `.active-video-player`, `.player-container`, `video`. Fallback: click center of page. Wait 8-10s for ad resolution.

### Step 3: Select best quality variant
- Bunny CDN: 720p > 480p > 360p variants at `/720p/video.m3u8`, `/480p/video.m3u8`
- Zavastream: 720p > 480p > master playlist

### Step 4: Download
```bash
yt-dlp --referer "https://borntobefuck.com" --add-header "Origin:https://borntobefuck.com" \
  --output "/mnt/storage/videos/borntobefuck_{ID}.mp4" --merge-output-format mp4 "{HLS_URL}"
```

Always use --referer + Origin headers — Bunny CDN enforces them.

## Batch Extraction Pattern

Use a single Puppeteer browser with `browser.newPage()` per video, closing each after capture. ~15-20s per video. Script at `backend/node_service/btbf_batch_extract.cjs`.

## Quality Notes
- Videos are typically 100-400 MB at 720p or 480p
- 720p preferred but not always available
- Lower IDs tend to be older/480p-only
- Some videos max at 360p
