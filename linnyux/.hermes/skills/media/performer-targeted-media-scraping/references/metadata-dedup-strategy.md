# Cross-Site Metadata Dedup Strategy

## Problem
The same video appears on multiple tube sites (PornHub, RedTube, XNXX, XVideos, YouPorn, Eporner, SpankBang) with different URL formats and different IDs. URL-based dedup misses these cross-site duplicates entirely.

## Solution: Title + Duration Fingerprinting

Two approaches, depending on whether you also need to update url2video's SQLite DB:

### Approach A: Batch metadata resolver (for queue-file dedup only)

Use `scripts/meta_deduper.py` — the full runnable script that handles batch processing, existing metadata loading, and dedup output. Groups by normalized title only.

### Approach B: Parallel per-URL resolver + duration bucket (for SQLite update)

Use `cross_site_dedup.py`-style (see `/tmp/cross_site_dedup.py` from 2026-06-30 session) when you also need to cancel dupes directly in url2video's SQLite DB. Uses `ThreadPoolExecutor` for parallel resolution and `(normalized_title, duration_bucket)` composite key grouping.

### Phase 1: Resolve metadata

**Approach A (batch, legacy):**
```python
cmd = [YTDLP, "--impersonate", "chrome", "--dump-json", "--skip-download", "--no-warnings", "-a", batch_file]
```

**Approach B (parallel, for SQLite update):**
```python
def extract_metadata(url):
    r = subprocess.run([YTDLP, "--dump-json", "--no-warnings",
        "--socket-timeout", "10", url],
        capture_output=True, text=True, timeout=30)
    data = json.loads(r.stdout)
    return url, data.get("title", ""), data.get("duration", 0)

with ThreadPoolExecutor(max_workers=8) as ex:
    fut_map = {ex.submit(extract_metadata, url): url for url in all_urls}
    for fut in as_completed(fut_map):
        url, title, duration = fut.result()
        results[url] = (title, duration)
```

Approach A is faster (yt-dlp reuses connections across batch URLs). Approach B lets you update the DB per-URL as metadata arrives.

### Phase 2: Normalize and group — composite key with duration bucket
```python
def normalize(t):
    s = t.lower()
    for k, v in [('4','a'),('3','e'),('1','i'),('0','o'),('5','s'),('7','t'),('8','b')]:
        s = s.replace(k, v)
    s = re.sub(r'[^a-z0-9\s]', '', s)
    return re.sub(r'\s+', ' ', s).strip()

def duration_bucket(d):
    """Bucket to nearest 5s window — prevents false matches between
    different videos with similar titles but different lengths."""
    if d is None or d <= 0: return 0
    return round(d / 5) * 5

groups = defaultdict(list)
for url, (title, duration) in results.items():
    if not title: continue
    key = (normalize(title), duration_bucket(duration))  # composite key
    groups[key].append((url, title, duration))
```

The **duration bucket** prevents false matches. Two videos titled "My Hot Neighbor" at 15min and 45min are different content; with title-only grouping they'd be conflated. The ±5s bucket absorbs normal intro/outro trimming.

### Phase 3: Keep best site
Sort by SITE_RANK (pornhub=1, spankbang=2, xvideos=3, xnxx=4, redtube=5, youporn=6, eporner=7, porntn=8, tnaflix=9, xhamster=10). Keep first, discard rest.

For SQLite update mode, cancel the discarded URLs in url2video's DB:
```python
conn.execute("UPDATE jobs SET status='cancelled', error='cross-site dupe' WHERE id=?",
             (job["id"],))
```

## Performance

- **50-URL batches (recommended)**: ~30 URLs/min — 2.5x faster than 20-URL batches
- **20-URL batches (legacy)**: ~12 URLs/min — slower due to yt-dlp process overhead per batch
- 552 URLs in ~18 min with 50-URL batches
- ~~552 URLs in ~90 min with 20-URL batches~~ (deprecated, use 50)

Use 50-URL batches with 180s timeout. The 120s timeout was marginally too short.

## Script: scripts/meta_deduper.py
1. Loads existing metadata from `/tmp/all_metadata.jsonl`
2. Processes remaining URLs in batches of 50 (180s timeout)
3. Groups by normalized title
4. Keeps best-ranked site per group
5. Writes `/tmp/video_queue_deduped_final.txt`

Run after Phase 1 crawl, before Phase 2 download.

## Edge Cases
- **PH viewkey URLs**: fast (~2s each)
- **XNXX**: `--dump-json` fails with "Unsupported URL" — falls back to slug
- **SpankBang**: Cloudflare blocks — slug-only dedup
- **Eporner**: truncated titles, no duration — slug-only
- **Duration tolerance**: ±5s for same video (trimmed intro/outro)
- **"bbc" in viewkey is false positive**: hex hash, not content. Phase 1 handles real BBC

## Verification
35-50% reduction normal (821→552 in one run). Spot-check sorted unique-slug count vs total.
