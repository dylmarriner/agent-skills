---
name: video-collection-manager
description: Full pipeline for adult video collection management — crawling, deduping, integrity checking, quality filtering, and organizing. Covers the url2video full-stack service, multi-site performer crawls, deduplication workflows, and ffprobe-based quality audits.
---

# Video Collection Manager

## Trigger
Use when the user asks to:
- Crawl/search for POV or performer videos across multiple sites
- Deduplicate video folders (exact or near-duplicate)
- Check video quality / remove corrupt or low-quality files
- Download/save videos to SMB share (`/mnt/storage/videos/`)
- Clean up a video collection folder (non-POV, BBC, non-video files, temp files, .info.json)
- Verify/filter/recrawl existing URL .txt files for content compliance (no BBC, POV, big tits)
- "remove the duplicates", "remove the non-POV", "remove BBC", "get rid of the trash", "recrawl all the URLs", "verify the .txt files"

## Architecture

### url2video Service (simple, /home/kubuntux)
At `/home/kubuntux/video-downloader/new-backend/url2video.py`:
- FastAPI on port 8800, single-file (~650 lines)
- SQLite persistent queue
- Extractor chain: yt-dlp → Puppeteer → curl
- Viewkey dedup built-in
- Per-site extractors (extractors.py)
- Output: `/mnt/storage/videos/`
- API: `POST /q` to queue, `GET /q` for stats, `GET /health`

### VideoSnap (full-stack, /media/kubuntux/DEVELOPMENT1)
At `/media/kubuntux/DEVELOPMENT1/video-downloader/`:
- FastAPI on port 8000, modular (~1644 lines across 9 files)
- CLI: `videosnap dl <url>`, `videosnap serve`, `videosnap queue add/list/cancel/retry/clear`
- SSE-streamed download progress (real-time)
- Full queue management (add, cancel, retry, clear, stats)
- Proxy rotation (ProxyManager class)
- Browser bypass (BrowserBypass class)
- Web UI (Next.js frontend)
- Tampermonkey userscript for browser integration
- Starts with: `bash start.sh` (launches node_service :3001 + uvicorn :8000 + Next.js)
- Output: `/mnt/storage/videos/`
- **Custom extractors integrated**: `backend/extractors.py` — same per-site extractor chain as url2video (pimpbunny, borntobefuck, eporner, porntn HTML extraction + yt-dlp + Puppeteer sniff). Integrated into `VideoDownloader.resolve_url()` as a pre-flight step before yt-dlp download. Full details: `references/videosnap-extractors-integration.md`

VideoSnap is the more capable codebase. Use it when the user wants a full web UI, CLI, or SSE progress. url2video is simpler and fine for headless queueing.

### SMB Sharing
- SMB share `\\KUBUNTUX\videos` maps to `/mnt/storage/videos/`
- Authenticated access only (kubuntux user, not guest) — config in `/etc/samba/smb.conf`
- Any downloader outputting to `/mnt/storage/videos/` is automatically shared

**Do NOT use standalone scripts** (`downloader.py`, `concurrent_downloader.py`) as primary tools — the user pushed back on this. Use the full-stack service or direct yt-dlp for one-off URLs.

### Video Output
- Fixed target: `/mnt/storage/videos/`
- SMB share: `\\KUBUNTUX\videos` (authenticated as kubuntux user, not guest — configured in `/etc/samba/smb.conf`)
- This machine also mounts SMB shares FROM macuntu (100.75.23.127): `/mnt/pivideos`, `/mnt/rabuntu_big`, `/mnt/nas/rabuntu/` — but the primary video output stays local
- File naming convention: varies — clean_downloader uses `{title} [{viewkey}].mp4`, VideoSnap uses `{sanitized_title}.mp4`, url2video uses `{title} [{hash}].mp4`

## Workflows

### 1. Performer POV Crawl
When the user asks to crawl for POV videos by specific performers:

1. **Split into batches** of 8-10 performers per subagent (delegate_task, max 3 concurrent)
2. **For each performer, search:**
   - eporner tag page: `https://www.eporner.com/tag/{name}-pov/`
   - eporner pornstar page: `https://www.eporner.com/pornstar/{name}/`
   - Other sites: pimpbunny.com, xhamster.com, xxbrits.com, porntn.com, borntobefuck.com, spankbang.com, motherless.com
   - General web search: `"{performer}" pov`
3. **Site-scoped searches:** Use site-specific queries:
   - `"{performer} pov site:pimpbunny.com"`
   - `"{performer} pov site:xhamster.com"`
   - etc.
4. **Save format:** `performer_name|url|site` in a pipe-delimited text file
5. **Deduplicate** collected URLs against existing files before downloading

#### Targeted-scraper mode (for under-represented performers)
When the user complains specific performers have too few videos, generic site feeds won't fix it — you need performer-targeted search. **Most site search URL patterns yt-dlp advertises DO NOT WORK.** Use this site-by-site cheat sheet:

