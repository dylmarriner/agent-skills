---
name: video-downloader-service
description: "Run the async url2video download service — architecture, per-site extraction, dedup, post-download folder cleanup, troubleshooting. Covers the full lifecycle: crawl URLs, download to SMB share, deduplicate by duration/title/hash, remove BBC and non-POV content, strip metadata junk."
---

# Video Downloader Service

## Queue Hygiene for Crawled Batches

When the input comes from an automated crawl, do not treat every deduped URL as downloadable. Add a classification gate before the batch runner:

1. Merge crawl outputs
2. Deduplicate exact URLs
3. Remove obvious non-video pages (search, profile, social, IMDB/IAFD, performer directories, chat/details pages)
4. Keep only direct-video pages in a URL-only file
5. Run title verification and download only from that cleaned file

This matters because the combined crawl pool can still be mostly navigation noise even after URL dedupe. A previous session started from 204 unique URLs, but only 73 were direct video pages once search/profile/social pages were stripped out.

**Rule of thumb:** if the URL points to a catalog, profile, search result, or social page instead of a single playable item, it does not belong in the download queue.

Related note: for direct user-pasted URLs, keep the existing bypass behavior — this queue-hygiene gate is for automated crawl batches only.


FastAPI (port 8800) -> Background Worker Threads (default: 4 concurrent)

- **Extract phase** — tries per-site extractor first, then falls back
- **Download phase** — aria2c (direct URLs, 16 connections) -> yt-dlp (HLS/DASH)
- **Dedup** — built-in viewkey check before extraction

Key design decisions:
- **Thread-per-job** worker pool — never blocks the HTTP event loop
- **Fail fast** — 8s timeouts per extract strategy, moves on
- **Site-aware extractors** — custom handler per domain
- **aria2c preferred** — significantly faster than yt-dlp for direct CDN URLs

## Per-Site Extraction

### borntobefuck.com (Puppeteer click-and-capture for HLS)

Borntobefuck uses **two different CDN backends** depending on video age:
- **Zavastream** (`content.zavastream.com/{content_id}/{uuid}/...`) — Older videos; m3u8 visible directly in player page HTML after Puppeteer rendering
- **Bunny CDN** (`vz-*.b-cdn.net/{uuid}/...`) — Newer videos; m3u8 only appears AFTER clicking the play area (network request interception)

**Distinguishing by player page size:** ~17KB = Zavastream (static HLS in HTML). ~9KB = Bunny CDN (needs click-and-capture).

**Method 1: Puppeteer click-and-capture (works for both CDNs) — PREFERRED**

Use the `scripts/bornto_sniff.cjs` script (one video) or `scripts/btbf_batch_extract.cjs` (batch):

```bash
# Single video
cd /media/kubuntux/DEVELOPMENT1/video-downloader/backend/node_service
NODE_PATH=$(pwd)/node_modules node /path/to/bornto_sniff.cjs <video_id>

# Batch (11 videos processed in ~90s — much faster per-video)
cd /media/kubuntux/DEVELOPMENT1/video-downloader/backend/node_service
NODE_PATH=$(pwd)/node_modules node /path/to/btbf_batch_extract.cjs <id1> <id2> ...
```

Both scripts launch headless Chromium via puppeteer, load the player iframe at
`https://borntobefuck.com/videos/{id}/player?lang=en`, register a `.m3u8` network
request listener, then click selectors in priority order:
`.active-video-player` → `.player-container` → `video` → center-of-page fallback.

Output: JSON with `{success, m3u8s: [HLS URLs]}`. The first URL is usually the
master playlist, second is the quality-specific variant.

Download with explicit output naming (raw HLS URLs produce useless filenames):

```bash
yt-dlp --referer "https://borntobefuck.com" \
       --add-header "Origin:https://borntobefuck.com" \
       --output "/mnt/storage/videos/borntobefuck_{video_id}.mp4" \
       --merge-output-format mp4 \
       "<720p_video_m3u8_URL>"
```

