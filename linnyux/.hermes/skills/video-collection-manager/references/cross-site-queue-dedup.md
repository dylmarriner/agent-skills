# Cross-Site Queue Dedup (url2video SQLite)

## When to use
When the url2video service has pending jobs from multiple sites (pornhub, youporn, xhamster, etc.) and the same video may be queued from 2+ different sites. Also checks all queued URLs against already-downloaded MP4s on disk.

Run BEFORE starting a new batch download session to avoid re-downloading the same video.

## Method

The dedup uses a **two-phase hybrid** approach:

### Phase 1: Pornhub viewkey dedup (instant, no HTTP)
Pornhub blocks both curl (Cloudflare challenge, ~1459 byte page) and yt-dlp
(requires PhantomJS, not installed). Instead of failing on every PH URL:

1. Extract `viewkey` from each pornhub URL (e.g. `viewkey=69dc102d4c820`)
2. Check if any existing MP4 filename contains `[69dc102d4c820]`
3. If matched — cancel the queued URL (already downloaded)

This is O(n) string matching with zero network calls. Handles 300+ PH URLs
instantly.

### Phase 2: Non-pornhub title extraction + dedup
For youporn, xhamster, pimpbunny, borntobefuck, and other non-PH sites,
curl can fetch the HTML (full pages, 300-500KB). Title+duration is extracted
from `<title>`/`og:title` tags + `video:duration` metadata. Fallback is
`yt-dlp --dump-json` (15s) for exotic sites.

Three checks run:
1. **Disk match** — cancel if normalized title matches existing MP4 filename
2. **Cross-site dupe** — cancel extras when same title+duration from 2+ sites
3. **Same-site dupe** — cancel extras when identical title+duration same site

### 1. Count by site
```bash
sqlite3 /mnt/storage/videos/.url2video.db \
  "SELECT substr(url, 1, instr(substr(url, 9), '/')+7) AS site, COUNT(*) FROM jobs WHERE status IN ('queued','downloading') GROUP BY site"
```

### 2. Run the dedup script
Use the canonical script at `~/.hermes/skills/video-collection-manager/scripts/cross-site-dedup.py`.

```bash
cd ~/.hermes/skills/video-collection-manager/scripts && python3 cross-site-dedup.py
```

### What it does (in order)

1. **Loads existing MP4s from disk** (`/mnt/storage/videos/*.mp4`) — normalizes filenames to title keys
2. **Gets all queued/downloading URLs** from url2video's SQLite DB
3. **Extracts title + duration** from every URL using two strategies:
   - **Primary (fast):** `curl` with 8s timeout — fetches HTML head, extracts `<title>` / `og:title` + duration meta tags. Used for known sites: pornhub, youporn, xhamster, xnxx, redtube
   - **Fallback:** `yt-dlp --dump-json` (15s timeout) — for all other sites
4. **Disk MP4 check:** Cancels any queued URL whose normalized title matches an existing MP4 filename
5. **Cross-site dupe check:** Groups resolved URLs by `(normalized_title, duration_bucket)` — if the same title+duration appears from 2+ different sites, cancels the extras
6. **Same-site dupe check:** Same grouping logic within a single site (e.g. two identical pornhub URLs)
7. **Updates the queue file** (`/tmp/video_queue_deduped_final.txt`) if it exists

### Performance

| Metric | curl-all (old approach, buggy) | Hybrid viewkey+curl |
|--------|-------------------------------|---------------------|
| Pornhub URLs handled | 0 (all timed out) | Instant — viewkey match |
| Non-PH URLs | 85-95% resolved | 85-95% resolved |
| Phase 1 runtime | N/A | ~1-2s |
| Phase 2 runtime (27 non-PH URLs) | N/A | ~30-60s |
| Total runtime (390 URLs) | 2-4 min (with 0 PH resolved) | ~1-2 min |

### Why this approach
`yt-dlp --dump-json` downloads the full page, parses the embedded player data, negotiates CDN links, and resolves formats — all unnecessary for dedup where you only need the video title and duration. A simple curl HTML fetch with 8s timeout is:
- **Faster:** 100s of KB (HTML) vs MBs (full page + JS)
- **More reliable:** Dead URLs timeout in 8s instead of 30s
- **Lighter:** No yt-dlp Python overhead per worker

### Pitfalls
- **Pornhub curl always fails** — Don't send PH URLs through curl. The Cloudflare challenge returns a 1459-byte page with no real content. Use viewkey matching instead.
- **Only clean_downloader.py saves viewkey** — url2video's downloader.py uses `%(title).100s.%(ext)s` (no `[id]`). Viewkey matching only works for MP4s downloaded by clean_downloader or parallel scripts.
- **Dead URLs** — curl silently times out; unresolvable URLs are kept as-is in the queue. Run a second pass if needed.

## Hang recovery — direct DB insert

When url2video's HTTP API is hung (port LISTEN but all requests time out with exit code 56), you can still add URLs directly to the SQLite DB:

```bash
sqlite3 /mnt/storage/videos/.url2video.db "
INSERT OR IGNORE INTO jobs (id, url, quality, status, source, created_at)
VALUES ('$(uuidgen | tr -d -)', 'https://example.com/video', '1080p', 'queued', 'api', datetime('now'));
"
```

For batch inserts:
```bash
sqlite3 /mnt/storage/videos/.url2video.db "
INSERT OR IGNORE INTO jobs (id, url, quality, status, source, created_at)
VALUES
  ('id1', 'url1', '1080p', 'queued', 'api', datetime('now')),
  ('id2', 'url2', '1080p', 'queued', 'api', datetime('now'));
"
```
