# Video Deduplication Workflow

Find and remove duplicate videos from the download folder. Three passes in order:

## Pass 1: Exact byte-size duplicates

Files with the same byte count are likely duplicates. Group by size, then for same-size pairs, MD5 the first 64KB to confirm.

```python
import os
from collections import defaultdict

videos = '/mnt/storage/videos'
files = [f for f in os.listdir(videos) if f.endswith('.mp4')]

# Group by size
by_size = defaultdict(list)
for f in files:
    sz = os.path.getsize(os.path.join(videos, f))
    by_size[sz].append(os.path.join(videos, f))

# Hash same-size groups on first 64K
import hashlib
for sz, paths in by_size.items():
    if len(paths) < 2:
        continue
    hashes = {}
    for p in paths:
        with open(p, 'rb') as fh:
            h = hashlib.md5(fh.read(65536)).hexdigest()
        if h in hashes:
            print(f"DUPE: {os.path.basename(hashes[h])} == {os.path.basename(p)}")
        else:
            hashes[h] = p
```

For confirmed dupes, keep the one with the better filename (prefer friendly names over truncated/auto-generated ones) and remove the other.

## Pass 2: Name normalization near-dupes

Normalize filenames and group by first 40 characters to catch the same video saved under different naming schemes (e.g. "Lana Rhoades POV.mp4" vs "Lana_Rhoades_POV.mp4").

```python
import re
by_key = defaultdict(list)
for f in files:
    n = f.lower().replace('_', ' ').replace('-', ' ')
    n = re.sub(r'\b(720p?|1080p?|4k|2160p|hd|xxx)\b', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    key = n[:40]
    by_key[key].append(f)

for key, names in sorted(by_key.items()):
    if len(names) > 1:
        sizes = [f"({os.path.getsize(videos + '/' + n)//1024//1024}MB)" for n in names]
        # Review manually — different sizes likely different scenes
        # Same size = run pass 1 MD5 check
```

Keep both files if sizes differ significantly — they're likely different scenes of the same performer. Same size = run hash check.

## Pass 3: Corrupt stub removal

Files that are disproportionately small compared to their named quality level are corrupt stubs (interrupted downloads that the session didn't clean up).

Criteria:
- `< 10MB` for a named HD video is almost certainly a stub
- Compare to the complete version if it exists alongside (e.g. `borntobefuck_30673.mp4` at 3MB vs `borntobefuck_30673_720p.mp4` at 258MB)

## Pass 5: Cross-site dedup (url2video queue vs disk)

When the url2video queue has the same video from multiple sites (e.g. pornhub + youporn + xhamster), find matches by extracting titles from non-pornhub URLs and comparing against existing MP4 filenames on disk.

**Why this matters:** The same scene gets uploaded to multiple tube sites. url2video dedups by URL, not content — so you get the same scene downloading 2-3 times from different sources.

**Approach (fast, tiered):**

1. Scan only non-pornhub URLs (youporn, xhamster, etc.) — pornhub is usually the primary source
2. Extract their yt-dlp titles in parallel (8 workers, 20s timeout)
3. Compare normalized titles against existing MP4 filenames on disk
4. Cancel matching jobs in url2video's DB

**Why not check all 553 URLs:** yt-dlp --dump-json on 500+ URLs is slow (many timeout). Only check the minority that could be cross-site dupes — typically 30-40 URLs.

```python
from urllib.parse import urlparse
import re, sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess, json

OUTDIR = "/mnt/storage/videos"
DB_PATH = "/mnt/storage/videos/.url2video.db"

def title_key(t):
    t = t.lower().strip()
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()[:80]

# MP4s on disk
mp4s = [f for f in os.listdir(OUTDIR) if f.endswith(".mp4")]
disk_titles = {title_key(re.sub(r'\s*\[[^\]]+\]\.mp4$', '', f)): f for f in mp4s}

# Pending jobs by site
conn = sqlite3.connect(DB_PATH)
by_site = defaultdict(list)
for r in conn.execute("SELECT id, url FROM jobs WHERE status IN ('queued','downloading')"):
    site = urlparse(r[1]).netloc.replace("www.","").split(".")[0]
    by_site[site].append(r)

# Only non-pornhub URLs
non_ph = [j for s,jobs in by_site.items() if s != "pornhub" for j in jobs]

# Extract titles in parallel
def extract(url):
    r = subprocess.run([YTDLP, "--dump-json", "--no-warnings",
        "--socket-timeout", "8", url], capture_output=True, text=True, timeout=20)
    d = json.loads(r.stdout)
    return url, d.get("title","")

with ThreadPoolExecutor(max_workers=8) as ex:
    fut_map = {ex.submit(extract, j[1]): j for j in non_ph}
    for fut in as_completed(fut_map):
        url, title = fut.result()
        if title and title_key(title) in disk_titles:
            j = fut_map[fut]
            conn.execute("UPDATE jobs SET status='cancelled', error='cross-site dupe' WHERE id=?", (j[0],))

conn.commit()
conn.close()
```

**Cancel count expectation:** Typically 5-15 cross-site dupes per sweep, depending on how many youporn/xhamster URLs are in the queue.

**Pitfall:** The dedup script's python process gets killed when url2video is restarted (they share port/process tree). Always re-run dedup after a url2video restart if you had one running.

RisqueCore numbered episodes (and similar sequentially-named collections) mix full-length videos with short clips/teasers. When the user says "only keep above X MB":
- Group files by series prefix (e.g. `RisqueCore Vid N.mp4`)
- Remove all files under the threshold size
- Keep files above it (these are the full episodes)

## Naming conventions kept vs removed

Prefer keeping:
- Longer, more descriptive filenames
- Names with performer prefix (lr_, aw_, kr_, etc.)
- Names with known quality tags (1080p, 720p)
- Non-truncated titles

Remove:
- Truncated/auto-generated names that are subsets of a kept file
- URL-encoded names (containing %XX)
- -1 suffixed duplicates (e.g. "Video-1.mp4" when "Video.mp4" exists and same size)

## Safety

Always check no yt-dlp or ffmpeg processes are running before removing files:
```bash
ps aux | grep -E '(yt-dlp|ffmpeg)' | grep -v grep
```

Only remove files that are confirmed duplicates by hash. For same-size files where hashes differ, keep both — they may be different encodings or different content that happens to be the same size (common with RisqueCore numbered episodes).