**Method 2: Puppeteer → player iframe → HLS from HTML (Zavastream only)**
1. Ensure Puppeteer node service running on port 3001
2. Extract watch page via `/extract-page` to find player iframe (`/videos/{id}/player?lang=en`)
3. Load player iframe via `/extract-page` — HTML contains `content.zavastream.com/.../index.m3u8`
4. Download with yt-dlp `--referer` + `--add-header "Origin:..."`

**Pitfalls:**
- `/watch/NNNNN` NOT supported by yt-dlp — must use player iframe
- **Dead videos return 0-byte HTML** from Puppeteer. Confirm by checking `html.length === 0` in the response. Skip these immediately.
- **Output naming is critical** — yt-dlp saves HLS URLs as `index [index].mp4`. Always use `--output borntobefuck_{id}.mp4`
- **Quality varies by video**: most Bunny CDN vids have 480p max; Zavastream usually has 720p. Check the m3u8s array for quality indicators (`720p/video.m3u8` vs `480p/video.m3u8`)
- `.active-video-player` is the primary click target. `.player-container` and plain `video` are reliable fallbacks
- Puppeteer CSS click on `.active-video-player` triggers the ad overlay removal + player start, which is what reveals the HLS stream to the network listener
- puppeteer-extra is broken on this Node version (missing dist/ builds). Always use bare `require('puppeteer')`

### pimpbunny.com

**Puppeteer node service (port 3001) → JSON-LD contentUrl → curl/aria2c — VERIFIED WORKING 2026-07-10**

The page embeds the video URL in a `<script type="application/ld+json">` block as `contentUrl`. Extract it via the node service's `/extract-page` endpoint, then download with curl or aria2c using the session cookies and Referer header.

**Step-by-step verified pipeline:**

1. **Start node service** (if not already running):
   ```bash
   cd /media/kubuntux/DEVELOPMENT1/video-downloader/backend/node_service
   NODE_PATH=$(pwd)/node_modules node index.js
   # Listens on port 3001
   ```

2. **Extract page via Puppeteer**:
   ```bash
   curl -s http://localhost:3001/extract-page -X POST \
     -H "Content-Type: application/json" \
     -d '{"url":"https://pimpbunny.com/videos/.../"}' \
     -o /tmp/pb_page.json --max-time 90
   ```

3. **Parse JSON-LD for contentUrl**:
   ```python
   import json, re
   data = json.load(open('/tmp/pb_page.json'))
   html = data.get('html', '')
   cookies = data.get('cookies', [])
   for m in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL):
       obj = json.loads(m.group(1))
       video_url = obj.get('contentUrl', '').rstrip('/?')
       title = obj.get('name', '')
   ```

4. **Save cookies** as Netscape format (handle `expires=-1` — clamp to 0):
   ```python
   with open('/tmp/cookies.txt', 'w') as f:
       f.write('# Netscape HTTP Cookie File\n')
       for c in cookies:
           domain = c.get('domain', '.pimpbunny.com')
           expires = int(float(c.get('expires', 0) or 0))
           if expires < 0: expires = 0
           f.write(f'{domain}\tTRUE\t{c.get("path","/")}\tTRUE\t{expires}\t{c.get("name","")}\t{c.get("value","")}\n')
   ```

5. **Download with curl** (single connection, good for <200MB):
   ```bash
   curl -fL --retry 3 --max-time 600 \
     --cookie /tmp/cookies.txt \
     -H "Referer: https://pimpbunny.com/videos/.../" \
     -o /mnt/storage/videos/title.mp4 \
     "$video_url"
   ```

6. **Or download with aria2c** (faster: 5 parallel connections, resume support):
   ```bash
   aria2c --max-connection-per-server=5 --split=5 --min-split-size=1M \
     --continue=true --allow-overwrite=true \
     --load-cookies=/tmp/cookies.txt \
     -H "Referer: https://pimpbunny.com/videos/.../" \
     -d /mnt/storage/videos -o title.mp4 "$video_url"
   ```

**Key findings from 2026-07-10 session (AlannasWorldx FFM + Queen Egirl):**

