# Session Log: 2026-07-08 — Pornhub 474 bypass + queue.py circular import fix

## URLs
- New: `/media/kubuntux/DEVELOPMENT1/video-downloader/` — VideoSnap project (full FastAPI app)
- Old: `/home/kubuntux/video-downloader/url2video.py` — earlier single-file service
- Output: `/mnt/storage/videos/` — SMB share `\\KUBUNTUX\videos`

## What happened

**Problem 1: `queue.py` circular import**
```
AttributeError: partially initialized module 'queue' has no attribute 'LifoQueue'
```
Cause: `backend/queue.py` shadows Python stdlib `queue`. urllib3 (→ yt-dlp) tries `from queue import LifoQueue` and gets the local module.

Fix: rename to `download_queue.py`, update imports in `cli.py`, `main.py`, `cli_impl.py`. The error cascades through urllib3 → yt-dlp → cryptodome → cookies → local `queue.py`.

**Problem 2: Pornhub HTTP 474**
```
HTTP Error 474: Client Error
```
Pornhub returns 474 to block non-browser requests. Stock yt-dlp (even via the Python API) triggers it.

Fix: use `--impersonate chrome` flag. Works because curl_cffi (bundled with modern yt-dlp) mimics Chrome's TLS fingerprint. yt-dlp stable@2026.06.09 has this built in — no Puppeteer, no cookie extraction, no extra services needed.

## Working download command
```bash
~/.local/bin/yt-dlp --impersonate chrome \
  --format "bestvideo[height<=1080]+bestaudio/best[height<=1080]" \
  --merge-output-format mp4 \
  --output "/mnt/storage/videos/%(title)s [%(id)s].%(ext)s" \
  --no-playlist \
  --socket-timeout 30 \
  "https://www.pornhub.com/view_video.php?viewkey=..."
```

## Result
**ANGELA WHITE - POV Threesome with Mia Malkova [ph62f7567a08d45].mp4** — 135MB, 1080p, 17s at 7.72MiB/s. Output landed in `/mnt/storage/videos/` which is exposed as `\\KUBUNTUX\videos` SMB share.

## Samba on this machine
- Already running: `smbd` active, `[videos]` share at `/mnt/storage/videos`
- Auth required: `valid users = kubuntux`
- Other shares include `[storage]` (whole drive) and `[DEVELOPMENT1]` (guest accessible)
- SMB is directly accessible from the LAN/Tailscale network
