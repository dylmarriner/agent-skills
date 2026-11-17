---
name: video-downloader-async
description: Build and operate async video downloader services that download from adult sites (pornhub, pimpbunny, borntobefuck, youporn, xhamster, xnxx, redtube, spankbang, eporner, porntn) to a local/SMB folder. Triggers on "video downloader", "url2video", "build a downloader", "fix hanging download service", "extract video URL", "bypass Cloudflare for video sites", "download to SMB share". Covers the full async architecture (FastAPI + background workers, never block HTTP), per-site extractor chain, Puppeteer-as-Cloudflare-bypass, viewkey dedup, and the aria2c → yt-dlp download strategy chain.
---

# Async Video Downloader Service

**Class of work:** Build/operate a FastAPI-based queue service that accepts video URLs via HTTP and downloads them to a local or SMB-mounted folder, surviving Cloudflare, anti-bot, and broken extractor/extractor combination patterns.

**When to use this skill:** Any time the user wants to:
- Build/fix a video downloader service
- Stop an existing downloader from hanging the HTTP handler
- Add support for a new video site
- Bypass Cloudflare on video sites (pornhub, spankbang, etc.)
- Move downloads from local disk to SMB share
- Fix a downloader that gets stuck on one site

---

## Architecture: The 3 rules

1. **HTTP handler must NEVER block.** Downloads run in background threads. The POST /q endpoint should return in <100ms even if the download takes 10 minutes. If the user says "the service hangs when I queue a URL" — this rule is being violated.
2. **Extractor chain, not single extractor.** Each site has a per-site strategy chain (Puppeteer → yt-dlp → cookies+curl → curl) that tries the fastest/most-reliable strategy first and falls through on failure. Never trust one extractor.
3. **Viewkey/ID dedup before extraction.** For pornhub, extract the viewkey from the URL and check if any existing file on disk contains it. This is an O(1) check via `os.listdir` and kills ~70% of duplicate queues instantly. Built-in dedup is non-negotiable for any service that queues crawled URLs.

## Service structure (one-file or split)

```python
# url2video.py — single-file FastAPI service
- DB: SQLite at OUTPUT_DIR/.url2video.db (WAL mode)
- MAX_CONCURRENT workers (default 4)
- Worker is a daemon thread polling every 2s for queued jobs
- Each job runs in its own daemon thread → worker doesn't block
```

**Pitfall:** Do NOT use FastAPI's async def for the /q endpoint and then call blocking yt-dlp inside it. Use `def` (sync) endpoint, or use BackgroundTasks. The original hang was because the async endpoint awaited a sync yt-dlp call that blocked the event loop.

**Pitfall:** Do NOT use `sqlite3.connect(...)` with `check_same_thread=False` and share the same connection across threads without a lock. The Worker class opens its own connection per operation; FastAPI handlers also open their own. This is intentional and avoids the WAL-busy timeout pain.

## Per-site extractor strategy

```python
SITE_STRATEGIES = {
    "pornhub":      [yt-dlp+impersonate, puppeteer, yt-dlp],     # --impersonate chrome bypasses 474
    "borntobefuck": [puppeteer-click-hls, yt-dlp],              # Puppeteer: iframe click → HLS stream
    "pimpbunny":    [extractors-package, yt-dlp, puppeteer+curl], # extractors/ package → JSON-LD → cookies+curl
    "youporn":      [yt-dlp],                                   # CDN URL works directly
    "xhamster":     [yt-dlp],                                   # CDN URL works directly
    "xnxx":         [yt-dlp, cookies+curl, puppeteer],          # CF protected
    "redtube":      [yt-dlp, cookies+curl, puppeteer],          # CF protected
    "spankbang":    [yt-dlp, cookies+curl, puppeteer],          # CF protected
    "eporner":      [yt-dlp, yt-dlp+impersonate],               # Direct yt-dlp works; --impersonate also valid
    "porntn":       [yt-dlp, cookies+curl, puppeteer],          # CF protected
}
```

### extractors/ package (new project structure)

The VideoSnap project now has a modular `backend/extractors/` Python package with a `@register` decorator pattern:

```python
# backend/extractors/__init__.py
_REGISTRY = {}

def register(pattern: str):
    """Decorator: register an extractor for sites matching regex `pattern`."""
    def wrapper(func):
        _REGISTRY[pattern] = func
        return func
    return wrapper

async def extract(url: str) -> dict | None:
    """Dispatch URL to the first matching registered extractor."""
    for pattern, func in _REGISTRY.items():
        if re.search(pattern, url, re.IGNORECASE):
            result = await func(url)
            if result:
                return result
    # fallback: yt-dlp
    ...
```

Each extractor is an `async` function that returns `{url, title, ext, source, cookie_file?, referer?}` or `None`. Add new sites by creating a new `@register(r"sitename\.com")` function.

### pimpbunny: Puppeteer → JSON-LD → cookies+curl (confirmed working)

**As of 2026-07-08, pimpbunny extraction is CONFIRMED WORKING.** Successfully downloaded a 104MB, 15-minute video through this chain:

1. **Puppeteer service** (`/extract-page` endpoint) loads the page with full JS execution
2. The JSON-LD script block (`<script type="application/ld+json">`) contains the `contentUrl` field with the direct video path
3. Puppeteer returns the cookies from the session
4. Download via curl with the extracted cookies + `Referer: https://pimpbunny.com/...` header

The video URL follows the pattern:
```
https://pimpbunny.com/get_file/<num>/<hash>/<id>/<id>_720p.mp4/
```

**Important**: The URL hash is session-tied and expires. A fresh extraction is needed for each download attempt. The direct URL returns a 1x1 GIF (anti-hotlink) without the correct cookies and Referer.

**The extractors/ package handles this automatically** — just call `await extract(url)` and it returns the URL with cookie_file and referer. Then use curl to download:
```bash
curl -L -o output.mp4 \
  -H "User-Agent: ..." \
  -H "Referer: <page_url>" \
  -b <cookie_file> \
  <video_url>
```

### yt-dlp+impersonate strategy (pornhub 474 bypass)

Pornhub returns HTTP 474 (custom anti-bot code) to stock yt-dlp requests. The `--impersonate chrome` flag uses curl_cffi to mimic Chrome's TLS fingerprint — this bypasses the 474 entirely and downloads directly. No Puppeteer, no cookie extraction, no browser overhead.

CLI usage:
```bash
~/.local/bin/yt-dlp --impersonate chrome --format "bestvideo[height<=1080]+bestaudio/best[height<=1080]" \
  --merge-output-format mp4 --output "/path/%(title)s [%(id)s].%(ext)s" \
  "https://www.pornhub.com/view_video.php?viewkey=..."
```

Python (yt-dlp library) usage — add to ydl_opts:
```python
ydl_opts = {
    "impersonate": True,  # enables curl_cffi impersonation
}
```

**Prerequisite:** `curl_cffi` must be installed. Check with `python3 -c "import curl_cffi; print('ok')"`. yt-dlp stable@2026.06.09 includes this support.

### The "cookies+curl" pattern (Cloudflare bypass without yt-dlp)

For sites where yt-dlp fails (Cloudflare challenge, 403, etc.):
1. POST to node_service `/extract-cookies` with the URL → returns cookies + User-Agent
2. Use curl with `-H "Cookie: <name>=<val>; ..."` and the returned UA
3. Parse the resulting HTML for `<meta og:video>`, `<source>`, or regex over `<script>` blocks

This is faster and more reliable than letting yt-dlp try its own CF handling. The node_service is a Puppeteer-stealth service at port 3001.

### Custom 2-step pattern (player/embed iframe → video URL)

Many sites put the actual video in a nested player/embed page. Pattern:
1. Fetch main page → extract `<iframe src=".../player/123\">` or `.../embed/123`
2. Fetch the iframe URL with `Referer: <main page URL>` header
3. Parse the player HTML for direct video URL (`.mp4`, `.m3u8`, or CDN URL)

### borntobefuck: Puppeteer → iframe click → HLS stream capture (confirmed working)