| Site | Working approach |
|------|------------------|
| **PornHub** | **JSON API:** `https://www.pornhub.com/webmasters/search?search={q}&per_page=15&thumbsize=medium` — no auth, ~30 clean URLs, fastest |
| **RedTube** | **JSON API:** `https://api.redtube.com/?data=redtube.Videos.searchVideos&search={q}&output=json` — no auth, 5-8 URLs |
| **XNXX** | **HTML scrape:** `https://www.xnxx.com/search/{slug}` — regex `<a href="(/video-[a-z0-9]+/[a-z0-9_-]+)"` |
| **Eporner** | **HTML scrape:** `https://www.eporner.com/search/{q}/` — regex `<a href="(/video-[^"]+)"` (filter out `THUMBNUM` placeholders) |
| **SpankBang** | **yt-dlp only** with `--impersonate chrome --flat-playlist --dump-json --skip-download` — plain curl gets Cloudflare-blocked |
| **XHamster** | BROKEN in 2026 (520/401) — skip, use direct URL feeds |

**Always run 4-6 downloads in parallel** via threads — sequential is glacial (~14 min per 15-URL batch). Each yt-dlp uses ~50MB RAM; the box handles 4-parallel fine.

**Block BBC/interracial on title** before download — PH search results routinely include "BLACKED ... BBC" content for legitimate performer queries. Block list: `bbc`, `interracial`, `ebony`, `bwc`, `blacked raw`, `blacked.com`, `blackzilla`, `black experience`. All apply even when "POV" is in the title — BBC is hard-blocked regardless of format.

**Post-download cleanup is also required** — titles can slip through the blocklist (different wording at download vs. search time). Run Content Cleanup (section 4) after any batch download to catch stragglers.

**Don't use `--max-filesize` below 4GB** — most full-scene videos are 1.5-4GB; tight caps reject legit files. Per-file timeout should be 6-8 min (not 3) at 16-conn aria2 from these CDNs.

The user's per-performer cap is **max 20 videos total including already-downloaded** (confirmed 2026-07-09). Before any crawl, count what's on disk per performer and calculate `needed = max(0, 20 - current)`. See `pov-video-crawler` skill's `scripts/pornhub_xnxx_crawl.py` for a working implementation (Pornhub yt-dlp + XNXX curl combo).

### 2. Video Deduplication

Run this after any batch download or when the user asks "dedupe the videos." The user's rule: **same title after stripping [viewkey] OR same duration (±30s) with similar title = duplicate. Delete the smaller.**

**Step 0 — Remove non-video files first:**
```bash
cd /mnt/storage/videos
# Remove metadata files
find . -maxdepth 1 -name "*.info.json" -delete
# Remove temp/partial downloads
find . -maxdepth 1 -name "*.temp.mp4" -delete
# Remove 0-byte files  
find . -maxdepth 1 -type f -size 0 -delete
# Remove known junk
rm -f DEDUP_DELETE.sh DEDUP_REPORT.txt bigtits_pov_URLs.txt pov_crawl_*.txt
# Remove non-.mp4 files that are clearly not videos (no extension, .sh, .txt)
```
Always do this first — .info.json files accumulate and bloat the folder.

**Step 1 — Strip [viewkey], group by base title, keep largest:**
```python
import re, os
from collections import defaultdict

def base_title(fname):
    t = re.sub(r'\s*\[[a-zA-Z0-9_-]{6,}\]', '', fname)
    t = re.sub(r'\.(mp4|mkv|webm)$', '', t)
    t = re.sub(r'\s*-\s*(1080p|720p|480p|360p)$', '', t)
    t = re.sub(r'_(1080p|720p|480p|360p|source|flat|hd|4k)', '', t)
    t = re.sub(r'\s*\((1080p|720p|480p|360p)\)', '', t)
    t = re.sub(r'^(EPORNER\.COM\s*-\s*\[[^\]]*\]\s*|am_|dd_|bt_|BTPOV_|DD_)', '', t, flags=re.I)
    t = re.sub(r'\[[^\]]*\]', '', t)
    t = re.sub(r'\([^)]*\)', '', t)
    t = re.sub(r'\s+', ' ', t).strip().lower()
    return t

groups = defaultdict(list)
for f in os.listdir('.'):
    if not f.endswith(('.mp4','.mkv','.webm')): continue
    bt = base_title(f)
    if len(bt) > 15:
        groups[bt].append(f)
# For groups with >1 file, keep largest, delete rest
```

**Step 2 — Duration-based dedup (same performer + same duration = same scene):**
When two files have the same performer in the filename and very close durations (<30s difference), they're the same scene regardless of title wording. Delete the smaller.

```python
import subprocess
def get_duration(f):
    r = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
                       '-of','default=noprint_wrappers=1:nokey=1', f],
                      capture_output=True, text=True, timeout=30)
    return float(r.stdout.strip())

# Pair files by performer, group by rounded duration (±30s)
# Same performer + same duration bucket = delete smaller
```
Pitfall: ffprobe on 800+ files takes several minutes. Batch the duration check.

