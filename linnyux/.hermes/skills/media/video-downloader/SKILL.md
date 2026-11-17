---
name: url2video-download
description: Download videos from pimpbunny.com, borntobefuck.com, spankbang.com and other protected sites
---

# URL2Video Download Patterns

## url2video service (default only when no downloader is specified)

The url2video service on port 8800 is the primary downloader. Queue URLs to it via:
```bash
curl -s -X POST http://localhost:8800/q \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://...","quality":"1080p"}'
```

It handles yt-dlp, proxy rotation, browser bypass, and persistence automatically. See `references/url2video-api.md` for full API.

**Known hang:** url2video can become unresponsive under load (high CPU, port open but no response). Recovery: kill the hung PID, restart as background process. DB persists — no jobs lost.

## DLP queue stack (alternative, when the user names it)

`/home/linnyux/dlp` is a local queue daemon with a pluggable per-site extractor registry, a terminal UI, and its own browser bridge for sites that need JS. Use it when the user says DLP or asks for a custom extractor the existing projects don't have.

```bash
systemctl --user status dlp-daemon.service      # API on :8765
systemctl --user status dlp-pimpbunny-browser.service   # bridge on :3001
tr -d '\n' < ~/.local/share/dlp/api-token      # bearer token
$HOME/.local/bin/dlp --tui                      # live progress
```

- Enqueue: `POST /jobs {"urls":[…],"dest":"/media/linnyux/excitement/Videos"}` with `Authorization: Bearer $TOKEN`; `POST /jobs/{id}/retry`, `POST /jobs/{id}/cancel`, `GET /jobs`.
- Job states are the only truth: `pending`/`running` are not done. Confirm `done` plus a nonzero file before reporting success.
- New extractor = subclass `Extractor` in `src/dlp/extractors/`, exact host matcher, low `priority`, register in `build_default_registry()`; write the routing and parsing tests first and run the suite before queueing real URLs.
- Tuning lives in a systemd drop-in (`~/.config/systemd/user/dlp-daemon.service.d/`), not the unit file: destination via `DLP_DOWNLOAD_DIR`, worker count via `DLP_WORKER_CONCURRENCY`. Four workers is the measured optimum — the browser bridge serialises page loads on its own, so raising it only delays extraction, and past four the CDN's per-IP cap absorbs the gain (4 → ~11.5 MB/s aggregate, 6 → ~10.8, 8 → ~10.9).
- Keep the browser navigation and challenge-wait budgets below the outer client timeout; a bridge call that outlives the caller turns every attempt into a phantom timeout. With three retries at a 45 s navigation timeout the extractor's HTTP client needs ~150 s, and the bridge's systemd unit needs a generous start/stop timeout because it holds a live Chrome.

## pimpbunny.com

**Custom extractor (recommended):** The VideoSnap project at `~/Documents/video-downloader/` has a custom pimpbunny extractor in `backend/extractors/__init__.py`. Uses Puppeteer node service (port 3001) to load page → extract JSON-LD `contentUrl` → yt-dlp with cookies + referer.

**via standalone script (bypasses videosnap circular import):**
```bash
# Ensure Puppeteer node service is running first
cd /media/kubuntux/DEVELOPMENT1/video-downloader/backend/node_service
NODE_PATH=$(pwd)/node_modules node index.js &
# Extract & download
python3 /tmp/pimp_dl.py <pimpbunny_url>
```
The script at `/tmp/pimp_dl.py` calls the node service directly via `urllib.request` (no `backend/` imports — avoids the circular import), extracts JSON-LD contentUrl, writes cookies to Netscape format, and downloads with yt-dlp.

**Manual fallback (Puppeteer direct):**
1. Start node service: `cd /media/kubuntux/DEVELOPMENT1/video-downloader/backend/node_service && NODE_PATH=$(pwd)/node_modules node index.js`
2. Extract page: `curl -s http://localhost:3001/extract-page -X POST -H "Content-Type: application/json" -d '{"url":"<url>"}'`
3. Parse JSON-LD for `contentUrl` field, save cookies
4. Download: `yt-dlp --cookies cookies.txt --referer <url> --impersonate chrome --format "bestvideo[height<=1080]+bestaudio..." <contentUrl>`

