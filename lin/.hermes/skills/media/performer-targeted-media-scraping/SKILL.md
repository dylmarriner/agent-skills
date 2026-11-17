---
name: performer-targeted-media-scraping
description: Per-site scraping of adult video sites for specific performer lists. Trigger when user wants to find and download POV videos of named performers across multiple adult tube sites. Hard constraints are NO BBC and POV-only.
---

# Performer-Targeted Media Scraping

Scrape a defined list of adult performers from 10+ tube sites, download POV content in parallel, with strict BBC/interracial blocking and priority-based performer ordering (lowest-count performers first).

**Architecture: TWO-PHASE pipeline. Do NOT interleave search and download — it's 4x slower. The user explicitly corrected this: "are we not just crawling the urls then downloading is that not smarter". YES.**

- **Phase 1 (crawler)**: Search all performers across all sites → save URLs to queue file (`/tmp/video_queue.txt`, format: `performer|site|url`). No downloading, just URL collection with title-based filtering. Runs in ~10-20 min for 40 performers.
- **Phase 1.5 (dedup)**: MANDATORY after crawl. Dedup the queue for cross-site duplicates — same video appears on PornHub AND RedTube AND XNXX with different URLs. **Two dedup passes**: URL-level (in-memory `seen` set) and title-level cross-site via metadata resolution. See `references/metadata-dedup-strategy.md`. Without this step, 821 raw URLs becomes ~500-550 after dedup.\n- **Phase 2 (downloader)**: **USE URL2VIDEO FULL STACK** — the user's custom service at `~/video-downloader/new-backend/url2video.py` (port 8800). It handles queue persistence (SQLite), background worker threads (async architecture, never blocks), per-site extraction, aria2c download engine, and built-in viewkey dedup. Feed it by posting URLs to `POST /q`. Monitor with `curl -s http://localhost:8800/health`. Fallback to `/tmp/phase2_downloader.py` only if url2video is unavailable or has been explicitly killed by the user.

Both phases can run simultaneously: Phase 2 downloads while Phase 1 adds more URLs to the queue.

## When to Use

- User provides a list of performer names and wants videos found + downloaded
- Existing library has uneven coverage (some performers with 30+ videos, others with 0-2)
- Sites block generic POV search but allow per-performer targeted fetches

## Status-Check Protocol

- **Do NOT use `sleep N` commands to wait and poll** — it annoys the user. Check status with direct commands: `ps`, `wc -l`, `find -mmin`, `tail`. The user can see the state in one shot.
- When Phase 2 is downloading, check: `ps aux | grep yt-dlp | wc -l` (active workers), `find ... -mmin -3 -name '*.mp4'` (completed), `find ... -mmin -5 -name '*.part'` (in progress)

## Hard Constraints (User Policy)

- **NO BBC / interracial / ebony / BWC / cuckold content** — block list must include:
  - `bbc`, `interracial`, `ebony`, `bwc`, `blacked raw`, `blacked.com`
  - `big white dick`, `big black dick`, `cuck`, `cucks`
  - `white cock for asian`, `brazzers bbc`, `interracial creampie`, `interracial anal`
