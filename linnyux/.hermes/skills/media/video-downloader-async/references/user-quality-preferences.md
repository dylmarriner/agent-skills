# User Quality Preferences (Dylan)

## Default quality: 1080p

Confirmed 2026-07-10. The user explicitly stated "1080p or less" when asked about download quality defaults.

**Implications:**
- All automated downloads (crawl→queue, single-URL, batch) should cap at 1080p
- The format string `bestvideo[height<=1080]+bestaudio/best[height<=1080]` is the standard
- Do NOT default to `best` (unbounded resolution) unless the user says `--quality best`
- Both `videosnap dl` and `videosnap queue add` defaults were patched from `"best"` to `"1080p"` on 2026-07-10

## Tool naming

The CLI tool is called **videosnap**, not "video2urk" or any other name. The binary lives at:
- `/home/kubuntux/Documents/video-downloader/videosnap` — **BROKEN** (circular import from `backend/queue.py` shadowing stdlib `queue`)
- Working project with extractors + Puppeteer service: `/media/kubuntux/DEVELOPMENT1/video-downloader/`

Fallback when videosnap is broken: direct yt-dlp with `--impersonate chrome` and the 1080p format string, or the Puppeteer service at port 3001 for protected sites.
