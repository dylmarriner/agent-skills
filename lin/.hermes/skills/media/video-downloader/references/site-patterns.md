# Site-Specific Download Patterns

## borntobefuck.com

**Detection**: yt-dlp fails with `ERROR: Unsupported URL`. Page uses iframe-based player.

**URL formats**:
- `/watch/NNNNN` — main page, has the iframe with player
- `/videos/NNNNN/player?lang=en` — player iframe page

**Player mechanism**: Videos play in an iframe at `/videos/{id}/player?lang=en`. The player uses canvas-based rendering (no DOM video element visible - only 3 elements total, shadow DOM or canvas). Video is served as HLS from ZavaStream CDN (`content.zavastream.com`).

**Gate types**:
- **Countdown timer** (shows "AVAILABLE IN X:XX:XX"): Server-side timer, cannot bypass. Set a cron job.
- **Ad-wall (shows "N clicks left" / "Unlock the video")**: The player loads but requires clicking Play in the iframe. Puppeteer can click it.

**UPDATED — Puppeteer HLS capture (works for /watch/NNNNN format)**:

The `data-hls-url` attribute approach via curl (old method) does NOT work for `/watch/NNNNN` URLs because the video data is loaded dynamically via JS. Use Puppeteer with network interception:

```javascript
const puppeteer = require('puppeteer');
const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
const page = await browser.newPage();
const urls = [];
await page.setRequestInterception(true);
page.on('request', req => {
  const u = req.url();
  if (u.includes('.m3u8') && u.includes('zavastream')) urls.push(u);
  req.continue();
});
await page.goto('https://borntobefuck.com/watch/NNNNN', { waitUntil: 'networkidle2' });
await new Promise(r => setTimeout(r, 3000));
// Click play inside the iframe
await page.evaluate(() => {
  const iframe = document.querySelector('iframe');
  if (iframe) {
    const d = iframe.contentDocument || iframe.contentWindow.document;
    const b = d.querySelector('button');
    if (b && b.textContent.toLowerCase().includes('play')) b.click();
  }
});
// Wait for HLS URL to appear
await new Promise(r => setTimeout(r, 8000));
console.log(urls.filter(u => u.includes('index.m3u8'))[0]);
```

Then download the HLS URL with yt-dlp:
```bash
yt-dlp --impersonate chrome \
  --referer "https://borntobefuck.com/" \
  --add-header "Origin:https://borntobefuck.com" \
  -o "output.mp4" "<m3u8_url>"
```

**Known CDN**: `content.zavastream.com/<account_id>/<uuid>/index.m3u8` with 720p and 480p variants. Server is Cloudflare'd with Turnstile CAPTCHA on the main page, but the player iframe loads without challenge.

## eporner.com

**Detection**: URL starts with `https://www.eporner.com/video-<id>/` or `https://www.eporner.com/hd-porn/<id>/`.

**Player mechanism**: Standard HTML5 `<video>` element with HLS stream. **yt-dlp handles this natively** — no browser extraction needed.

**Download** (Tier 1 — yt-dlp):

```bash
yt-dlp -f "bestvideo[height<=1080]+bestaudio/best" --merge-output-format mp4 \
  -o "/path/to/output/%(title)s.%(ext)s" "<url>"
```

**Quality variants**: Available in 720p, 1080p, and sometimes 1440p (4K). Use `yt-dlp -F <url>` to list available formats first.

**Batch download**: Multiple eporner URLs can be passed to yt-dlp or run as separate background processes:

```bash
# From a file listing
cat urls.txt | while read url; do
  yt-dlp -o "/path/output/%(title)s.%(ext)s" "$url" &
done
```

**Serving multiple quality levels**: Some eporner pages serve different resolutions as separate entries on the same page. `yt-dlp -F` will show all available quality tiers.

**No special headers needed**: eporner.com does not require custom referers, cookies, or user agents beyond standard browser UA.

## mega.nz

**Detection**: URL starts with `https://mega.nz/folder/...` — encrypted cloud storage, not a standard tube site.

**Tool**: `megadl` (from `megatools` package).

**URL format**:
```
https://mega.nz/folder/<folderID>#<folderKey>/folder/<subfolderID>
```
The `#folderKey` is required — it decrypts the folder listing. Without it, MEGA shows an empty page.

**Browser automation**: MEGA detects automated browsers and renders only a bare page with a "copy" textbox. The actual file listing is loaded via JS that checks for bot signals. Browser-based listing is not viable — the page snapshot shows only generic elements.

**Python library**: `mega.py` has a cffi version conflict on Python 3.12 (system `_cffi_backend` vs shipped cffi). Install in a venv to avoid conflicts, and watch for tenacity deprecation (`asyncio.coroutine` removed in Python 3.12 — pin tenacity >8.5.0).

**MEGA API**: Direct API calls (`curl https://g.api.mega.co.nz/cs`) return -11 or -15 without proper auth. Not worth the effort for public folder downloads.

