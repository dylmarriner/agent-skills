# url2video Operations

The user's custom video-downloader service. Handles queue persistence (SQLite), 10 concurrent downloads, CDN URL extraction, 1080p cap, retries. Lives at `~/video-downloader/backend/url2video.py` (port 8800).

## Always prefer url2video over custom yt-dlp scripts

Reasons:
- Has built-in CDN URL extraction (3-5x faster than direct page-URL downloads)
- Queue is durable (SQLite WAL mode)
- Resumes after restart — never loses state
- Concurrent worker pool with proper semaphore (avoids rate limiting)
- Per-site retry strategies with proxy fallback (currently disabled per user)

## Starting the service

```bash
cd ~/video/kubuntux/video-downloader/backend && python3 -u url2video.py > /tmp/url2video.log 2>&1 &
```

**Always redirect to a file.** Without redirect, stdout goes to a pipe and you cannot see what it's doing. The pipe is the most common debugging failure mode.

The service is ready when the log shows:
```
INFO url2video ready on :8800
INFO   Output:  /mnt/storage/videos
INFO   Watch:   /mnt/storage/videos/.queue
INFO   API:     POST http://localhost:8800/q
INFO   Quality: 1080p  |  Workers: 10
```

## Feeding URLs

Two ways:

### Watch folder (preferred for batch crawls)
Drop a `.txt` file with ONE URL per line into `/mnt/storage/videos/.queue/`. The file must be **bare URLs only**, not `performer|site|url` format. After processing, it moves to `/mnt/storage/videos/.queue/processed/`.

```bash
awk -F'|' '{print $NF}' /tmp/video_queue_final.txt > /mnt/storage/videos/.queue/batch.txt
```

### HTTP API
```bash
curl -X POST http://localhost:8800/q \
  -H "Content-Type: application/json" \
  -d '{"url": "https://...", "quality": "1080p"}'
```

## Monitoring

```bash
# Health snapshot (quick — queued, downloading, complete, failed, active)
curl -s http://localhost:8800/health
# Returns: {"status":"ok","queued":526,"downloading":4,"complete":3,"failed":21,
#           "active":[{"id":"...","url":"...","progress":0.0,"speed":null,"eta":null}]}

# Queue status (more detail)
curl -s http://localhost:8800/q

# Active downloads
curl -s http://localhost:8800/q | python3 -c "import sys,json;[print(f'{a[\"progress\"]:.0f}% {a[\"url\"][:60]}') for a in json.load(sys.stdin)['active']]"

# Direct DB query (most reliable when API is wedged)
python3 -c "
import sqlite3
c = sqlite3.connect('/mnt/storage/videos/.url2video.db')
print(dict(c.execute('SELECT status, COUNT(*) FROM jobs GROUP BY status').fetchall()))
"```
```

## Common failure modes

### 1. FastAPI `on_startup` crash (silent)

Current FastAPI (0.110+) doesn't accept the `on_startup=[...]` parameter that older versions did. The port binds, the process is alive, but no endpoints work. Symptom: `curl http://localhost:8800/q` returns `{"detail":"Not Found"}`.

**Fix:** Edit `url2video.py` line ~309:
```python
# OLD (broken):
app = FastAPI(title="url2video", version="1.0.0", on_startup=[init_lifespan])

# NEW (correct):
app = FastAPI(title="url2video", version="1.0.0", lifespan=lifespan)
```
Where `lifespan` is the `@asynccontextmanager` function defined above. The user's install already uses the lifespan pattern; this only bites when starting from a different working tree.

### 2. Wedged on a single job (infinite retry loop)

Symptom: log shows the same job ID 10-20 times in 1 second, all `Starting <id>: <url>`, no actual progress. DB says `downloading` but no yt-dlp child process exists.

**Fix (without killing the service):** Reset the wedged jobs directly in SQLite:
```python
import sqlite3
c = sqlite3.connect('/mnt/storage/videos/.url2video.db')
c.execute("UPDATE jobs SET status='failed', error='wedged' WHERE status='downloading'")
c.commit()
```

The worker picks the next queued job on its next loop iteration. Killing the parent process loses the lifespan reset (stale jobs are re-queued but worker pool dies).

### 3. Watch file not parsed

Symptom: file moves to `processed/` but DB queue count stays at 0. Most common cause: file has `performer|site|url` format instead of bare URLs. url2video expects ONE URL per line, no pipes.

**Verify:** `head -2 /mnt/storage/videos/.queue/batch.txt` should be just URLs.

### 4. Stale jobs from old DB

When you start url2video, the lifespan logs:
```
INFO Reset 4 stale downloading jobs to queued
```
If you see non-zero N, the previous instance died mid-download. If the DB has 130+ queued jobs from an old feed, url2video processes them all before your new batch.

**Fix:** Wipe the DB and restart:
```bash
rm -f /mnt/storage/videos/.url2video.db
# Restart service
```

### 5. `Output filename too long`

Symptom: download fails with `OSError: [Errno 36] File name too long` on certain titles.

**Fix:** Already handled by `%(title).120s` template in the downloader module. Don't change the format to allow longer titles — the filesystem limit is real.

## Clearing the queue

**There is NO `/q/clear` endpoint.** Options:
- Per-job delete: `curl -X DELETE http://localhost:8800/q/{job_id}`
- Wipe everything: `rm /mnt/storage/videos/.url2video.db` and restart

For "stop everything and start fresh", wiping the DB is faster than deleting 500+ jobs one at a time.

## Why url2video can be slower than expected

The service uses `yt-dlp` to extract the CDN URL, then downloads. Cloudflare protection on some sites means CDN URL extraction takes 30-60s, but the download itself runs at 5-12MB/s. Compare to direct page-URL downloads which:
- Go through the player wrapper, adding latency
- Cap at 1MB/s due to fragmented streaming

So **direct downloads appear faster initially** but **url2video is faster end-to-end** for full files. The trade-off is worth it.

## Configuration

Environment variables (set in `url2video.py`):
- `OUTPUT_DIR` (default: `/mnt/storage/videos`) — download destination
- `WATCH_DIR` (default: `$OUTPUT_DIR/.queue`) — watch folder
- `MAX_CONCURRENT` (default: 10) — parallel downloads
- `MAX_RETRIES` (default: 2) — retries per job
- `DEFAULT_QUALITY` (default: `1080p`) — quality cap
- `URL2VIDEO_PORT` (default: 8800) — listen port