- **POV-only** - reject titles matching non-POV studio markers (brazzers, vixen, blacked, reality kings, girlsway, transfixed, futa, futanari, family sinners, pure taboo, mommy's girl, new sensations, tushy, tushyraw, mofos, private, digital playground) UNLESS the title contains `pov`
- **Priority order** - performers sorted by current video count ASCENDING, zero-count performers get hit before top-tier

## Site Strategy Matrix

Each site needs a different approach. Do NOT assume `yt-dlp --impersonate chrome` works uniformly:

| Site | Mechanism | Notes |
|------|-----------|-------|
| **PornHub** | `yt-dlp --flat-playlist --dump-json` on search URL | **Confirmed working 2026-07-09.** Returns title+viewkey for filtering. ~40 results per search. Filter with BLOCKED regex + score by POV/tits relevance. No auth needed. |
| **RedTube** | `api.redtube.com/?data=redtube.Videos.searchVideos&...` JSON API | 5-8 results/req, public API no auth |
| **XNXX** | HTML scrape `/search/<slug>` for `<a href="/video-<id>/..."` | ~37 results/page |
| **Eporner** | HTML scrape `/search/<q>/` for `<a href="/video-...">` | Filter out `THUMBNUM` placeholders |
| **XVideos** | HTML scrape `/?k=<q>` for `xvideos.com/video<id>/...` | Watch for `.red` mirrors |
| **YouPorn** | HTML scrape `/search/?query=...` for `/watch/<id>/<slug>` | |
| **PornTN** | HTML scrape `/search/<q>/` for `porntn.com/video/<id>/...` | |
| **TnAFLIX** | HTML scrape `search.php?what=<q>` for `tnaflix.com/.../video<id>` | Use `" ".join(url.split("/")[-2:])` for slug |
| **SpankBang** | `yt-dlp --impersonate chrome --flat-playlist --dump-json` on `/s/<q>/` | Cloudflare-blocked direct curl |
| **XHamster** | HTML scrape `/search/<q>` for `xhamster.com/videos/<slug>-<id>` | Returns 520 without proper headers |
| **PimpBunny** | HTML scrape `/search/<q>/` for `pimpbunny.com/embed/<id>/` | |
| **PornHub pornstar page** | HTML scrape `/pornstar/<slug>` for `/view_video.php?viewkey=...` | Alt to API when quota-limited |

## Downloader Setup

**PRIMARY: url2video full stack.** The user's custom video-downloader service handles queue management (SQLite), deduplication, retries, 10 concurrent downloads, CDN URL extraction, and 1080p cap natively. Always prefer it over custom scripts.

```bash
# Start the service
cd ~/video-downloader/backend && python3 url2video.py  # Port 8800

# Feed it URLs (one per line)
awk -F'|' '{print $NF}' /tmp/video_queue_deduped.txt > /mnt/storage/videos/.queue/batch.txt

# Monitor
curl -s http://localhost:8800/q
```

It watches `/mnt/storage/videos/.queue/` for `.txt` files and auto-processes them. Queue is persisted in SQLite at `/mnt/storage/videos/.url2video.db`. Completed files go to `/mnt/storage/videos/` with the `--downloader aria2c -x16 -s16 -k10M` args.

**Fallback: Phase 2 downloader** (`/tmp/phase2_downloader.py`) when url2video is unavailable:

```python
YTDLP = "/home/kubuntux/.local/bin/yt-dlp"
TIMEOUT = 600  # 10 min per file — files are 400-1500MB, CDN at 2-5MB/s
MAX_PARALLEL = 6  # concurrent workers

cmd = [
    YTDLP, "--impersonate", "chrome",
    "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
    "--merge-output-format", "mp4",
    "--downloader", "aria2c",
    "--downloader-args", "aria2c:-x16 -s16 -k10M",
    "--retries", "3",
    "--fragment-retries", "3",
    "--no-playlist", "--no-warnings",
    "-o", f"{OUTDIR}/%(title).120s [%(id)s].%(ext)s",
    url
]
```

**Do NOT mark timeouts as done** — they must be retried. Only write to the done file when a `.mp4` was actually created and verified on disk.

**Queue file format** (`/tmp/video_queue.txt`): `performer_name|site|video_url` — one per line, appended by Phase 1. Phase 2 skips URLs appearing in `/tmp/video_done.txt`.

## Queue Backup Protocol

Before any dedup pass, **copy the current queue file** to preserve intermediate state:

```bash
cp /tmp/video_queue.txt /tmp/video_queue_backup_$(date +%s).txt
```

This session produced 4 queue files (raw, deduped, final, deduped-final). Keep all of them until the next Phase 1 run confirms they're stale. Multiple dedup passes with different thresholds can turn 821 raw URLs into 552, then into ~400 final, and you may want to roll back.

## Cleanup Rules

After any cleanup pass (performer deletions, VR removals, fragment sweeps, sub-file-size purges):
- **Recount from disk.** Don't trust cached counts — the file listing changes after every bulk delete.
- **Delete sub-100MB files on cleanup runs.** These are usually corrupt stubs, partial downloads, or low-quality encodes.
- **Delete VR videos.** Use `-iname "*vr*"` with specific prefix checks (NOT `*[Vv][Rr]*` which randomly matches viewkeys).
- **Hash/numeric filenames are trash.** Delete files matching `^[a-z0-9]{10,40}(?:_flat|_source|_720p|_1080p)?$` — these are corrupt or renamed partials.
- **Sweep .part/.ytdl/.info.json/.temp fragments** before counting or presenting library state.

## Pitfalls

- **clean_downloader.py cron pileup.** The 5-min cron at /tmp/clean_downloader.py spawns overlapping instances when downloads exceed 5 min, accumulating 3-5 concurrent clean_downloader processes. Before any cleanup, pkill both yt-dlp and clean_downloader, then sweep fragments in one pass. Fix: add `flock -n /tmp/clean_downloader.lock` to the cron entry.
- **VR detection: avoid `*[Vv][Rr]*` glob patterns.** This catches viewkeys containing vR (e.g., `1EK18vRQ8jO` is mistakenly classified as VR). Use `-iname "*vr*"` with specific prefix matches instead.
- **New performers to add to patterns (2026-07-09 audit):** WettMelons, Dan Dangler (`dd_` prefix), Camila Herrera7, Lexi Belle, Kate Dee, Angel Youngs, Jade Hutchison, Linda Lan, Lani Rivers, Louisa Rain. These have matching filenames on disk.
- **180s timeout is too short** for files above 600MB. CDN speeds are 2-5MB/s with aria2c + impersonate overhead. Use **600s minimum**. Single-threaded CDN connections can drop to 800KB/s on some sites.
- **Do NOT interleave search and download in one pass** — it's 4x slower. Downloads block the search loop, and timeouts waste the URLs already found. Two-phase (crawl → download) lets downloads run at full speed without search overhead.
- **Do NOT mark timed-out downloads as done** — they must be retried. Only write to `/tmp/video_done.txt` when a `.mp4` was actually created on disk.
- **aria2c with 16 connections** can leave orphan aria2c processes if yt-dlp is killed mid-download. Clean up `.part` files explicitly.
- **Block-list gaps** - "mixed" is too broad (rejects legit content). "big white dick" and "cuck" are needed explicit terms. "Blacked" alone misses "BLACKED RAW" variations, so use both `blacked raw` and `blacked.com`. **"Big White Dick Pounds Asian Wife" slipped through** as an interracial-adjacent title — the BBC block list must include `big white dick` and `big black dick` literally.
- **Filenames on disk use `%(title).120s [%(id)s].mp4` format** — dedup against library needs to strip the `[id]` bracket, then leet-normalize and strip non-alphanumeric. Library filenames frequently use different IDs than the queue URLs (e.g., `Brattysis Lulu Chu... [65ef3242bec12].mp4` uses ID `65ef3242bec12`, queue uses `viewkey=65ef3242bec12`), so simple ID match misses most files. Big-bigram title overlap > 0.4 is a reliable fuzzy dupe signal.
- **POV filter is the inverse of block** - allow studio content (Brazzers, Vixen) if the title contains "pov", not as a hard block.
- **TnAFLIX URL slug extraction** uses `" ".join(full.split("/")[-2:])` — Python 3 literal, not `m.split(...).join(...)`.
- **Output filename format** `%(title).120s [%(id)s].%(ext)s` keeps titles truncated to 120 chars to avoid filesystem limits. The previous 100-char limit was too tight for some titles.
- **Log to file with line buffering** (`open(path, "a", buffering=1)`) so background processes do not lose output to stdout buffering.
- **After any code edit, restart the scraper** - running Python processes do not reload edited source.
- **Cloudflare 403/520/522 on SpankBang/XHamster** without `--impersonate chrome`. Plain `urllib` request fails silently.
- **yt-dlp extractors return "Unsupported URL"** for many valid site search URLs even though the extractor exists - the URL format changed and the extractor was not updated. Use HTML scrape or API instead.
- **Don't sleep-poll** — the user finds `sleep 60; sleep 120; sleep 180` chains annoying. Check status with direct commands. Show state once, not a running commentary. Just respond to messages — running terminal checks for 5+ minutes without output is also noise. If the user asks "how's it going", give one snapshot, not a running tally.
- **Video page URLs are SLOW** — `--impersonate chrome` on `/view_video.php?viewkey=...` goes through the player wrapper, adding latency and capping throughput at ~1MB/s. Direct CDN URLs (`ev-h.phncdn.com/hls/videos/...mp4`) from `yt-dlp -g` hit 5-12MB/s. The site JSON APIs return video page URLs — extracting the CDN URL first cuts download time 3-5x. url2video handles CDN extraction internally.
- **url2video crashes on startup with FastAPI `on_startup` error** in current FastAPI versions (0.110+). The port binds (so it looks alive) but no endpoints work and the watch loop never processes the queue. Fix: edit the app init to remove `on_startup=[...]` (FastAPI deprecated that param) and use `lifespan` context manager instead, or pin `fastapi<0.100`. Symptom: `curl http://localhost:8800/q` returns `{"detail":"Not Found"}` despite the process being up.
- **url2video's SQLite DB has no `/q/clear` endpoint** — to wipe and restart cleanly, you must `rm /mnt/storage/videos/.url2video.db` and restart the service. The `/q/{job_id}` DELETE endpoint only removes individual jobs, not all queued work.
- **The watch loop in url2video moves processed `.txt` files to `processed/` almost instantly** — if the queue DB ends up empty after the file moves, the watch loop didn't parse URLs correctly. Most common cause: file has `performer|site|url` format instead of bare URLs. url2video expects ONE URL per line, no pipes.
- **url2video can get stuck in an infinite retry loop on a single job** — symptom: log shows the same job ID 10-20 times in 1 second, all `Starting <id>: <url>`, no actual progress. The DB says `downloading` but no yt-dlp child process exists. Fix: directly `UPDATE jobs SET status='failed' WHERE status='downloading'` on the SQLite DB, then the worker picks the next queued job. Killing the parent process is more disruptive.
- **url2video stdout goes to a pipe, not a file** — if you start it via `&` in bash, logs vanish. Always start with explicit redirect: `python3 -u url2video.py > /tmp/url2video.log 2>&1` so you can see what it's doing.
- **url2video watch files must be bare URLs only** — the watch loop reads ONE URL per line. If you drop a file with `performer|site|url` format, it will silently fail (file moves to `processed/` but 0 URLs enqueued). Use `awk -F'|' '{print $NF}'` to strip the prefix.
- **"bbc" in PornHub viewkeys is a false positive** — viewkeys like `64c3bbc516493` contain "bbc" because the key is a hex hash, not because the video is BBC content. Remove such queue entries anyway to be safe, but note it's a false positive.
- **False positive "big white dick" matches** — the slug `viewkey=6971fa10d3bbc` contains "bbc" and gets flagged even though the video title is clean. After the Phase 1 crawl, scan the deduped queue for any remaining "bbc|interracial|cuck" in URL strings and remove them.
- **Old stale DB prevents fresh feed** — url2video has a SQLite DB that persists across restarts. A previous run's 1400+ queued jobs will be processed before your new batch. Always `rm /mnt/storage/videos/.url2video.db` before restarting url2video for a fresh crawl.
- **url2video lifespan logs show "Reset N stale downloading jobs to queued"** at startup. If you see non-zero N without an explanation, a previous instance crashed mid-download — those jobs need to be reset. After a clean kill, expect 0.
- **url2video "Reset stale downloading jobs to queued" includes jobs from OLD watch files** — if the DB has 130+ queued jobs from an old feed sitting for a day, url2video will process them all before touching your new batch. Solution: nuke the DB and start fresh.
- **OSError: [Errno 36] File name too long** can happen with `%(title)` if titles exceed 240 chars — use `%(title).120s` to truncate safely. Already a pitfall, but combined with the per-site URL slug extraction, can hit edge cases.
- **Background `notification` messages from killed processes are misleading** — when you kill a process, Hermes delivers a `Background process exited (exit code -15, SIGTERM)` notification, but the LIVE process running the same task is unrelated. Always check `ps -p <pid>` for the actual current PID, not the one named in the notification.
- **Metadata resolution for dedup is slow** — `yt-dlp --dump-json --skip-download` runs at ~6 URLs/min for sites that require `--impersonate chrome`. For 555 URLs that's 90+ min. Don't block Phase 2 on metadata resolution — run the resolver in background, dedup new entries as metadata arrives. The 13% false-negative rate from slug-only dedup is acceptable trade-off vs blocking downloads.
- **SpankBang pornstar pages (`/lulu-chu/`) need a different URL than search results** — the extractor treats them as different playlist types. Use `/s/{q}/` search first, fall back to `/{slug}/` pornstar page. Both need `--impersonate chrome` to bypass Cloudflare.
- **Top performers dominate the queue (Vina Sky alone = 42 URLs)** — without a hard per-performer cap, low-count performers get buried. Cap to 5-8 URLs per performer per site, OR sort by current count and allocate based on inverse count (more URLs for performers with 0-2 vids). The sorted list covers 40 performers; the zero-count 8 get searched first.
- **"bbc" in viewkey is a false positive** — PornHub viewkeys like `64c3bbc516493` contain "bbc" but are unrelated to content. Only check the actual video title, not the URL string. Remove ALL queue entries containing "bbc" in the URL before downloading to be safe, but note that this also removes false positives.

## Working Performer List (40 performers, priority-sorted by current vid count, 2026-06-28)

Performers sorted by lowest current count FIRST — zero-vid performers get searched first. Re-count from disk before each run with `os.listdir()`.

```
0:  Kimmy Granger, Jade Kush, Eva Lovia, Lily Lane, Ember Snow, Siri Dahl, Richelle Ryan (Vina Sky removed 2026-07-09)
1:  Ava Nicks, Camila Castillo, Tru Kait, Lexi Luna, Ava Addams, Rissa May, Faith (Emily Willis removed 2026-07-09)
2:  Natasha Nice, Lulu Chu
4:  Sophie Dee, Aleksa Mink, Riley Reid
6:  Kali Roses
7:  Asa Akira
9:  Lena Paul, Payton Preslee
10: Sky Bri, Mia Melano
11: Alanna Pow
12: Sharon Lee
13: Karma Rx
14: Vivian Taylor
15: Blondie Fesser
16: Angela White, Kendra Sunderland
19: Nicole Aniston
22: Blake Blossom
24: Lana Rhoades
25: Lauren Phillips
26: Violet Myers
29: Mia Malkova
```

Asian OK if professional (Asa Akira, Lulu Chu, Kimmy Granger, Lily Lane, Eva Lovia). **Tomie Tang removed** (2026-07-09). **Vina Sky removed** (2026-07-09). **Emily Willis removed** (2026-07-09). NOT random amateur Indonesian/Indian/Pinay content — delete those on sight.

## Script Template

The two-phase pipeline lives at:
- `/tmp/phase1_crawler.py` — URL collector (10 sites, BBC/POV filter, dedup)
- `/tmp/phase2_downloader.py` — parallel downloader (6 workers, 600s timeout, retry-on-timeout)

See `references/dedup-strategy.md` for URL-level dedup, `references/metadata-dedup-strategy.md` for title-based cross-site dedup, `references/two-phase-architecture.md` for the full pipeline, `references/url2video-operations.md` for url2video service gotchas, `scripts/meta_deduper.py` for the runnable cross-site deduper, and `scripts/clean_downloader.py` for the fallback parallel downloader.

## Verification

After Phase 1: dedup the queue before launching Phase 2. See `references/dedup-strategy.md` for the full dedup pipeline.

After a run:
- `wc -l /tmp/performer_scraper.log` shows progress per performer
- `find /mnt/storage/videos/ -name "*.mp4" -mmin -10 ! -name "*.part*"` should be non-zero
- No `.part` files older than 1 hour (sign of stuck downloads)
- BBC check: `grep -li "bbc\|interracial" /mnt/storage/videos/*.mp4 2>/dev/null` should return nothing