- **JSON-LD contentUrl is the 720p version** (`*_720p.mp4`). The 1080p version exists on the page with a different hash (`*_1080p.mp4`) but its access token may not be valid — stick with the contentUrl from JSON-LD.
- **get_file URLs redirect** to `st{XX}.pimpbunny.com/remote_control.php?...&file=...` which serves the MP4. The redirect chain handles auth — just pass cookies + referer.
- **Cookies must be fresh** — extracted within the same session as the download. The PHPSESSID cookie has `expires=-1` (session cookie) — clamp to 0 in Netscape format.
- **Single-file size**: ~660MB for a 30min 720p video.
- **Download speed**: ~200-250KB/s from st40.pimpbunny.com via curl. aria2c with 5 connections is proportionally faster.

**videosnap CLI cannot run** — the `backend/queue.py` module shadows Python's stdlib `queue` module, triggering a circular import crash when any backend module is imported. The working standalone download script is at `/tmp/pimp_dl2.py` (uses node service directly via urllib, no backend imports). A more advanced version at `/tmp/dl_aria2.py` uses aria2c with multi-connection and resume.

**yt-dlp won't work directly** — pimpbunny returns `Unable to extract flashvars` error because the video player is JavaScript-rendered. The get_file URL when passed to yt-dlp gets misinterpreted as a generic extractor URL and fails with `Requested format is not available`.

**Blob URL limitation (note):** Pimpbunny loads video via JavaScript `blob:` URLs. The underlying `get_file` URLs are session-signed. Extraction via Puppeteer + JSON-LD is the only reliable method.

**yt-dlp approaches (all less reliable):**
1. `yt-dlp --impersonate chrome` — fails with `Unable to extract flashvars`
2. `yt-dlp --cookies-from-browser chrome --impersonate chrome` — may work if a real Chrome session exists on the machine
3. `yt-dlp --force-generic-extractor <get_file_url>` — fails, URL gets mangled through remote_control.php

### pornhub.com

**Current approach (works as of 2026-07): `--impersonate chrome`**
Pornhub returns HTTP 474 (custom anti-bot code) to stock requests. The `--impersonate chrome` flag uses curl_cffi to mimic Chrome's TLS fingerprint — bypasses 474 entirely. No Puppeteer, no cookie extraction, no extra services needed.

CLI command:
```bash
~/.local/bin/yt-dlp --impersonate chrome \
  --format "bestvideo[height<=1080]+bestaudio/best[height<=1080]" \
  --merge-output-format mp4 \
  --output "/mnt/storage/videos/%(title)s [%(id)s].%(ext)s" \
  --no-playlist --socket-timeout 30 \
  "https://www.pornhub.com/view_video.php?viewkey=..."
```

**Speed note:** Direct MP4 format (when available) downloads at 7-8 MiB/s. HLS streams are rate-limited to ~500-800 KiB/s on Pornhub's CDN. yt-dlp picks whichever 1080p format is available — no way to force direct MP4.

**Prerequisite:** `curl_cffi` must be installed. `yt-dlp stable@2026.06.09+` includes it. Check with `python3 -c "import curl_cffi; print('ok')"`.

**Legacy info (outdated, kept for history):**
- yt-dlp used to require PhantomJS — `--impersonate chrome` supersedes this
- Puppeteer sniff via node_service was previous fallback — no longer necessary
- Many viewkeys still dead — expect 60%+ failure rate on older videos
- Viewkey dedup: checks `[viewkey].mp4` on disk before queuing

### Other sites (youporn, xhamster, xnxx, redtube, spankbang, eporner, porntn)
- yt-dlp native extractor works for most
- **xnxx.com** — direct video URLs (not search) work with `yt-dlp --impersonate chrome`. Tested 2026-07-08: BangBros Mia Malkova scene, 241MB HLS, downloaded cleanly.
- **xhamster.com** — works with `yt-dlp --impersonate chrome`. Tested 2026-07-08: VRBangers scene, 76MB HLS.
- **pimpbunny.com** — try `yt-dlp --impersonate chrome` first before falling back to custom curl extraction.
- Fall back to Puppeteer sniff or curl if yt-dlp fails