**Pick the tokenized rendition, not the JSON-LD URL.** JSON-LD `contentUrl` points at an untokenized `_720p.mp4` that answers `403 text/html` almost always. The player instead streams `https://pimpbunny.com/get_file/..._1080p.mp4/?v-acctoken=…` URLs that serve a normal `206 video/mp4` with the page's cookies and referer. Scrape the page HTML with `get_file/[^"'\s]+?_(\d{3,4})p\.mp4/\?v-acctoken=[^"'\s&]+`, keep variants at or below the requested ceiling, and take the tallest. Tokens expire with the page, so extract and download in the same pass. Use JSON-LD only for the title (`VideoObject.name`) and as a media fallback when no tokenized variant exists.

**Known issue:** yt-dlp's generic extractor can't handle Pimpbunny's flashvars. Don't attempt `--force-generic-extractor` — route to a dedicated browser-backed extractor.

**Name the output file yourself; never let yt-dlp derive it.** The `get_file` URL redirects to `stNN.pimpbunny.com/remote_control.php?file=….mp4&acctoken=…`. The generic extractor then takes its `id` from the whole redirect URL, so `%(title)s [%(id)s].%(ext)s` blows past the 255-byte filename limit (`File name too long`) and the extension resolves to `.php` off `remote_control.php`. Build the stem in code — sanitised page title plus the numeric asset id — leave only `%(ext)s` to yt-dlp, and pass `--remux-video mp4` (a rename, no re-encode, since the stream is already mp4). Same rule for any extractor whose media URL redirects to a `.php`/script endpoint.

**Better: don't hand a redirecting endpoint to yt-dlp at all.** `--remux-video` fixes the *name* but not the *abort* — yt-dlp still errors out with `The extracted extension ('php') is unusual and will be skipped` before a byte is fetched. Drive `aria2c` from the extractor instead, with the resolved media URL, `--out` set to your own `<stem>.mp4`, the Netscape cookie jar via `--load-cookies`, and `Referer`/`Origin`/`User-Agent` as `--header`s. That also buys `--split`/`--max-connection-per-server` (the throughput win) and `--continue=true` (restart resumes instead of re-downloading gigabytes). Keep the yt-dlp path as a fallback for when `aria2c` is absent.

**Bridge reliability.** Bunny Shield rate-limits repeated cold starts, so launch one long-lived Chrome with `userDataDir` on disk (keeps `cf_clearance`/`bunny_shield_id`), serialise page loads behind a promise queue, and retry the navigation up to three times with backoff while polling for the challenge to clear. Wait for `v-acctoken=` to appear in the DOM before reading `page.content()` — the player injects the renditions after the challenge, and a `domcontentloaded` read alone yields a page with no media. Set the navigation timeout well above Chrome's default and keep the outer client timeout larger still, or every attempt dies as a phantom client timeout.

**A 403 here is usually the wrong URL, not a blocked browser.** Before cycling User-Agents, Referers, proxies or cookies, check which URL you asked for: an untokenized `get_file/..._720p.mp4/` (the JSON-LD `contentUrl`) 403s even from a real browser with valid cookies. A tokenized `?v-acctoken=` variant on the same host serves immediately from headless Chrome. Only treat it as a genuine browser gate when the tokenized variant also fails.

**Fallback when even the tokenized variant is gated — hand the resolution to the downloader from the real browser.** The user's own logged-in browser clears the challenge and holds the cookies. Expose a job field for the pre-resolved media URL plus a Cookie header, and have the extractor prefer it over its own browser probe:
- API: `POST /jobs {"urls":[…], "media_url":"…", "cookie":"name=value; …"}`; store the pair as a JSON hint column on the job (migrate with `ALTER TABLE … ADD COLUMN` guarded by a `PRAGMA table_info` check so existing queues survive) and pass it into the extractor context.
- Extractor: if both are present, build the cookie jar from the header and skip the browser entirely; fall back to the browser only when the hint is absent or incomplete.
- The client is a Tampermonkey userscript that reads the page's own tokenized rendition (JSON-LD only as fallback), reads cookies with `GM_cookie.list`, makes its own Range request, and only then POSTs — so a media 403 is reported to the user instead of becoming a silent failed job. Bind the daemon on a reachable interface and keep the bearer token as the gate. DLP ships one at `userscript/dlp-pimpbunny.user.js`; the daemon must be restarted with `DLP_HOST=0.0.0.0` for the browser to reach it.
- Requeue the whole failed set with `POST /jobs/retry-failed` rather than replaying ids one at a time.
- Give the yt-dlp call a `…/best` tail: a video-only selector fails outright on audio-only media.
- Route the userscript at the downloader, not the site's player: it must post the extracted URL, never trigger a browser download.

**Preflight before queueing:**
- Resolve one URL in the browser and require a VideoObject `contentUrl` plus that same page session's cookies. Metadata alone does not prove the CDN will serve the media.
- Preserve the full browser cookie attributes (domain, path, expiry, secure, HttpOnly) in a mode-0600 temporary Netscape cookie jar; pass it to yt-dlp with the page referer and browser User-Agent, adding Origin when required. Do not flatten the cookie list to a bare `Cookie:` header, because domain/path scoping can be lost across redirects.
- Before submitting the batch, make a bounded Range request for the extracted media URL using the exact cookie jar and headers. Verify a video content type and a successful partial response; treat 403, 410, HTML, a tracking GIF, or a challenge page as a failed preflight. Do not enqueue or blindly retry until the cause is resolved.
- Keep the format selector capped at 1080p with no unbounded fallback. Verify the selected media variant also stays under the ceiling.
- Keep the browser navigation and challenge-wait budget shorter than the outer HTTP client's timeout, with server deadlines longer than the full operation; serialize browser extraction when concurrent headless contexts cause timeouts or resource spikes.
- Delete temporary cookie jars in `finally` blocks and never log their contents or tokenized media URLs.

A repeated URL submission is not a reason to repeat the same failing run: retry only after a changed extractor/session path passes the media-URL preflight.

**Report progress from the downloader's own summary, not the file size.** `aria2` expands the output file to its full extent immediately, so `os.stat().st_size` hits the total within a second and a size-polling loop declares success almost instantly while nothing is on disk. Parse its one-second line instead — `[#gid 37MiB/1.3GiB(2%) CN:16 DL:3.9MiB ETA:5m45s]` gives done/total/percent/rate/ETA — and terminate on process exit code, never on size. Same class of bug applies to any downloader that preallocates.

## borntobefuck.com

**Three methods — Puppeteer click-and-capture preferred (see `scripts/bornto_sniff.cjs`), then simple Puppeteer load, lastly curl fallback.**

### Background: two CDN backends

Borntobefuck uses two different CDN backends depending on video age:
- **Zavastream** (`content.zavastream.com/{content_id}/{uuid}/index.m3u8`) — Older videos; HLS URL is directly in the player HTML after Puppeteer rendering. Player page is ~17KB.
- **Bunny CDN** (`vz-*.b-cdn.net/{uuid}/playlist.m3u8`) — Newer videos; HLS URL only appears AFTER clicking play (network request interception). Player page is ~9KB — no video URLs in static HTML.

### Method 1: Puppeteer Click-and-Capture (most reliable — works for both CDNs)

Use the `bornto_sniff.cjs` script (in `scripts/` of this skill) which launches Puppeteer, loads the player page, clicks the play area, and captures `.m3u8` URLs via network request interception:

```bash
cd /media/kubuntux/DEVELOPMENT1/video-downloader/backend/node_service
node <path>/bornto_sniff.cjs <video_id>
```

The script navigates to `https://borntobefuck.com/videos/{id}/player?lang=en`, registers a `.m3u8` request listener, then clicks selectors in order: `.active-video-player`, `.player-container`, `.video-player`, `#player`, `video`, play buttons, then center of page. Waits 8s for HLS manifest, returns JSON with `m3u8s[]`:

```json
{"success":true,"m3u8s":["https://vz-0c578c5b-997.b-cdn.net/{uuid}/playlist.m3u8",".../720p/video.m3u8"]}
```

Download with descriptive output name (raw HLS URLs have no title metadata):

```bash
yt-dlp \
  --referer "https://borntobefuck.com" \
  --add-header "Origin:https://borntobefuck.com" \
  --output "/mnt/storage/videos/borntobefuck_{video_id}.mp4" \
  --merge-output-format mp4 \
  "https://vz-0c578c5b-997.b-cdn.net/{uuid}/720p/video.m3u8"
```

### Method 2: Puppeteer → Player Iframe → HLS page load (Zavastream only)

1. Ensure Puppeteer node service running on :3001: `cd /media/kubuntux/DEVELOPMENT1/video-downloader/backend/node_service && NODE_PATH=$(pwd)/node_modules node index.js`
2. Extract watch page via Puppeteer `/extract-page` to find player iframe (`/videos/{id}/player?lang=en`)
3. Load player iframe via `/extract-page` — HTML contains `content.zavastream.com/{content_id}/{uuid}/index.m3u8`
4. Download with yt-dlp `--referer` + `--add-header "Origin:..."`

### Method 3: curl player page directly (least reliable)
```bash
curl -sL -H "Referer: https://borntobefuck.com/" \
  "https://borntobefuck.com/videos/{id}/player?lang=en" | \
  grep -oP 'https?://[^"'"'"'\\\\s]+\\.m3u8[^"'"'"'\\\\s]*'
```

### Known issues:
- `/watch/NNNNN` format NOT supported by yt-dlp — must extract player iframe first
- videosnap queue add accepts URLs but serve does NOT reliably process for this site
- curl returns ~5KB (incomplete); Puppeteer returns 9-17KB
- Quality cap: 720p most videos; some 480p only (check variant in m3u8s array: `480p/video.m3u8` vs `720p/`)
- **Filenames from raw HLS are useless** — yt-dlp saves as `index [index].mp4`. Always use `--output borntobefuck_{id}.mp4`
- **Dead videos** — `/watch/{id}` returns empty (0-byte) from Puppeteer. Skip these.
- Content ID and UUID vary per video — extract from player page thumbnail reference or m3u8 in captured URLs

## spankbang.com
**Known issue (2026-06):** Returns 403 Forbidden to yt-dlp even with custom User-Agent and Referer headers. The page also blocks curl (returns tiny 5KB block page).

**Possible workaround:**
```bash
yt-dlp --cookies-from-browser chromium <url>
```
This uses browser cookies which may bypass the 403. If that also fails, the site requires a logged-in browser session or is using CDN-level blocking that can't be bypassed.

## xhamster.com
Works well with standard yt-dlp + aria2c. Better encode quality than eporner.com.

## porntn.com
Works with yt-dlp generic extractor. Album pages are valid batch sources. Extraction is slow but downloads once started.

## General rules
- Honor the explicitly requested downloader stack and destination; do not silently switch stacks just because another service supports a site-specific extractor.
- Before queueing a pasted batch, split on whitespace and validate every URL. If one token contains multiple embedded `https://` schemes and the intended boundaries are unambiguous, split at those boundaries and report the parsed count; never send the concatenated token as a URL.
- The user sends URLs and expects execution-first handling: download when possible, then report only verified `DONE: filename` or a concise `FAILED: reason`.
- Before queueing a batch for a protected site, preflight one URL through the intended extractor; require actual media metadata, session cookies, and a tiny Range request to the exact media URL that returns video bytes. Page metadata alone is not proof of download access. On 403/410, retry once against a different rendition of the same asset (tokenized instead of plain, taller variant, different host) before concluding the session is gated; only then stop instead of burning retries on the same URL.
- For a custom extractor, use an exact host/path matcher, register it ahead of the generic handler, and test both routing and metadata parsing before queueing real URLs; otherwise the generic extractor silently claims the URL.
- Treat a rendered challenge/interstitial or missing expected structured metadata as a hard preflight stop; do not claim a download or blindly retry the batch.
- Verify the job reached a terminal success state and its output file exists with nonzero size before reporting `DONE`; queued is not downloaded.
- Honor the requested resolution ceiling in the actual format selector and verify that no fallback branch can select a higher resolution.
- Run downloads in background so the user can keep sending URLs.
- `--impersonate chrome` is ESSENTIAL for pornhub.com (returns HTTP 474 without it). Confirm the target exists first with `yt-dlp --list-impersonate-targets`: the flag is hard-failing, not best-effort — with no targets listed yt-dlp aborts before downloading anything, and the targets come from the `curl_cffi` dependency being installed for yt-dlp's interpreter (apt/wrapper-installed yt-dlp often lacks it) rather than from yt-dlp's version.
- For protected sites, use the VideoSnap project at `/media/kubuntux/DEVELOPMENT1/video-downloader/`:
  - `backend/extractors/` — Python extractors with `@register` decorator pattern
  - `backend/node_service/index.js` — Puppeteer microservice on port 3001
  - `backend/browser_bypass.py` — Client for the Node service
  - **puppeteer-extra is broken** on Node v22 (missing dist/ build). Edit index.js to use `require('puppeteer')` directly instead.
  - **`backend/queue.py` shadows Python stdlib `queue`** — rename to `download_queue.py` if you see circular import errors.