**As of 2026-07-08, borntobefuck extraction is CONFIRMED WORKING** via a multi-step Puppeteer pipeline. Successfully downloaded two videos (296MB Lana Rhoades, 192MB Wettmelons).

**The site is ad-gated:** The video is hidden behind an "Unlock the video" overlay. The actual video plays inside an iframe (`/videos/<id>/player?lang=en`) using a **canvas-based player** — no `<video>` element exists in the DOM even after playback. However, the underlying HLS stream URL is visible via Puppeteer network interception.

**Extraction steps:**

1. Navigate to `/watch/<id>` with Puppeteer
2. Enable network interception, filter for `.m3u8` + `zavastream`
3. Click Play inside the iframe:
   ```javascript
   const iframe = document.querySelector('iframe');
   const doc = iframe.contentDocument || iframe.contentWindow.document;
   doc.querySelector('button')?.click();
   ```
4. Wait 8s for the HLS manifest to load
5. Collect the `index.m3u8` URL:
   ```
   https://content.zavastream.com/<numeric>/<uuid>/index.m3u8
   ```
6. Download with yt-dlp:
   ```bash
   yt-dlp --impersonate chrome --output "filename.mp4" \
     --referer "https://borntobefuck.com/" \
     --add-header "Origin:https://borntobefuck.com" \
     "https://content.zavastream.com/.../index.m3u8"
   ```

**Key details:**
- The HLS CDN (`content.zavastream.com`) accepts yt-dlp with `--impersonate chrome` + referer
- Stream is delivered in ~180-280 fragments; yt-dlp auto-fixes MPEG-TS in MP4
- HLS URL is session-tied — must re-extract per download (fresh Puppeteer session each time)
- Available: 720p and 480p; yt-dlp picks best automatically
- File sizes observed: ~99-296MB for 9-28 minute videos at 720p
- **Filename issue:** Raw HLS URLs have no title metadata, so yt-dlp saves as `index [btbf-ID].mp4`. After download, look up the title from the page (web_extract on /watch/ID) and rename. The BTBF page title comes cleanly — just strip trailing "Porn Video" or site suffix.

**Note on content filtering:** Many borntobefuck videos carry `#BWC`, `#Interracial`, or `#BBC` tags. Per user preferences, block unless explicitly requested by URL. When user pastes directly, their explicit request overrides filtering.

### Node service: restart pattern

The Node Puppeteer service at port 3001 can die for various reasons (port conflict on restart, process killed). When restarting:

```bash
# Kill anything on port 3001 FIRST, then start
fuser -k 3001/tcp 2>/dev/null
sleep 1
cd /path/to/node_service && node index.js &
```

Without the `fuser -k`, a stale process causes `EADDRINUSE: address already in use :::3001` even though `ps` shows nothing — the kernel may still hold the port during TIME_WAIT.

### Puppeteer script file pattern (not inline -e)

When writing Puppeteer scripts, **write them to a temp file first**, then run with `node /tmp/script.js`. Do NOT use inline `node -e "..."` because:

1. Template literals with `${}` inside the string get interpreted by the shell before Node sees them
2. The `$$` shorthand (`page.$$(...)`) is interpreted as a shell variable reference
3. Escape sequences and nested quotes become unmanageable

**Correct pattern:**
```javascript
// Write to /tmp/extract.js first
write_file(path="/tmp/extract.js", content="...")
// Then run
terminal(command="cd /path/to/node_service && node /tmp/extract.js", ...)
```