**Step 3 — Full MD5 hash for exact-size pairs:**
```python
with open(p, 'rb') as fh:
    h = hashlib.md5(fh.read(65536)).hexdigest()
```

**Step 4 — Cross-site dedup (url2video queue):**
When the same video is queued from 2+ different sites (pornhub + youporn + xhamster), or exists on disk already, cancel duplicates in url2video's SQLite DB:
```bash
cd ~/.hermes/skills/video-collection-manager && python3 scripts/cross-site-dedup.py
```

The script uses a two-phase hybrid approach:
- **Phase 1 (instant):** Pornhub URLs — extracts `viewkey` from URL, matches against `[viewkey]` in existing MP4 filenames. Zero HTTP calls.
- **Phase 2 (fast HTTP):** Non-pornhub URLs — curl (8s timeout) fetches HTML, extracts `<title>`/`og:title` + `video:duration` metadata. Fallback to `yt-dlp --dump-json` (15s) for exotic sites.

Three checks performed:
1. **Disk MP4 match** — cancels any queued URL whose normalized title or viewkey matches an existing MP4
2. **Cross-site dupe** — groups by `(normalized_title, duration_bucket)`; cancels extras when same video appears from 2+ sites
3. **Same-site dupe** — cancels duplicate URLs from the same site

**Step 5 — Queue reconciliation:**
After any queue change, cross-check url2video DB against queue files:
```bash
sqlite3 /mnt/storage/videos/.url2video.db "SELECT url FROM jobs WHERE status IN ('queued','downloading')"
wc -l /tmp/video_done.txt
```

**Pitfalls:**
- RisqueCore numbered episodes (Vid 1, Vid 2...) may have identical sizes but different content — check MD5 before removing
- Files like `borntobefuck_XXXXX.mp4` and `borntobefuck_XXXXX_720p.mp4` may be same or different — always check MD5
- Angie Faith files with the same title but different [viewkey] are often different scenes — skip when MD5 differs
- Don't skip files just because they have different [viewkeys] — same base title + same duration = same scene even with different IDs (cross-site reuploads)
- After dedup, always report: count removed, MB freed, and final video count
- Normalize leetspeak (`4→a, 3→e, 0→o, 5→s`) before matching performer names in duration-based dedup

### 3. Quality Audit (corrupt + low-quality removal)
When the user asks to "check for corrupt or shitty videos":

**Small file thresholds:**
- `<5MB`: almost always corrupt or teaser clip — flag for review
- `<10MB`: suspicious unless duration is also very short (<60s)
- `<20MB`: check resolution and duration

**ffprobe integrity check:**
```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,duration -of json "{file}"
```

**Removal criteria:**
- **Corrupt:** ffprobe returns non-zero exit or no video stream
- **Teaser clips:** `<30 seconds` duration, regardless of resolution
- **Garbage resolution:** `<480p` height (e.g. 240p, 360p, 144p)
- **Impossible compression:** `<5MB` for `>60 seconds` of video (corrupt/empty frames)
- **Specific thresholds used in this session:**
  - RisqueCore files: remove if `<400MB`

**Files to always check:**
- Generic-named files (`borntobefuck_video.mp4`, `hornyfap_*.mp4`, `finish me off.mp4`)
- Files with "720p" label but suspiciously small sizes
- Rickrolls / memes that aren't actual content

### 4b. URL List Compliance Verification (existing crawl files)
When the user asks to verify/filter/recrawl existing URL .txt files against content rules (no BBC, POV only, big tits).

**Trigger:** "recrawl all the URLs", "verify the .txt files", "check for BBC in the URL lists", "ensure every URL is NO BBC"

**Real-world results from 2026-07-09 (703 pornhub URLs fully verified):**
- **703 pornhub URLs → 1 BBC found** (title: "Sophie Dee is a whore who enjoys three black cocks")
- The slug-based crawl filter missed it because pornhub viewkey URLs have no descriptive path
- **Hit rate:** ~0.14% false negatives the crawl filter misses. One hit per 700 URLs is enough that full verification is worth running.
- The 1 BBC hit was a partial download (.part + .ytdl) — already deleted. No actual video made it to disk from that URL.

This workflow verifies that crawled URL lists actually comply with content rules — it catches content that the automated crawl filters may have missed.

**⚠️ CRITICAL: URL-slug-based filtering is NOT real verification.** This session proved it: a title-filter pass on URL slugs claimed "zero violations found" and "the crawl filters worked", but the user confirmed the data was "a fucking mess" with non-POV and BBC content that slug filters never caught. **Real verification requires fetching the actual page title with yt-dlp --get-title for every video URL.** Spot-checking 35 out of 1,975 URLs is insufficient — the user expects a full pass.

