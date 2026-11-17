---
name: pov-video-crawler
description: "Crawl multiple sites (eporner, xhamster, spankbang, porntn, pimpbunny, pornhub) for performer-specific POV videos. Collect URLs, filter by quality/exclusions, batch download with yt-dlp+aria2c, deduplicate, and clean up. For Dylan's recurring POV video collection workflow."
tags: ["video", "download", "crawl", "pov", "batch", "yt-dlp"]
---

# POV Video Crawler

## When to Use
User asks to crawl/collect/download POV videos by performer names across multiple adult sites.

## Workflow

### 0. Use the two-phase architecture (mandatory)

**Never interleave search and download in a single pass.** The user explicitly corrected this: *"are we not just crawling the urls then downloading is that not smarter"*. Search then download is 4x faster because:
- Searches complete in 10-20 min for 40 performers × 10 sites (no download waiting)
- Downloads run at full CDN speed with no search overhead
- Dedup can happen between phases — same video appears across 3+ sites with different URLs
- Failed downloads can be retried without re-crawling

**Phase 1 (crawl):** Search all performers × all sites, write URLs to `/tmp/video_queue.txt` in `performer|site|url` format. Run for 10-20 min.

**Phase 1.5 (dedup, mandatory):** Normalize slugs, group by video, drop cross-site dupes, drop URLs already in library. See `media/performer-targeted-media-scraping/references/dedup-strategy.md`.

**Phase 2 (download):** Feed deduped queue to url2video OR custom parallel downloader. url2video is the primary choice.

### 0.5. Sort performers by current count, lowest first

The user explicitly requires: *"remember we want to find videos with the lowest count first"*. Re-count from disk before each run, sort ascending. Zero-vid performers get hit before top-tier. This prevents popular performers (Mia Malkova 39) from drowning out starved ones (Lulu Chu 0).

### 1. Know the User's Preferences (Dylan)
- **NO BBC/interracial/BWC/ebony** — ever, across ALL content. Filter aggressively by checking URL slugs AND page titles. Use the keyword list: `bbc, bwc, interracial, black, ebony, blacked, blackedraw, blacked raw`.
- **POV-only** — reject non-POV studio scenes (Vixen, Brazzers non-POV, Blacked Raw, Reality Kings non-POV, Girlsway, Transfixed, Futa/Futanari content, VR) UNLESS the title explicitly contains "POV". Use `is_pov(title)` logic: title must contain "pov" OR none of the non-POV studio keywords.
- **RULE: Direct user-provided URLs bypass ALL filters.** When the user pastes a URL by hand (not from an automated crawl), download it regardless of content filters. The user has already screened it. VR, non-POV studio content, or any other filter rule applies only to automated discovery — never to user-curated URLs.
- **Asian is OK** — but only top Asian performers (Lulu Chu, Asa Akira, Lily Lane, Kimmy Granger, Eva Lovia, Cindy Starfall, Jade Kush, Alina Li, Morgan Lee, Ember Snow, Siri Dahl, Richelle Ryan). **Vina Sky removed** (user deleted all videos 2026-07-09). **Emily Willis removed** (user deleted all videos 2026-07-09). NOT random amateur Indonesian/Indian/Pinay content — delete those on sight.
- **Top performers only** — 39-performer list (canonical as of 2026-07-10). Full list in `scripts/performer_scraper.py`. The core: Lana Rhoades, Lauren Phillips, Angela White, Alanna Pow, Kendra Sunderland, Blake Blossom, Blondie Fesser, Karma RX, Violet Myers, Mia Malkova, Nicole Aniston, Sharon Lee, Lena Paul, Sky Bri, Vivian Taylor, Mia Melano, Payton Preslee, Sophie Dee, Kali Roses, Ava Nicks, Natasha Nice, Aleksa Mink, Camila Castillo, Riley Reid, Tru Kait, Lulu Chu, Asa Akira, Kimmy Granger, Jade Kush, Eva Lovia, Lily Lane, Ember Snow, Siri Dahl, Richelle Ryan, Lexi Luna, Ava Addams, Rissa May, Alexis Texas (added 2026-07-10). **Tomie Tang removed**, **Vina Sky removed**, **Emily Willis removed**.
- **Site preference (quality):** xhamster > xnxx > redtube > spankbang > porntn > pimpbunny > pornhub > eporner. Eporner is last resort (compressed, rate-limited, garbage filenames).
- **Site diversity matters** — don't dump everything on eporner. Spread across sites evenly.
- **Quality threshold:** Skip files under 20MB. Remove <50MB unknown/amateur. Remove <400MB RisqueCore generic clips. Keep nothing under 480p vertical resolution.

