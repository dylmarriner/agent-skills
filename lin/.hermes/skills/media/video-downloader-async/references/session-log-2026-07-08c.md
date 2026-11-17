# Session Log: 2026-07-08c — Pimpbunny confirmed + borntobefuck ad-gated

## Downloads completed (8 videos)

| Video | Site | Size | Method |
|-------|------|------|--------|
| ANGELA WHITE - POV Threesome w/ Mia Malkova | pornhub | 135MB | yt-dlp --impersonate chrome |
| Step Bro S15E4 | pornhub | 157MB | yt-dlp --impersonate chrome |
| BANGBROS - Blonde PAWG Mia Malkova | pornhub | 313MB | yt-dlp --impersonate chrome |
| Mia Malkova Blowjob Fucking POV | eporner | 132MB | yt-dlp direct |
| A Lucky Guy Fucks Mia Malkova (cached) | eporner | 278MB | yt-dlp (already had) |
| BANGBROS - Bailey Brooke & Mia Malkova | xnxx | 238MB | yt-dlp --impersonate chrome |
| VRBangers - Mia Malkova + Riley Reid | xhamster | 76MB | yt-dlp --impersonate chrome |
| Louisa Rain Enjoys Riding Her Dildo | pimpbunny | 104MB | Puppeteer→JSON-LD→cookies+curl |

## Key learnings

### 1. Pimpbunny pipeline CONFIRMED WORKING

The full pipeline proved end-to-end:
1. Node Puppeteer service at port 3001 loads the page
2. `BrowserBypass.extract_page(url)` returns HTML + cookies
3. Old single-file `extractors.py` parses JSON-LD `<script type="application/ld+json">` for `contentUrl`
4. curl downloads with the cookies + Referer header

**Proof:** 104MB, 15:14 duration video downloaded successfully. Path: `/mnt/storage/videos/Louisa Rain Enjoys Riding Her Dildo [pimpbunny].mp4`

**URL pattern:** `https://pimpbunny.com/get_file/<num>/<hash>/<id>/<id>_720p.mp4/`
**Anti-hotlink:** Returns 1x1 GIF without valid cookies. Returns `HTTP/2 410` (Gone) with expired `rnd` tokens.

### 2. borntobefuck.com is AD-GATED (still unsolved)

**Ad wall:** "Unlock the video (4 clicks left)" overlay prevents direct access to the video URL. The video plays inside an iframe (`/videos/<id>/player?lang=en`).

**Canvas-based player:** After clicking Play through the ad wall, the player controls appear (Pause, Seek, Volume, Fullscreen) but there is NO `<video>` element in the DOM — the video is rendered to a `<canvas>` element. This means:
- `document.querySelector('video')` returns null
- Network interception shows no `.mp4` or `.m3u8` requests on borntobefuck's domain
- Performance entries show no relevant video resources
- The iframe's DOM after clicking Play has `<video>` count = 0

**All extraction methods failed:**
- yt-dlp (--impersonate chrome, cookies-from-browser, etc.)
- Custom curl HTML scraping
- Both old and new extractors/ packages
- Puppeteer network interception (only ad/tracker URLs captured)
- Browser devtools performance API

**Possible (untested) solutions:**
- MediaRecorder API in Puppeteer to capture the canvas stream
- DevTools Protocol `Page.captureStream()` or CDP screencast
- Intercept `MediaSource.addSourceBuffer()` calls for HLS manifest extraction

### 3. Node service restart fix

When the Node service dies and needs restarting:
```bash
fuser -k 3001/tcp 2>/dev/null
sleep 1
cd /path/to/node_service && node index.js
```
Without `fuser -k`, the old process's port lingers and causes EADDRINUSE.

### 4. Puppeteer script file pattern

Writing Puppeteer extraction scripts as files (not inline `node -e`) is critical:
- `node -e "..."` breaks on `${}` and `$$` in template literals
- The `page.$$('button')` shorthand gets interpreted as `page.PID('button')`
- File-based scripts at `/tmp/*.js` avoid all shell escaping issues

### 5. VideoSnap project fixes

- **Circular import fix:** Renamed `backend/queue.py` to `backend/download_queue.py` — the name `queue.py` shadows Python's stdlib `queue` module, which `urllib3` imports for `queue.LifoQueue`. All import sites updated.
- **Node service updated** with `/extract-page` endpoint that waits for `contentUrl`/`get_file`/`<video>` elements before returning HTML.