**Step 0 — Understand the file layout:**
Crawl files are typically at `/mnt/storage/videos/.queue/processed/` and come in multiple formats:
- `bigtits_asian_pov_<timestamp>.txt` — URL + quality suffix, one per line
- `asian_performers_pov_<timestamp>.txt` — `performer_name|url` pipe-delimited
- `crawl_batch_<description>_<timestamp>.txt` — mixed formats
- `deduped_batch_<timestamp>.txt` / `deduped_final_<timestamp>.txt` — deduped URL-only
- Various named crawl files

**Step 1 — Extract and deduplicate all URLs across files:**
```python
from pathlib import Path
import re

processed_dir = Path("/mnt/storage/videos/.queue/processed")
url_pattern = re.compile(r'(https?://\\S+)')
all_urls = {}

def clean_url(url):
    url = re.sub(r'\\s+\\d+p$', '', url)           # Strip quality suffix
    url = re.sub(r'\\|[a-z]+\\.[a-z]+$', '', url)  # Strip pipe-delimited site
    url = re.sub(r'\\|\\w+$', '', url)              # Strip pipe-delimited names
    return url.strip()

for f in sorted(processed_dir.glob("*.txt")):
    for line in f.read_text().split('\\n'):
        if not line.strip() or line.startswith('#'):
            continue
        for m in url_pattern.finditer(line):
            url = clean_url(m.group(1))
            if url.startswith('http'):
                all_urls[url] = all_urls.get(url, 0) + 1
```

2000+ unique URLs is normal after multiple crawl sessions.

**Step 2 — Classify URLs:**
Separate individual video pages from search/pornstar/tag/album pages. Non-video pages can't be verified via yt-dlp alone — they're structural pages, not content pages.

Non-video patterns: `/search/`, `/pornstar/`, `/tag/`, `/channels/`, `/playlists/`, `/album/`, `/fr/album/`, `/s/`, `/playlist/`, `/embed/`, `xxbrits.com`

For porntn.com, youporn.com — these are album/search pages, not individual videos. Skip them from yt-dlp verification.

**Step 3 — FULL LIVE VERIFICATION (not spot-check):**
For each individual video URL, fetch the actual page title with yt-dlp and check against block keywords.

**Do NOT use exported bash functions with xargs** — `export -f process_url` followed by `xargs -P sh -c 'process_url "{}"'` fails silently (the function is not available in the subshell). Instead, create a standalone script file:

```bash
#!/bin/bash
# /tmp/verify_single.sh — called once per URL via xargs
# Output format: url|title|POV|BIGTITS|FLAG_BBC

url="$1"
outfile="${2:-/tmp/verify_results.txt}"

title=$(yt-dlp --impersonate chrome --get-title "$url" 2>/dev/null | head -1)
[ -z "$title" ] && title="(no title / error)"

title_lower=$(echo "$title" | tr '[:upper:]' '[:lower:]')

flag=""
echo "$title_lower" | grep -qiE '(bbc|interracial|black.?cock|black.?dick|big.?black|black.?bf|black.?guy|black.?man|black.?bull|blacked|blackedraw|bwc|ebony|monster.?dick|chocolate.?pussy)' && flag="FLAG_BBC"

pov=""
echo "$title_lower" | grep -q 'pov' && pov="POV"

tits=""
echo "$title_lower" | grep -qiE '(big.?tit|busty|huge.?tit|massive.?tit|boobs|breast|juggs)' && tits="BIGTITS"

echo "$url|$title|$pov|$tits|$flag" >> "$outfile"
```

Run in parallel batches:
```bash
chmod +x /tmp/verify_single.sh
cat /tmp/video_urls_to_check.txt | xargs -P 8 -I{} /tmp/verify_single.sh "{}" /tmp/verify_results.txt
```

**Troubleshooting the parallel approach:**
- The script file approach works because xargs spawns actual bash processes that can exec the script
- `export -f process_url` + `xargs -P sh -c 'process_url "{}"'` does NOT work — exported functions are invisible to xargs-spawned subshells
- Run this in the background for large batches: `terminal(background=true, notify_on_complete=true)`
- Progress can be checked with `wc -l /tmp/verify_results.txt`
- Expected rate: ~200 URLs per minute with 8 parallel workers on eporner/pornhub
- Sample size for spot-check: 30 random pornhub viewkey URLs minimum

**Step 4 — Keyword detection on actual titles (proven patterns from 2026-07-09):**