**Download behavior**:
- `megadl <folder_url>` downloads ALL files in the folder sequentially (one at a time)
- No concurrency — files are queued
- Default output path is `$HOME` — always use `--path=<target>` to set destination
- Files with undecryptable keys are skipped with a WARNING and CRITICAL error in stderr
- Killing megadl mid-download removes the partial file (no .part artifact left)
- Average speed: ~11 MiB/s on fast connections, can drop to ~650 KiB/s for some segments
- Total folder size shown in the page title (e.g., "16.76 GB folder on MEGA")

**Handling subfolders within a folder**: Append `/folder/<subfolderID>` to the parent folder URL. Example:
```
https://mega.nz/folder/ekoSVSAA#ARPAg78WzlPzrlGcMf0D8w/folder/ftgnUaSQ
```

**Recommended approach**:
```bash
megadl --path="/mnt/pivideos/videos/" "<folder_url>"
```
Run in background with a cron job for large folders — megadl takes hours for multi-GB downloads.

## internetchicks.com (and similar WordPress tube sites)

**Detection**: yt-dlp fails with `ERROR: Unsupported URL`. Page has multiple numbered PLAYER buttons.

**Site pattern**: WordPress-based site with 5 player buttons triggered by `onclick="playEmbed('URL')"`. Each button loads a different embedded player host into an `<iframe id="main-player">`. Active host shown in the iframe's `src`.

**Embed providers used** (all commonly encountered):
- `streamtape.com/e/<id>` — heavily obfuscated video source, requires Playwright interception (Tier 3)
- `vidoza.net/embed-<id>.html` — alternate HTML5 player
- `playmogo.com/e/<id>` — embed player
- `voe.sx/e/<id>` — embed player
- `bysezejataos.com/e/<id>` — embed player

**Extracting embed URLs — curl grep (most reliable)**:
The browser snapshot often doesn't surface onclick handlers in the flattened DOM. Fetch raw HTML and grep for `playEmbed` directly:

```bash
curl -s "<page_url>" | grep -oP "playEmbed\('[^']+'"
```

This reveals all embed URLs without browser navigation at all. Example output:
```
playEmbed('https://streamtape.com/e/8DoJ33Lq2zU4xw'
playEmbed('https://vidoza.net/embed-dqebcyzg42wk.html'
playEmbed('https://playmogo.com/e/9uoqo1x5o09i'
playEmbed('https://voe.sx/e/ro63osfwg7jb'
playEmbed('https://bysezejataos.com/e/6nhnpckbrxbz'
```

**Download strategy — vidoza.net direct MP4 extraction (recommended)**:

Not all embed providers are equally resistant. Vidoza.net often serves a direct MP4 that can be extracted via curl:

```bash
# Step 1: Extract all embed URLs from the page
curl -s "<page_url>" | grep -oP "playEmbed\\('[^']+'"

# Step 2: Try vidoza.net embed — usually yields a direct MP4
curl -s "https://vidoza.net/embed-<id>.html" | grep -oP 'https?://[^"<>]+\.mp4[^"<>]*'

# Step 3: Download the direct MP4 URL with curl
curl -L -o "/path/output/%(title)s.%(ext)s" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  -H "Referer: https://vidoza.net/" \
  "<direct_mp4_url>"
```

**Example** — Vidoza returns MP4 URLs like:
```
https://str38.vidoza.net/vod/v2/<hash>/v.mp4
https://cache80.vidoza.net/vod/v2/<hash>/v.mp4
```
These are stable direct MP4 files (Content-Type: video/mp4, Content-Length in the hundreds of MB).
The User-Agent header is required (vidoza returns 403 without it). The Referer header is needed for some CDN nodes.

**Fallback approach** — If vidoza.net fails or returns no MP4:
1. Cycle through alternative embed hosts (streamtape, playmogo, voe.sx) with the same curl grep technique
2. Some may have direct MP4/HTTP-accessible sources even if their JS player is obfuscated
3. If all embed hosts fail, search for the video on an easier site (eporner.com is Tier 1)
4. Tell the user if specific embeds are too resistant

**Stale `dlv --hard` note**: Some outdated documentation references `dlv --hard <url>` as a Playwright-based approach. This command does NOT exist on this system. `dlv` is a simple yt-dlp wrapper — it has no `--hard` mode. For obfuscated video sites, you must extract the video URL manually using the techniques above.

## porndd.com

**Detection**: yt-dlp times out or hangs.

**Player mechanism**: Uses a custom Flowplayer/KT Player variant with `flashvars` config embedded in a script tag on the page. Video URLs are session-tokenized `get_file/0/` URLs with `v-acctoken` parameters. Multiple quality variants are defined in `flashvars`:
- `video_url` → 480p
- `video_alt_url` → 720p
- `video_alt_url2` → 1080p

**Extraction via flashvars** (preferred method):

1. Navigate to the video page with `browser_navigate`
2. Look for the script tag containing `flashvars` — search all scripts for `.mp4`:
   ```js
   document.querySelectorAll('script').forEach(s => {
     const t = s.textContent || '';
     if (t.includes('.mp4')) console.log(t);
   });
   ```