## Cross-Site Dedup

1. **Viewkey match** (instant): `viewkey=XXXX` matched against `[XXXX].mp4` files on disk
2. **Title+duration match**: yt-dlp --dump-json or curl title extraction, grouped by normalized title + 5s duration bucket
3. **Filename match**: MP4s indexed by stripping `re.sub(r'\\s*\\[[^\\]]+\\]\\.mp4$', '', filename)`
4. **Title-similarity match** (aggressive): Strip site prefixes, viewkeys, quality tags, and generic scene words. Files sharing the same normalized title text are flagged regardless of hash — same title = same scene, keep the largest. See `references/library-maintenance.md` for the full workflow.

**User preference for aggressive dedup:** "If one is 80-90% the same, it's a duplicate." Same title text after stripping `[viewkey]` and quality tags = duplicate, regardless of hash. Delete the smaller file. Do not second-guess with hash checks on same-titled files — the title match IS the signal.

Run the full dedup script: `cd /tmp && python3 smart_dedup.py`

## VideoSnap CLI

The VideoSnap project at `/media/kubuntux/DEVELOPMENT1/video-downloader/` has a CLI entry point at `videosnap` and a FastAPI API.

**CLI entry point:** `/media/kubuntux/DEVELOPMENT1/video-downloader/videosnap`

**IMPORTANT: Invoke with `python3` prefix** — the shebang (`#!/usr/bin/env python3`) fails on this mounted filesystem (`/media/kubuntux/DEVELOPMENT1/`). Direct execution gives "Permission denied" despite correct file permissions. Always run as:
```bash
python3 /media/kubuntux/DEVELOPMENT1/video-downloader/videosnap dl <url> --quality 1080p --output /path
```

**`--quality` values are strict choices:** must match exactly one of `{best,1080p,720p,480p,360p,audio}`. Passing `1080` (bare integer) fails with exit code 2. Always use the string with the `p` suffix.

**Browser bypass dependency:** videosnap internally uses `browser_bypass.py` which connects to a Puppeteer Node service at `NODE_SERVICE_URL` (default `http://localhost:3001`). If this service isn't running, every blocked URL (eporner, beeg, redtube) fails with "Browser bypass unavailable: All connection attempts failed". **Start it before any batch download run:**
```bash
cd /media/kubuntux/DEVELOPMENT1/video-downloader/backend/node_service
NODE_PATH=$(pwd)/node_modules node index.js
# Verify: curl -s http://localhost:3001/health → {"status":"ok"}
```

**Known fix needed before first use:** The `backend/queue.py` module shadows Python's stdlib `queue` module, causing a circular import crash (`AttributeError: partially initialized module 'queue' has no attribute 'LifoQueue'`). Rename it to `download_queue.py` and update all `from queue import …` → `from download_queue import …` in `cli.py`, `cli_impl.py`, and `main.py`.

**VideoSnap's browser_bypass module currently fails** for pornhub (HTTP 474). The fix is to pass `--impersonate chrome` through to yt-dlp directly rather than relying on the custom bypass chain.

## Troubleshooting

**HTTP 500 on health — DB schema mismatch:**
```bash
for col in title site strategy size_mb; do
  sqlite3 /mnt/storage/videos/.url2video.db "ALTER TABLE jobs ADD COLUMN $col TEXT;"
done
```

**Port 8800 in use:** `kill $(lsof -ti :8800 2>/dev/null)`\n\n**Service unresponsive:** Kill process, restart. DB persists.\n\n**Clear failed jobs:** `curl -X POST http://localhost:8800/queue/clear-failed`\n\n**Orphaned processing processes:** Before starting a new download/convert workflow in a fresh session, check for orphaned ffmpeg or conversion processes from prior sessions. These survive session boundaries and continue running silently, consuming RAM and writing to ghost (deleted) temp files:\n```bash\npgrep -a -f "ffmpeg.*vr2normal|ffmpeg.*hequirect|ffmpeg.*input.mp4"\n# Kill them:\npkill -f "ffmpeg.*vr2normal|ffmpeg.*hequirect" 2>/dev/null\npgrep -a -f "vr2normal convert|videosnap dl.*vr" 2>/dev/null\n```\nAlso sweep stale fragment files that accumulate across sessions:\n```bash\nfind /mnt/storage/videos -name "*.part" -size -50M -delete 2>/dev/null\nfind /mnt/storage/videos -name "*.ytdl" -delete 2>/dev/null\nfind /mnt/storage/videos -name "*.part-Frag*" -delete 2>/dev/null\n```