### 2. Crawl for URLs (Per-Site Method)

The working methods per site (see `references/site-search-urls.md` for code). Session notes and manual-scrape findings are in `references/manual-site-scrape-2026-07-12.md`:

| Site | Method | Why |
|------|--------|-----|
| pornhub | yt-dlp --flat-playlist --dump-json on search URL | Confirmed 2026-07-09. Returns title+viewkey. ~40 results/search. |
| redtube | JSON API (`api.redtube.com`) | Clean JSON, no auth needed; manually useful in the 2026-07-12 pass |
| xnxx | curl HTML scrape | yt-dlp rejects search URLs; HTML has clean `<a href="/video-XXX/slug">` |
| eporner | HTML scrape | yt-dlp rejects search URLs; HTML is scrapable and was one of the strongest manual sources |
| spankbang | yt-dlp + impersonate chrome | Cloudflare-protected but yt-dlp impersonate works; skip quickly if it returns nothing useful |
| xhamster | manual HTML scrape | Search-page scraping is spotty but can still return usable pages; don't burn the whole pass here |
| pimpbunny | Puppeteer → JSON-LD contentUrl → curl :3001 | yt-dlp chokes on PHP redirector. Use curl only. See references/pimpbunny-curl-extraction.md |
| borntobefuck | Puppeteer click-and-capture: load player iframe → click play → sniff m3u8 from network requests → yt-dlp with --referer + Origin | Canvas-based player with dynamic HLS. Two CDNs: zavastream (older) and Bunny CDN (newer). See references/borntobefuck-extraction.md |

**Quick combo crawl (Pornhub + XNXX):** Use Pornhub via yt-dlp `--flat-playlist --dump-json`, XNXX via curl HTML scrape (`href="/video-XXX/slug"` extraction). Combined scoring: +3 for POV, +2 for big tits keywords, +1 for performer name match, -5 for compilations. This approach found ~450 new URLs across 37 performers in one pass (~7 min runtime).

For manual site search (performer + site), `web_search` is still the fallback discovery layer:
```
web_search "[performer] pov site:SITE"
```

If `web_search` comes back empty or noisy, switch to site-native search pages/API calls directly. The 2026-07-12 pass found usable URLs that search engines missed, especially from Eporner, XNXX, PornHub, and Redtube. Keep site-specific scraping in the same crawl phase; do not abandon it after one dry query.

If `web_search` dries up, switch to site-native search pages/API calls directly. The 2026-07-12 pass found usable URLs that search engines missed, especially from Eporner, XNXX, PornHub, and Redtube. See `references/2026-07-12-manual-site-scrape-notes.md`.

### 3. Filter URLs (BBC + POV)

```
BLOCKED_KEYWORDS = [bbc, interracial, ebony, bwc, blacked raw, blacked.com, blacks on, blacks.on]
NON_POV_STUDIOS = ["brazzers", "vixen", "blacked raw", "reality kings", "girlsway",
                   "transfixed", "futa", "futanari", "vr", "vrbangers"]
```

**CRITICAL: URL-slug-only content verification is INSUFFICIENT.** The 2026-07-09 session proved this: a slug-only pass claimed 0 BBC violations across 1,975 URLs, but the user confirmed the library was "a fucking mess" with non-POV and BBC content.