```python
# These actual page titles were found to contain BBC/interracial content:
# - "sexy-japanese-milf-gets-fucked-her-daugthers-black-bf"
# - "destroyed-by-bbc"
# - "vivian taylor bbc blowjob pov"
# - "larged_breasted_teen_takes_on_big_black_cock_pov"
# - "jason-luv-kali-roses-v-jason-luv-amazing-busty-blonde-and-the-bbc"
# - "lena-paul-gets-fucked-by-van-wylde-s-bwc"
# - "sky bri gets wrecked by monster dick" (grey-area)
# - "vanilla pussy or chocolate pussy kali roses or hazel grace" (grey-area)

BLOCK_KEYWORDS = [
    'bbc', 'black.?cock', 'big.?black', 'interracial', 'bwc', 'ebony',
    'black.?dick', 'black.?bf', 'black.?guy', 'black.?man', 'black.?bull',
    'blacked', 'blackedraw', 'black.?king', 'dark.?meat', 'chocolate.?pussy',
    'monster.?dick', 'huge.?black', 'black.?fuck', 'blackzilla',
    'black.?experience'
]
```

**Step 5 — Report results with proper classification:**

```
CONFIRMED BAD (definite BBC/interracial from URL or page title):
  [site] URL slug/title — reason

GREY-AREA (ambiguous — flag for user review):
  [site] URL slug/title — "monster dick" could be racial or size reference
  [site] URL slug/title — "chocolate pussy" could be performer comparison, not racial

SPOT CHECK (sample of clean URLs — report how many checked):
  X random pornhub viewkey URLs → all clean, zero BBC/interracial violations
  Y eporner Asian URLs → all POV/big tits, matching slug descriptions
```

**Step 6 — Deliver removal list:**
Write flagged URLs to `/tmp/flagged_urls_remove.txt` with clear section headers so the user knows which are confirmed and which are grey-area.

**Pitfalls:**
- **URL slug filtering alone is NOT verification.** Many video pages have titles that don't match their URL slugs. A slug without "bbc" does NOT mean the video is BBC-free. You MUST fetch actual page titles.
- Pornhub viewkey URLs have no descriptive path — you MUST use yt-dlp --get-title to see their real titles
- Multiple crawl txt files share URLs (same video appears in different crawl batches) — always dedupe first before reporting counts
- Some URLs in crawl files are search/tag/album pages, not individual videos — skip these from yt-dlp verification
- `yt-dlp --impersonate chrome --get-title` is fast (<3s per URL) and works for most adult sites
- `xargs -P 5` runs 5 parallel yt-dlp instances — don't exceed 5-8 or you'll hit rate limits (especially eporner). Eporner rate-limits at ~3 concurrent
- "No POV in title" counts will be inflated for sites with generic titles (pornhub, redtube) — this is expected and NOT actionable
- Crawl files use multiple formats (URL-only, pipe-delimited, quality-suffixed) — the clean_url() regex must handle all of them
- Eporner returns ~20% "(no title / error)" results — this is normal rate-limiting, retry those separately or accept the loss
- **Don't export functions for xargs** — create a standalone script file instead
- The "no POV" count will be very high (1000+) for a 2000-URL verification — most pornhub URLs have generic titles that don't contain "POV" even for POV scenes. This is normal and not actionable.
- After verification, always deliver a `/tmp/flagged_urls_remove.txt` file the user can use as a removal reference

### 4c. Performer Video Counting (count videos per performer from filenames)
When the user asks to count how many videos each performer has in the collection.

**Trigger:** "count all the current videos that are saved per model", "how many videos per performer", "video counts"

Use this for actual downloaded files, not queue URLs. Queue counts and on-disk counts are different questions.

**Step 0 — Decide which inventory is being counted:**
- Queue inventory: match performer names in `.txt` crawl files.
- Downloaded inventory: scan `/mnt/storage/videos/` directly and exclude `/mnt/storage/videos/.queue/`.
- If the user says "actual downloaded files", do not answer from queue files.

**Step 1 — Build the performer pattern list:**
Use a list of `(performer_name, [substring_variants])` tuples. Order by specificity — longer/fuller names first. This matters because `Mia` would match `Mia Malkova` files but `Mia Malkova` should match those first.

See `references/2026-07-12-performer-aliases.md` for alias-style filename notes and concatenated-name handling.

```python
PERFORMER_PATTERNS = [
    ("Mia Malkova", ["mia malkova", "mia_malkova", "miamalkova"]),
    ("Lana Rhoades", ["lana rhoades", "lana_rhoades"]),
    # ... full name first
    ("Mia", [" mia "]),  # space-wrapped to avoid false matches inside words
]
```

Search patterns are lowercased substrings. `"mia malkova" in "Mia Malkova POV [viewkey].mp4".lower()` works reliably across many naming conventions.

**Step 2 — Scan and count actual files:**
```python
from pathlib import Path
from collections import defaultdict
import re

videos_dir = Path("/mnt/storage/videos/")
performer_counts = defaultdict(int)

for f in videos_dir.rglob("*"):
    if ".queue" in f.parts:
        continue
    if f.suffix.lower() not in ['.mp4', '.webm', '.mkv', '.mov', '.m4v', '.avi', '.mpg', '.mpeg', '.ts']:
        continue
    name_lower = f.stem.lower()
    name_clean = re.sub(r'\s*\[[a-zA-Z0-9_-]+\]', '', name_lower)
    
    for perf_name, patterns in PERFORMER_PATTERNS:
        if any(p in name_lower or p in name_clean for p in patterns):
            performer_counts[perf_name] += 1
            break
```