## Config (env vars)

| Variable | Default | Description |
|----------|---------|-------------|
| OUTPUT_DIR | /mnt/storage/videos | Download target |
| MAX_CONCURRENT | 4 | Background worker threads |
| URL2VIDEO_PORT | 8800 | HTTP API port |
| NODE_SERVICE_URL | http://localhost:3001 | Puppeteer endpoint |

## Cron Automation (clean_downloader.py)

A lightweight cron-based downloader runs alongside url2video to process deduped queues:

- **Script:** `/tmp/clean_downloader.py`
- **Cron:** `lin-worker` Hermes cron job, every 5 minutes
- **Queue:** `/tmp/video_queue_deduped_final.txt`
- **Done list:** `/tmp/video_done.txt`
- **Lock:** `/tmp/clean_downloader.lock` (prevents overlap)
- **Concurrency:** 2 simultaneous yt-dlp processes max
- **Output:** Same `/mnt/storage/videos/` as url2video

Uses yt-dlp directly (no aria2c). Skips already-downloaded URLs via done file. Format: `bestvideo[height<=1080]+bestaudio/best[height<=1080]`.

**Title blocklist** (before download): BBC, interracial, BWC, black cock/dick/pussy. Uses yt-dlp --dump-json to check title, downloads only after passing.

**Pitfall:** clean_downloader uses a different filename format (`%(title)s [%(id)s].%(ext)s`) than url2video (`sanitize(title) [hash].mp4`). This means the two downloaders produce different filenames for the same video — the offline dedup reference covers how to find real content duplicates across both naming schemes.

**Pitfall:** The clean_downloader cron and url2video service can conflict over the same output directory. Ensure only one is running at a time, or monitor for duplicate files. The cron dedup checks the done file first, url2video checks viewkey on disk — different dedup strategies, so the same URL can download via both if not coordinated.

## VR Conversion via vr2normal

When the user provides VR video URLs (eporner VR, etc.), run them through the vr2normal pipeline at `/media/kubuntux/DEVELOPMENT1/vr2normal/`. This tool downloads the source AND converts VR projections to flat MP4 in one command — no separate download step needed.

**CLI usage:**
```bash
cd /media/kubuntux/DEVELOPMENT1/vr2normal
./vr2normal convert "<eporner_vr_url>" --quality 1080 --output /mnt/storage/videos/flat_final
```

- `--quality` accepts `720`, `1080`, or `4k` (default `1080`) — INT, not string like videosnap
- Output dir defaults to `/mnt/storage/videos/flat_final/`
- Tool auto-detects: SBS VR180, equirect 360°, over-under, or flat source — no manual flagging
- You can run `./vr2normal check` first to verify ffmpeg/GPU/output dir are all sane

**What it does under the hood (from the README, AMD RX 580 on Mesa RADV):**
1. Downloads via yt-dlp (excludes AV1 since RX 580 has no AV1 hardware decode)
2. Detects layout: SBS / equirect / over-under / flat
3. GPU path (when available): VAAPI decode → Vulkan/libplacebo shader → piped raw frames → h264_vaapi encode
4. CPU fallback: single ffmpeg process with `v360` filter + VAAPI encode if available

**Batch conversion (3+ VR videos) — USE THE QUEUE CLI (CORRECT):**