**CRITICAL: PornHub viewkey URLs carry ZERO title info.** The URL `http://www.pornhub.com/view_video.php?viewkey=abc123` contains no descriptive text. Title-based filtering at crawl time cannot catch BBC content for these URLs. Post-crawl verification with yt-dlp --get-title on EVERY URL is mandatory. A 20-sample spot check on 450 URLs is NOT verification.

**Real verification** — fetch the actual page title with yt-dlp --get-title on EVERY URL in parallel (xargs -P 8). See `references/parallel-verification.md`.

Save URLs as `performer_name|url|site` for tracking.

### 4. Deduplicate Against Existing Files

**CORRECT — match by video ID:**
```python
def get_video_id(url):
    if 'viewkey=' in url:
        return url.split('viewkey=')[1].split('&')[0]
    if '/video-' in url:
        parts = url.split('/video-')
        if len(parts) > 1:
            return parts[1].split('/')[0][:12]
    return url.rstrip('/').split('/')[-1][:30]
```

Also check URL slug as fallback. DO NOT check by performer name — you'll falsely flag everything as "already have".

When combining multiple crawl outputs, do a two-stage dedupe before download:
1. exact URL dedupe
2. title-key dedupe across sites (normalize punctuation, strip obvious POV boilerplate, pick one winner)

Before download, add a third gate: classify the merged queue into direct-video URLs vs search/profile/social/playlist pages. Keep only direct-video URLs in the download file. See `references/2026-07-12-combined-url-classification.md`.

Write a URL-only file for the downloader after dedupe so batch download stays simple and repeatable.

### 5. Prerequisite: Start the browser bypass service

Before batch downloading, ensure the Puppeteer browser bypass service is running on port 3001. Without it, sites like eporner, redtube, beeg all fail with "Browser bypass unavailable":
  cd /media/kubuntux/DEVELOPMENT1/video-downloader/backend/node_service
  NODE_PATH=$(pwd)/node_modules node index.js
Verify with curl -s http://localhost:3001/health. The Python wrapper is at backend/browser_bypass.py. Start this BEFORE any download run targeting protected sites. If the service was already running from a prior session, it persists — check first before starting a duplicate.

### 6. Batch Download

**First choice:** feed the cleaned URL-only file to `videosnap` or the batch runner.

**Do not batch-download the raw combined crawl file.** It can contain search pages, profile pages, social links, and other non-video noise. The user explicitly called this out after a run where the 204-URL pool was mixed garbage.

**videosnap CLI path and quirks:** The entry point is at `/media/kubuntux/DEVELOPMENT1/video-downloader/videosnap`. Invoke with `python3` prefix — shebang execution fails on this mounted filesystem:
```bash
python3 /media/kubuntux/DEVELOPMENT1/video-downloader/videosnap dl <url> --quality 1080p --output /mnt/storage/videos
```
The `--quality` value must match exactly one of `{best,1080p,720p,480p,360p,audio}` — passing `1080` (integer) fails with exit code 2. The `backend/queue.py` circular-import issue does NOT prevent the `videosnap` entry point from working (confirmed 2026-07-12: 21/73 URL batch succeeded).

**Retry failed URLs with browser bypass:** When the first batch pass fails due to blocked sites, extract failed URLs from the batch log, start the Puppeteer service if not already running, and re-run only the failures. The browser bypass handles Cloudflare JS challenges and session cookies that yt-dlp alone cannot negotiate. Use the same async batch script with `timeout=180` per URL and 2 workers.

**Direct yt-dlp download pattern** (use when videosnap is unavailable):
```bash
grep -oP 'https?://\S+' crawl_file.txt | sort -u | \
  xargs -P 3 -I{} sh -c '
    yt-dlp --impersonate chrome \
      --format "bestvideo[height<=1080]+bestaudio/best[height<=1080]" \
      --merge-output-format mp4 \
      --output "/mnt/storage/videos/%(title)s [%(id)s].%(ext)s" \
      --no-playlist --no-warnings --no-mtime \
      --retries 3 --fragment-retries 3 --socket-timeout 30 \
      "$url" > /dev/null 2>&1'
```
**3 parallel workers** recommended to avoid rate limiting on Pornhub/XNXX.