**Pitfall -- NODE_PATH:** When the script file is in `/tmp/` and `puppeteer` is installed in `node_service/node_modules/`, the script can't find the module unless `NODE_PATH` points to the right `node_modules`:
```bash
NODE_PATH=/path/to/node_service/node_modules node /tmp/script.js
```
Without this, Node resolves from `/tmp/node_modules/` (doesn't exist) instead of the project's `node_modules/`. Set `NODE_PATH` explicitly when running scripts from outside the project directory, or run the script from within the project directory (via `cd`).

**Verification pattern (cookie extraction for pimpbunny-type sites):**
The verify-success pattern for Puppeteer extraction scripts is to print `===`-delimited sections:
1. `VIDEO_URL: <url>` — the extracted direct URL
2. `COOKIES: <cookie-string>` — the session cookies
3. If the URL is found, pipe it through `curl -sI` to check for `HTTP/2 200` with `content-type: video/mp4` (success) vs `image/gif` or `410 Gone` (expired/blocked)

**Pitfall:** NEVER name a local module `queue.py`. Python's stdlib `queue` module is imported by `urllib3` (which `yt-dlp` depends on). A local `queue.py` shadows the stdlib version, and urllib3's `queue.LifoQueue` resolves to your local module instead — causing `AttributeError: partially initialized module 'queue' has no attribute 'LifoQueue'` (circular import). Rename it to `download_queue.py` or `job_queue.py` and update all imports.

**Pitfall:** Don't use a variable name `html` in a function that also imports the `html` module. `html = r.stdout` shadows the module, and later `html.unescape(...)` fails with `'str' object has no attribute 'unescape'`. Use `page` instead.

**Pitfall:** When parsing borntobefuck/pimpbunny player pages, you will see BOTH video URLs AND preview-thumbnail URLs (`preview_360p.mp4.jpg`, `screenshots/...`). Filter them out by:
- Skipping URLs containing `preview` or `screenshots`
- For pimpbunny: only accept `pimpbunny.com/get_file/...` paths (preview thumbs live under `pimpbunny.com/contents/videos_screenshots/...`)

## Download strategy chain

After extraction, three strategies in order:
1. **aria2c** for direct .mp4/.webm URLs — 16 connections, 10M chunks, fastest
2. **yt-dlp** for HLS (.m3u8), DASH (.mpd), or any complex manifest
3. (No third — if both fail, mark as failed)

```python
# aria2c command
aria2c -x 16 -s 16 -k 10M --max-tries=2 --retry-wait=1 -o <fname> <url>
# Run with cwd=OUTPUT_DIR so files land in the right place
```

**Pitfall:** aria2c's `-o` is relative to cwd, not to any other base. Always `cwd=output_dir`.

**Pitfall:** yt-dlp may create the file with a different extension than you specified (e.g. `.mkv` when you asked for `.mp4`). After the run, scan OUTPUT_DIR for any file whose name starts with the sanitized title and rename it to the expected name. The new service's `download_video` function does this.

## User quality preference (Dylan)

**Default quality: 1080p max, never "best" unless explicitly overridden.**

- `--quality 1080p` is the preferred default for all downloads. Both `videosnap` CLI flags were patched to default to `"1080p"` (2026-07-10).
- The format string `bestvideo[height<=1080]+bestaudio/best[height<=1080]` caps resolution at 1080p while selecting the best available audio track.
- This is a strict user preference — do not default to `best` (unlimited/unbounded resolution) unless the user explicitly says `--quality best`.
- See `references/user-quality-preferences.md` for session history.

## Filename strategy

```python
def sanitize(title):
    title = re.sub(r'[<>:"/\\|?*]', '_', title)  # filesystem-safe
    title = re.sub(r'\s+', ' ', title).strip()[:120]
    return title or "video"

filename = f"{sanitize(title)} [{abs(hash(video_url)) % 100000}].mp4"
```

The hash suffix prevents name collisions when the same title appears twice (e.g. cross-site dupes). 5 digits is enough entropy for typical queues.

## SQLite schema (minimal but complete)

```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    quality TEXT NOT NULL DEFAULT '1080p',
    status TEXT NOT NULL DEFAULT 'queued',  -- queued, downloading, complete, failed, cancelled
    title TEXT,
    filename TEXT,
    size_mb REAL,
    strategy TEXT,                          -- e.g. "yt-dlp+aria2c" or "curl+yt-dlp"
    site TEXT,                              -- detected site
    error TEXT,
    retries INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'api',      -- 'api' or 'watch_folder'
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT
);
CREATE UNIQUE INDEX idx_jobs_url_pending
    ON jobs(url) WHERE status IN ('queued','downloading');
```

The partial unique index prevents the same URL being queued twice while still allowing re-queueing of previously-completed URLs.

## viewkey dedup (the killer feature)

```python
def viewkey(url):
    m = re.search(r'viewkey=([a-f0-9]+)', url)
    return m.group(1) if m else None

def has_viewkey(vk):
    if not vk: return False
    for f in os.listdir(OUTDIR):
        if f.endswith(".mp4") and vk in f: return True
    return False
```

Call this BEFORE extraction. Cancels ~50-70% of duplicates in a typical crawl-fed queue, instantly, no network. Mark the job as `cancelled` with `error='viewkey dupe'` so it shows in the dedup report.

## Puppeteer Node v22 compatibility

As of 2026-07-08, Puppeteer packages on Node v22.22.0 have these trapdoors:

**Problem 1: `puppeteer-extra@3.3.6`** — The `dist/` directory is missing (package was installed from source and never built). Error: `Cannot find module 'dist/index.cjs.js'`.

**Fix:** Replace with plain `puppeteer`:
```javascript
// Instead of:
// const puppeteer = require('puppeteer-extra');
// const StealthPlugin = require('puppeteer-extra-plugin-stealth');
// puppeteer.use(StealthPlugin());
//
// Use:
const puppeteer = require('puppeteer');
```
The stealth plugin is nice but not essential. Manual UA + viewport + `navigator.webdriver` override covers most sites.

**Problem 2: `proxy-agent` package** — The older `proxy-agent` in the dependency tree has a missing `"main"` entry in its `package.json`. Error: `Cannot find module 'proxy-agent/dist/index.js'`.

**Fix:** Reinstall puppeteer at the latest version:
```bash
cd /path/to/node_service && npm install puppeteer@latest
```
Latest puppeteer (>v23) pulls in a compatible proxy-agent.

**If Puppeteer can't be fixed:** The Hermes browser tool can load the page but its security sandbox blocks `document.cookie`, `fetch()`, `XMLHttpRequest`, and `PerformanceObserver` from console expressions. This means blob-URL video sources (pimpbunny, etc.) can't be extracted through the browser tool's console. The `@register` extractor pattern using `browser_bypass.extract_page()` is the correct fix — it uses Puppeteer directly, not the Hermes browser sandbox.

### Node service endpoints

The Puppeteer service at port 3001 now provides two endpoints:

- **`POST /extract-cookies`** `{url, proxy?}` → `{cookies[], headers, success}`
  - Loads the URL, waits for network idle + 2.5s settle, returns cookies
  - Used by `BrowserBypass.get_context()`

- **`POST /extract-page`** `{url, proxy?}` → `{html, cookies[], headers, success, url}`
  - Loads the URL, waits for network idle + 3s settle, then waits up to 8s for `contentUrl`, `get_file`, or `<video>` elements to appear
  - Returns the full page HTML (after JS execution), cookies, and final URL
  - Used by `BrowserBypass.extract_page()`

Starting the service:
```bash
cd /path/to/node_service && node index.js
# Listens on http://localhost:3001
```

## Dependencies

- `fastapi`, `uvicorn` — HTTP server
- `httpx` — async HTTP for node_service calls
- `yt-dlp` — fallback extractor + manifest downloader
- `aria2c` — fast direct downloader
- `ffmpeg` — HLS merge fallback (not usually needed if yt-dlp handles it)
- `node_service` (Puppeteer-stealth) on port 3001 for Cloudflare bypass
- `curl` for HTML scraping — available everywhere, fast, no Python dep

## File locations (kubuntux)

- **VideoSnap project (new):** `/media/kubuntux/DEVELOPMENT1/video-downloader/`
  - `backend/extractors/` — modular extractor package with @register decorator (one file per site group)
  - `backend/extractors/__init__.py` — registry + dispatcher + pimpbunny extractor
  - `backend/downloader.py` — yt-dlp wrapper with custom extractor chain integration
  - `backend/download_queue.py` — SQLite-backed download queue (renamed from queue.py to avoid stdlib clash)
  - `backend/browser_bypass.py` — Puppeteer service client with get_context() + extract_page()
  - `backend/cli.py` — `videosnap` CLI (dl, queue, serve commands)
  - `backend/main.py` — FastAPI app
  - `backend/node_service/index.js` — Puppeteer-stealth microservice on port 3001
  - `backend/universal_downloader.py` — single-function download for all sites
- **Old service:** `/home/kubuntux/video-downloader/new-backend/url2video.py` (port 8800, single-file FastAPI)
- **Output dir:** `/mnt/storage/videos` (SMB share `\\\\kubuntux\\videos`)
- **DB:** `<output>/.url2video.db`
- **yt-dlp:** `/home/kubuntux/.local/bin/yt-dlp`
- **smb.conf:** `[videos]` share at `/mnt/storage/videos`, `valid users = kubuntux`, not guest

## API endpoints

- `POST /q` `{url, quality?}` → `{id, status}` (returns <100ms)
- `GET /health` → `{queued, downloading, complete, failed, mp4s, active[]}`
- `GET /status/{id}` → full job row
- `POST /node/start` → start node_service if not running

## Verification

1. `python3 -c "import py_compile; py_compile.compile('url2video.py', doraise=True)"` — syntax check
2. `curl -s http://localhost:8800/health` — service responds
3. POST a known-good URL → wait 30s → check `mp4s` count incremented
4. `sqlite3 .url2video.db "SELECT status, COUNT(*) FROM jobs GROUP BY status"` — pipeline flow

## One-off downloads via Hermes background terminal

For ad-hoc downloads (user pastes a single URL mid-conversation without url2video running), use Hermes's built-in background process management rather than nohup/tmux/shell `&`:

```python
# From terminal tool (NOT shell):
terminal(
    command="~/.local/bin/yt-dlp --impersonate chrome --format ...",
    background=True,
    notify_on_complete=True,   # flags you when it exits
    timeout=600,
)
```

**Pattern:** Each call spawns one independent yt-dlp process. Kick off multiple URLs concurrently — each gets its own session_id. Track progress with `process(action='poll', session_id='...')`.

**Rules:**
- Do NOT use nohup/setsid/trailing `&` — Hermes rejects these with `"Foreground command uses shell-level background wrappers"`. Always use `background=True`.
- Do NOT use `notify_on_complete=False` for bounded downloads — without it you have no way to learn the job finished short of remembering to poll manually. Silent-only makes sense for long-lived daemons (servers, watchers), not downloads.
- Poll progress with `process(action='poll', session_id='...')` to see mid-job progress lines.
- Kicking off 3+ concurrent yt-dlp processes is fine on this machine (12-core, 32GB RAM) but watch for disk/network contention.

**Resuming partials:** If a download is interrupted (output truncated, session ended), yt-dlp leaves `.part` files. Re-running the same URL with the same `--output` template resumes from existing fragments — no special flags needed.

## Support files in this skill

- `templates/extractors.py` — Drop-in copy of all five extractor strategies (yt-dlp, Puppeteer, cookies+curl, two-step, generic curl). Each function is self-contained and returns a `{title, url, ext}` dict or raises. Includes a site-specific dispatch chain. Customize the `CHAINS` dict for new sites.
- `references/session-log-2026-06-30.md` — Full session notes: what we built, the exact bug fixes (`html = r.stdout` shadow, SQLite multi-PRAGMA error, PhantomJS wall on yt-dlp 2026.06.09), and the final verification commands. Read this first if you're extending the kubuntux `url2video.py` instance.
- `references/session-log-2026-07-08.md` — Pornhub 474 bypass via `--impersonate chrome`, queue.py circular import fix, SMB share verification.
- `references/session-log-2026-07-08b.md` — VideoSnap project restructure (extractors/ package), pimpbunny Puppeteer+JSON-LD+curl extraction pipeline, puppeteer-extra build fix.
- `references/pimpbunny-puppeteer-node22.md` — Pimpbunny blob-URL extraction failure, Puppeteer Node v22 dependency break, workarounds.
- `references/session-log-2026-07-08d.md` — borntobefuck cracked via Puppeteer iframe click + HLS capture, 12-video batch, NODE_PATH pitfall.
- `references/user-quality-preferences.md` — User's quality preference history (1080p default, 2026-07-10).