DO NOT launch multiple `./vr2normal convert` processes in parallel, and do NOT use the API server's `/convert` endpoint for batches — both overload the GPU. The README's dedicated `queue` subcommand is THE correct path. Jobs run **strictly one at a time** because the GPU pipeline (Vulkan shader + VAAPI encode on RX 580) is not safe to share across concurrent ffmpeg processes:

```bash
# 1. Add URLs to the queue (stored at ~/.vr2normal/queue.json)
cd /media/kubuntux/DEVELOPMENT1/vr2normal
./vr2normal queue add "https://www.eporner.com/video-XXXXXX/vr-title/" --quality 1080
./vr2normal queue add "https://www.eporner.com/video-YYYYYY/vr-title2/" --quality 1080

# 2. Process everything pending one at a time
./vr2normal queue run

# 3. Check status
./vr2normal queue list          # pending only
./vr2normal queue list --all    # includes completed/failed

# 4. Management
./vr2normal queue clear         # remove finished/failed jobs
./vr2normal queue remove <id>   # drop a single pending job
```

One-off conversions (1-2 videos) are fine with the direct CLI:
```bash
./vr2normal convert "<url>" --quality 1080 --output /mnt/storage/videos/flat_final
```

Batch jobs (3+) MUST use the `queue add` + `queue run` CLI — never parallel background processes, never the API server's `/convert` endpoint.

**One-off conversion CLI:**
```bash
cd /media/kubuntux/DEVELOPMENT1/vr2normal
./vr2normal convert "<eporner_vr_url>" --quality 1080 --output /mnt/storage/videos/flat_final
```

**Pitfalls:**
- **SIGTERM (exit 143) on long 1080p conversions:** The Vulkan pipe pipeline (stage 1 → stage 2) can trigger a SIGTERM from the pipe reader on long videos (2209s 36-min sources). The 720p quality path completed successfully — 1080p may need a retry or quality downgrade for very long sources
- **Flat source detected ≠ error:** Some VR URLs are actually flat (1280x720 av1). vr2normal detects this and just scales to 1080p. Output is in `flat_final/` alongside real VR conversions
- **Output naming:** vr2normal generates `flat_XXXXXXXX.mp4` with a random suffix — not human-readable. The output path is printed on completion
- **AV1 avoidance:** The tool explicitly excludes AV1 formats because RX 580 has no AV1 hardware decode. This is correct — don't override it
- **NEVER run parallel `./vr2normal convert` processes.** The user will correct this. Always use the `queue add` + `queue run` CLI for 3+ conversions — never the API server's `/convert` endpoint either (both spawn concurrent pipeline instances). The parallel pattern overloads both download bandwidth and GPU encoder throughput.

## SMB Sharing

Output folder `/mnt/storage/videos` is exported as the SMB share `\\KUBUNTUX\videos`:

```
# smb.conf definition:
[videos]
   comment = Videos
   path = /mnt/storage/videos
   browseable = yes
   read only = no
   valid users = kubuntux
   force user = kubuntux
   force group = kubuntux
```

**Auth:** Requires kubuntux credentials (not guest). Accessible over Tailscale via kubuntux's Tailscale IP 100.93.75.87.

## Library Maintenance (SMB Videos Folder)

Periodic cleanup removes duplicates and non-video junk from `/mnt/storage/videos/`. Run after a download batch or when space is tight.

### Phase 1 — Scrub non-video files
Remove these accumulators:
- `.info.json` — yt-dlp metadata (safe once download verified)
- `.temp.mp4` — partial/incomplete downloads
- `0-byte files` — failed/stalled downloads
- `.txt`, `.sh` — queue lists, dedup reports, leftover helper scripts
- Orphan dirs (`.queue/`, `eporner_batch/`, `media/`, `processed/`)

### Phase 2 — Hash-based exact duplicates
MD5-hash first 64KB + file size as composite signature. Same sig = same file. Delete all but the largest, preferring filenames with a `[viewkey]` over bare filenames.

```python
with open(fp, 'rb') as fh:
    sig = f'{sz}:{hashlib.md5(fh.read(65536)).hexdigest()}'
```

Full MD5 for files with size ratio >0.95 to confirm byte-identical content.