For per-performer scrapes, run 4 yt-dlp processes in parallel with a 600s per-file timeout. Larger batches (15+ URLs) should be sliced into chunks.

```
yt-dlp -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" \
  --merge-output-format mp4 \
  --downloader aria2c \
  --downloader-args "aria2c:-x16 -s16 -k10M" \
  --retries 10 --fragment-retries 10 \
  --no-playlist --no-warnings \
  --batch-file /tmp/performer_batch.txt
```

### 6. Post-Download Cleanup

- **Exact duplicate removal** — Group files by size, MD5 first 64KB of same-size files, remove dupes.
- **Remove actual trash:**
  - Files under 10MB (corrupt stubs)
  - Amateur Asian content: `abg`, `bocil`, `indonesia`, `bokep`, `jilbab`, `hijab`, `tante`, `pinay`, `desi`, `ngentot`, `indian` in filename
  - `bwc`, `bbc`, `blacked`, `ebony`, `interracial` in filename or title
  - RisqueCore files under 400MB
- **Scan with ffprobe for quality**
- **Verify zero duplicates:** Run a final MD5 scan after cleanup.

### 7. File Organization

Output: `/mnt/storage/videos/`
Queue/watch system: `/mnt/storage/videos/.queue/` (drop .txt files, url per line)

### Max-20 per-performer cap (confirmed 2026-07-09)

**Rule: each performer has a maximum of 20 videos including already-downloaded on disk.**

Before any crawl:
1. Count current videos per performer from disk
2. Calculate `needed = max(0, 20 - current_on_disk)`
3. Only crawl performers where `needed > 0`
4. Performers already at 20+ are skipped

## Pitfalls

- **VR detection via find: avoid `*[Vv][Rr]*` glob patterns.** This catches viewkeys containing vR (e.g., `1EK18vRQ8jO`). Use `-iname "*vr*"` with specific prefix matches instead.
- **Kill active yt-dlp/clean_downloader before cleanup.** Multiple clean_downloader.py processes pile up from the 5-min cron. pkill -f yt-dlp then sweep .part/.ytdl/.info.json fragments.
- **Duplicate detection by performer name is WRONG.** Always check by video ID from the URL, not by performer name.
- **Eporner rate-limits heavily.** Don't run more than 4 concurrent yt-dlp workers against eporner.
- **Worker timeout in batch download scripts**: The `videosnap_batch_download.py` pattern uses `subprocess.run(cmd, capture_output=True, text=True)` with NO timeout. A single hung download (stuck on CDN timeout, Cloudflare challenge, or dead URL) blocks that worker slot indefinitely — the entire batch stalls as remaining slots fill up with stuck workers. Always add `timeout=180` to `subprocess.run` calls in batch scripts, and catch `subprocess.TimeoutExpired` to mark that URL as failed and move on.

  Use 180s not 600s because: with 3 workers and 73 URLs, each stuck URL costs the timeout length. After 2-3 stuck URLs per worker slot (common on eporner/redtube), a 600s timeout makes the batch unrecoverable for 30+ min. 180s catches network hangs fast enough for tube sites, and the faster recovery more than compensates for the rare false-positive timeout on a genuinely slow download.

  **Cleanup on failure:** After a timeout or error, sweep stale `.part` files left by the downloader:
  ```python
  for p in OUTPUT.glob('*.part'):
      if time.time() - p.stat().st_mtime > 60 and p.stat().st_size < 1_000_000:
          p.unlink(missing_ok=True)
  ```
  Also delete orphaned `.ytdl` and `.part-Frag*` files — they accumulate across batch runs.

  **Log progress to file:** Write each attempt (ok/fail) to `/tmp/pov_batch_v2.log` so you can check progress across Hermes sessions even if the batch is still running:
  ```python
  LOG = Path('/tmp/pov_batch_v2.log')
  with LOG.open('a') as f:
      f.write(f'[{idx}/{total}] {"OK" if ok else "ERR"} {url[:80]}\n')
  ```