**Step 3 — Handle uncategorized videos (always substantial):**
In a collection of 800+ videos, expect a large uncategorized bucket. Common categories:

| Category | Example | Typical count |
|----------|---------|---------------|
| Generic titles | "POV Blowjob.mp4" | 30-50% |
| Hash filenames | `0glt5wev9obclbtyssfqi_flat.mp4` | 1-5% |
| Site-stamped | `EPORNER.COM - [hash] Title.mp4` | 20-30% |
| JAV codes | `MIAA-599 [viewkey].mp4` | 1-5% |
| Studio/taboo | `ADULTMOBILE - Horny MILF...` | 5-10% |
| Non-English | Arabic, Indonesian titles | 1-5% |

**Step 4 — Second pass for hidden performers:**
Run a second scan with additional performer names found from session-specific patterns (performers spotted in uncategorized titles). In the 2026-07-09 session, 33 additional performers were found this way: Camila Mendez, Savannah Bond, Dan Dangler, Octokuro, Kazumi, Atlanta Moreno, and others.

**Pitfalls:**
- **One file can match multiple performers.** If a filename contains two names, counting it once per match is fine, but say so clearly.
- **Leetspeak in filenames (eporner downloads):** `Bl4k3 Bl0ss0m`, `L4n4 Rh04d35` won't match. Normalize `4→a, 3→e, 0→o, 1→i, 5→s` before matching when needed.
- **Alias-style performer names can be concatenated** — e.g. `TheDanDangler` should still count as TheDanDangler even when the filename omits spaces/punctuation. Keep a small alias map for known performer aliases in the current library and re-run unmatched buckets after adding one.
- **Site-stamped filenames hide the performer:** Strip the `EPORNER.COM - [hash]` prefix before matching.
- **Short performer names create false positives** — `Mia` matches both Mia Malkova and Mia Melano. Put full-name entries first so they match before the short-name catch-all.
- **Studio credits in title:** `Family Therapy - Alex Adams` is a studio credit (Alex Adams = male director), not the female performer. Parse carefully.
- **Hash filenames** (`^[a-z0-9]{10,40}(_flat|_source|_720p)?\.mp4$`) have no performer info — flag as junk candidates.
- If the user wants a strict inventory, say whether counts are name-matched heuristic counts or metadata-backed counts.
- Always report: matched count, uncategorized count, top performers.
- For this repo, save the report as `/mnt/storage/videos/.queue/performer_video_counts.md` and keep mainstream and Asian sections separate.
- Count against the live `/mnt/storage/videos/` inventory, not queue files, unless the user explicitly asks for queue counts.

**Support file:** see `references/2026-07-12-performer-file-counting.md` for a compact recipe and session notes, plus the naming/alias normalization used in this session.

### 5. Content Cleanup (non-POV / BBC / Interracial filtering)
When the user says the collection has content that shouldn't be there — BBC, non-POV, compilations, VR, etc.

**Trigger:** "remove the non-POV", "remove BBC", "clean up the videos", "get rid of the trash"

#### Step 1 — Remove BBC/Interracial filenames
Search filenames for patterns that indicate prohibited content. The user's hard blocklist:
```python
BBC_PATTERNS = [
    r'\bbbc\b', r'\binterracial\b', r'\bbwc\b', r'\bblack\s+cock\b',
    r'\bblack\s+dick\b', r'\bblack\s+pussy\b', r'\big\s+black\b',
    r'\bblackzilla\b', r'\bblack\s+experience\b', r'\bblacked\b',
    r'\bebony\b',
]
```
Any match = delete immediately. Even if the title also says "POV" — BBC content is blocked regardless.