### Phase 3 — Title-similarity dedup
Normalize filenames: strip `[viewkey]`, quality tags (`1080p`, `720p`, etc.), and site prefixes (`EPORNER.COM - `, `BT_`, `AM_`, `DD_`, `BTPOV_`).

1. **Exact same normalized title** → remove the smaller (same scene, duplicate upload)
2. **Same performer + >60% title similarity** → likely same scene from different studios (e.g. Brattysis vs Stepsis) — prompt user or apply aggressive rule
3. **Same performer + identical title, different hash** → remove the smaller (user preference: "80-90% same = duplicate")

**Aggressive rule:** Same title after stripping `[viewkey]` and quality tags = duplicate, period. Keep the largest file.

### Phase 4 — Duration-match dedup (same duration = same scene)

Group files by performer + duration to find same-scene duplicates with
DIFFERENT titles (same video uploaded to different studios/sites).

```python
# Get duration with ffprobe
def get_dur(f):
    r = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
                       '-of','default=noprint_wrappers=1:nokey=1', f],
                      capture_output=True, text=True, timeout=30)
    return float(r.stdout.strip())

# Group by performer name + duration bucket (5s bucket)
from collections import defaultdict
watch_list = defaultdict(list)
for f, dur in durations.items():
    bucket = int(dur / 5) * 5
    for p in known_performers:
        if p.lower() in f.lower():
            watch_list[(p.lower(), bucket)].append((dur, f))
```

**Aggressive duration rule:** Same duration (±5s) + same performer = same scene =
duplicate. Keep the largest file. Do not second-guess with hash checks — the
user's rule is explicit: "if the time is the same, it's a duplicate."

**Cross-performer caution:** Duration matching only works within the same performer.
A 28.4min "Lana Rhoades POV Part 2" and a 28.4min "Lana Rhoades 6" are the same
scene at different quality — delete the smaller.

### Phase 5 — Verify
```bash
cd /mnt/storage/videos
ls *.mp4 *.mkv *.webm 2>/dev/null | wc -l   # video count
du -sh .                                      # total size
```

See `references/library-maintenance.md` for worked example and exact commands from a recent cleanup session.

## Related Files

- `references/session-log-2026-07-08-adhoc-downloads.md` — ad-hoc single-URL download session with user-provided URLs; demonstrates the background process pattern, interrupt resume, and the direct-URL-bypasses-filters rule.
- `references/vr-conversion-session-2026-07-13.md` — VR batch conversion session: correct `queue` CLI workflow vs wrong parallel/API patterns, pimpbunny extraction re-verification, SIGTERM pitfall on long 1080p conversions.
- `references/borntobefuck-extraction.md` — two-step player iframe -> HLS extraction
- `references/cross-site-dedup.md` — viewkey, title+duration, and filename dedup patterns
- `references/offline-collection-dedup.md` — hash-based dedup for already-downloaded collections (checks by viewkey, exact size, and content hash)
- `references/library-maintenance.md` — full worked example from 2026-07-08 cleanup: non-video scrub, hash-based exact dedup, title-similarity dedup, final results
- `references/post-download-cleanup.md` — dedup methodology, BBC/non-POV detection patterns, file removal policy, and the complete cleanup workflow used in Jul 2026 (45GB reclaimed)

## Borntobefuck & Pimpbunny Extraction Scripts

- `scripts/bornto_sniff.cjs` — single-video Puppeteer click-and-capture for borntobefuck HLS
- `scripts/btbf_batch_extract.cjs` — batch borntobefuck extraction (reuses browser across multiple IDs)
- `scripts/pimpbunny_extract.cjs` — Puppeteer JSON-LD extraction for pimpbunny (returns contentUrl + cookies)

## Local Dedup Scripts

Runnable scripts at `/tmp/`:
- `/tmp/smart_dedup.py` — full three-phase dedup (viewkey + curl title + cross-site)
- `/tmp/cross_site_dedup_fast.py` — fast non-pornhub only dedup
- `/tmp/full_dedup.py` — full title extraction attempt