- **Use terminal(background=true) for long batches, not nohup.** The batch script runs for 30+ min. Using shell-level `nohup` or `&` is blocked by the Hermes tool wrapper. Start it via `terminal(background=true, notify_on_complete=true)` so Hermes tracks the process lifecycle.

- **Check for leftover processes from prior sessions.** When starting a new batch in a fresh Hermes session, always check for orphaned processes first:
  ```bash
  pgrep -a -f "videosnap dl|yt-dlp|videosnap_batch|ffmpeg.*vr|ffmpeg.*hequirect|ffmpeg.*input.mp4|vr2normal convert"
  ```
  Orphaned processes from a dead session may still be running, blocking ports, and writing to deleted temp files (ghost I/O). Kill them before starting fresh.

  **Crucially: don't trust delayed process-notification messages.** When you kill a background process, Hermes delivers a `Background process exited (exit code -15, SIGTERM)` notification minutes later — but that notification refers to the already-killed process, NOT to any live one you started afterward. Multiple delayed SIGTERM notifications can pile up and look like the new conversion failed. Always verify the actual running PID with `ps -p <pid>` or `pgrep -f <pattern>` instead of relying on notification content.

- **Block-list gaps** - "BlacksOnBlondes" slips through `black\s*cock` regex (2026-07-10 session). The pattern expects a space before "cock", but "BlacksOnBlondes" has "Blacks" followed by "On". Add `blacks.?on` to blocked patterns. Both titles found were PornHub viewkey URLs — invisible at crawl time, only caught by post-crawl yt-dlp --get-title verification.
- **PornHub webmasters JSON API requires a Referer header.** Without it you get 403. Use Referer: https://www.pornhub.com/.
- **Spot-checking a sample of URLs and claiming the whole set is clean is not verification.** Run yt-dlp --get-title on EVERY URL in parallel.
- **clean_downloader.py cron pileup.** 5-min cron spawns overlapping instances. Fix: add `flock -n /tmp/clean_downloader.lock` to the cron entry.
- **Download timeout vs worker timeout**: These are two different things. The batch script's `subprocess.run(timeout=180)` guards against hung workers — a single URL shouldn't stall the entire batch. Individual video downloads (yt-dlp) have their own internal timeout (`--socket-timeout 30 --retries 3`). If a 1500MB file truly takes longer than 180s on a slow connection, it'll timeout at the batch level — consider increasing the timeout or splitting the batch into smaller chunks for slow sites.
- **Newly discovered performers (2026-07-09 audit):** WettMelons (8), Dan Dangler (6, `dd_` prefix), Camila Herrera7 (4), Lexi Belle (1), Kate Dee (1), Angel Youngs (1), Jade Hutchison (1), Linda Lan (1), Lani Rivers (1), Louisa Rain (1).
- **After bulk deletions, recount from disk.**
- **3 cleaning strategies for filename matching:** raw stem, underscore-to-space, dot-to-space. Catches leetspeak and unicode formatting that a single pass misses.
- **PimpBunny: yt-dlp cannot handle get_file URLs.** Even with cookies and referer set, yt-dlp's generic extractor fails on the `remote_control.php` redirector with "Requested format is not available". Use curl instead: `curl -fL --retry 3 --max-time 600 --cookie <file> -H "Referer: <page>" -o output.mp4 <contentUrl>`.
- **PimpBunny: JSON-LD contentUrl is the only reliable token.** Other `get_file` URLs in the HTML (1080p, source, 4k variants) have different session-signed hashes that return HTTP 400. Despite being `_720p.mp4`, the JSON-LD contentUrl is what works.
- **PimpBunny: cookie expires=-1 must be clamped.** Puppeteer session cookies return `expires=-1` which breaks Netscape cookie file format. Clamp to 0: `if expires_int < 0: expires_int = 0`.,