#### Step 2 — Remove obviously non-POV content
These categories are clearly not POV and should be deleted immediately (don't ask, just do it):

| Category | Patterns to search |
|----------|-------------------|
| **VR** | `\bvr\b`, `virtual reality`, `360` |
| **Compilations** | `\bcompilation\b`, `\bpmv\b`, `comp`, `blowpass` |
| **Trans/FUTA** | `\bfuta\b`, `\btrans\b.*(girl\|cis)` |
| **Gangbang** | `\bgangbang\b` |
| **DP/DVP** | `\bdp\b`, `\bdvp\b`, `double\s+(anal\|pen\|stuffed)` |
| **JAV (Japanese)** | `\bjav\b`, `\buncensored\b` (unless pure JAV collection) |
| **Parody** | `\bparody\b` |
| **Cuckold** | `\bcuckold\b`, `\bcucking\b` |
| **Anime/Hentai** | `\bhentai\b`, `\banime\b` |

**Pitfall:** Some files in these categories have "POV" in the filename (e.g. "Savannah_Bond_Anal_VR_POV.mp4", "Mia Malkova POV COMPILATION!") — still delete them. "POV" in the filename does NOT override VR/compilation/DP categorization.

#### Step 3 — Grey-area content (3rd-person titles)
Files with descriptive 3rd-person titles that COULD be POV (stepson cam) or non-POV (3rd person camera). Common patterns:

```python
GREY_PATTERNS = [
    r'\bgets\s+fucked\b', r'\btakes\s+(a|his|her).*(cock|dick|load)',
    r'\bfucks\s+her\b', r'\bpounds?\s+her\b',
    r'\bhe\s+fucks\b', r'\bher\s+(ass|pussy|mouth)\s+gets\b',
    r'\bfucked\s+by\b', r'\bgetting\s+fucked\b',
    r'\bthreesome\b', r'\bhuge\s+cock\b', r'\bhung\b',
    r'\brough\b', r'\bhardcore\b',
    r'\bcreampied?\s+her\b', r'\bslut\b.*(gets|is)',
    r'\bwhore\b', r'\bfacial\b', r'\bswallow(ed|s|ing)',
]
```

**How to handle:** Present the files to the user grouped by size (largest first). Many of these are actually POV step-family content (e.g. "Stepmom Gets Fucked By Stepson" shot from stepson's perspective). Let the user choose. The user's rule: **same duration (±30s) from the same performer = same scene = duplicate regardless of title wording.**

#### Step 3.5 — Kill active downloads before cleanup
Before any cleanup, check for active yt-dlp / clean_downloader processes. Multiple `clean_downloader.py` instances can pile up from the 5-min cron — they spawn overlapping runs when download takes >5m:

```bash
ps aux | grep -iE 'yt-dlp|clean_downloader|url2video' | grep -v grep
pkill -f yt-dlp 2>/dev/null
kill -9 <PID1> <PID2>   # specific PIDs if pkill is too blunt
```

After killing, always sweep leftover fragments:
```bash
cd /mnt/storage/videos && rm -f *.part *.part-Frag* *.ytdl *.info.json *.temp.mp4
```

Consider adding a lockfile to clean_downloader.py: `flock -n /tmp/clean_downloader.lock python3 /tmp/clean_downloader.py`

#### Step 3.75 — Aggressive size-based cleanup (under 100MB)
When the user says to clean up small files, delete ALL files under 100MB — not just video files. This catches leftover .db files, orphaned fragments, teaser clips, and low-quality shorts:

```bash
cd /mnt/storage/videos && find . -maxdepth 1 -type f -size -100M -delete
```

Run this AFTER killing active downloads (Step 3.5) or you'll kill .part files mid-download. A 5-min 1080p H.264 scene is 300-600MB, so anything under 100MB is either a teaser, a clip, or garbage quality.

#### Step 3.8 — VR removal (dangerous: avoid `*[Vv][Rr]*` patterns)
When the user says to delete VR videos, match prefix/whole-word patterns only. **Do NOT use `*[Vv][Rr]*`** — this matches random `vR` / `Vr` substrings in video viewkeys (e.g. `1EK18vRQ8jO` matches because it contains `vR`):

```bash
# GOOD — matches only actual VR-named videos
find . -maxdepth 1 -type f -iname "*vr*" ! -iname "*[0-9]*vr*" -delete
# BAD — matches viewkeys containing "vR" or "Vr" (false positives on random hash chars)
find . -maxdepth 1 -type f -name "*[Vv][Rr]*"   # DON'T USE THIS
```

Actual VR filenames are obvious: `VRBangers.com - Title.mp4`, `VRCosplayX - Title.mkv`, `BadoinkVR - Title.mkv`. Keep the `-iname` match tight.

#### Step 4 — Check for non-video files and remove
```bash
cd /mnt/storage/videos
# .info.json metadata files
find . -maxdepth 1 -name "*.info.json" -delete
# Partial downloads
find . -maxdepth 1 -name "*.temp.mp4" -delete  
find . -maxdepth 1 -type f -size 0 -delete
# Non-video junk
rm -f DEDUP_DELETE.sh DEDUP_REPORT.txt *.txt
# Remove non-.mp4 files that aren't directories
```

**Pitfalls:**
- Some files with generic titles like "Beautiful Face, Big Tits And A Sexy Body" are POV even though the title doesn't say it — check duration first
- "POV" in the filename doesn't guarantee it's POV — compilations, VR, and DP content sometimes have "POV" in the title
- Don't delete step-family threesomes automatically — many are POV threesomes
- Always show the user the count and total MB before deleting grey-area files
- After cleanup, always report: removed count, MB freed, remaining video count

### 4. url2video Service Setup

#### Starting the service
```bash
# In Hermes: use background=true (no & foreground)
cd /home/kubuntux/video-downloader/backend && python3 url2video.py
# Wait 3s then verify
sleep 3 && curl -s http://localhost:8800/health
```

#### Queue a URL
```bash
curl -s -X POST http://localhost:8800/q \
  -H "Content-Type: application/json" \
  -d '{"url":"...","quality":"1080p"}'
```

#### Check queue status
```bash
curl -s http://localhost:8800/health
```

#### Watch folder (drop `.txt` files with URLs, one per line)
```
/mnt/storage/videos/.queue/
```

#### Service hang recovery (common)
The service can become unresponsive while a download hangs — the port stays LISTEN but health endpoint returns curl exit code 56 ("failure in receiving network data") and every API call times out.

**Recovery steps:**
1. Identify the hung process: `ps aux | grep url2video | grep -v grep`
2. Kill it: `kill <PID>` then `kill -9 <PID>` if needed
3. Confirm port clear: `ss -tlnp | grep 8800 || echo "port clear"`
4. Restart with background=true (Hermes terminal)
5. Wait 3s then verify: `curl -s http://localhost:8800/health` — must return `{"status":"ok",...}`

#### Direct DB insert (when API is hung)
If you need to queue URLs while the service is hung, insert directly into the SQLite DB:
```bash
sqlite3 /mnt/storage/videos/.url2video.db "
INSERT OR IGNORE INTO jobs (id, url, quality, status, source, created_at)
VALUES ('$(echo $RANDOM | md5sum | cut -c1-12)', 'https://example.com/video', '1080p', 'queued', 'api', datetime('now'));
"
```
For batch inserts, comma-separate the VALUES rows. The `UNIQUE INDEX idx_jobs_url_pending` prevents re-adding already-queued URLs. These will be picked up by the service when it restarts.

#### Batch queuing limitation
When queuing multiple URLs rapidly in a loop, the service can become unresponsive after 1-2 successful submissions. If subsequent `curl -X POST /q` calls hang or return exit code 56:
- Add `--max-time 15` to each curl call
- The hung state means the downloader thread is blocking the HTTP handler — kill and restart the service

## Pitfalls
- Eporner rate-limits at ~3 concurrent yt-dlp instances — bulk launches stall
- Eporner encodes vertical POV at 404x720 or 406x720 — this is NORMAL for their POV content, NOT a quality issue
- motherless.com returns zero search results for most performers
- xxbrits.com returns search pages, not direct video URLs
- The node_service (Puppeteer) at port 3001 is optional — url2video uses the Python browser_bypass module directly
- **Cap per performer: max 20 videos including already-downloaded.** The user confirmed this on 2026-07-09. Before any crawl, count from disk and calculate `needed = max(0, 20 - current)`. The `pov-video-crawler` skill's `scripts/pornhub_xnxx_crawl.py` implements this correctly.\n- Generic site-feed crawls starve specific performers** — Mia Malkova gets 30+ files, equally-top Riley Reid gets 2 because she's not in the feed window. Use performer-targeted search (see §1 Targeted-scraper mode)
- **Batch URL queuing can lock the service** — Rapid sequential `POST /q` calls (in a bash for-loop) can cause url2video to go unresponsive after 1-2 successful submissions. The downloader thread blocks the HTTP handler. Queue individually with `--max-time 15` and kill+restart if it hangs.
- **pimpbunny.com URLs work at 1080p** — These queue and download fine. No special handling needed beyond the normal API.
- **Cross-site dedup script runtime** — Expect ~9-15 min for 550 URLs at 8 workers. The script outputs periodic progress every 25 URLs. If the service is restarted while dedup is running, kill the old dedup processes too (multiple copies can pile up).
- **yt-dlp `ytsearch:` prefix only works for YouTube** — don't use it for adult sites
- **Leetspeak filenames (`Bl4ke Bl0ss0m`, `As4 Ak1r4`) break exact-match counting** — normalize with `4→a, 3→e, 1→i, 0→o, 5→s, 7→t, 8→b` before matching performer names
- **Dedup by video ID, not full URL** — `viewkey=`, `/video-XYZ/`, `/NUMBER/` all need a combined regex to dedupe across sites
- **BBC content slips through performer searches** — PH's "Lulu Chu" results include BBC titles; filter on title at search time, not after download
- **Same title + different [viewkey] can mean different scenes** — Angie Faith files with identical titles but different viewkeys were different content. Always check MD5 or duration before deleting.
- **Same duration = same scene** — User's rule: two files with the same performer name and close durations (<30s diff) are the same scene regardless of title wording. Delete the smaller. This catches cross-site reuploads with different studio titles.
- **Don't trust "POV" in filenames as proof of POV content** — Compilation videos, VR, and DP scenes sometimes include "POV" in their filenames. Check actual content by duration and structure.
- **Duration comparison is the most reliable dedup signal** — Beats filename matching, hash comparison, and size matching. Two files with the same duration from the same performer are always the same scene.
- **After any cleanup, always report the final counts** — videos remaining, total GB, and MB freed

## Verification
- After dedup: count MP4s and total size (`ls *.mp4 | wc -l; du -sh`)
- After quality audit: verify remaining files with random ffprobe sampling
- Report total count and GB to user
