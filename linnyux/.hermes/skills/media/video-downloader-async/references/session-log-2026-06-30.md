# url2video next-gen — session log

## What we built (June 30, 2026)

Replaced the old `url2video.py` (which kept hanging the HTTP handler because it ran `yt-dlp` synchronously inside the FastAPI request thread) with a new single-file service at:

`/home/kubuntux/video-downloader/new-backend/url2video.py`

**Architecture:**
- FastAPI (sync `def` endpoints, NOT async — avoids event loop blocking)
- SQLite DB at `/mnt/storage/videos/.url2video.db` (WAL mode, partial unique index for dedup)
- Single `Worker` class with a daemon thread polling every 2s for queued jobs
- Each job runs in its own daemon thread → no job can block the worker loop
- `MAX_CONCURRENT = 4` (configurable via env)

**Node service:** `/home/kubuntux/video-downloader/backend/node_service/index.js` on port 3001 (Puppeteer-stealth, Chromium). Started as separate background process.

**Output:** `/mnt/storage/videos` (SMB share `\\kubuntux\videos`, 368GB used, 712 MP4s)

## Per-site extractor chains (in priority order)

| Site | Chain |
|------|-------|
| pornhub | Puppeteer → yt-dlp (CF bypass) |
| borntobefuck | Custom 2-step (player iframe → m3u8) → yt-dlp |
| pimpbunny | Custom 2-step (embed iframe → direct .mp4) → yt-dlp |
| youporn, xhamster | yt-dlp (CDN URL works directly) |
| xnxx, redtube, spankbang, eporner, porntn | yt-dlp → cookies+curl → Puppeteer |

## Key techniques that emerged

### 1. The "cookies+curl" Cloudflare bypass
Pornhub, xnxx, spankbang, eporner, porntn, redtube all have Cloudflare or anti-bot that blocks raw curl and even yt-dlp in some cases. The pattern that works:

1. `POST /extract-cookies` to node_service → returns Puppeteer-fetched cookies + UA
2. `curl` the page with `-H "Cookie: <name>=<val>; ..."` and the returned UA
3. Parse HTML for og:video, <source>, or .mp4/.m3u8 URLs

This is faster than letting yt-dlp try its own CF handling, and works on sites where yt-dlp fails outright.

### 2. Custom 2-step extractor (borntobefuck / pimpbunny)
Both sites put the actual video in a nested player/embed page:
- borntobefuck: main page → `/videos/N/player` iframe → fetch player with Referer → `.m3u8` URL (often from `content.zavastream.com`)
- pimpbunny: main page → `/embed/N` iframe → fetch embed → direct `.mp4` from `pimpbunny.com/get_file/...`

**Filter pitfall:** pimpbunny embed pages contain BOTH video URLs AND preview thumbnails. Filter out URLs containing `preview` or `screenshots`; only accept `pimpbunny.com/get_file/...` paths.

### 3. Viewkey dedup (the killer feature)
For pornhub URLs, extract the viewkey from the URL and check if any existing MP4 filename contains it:

```python
def viewkey(url):
    m = re.search(r'viewkey=([a-f0-9]+)', url)
    return m.group(1) if m else None

def has_viewkey(vk, outdir):
    for f in os.listdir(outdir):
        if f.endswith(".mp4") and vk in f:
            return True
    return False
```

Cancelled **70 pornhub URLs** instantly in a single 116s run, no network calls. Mark as `cancelled` with `error='viewkey dupe'` so it shows in reports.

### 4. Filename strategy
```python
filename = f"{sanitize(title)} [{abs(hash(video_url)) % 100000}].mp4"
```
Hash suffix prevents collisions when cross-site dupes have identical titles.

## Bugs hit and fixes

### `html = r.stdout` shadows the `html` module
First version of `_extract_curl` did:
```python
html = r.stdout
title = html.unescape(...)  # FAILED — str has no .unescape
```
Fixed by renaming to `page = r.stdout`. Lesson: don't name a local var the same as a stdlib module.

### SQLite `PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000`
Can't run two PRAGMA statements in a single `execute()`. Split into two calls.

### yt-dlp 2026.06.09 requires PhantomJS for pornhub
Latest yt-dlp now requires PhantomJS binary for pornhub extraction — and `apt install phantomjs` doesn't work on modern Ubuntu. Workaround: use Puppeteer for pornhub (which already bypasses CF and can sniff the real video URL from network traffic).

### aria2c `-o` is relative to cwd
Not relative to any other base. Always `cwd=output_dir` when invoking.

## Verification commands

```bash
# Syntax check
python3 -c "import py_compile; py_compile.compile('url2video.py', doraise=True)"

# Service health
curl -s http://localhost:8800/health

# DB state
sqlite3 /mnt/storage/videos/.url2video.db "SELECT status, COUNT(*) FROM jobs GROUP BY status"

# Force restart
kill $(lsof -ti :8800 2>/dev/null)
cd /home/kubuntux/video-downloader/new-backend && python3 url2video.py &
```

## Final state at session end
- 237 queued, 4 downloading, 11 complete, 712 MP4s, 368GB
- 4 worker slots, all using the new async architecture
- HTTP handler stays responsive even when downloads are mid-flight