3. Extract the quality URLs from the `flashvars` object in that script — look for keys like `video_url` (480p), `video_alt_url` (720p), `video_alt_url2` (1080p) with corresponding `.mp4` `get_file` URLs ending in `?v-acctoken=...`
4. Get the browser's cookies:
   ```js
   document.cookie
   ```
5. The `PHPSESSID` and `kt_acctoken` cookies are required for successful download. The `v-acctoken` parameter in the URL alone is not sufficient — the PHP session cookie must be forwarded.
6. Download with curl, passing both the Referer and the full cookie string:
   ```bash
   curl -L -H "Referer: https://porndd.com/" \
     -H "User-Agent: Mozilla/5.0 ..." \
     -H "Cookie: PHPSESSID=...; kt_acctoken=...; kt_qparams=...; kt_tcookie=1" \
     -o "output.mp4" "<get_file_url>"
   ```

**Alternative — video element extraction** (if flashvars approach fails):

1. Navigate to the page
2. Click the play button / video area (be careful of ad overlays — click the control bar instead)
3. Wait for the video to start
4. Extract from the video element:
   ```js
   const v = document.querySelector('video');
   v.currentSrc
   ```
5. Download with curl + cookies as above

**Known behavior**: The `v-acctoken` in the URL is one-time-use per session. If you try to reuse a URL from a previous page load, it returns a 37-byte tracking GIF (HTTP 200) instead of the video. Always extract fresh URLs from the current page session.

**Available qualities**: 1080p (video_alt_url2_hd: '1'), 720p (video_alt_url_hd: '1'), 480p (video_url)

## pimpbunny.com

**Player mechanism**: Uses a `<video>` element with a direct MP4 URL via the `get_file` endpoint. URLs are session-tokenized with:
- A hash component in the path that changes per session
- A `?rnd=<timestamp>` parameter for cache busting
- Format: `https://pimpbunny.com/get_file/<quality_id>/<hash>/<video_path>/<filename>.mp4/?rnd=<timestamp>`

**Quality IDs**: `1` = 1080p (best), `39` = 720p, `38` = 480/360p

**Video URLs are in JSON-LD structured data, NOT in `<video>` elements**: The video `contentUrl` is embedded in a `<script type="application/ld+json">` tag. The `<video>` element's src is a blob URL (`blob:https://...`), not the direct URL. **Do NOT extract from the video element** — use JSON-LD.

**Direct URL does NOT work without cookies**: The `get_file` URL returns `image/gif` (1x1 tracking pixel) or HTTP 410 (Gone) when accessed without the session's cookies. You must forward the browser's cookies.

**UPDATED — Use video-downloader project's extractors package** (preferred):

The project at `/media/kubuntux/DEVELOPMENT1/video-downloader/` has a `backend/extractors/` package with a dedicated pimpbunny extractor:

```bash
cd /media/kubuntux/DEVELOPMENT1/video-downloader/backend && python3 -c "
import asyncio
from extractors import extract
result = asyncio.run(extract('https://pimpbunny.com/videos/.../'))
if result: print(result['url'])
"
```

This runs Puppeteer (Node service at port 3001) → parses JSON-LD → gets cookies → returns `{url, title, cookie_file, referer}`. Then download with curl using the cookie file:

```bash
curl -L -o "output.mp4" \
  -H "User-Agent: Mozilla/5.0 ..." \
  -H "Referer: <referer>" \
  -b "<cookie_file>" \
  "<video_url>"
```

**Puppeteer service setup** (one-time):
```bash
cd /media/kubuntux/DEVELOPMENT1/video-downloader/backend/node_service
npm install puppeteer@latest
# IMPORTANT: puppeteer-extra has broken package.json (missing dist/)
# Edit index.js to use require('puppeteer') instead of puppeteer-extra
node index.js  # starts on port 3001
```

**Manual fallback — browser console**:
1. Navigate to the video page with `browser_navigate`
2. Extract the contentUrl from JSON-LD:
   ```js
   const s = document.querySelector('script[type="application/ld+json"]');
   JSON.parse(s.textContent).contentUrl
   ```
3. Get cookies — this is blocked in Hermes browser_console, so use the extractors package (above) or Puppeteer directly.

**curl direct download**:
```bash
curl -L -o "output.mp4" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  -H "Referer: https://pimpbunny.com/" \
  -b "PHPSESSID=...; __tad=..." \
  "https://pimpbunny.com/get_file/1/<hash>/581000/581977/581977.mp4/"
```

**CDN**: Videos final URL after redirect is from `st*.pimpbunny.com` via `remote_control.php`.

**URL expiry**: The `get_file` URL expires when the page is reloaded or after a few minutes. Old hash returns HTTP 410 (Gone). Always use a fresh extract from the current page session.

**Ad interference**: The page has ad overlays covering the video. The browser-based extraction (JSON-LD) doesn't need to interact with the player at all — so ads are irrelevant for extraction.
