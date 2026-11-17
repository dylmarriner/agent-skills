# url2video API Reference

Full-stack queue-based video downloader service.

**Location**: `/home/kubuntux/video-downloader/backend/url2video.py`
**Port**: 8800
**Output**: `/mnt/storage/videos/`
**Watch folder**: `/mnt/storage/videos/.queue/`

## Starting

```bash
cd /home/kubuntux/video-downloader/backend
uvicorn url2video:app --host 0.0.0.0 --port 8800
```

Deps: fastapi, uvicorn, yt-dlp (all installed in system Python).

## Configuration (env vars)

| Var | Default | Description |
|-----|---------|-------------|
| `OUTPUT_DIR` | `/mnt/storage/videos` | Download destination |
| `MAX_CONCURRENT` | `3` | Max parallel downloads |
| `MAX_RETRIES` | `2` | Retry attempts per job |
| `DEFAULT_QUALITY` | `1080p` | Default quality tier |
| `URL2VIDEO_PORT` | `8800` | HTTP listen port |

## Endpoints

### POST `/q` — Queue a single URL

Request:
```json
{"url": "https://example.com/video", "quality": "1080p"}
```

Response (new):
```json
{"id": "abc123def456", "url": "...", "quality": "1080p", "status": "queued"}
```

Response (duplicate):
```json
{"id": "abc123def456", "url": "...", "status": "queued", "duplicate": true}
```

Jobs are deduplicated by URL — only one pending/active job per URL.

### POST `/q/bulk` — Queue multiple URLs

Request:
```json
{"urls": ["url1", "url2"], "quality": "1080p"}
```

Response:
```json
{"queued": 2, "duplicates": 0, "jobs": [...]}
```

### GET `/q` — Queue stats

Response:
```json
{"queued": 3, "downloading": 1, "complete": 15, "failed": 2, "active": [...]}
```

### GET `/q/jobs?limit=50` — Recent jobs

Returns jobs ordered by created_at DESC, latest first. Each has: id, url, quality, status, filename, error, retries, source, created_at, started_at, finished_at, progress, speed, eta.

### POST `/q/retry/{job_id}` — Retry single job

Resets status to queued, retries=0, clears error.

### POST `/q/retry-failed` — Retry all failed jobs

Returns: `{"retried": N}`

### DELETE `/q/{job_id}` — Cancel queued job

Only works on `queued` status jobs. Returns: `{"id": "...", "status": "cancelled"}`

### GET `/health` — Health check

Returns: `{"status": "ok", "queued": N, "downloading": N, "complete": N, "failed": N}`

## Watch folder

Drop `.txt` files into `/mnt/storage/videos/.queue/`. Format:

```
https://example.com/video1
https://example.com/video2 720p
# comment lines are ignored
```

Processed files move to `.queue/processed/{name}_{unix}.txt`.

## Queue behaviour

- Jobs are processed FIFO (oldest queued first)
- Max 3 concurrent downloads (MAX_CONCURRENT)
- Failed jobs retry up to 2 times (MAX_RETRIES)
- Each attempt tries direct first, then with proxy
- Stale "downloading" jobs reset to "queued" on service restart
- SQLite DB lives at `/mnt/storage/videos/.url2video.db`

## Browser bypass

Uses `browser_bypass.py` from the video-downloader/backend directory. Does NOT depend on the node_service (port 3001). Acts as a fallback — if bypass fails, download proceeds without it.

## curl example

```bash
# Queue and forget
curl -s -X POST http://localhost:8800/q \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com/video"}' | jq .

# Then check status
curl -s http://localhost:8800/q | jq .
```

## Supporting services (not required by url2video)

- `backend/main.py` — FastAPI on port 8000, SSE-based /api/download
- `backend/node_service/index.js` — Puppeteer on port 3001, /sniff-video + /extract-cookies

## Recovery: service hangs / unresponsive

url2video can hang under load: port 8800 stays open but HTTP requests timeout (exit code 56). Symptoms: high CPU (30%+), `ps aux` shows python3 active, health endpoint returns nothing.

**Fast recovery:**
```bash
# 1. Kill the hung processes
kill -9 $(pgrep -f url2video.py)

# 2. Verify port is free
ss -tlnp | grep 8800 || echo "port clear"

# 3. Restart in background
cd /home/kubuntux/video-downloader/backend && python3 url2video.py
```

**No data loss:** The SQLite DB persists across restarts. Stale `downloading` status jobs auto-reset to `queued` on service restart. Cross-site dedup also needs to be re-run if it was mid-execution (the python process gets killed).
