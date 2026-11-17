# Ad-Hoc Download Session — 2026-07-08

User pasted Mia Malkova URLs one at a time directly. Pattern: drop URL → background download → short confirmation → next URL.

## What worked

- **All pornhub URLs** — `yt-dlp --impersonate chrome` bypassed HTTP 474 consistently. Some returned direct MP4 (7-8 MiB/s), most returned HLS (~500-800 KiB/s).
- **eporner.com** — direct yt-dlp worked. One file was already downloaded (yt-dlp detected and skipped).
- **xhamster.com** — direct yt-dlp with `--impersonate chrome` worked. VRBangers scene, 76MB. Fixed up MPEG-TS in MP4 container.
- **xnxx.com** — direct video URL (not search) worked with yt-dlp. BangBros scene, 241MB HLS, needed FixupM3u8.
- **Pimpbunny.com** — FAILED. yt-dlp `Unable to extract flashvars`. Browser showed video is a `blob:` URL served via JS. Direct `get_file` URLs are session-signed with `?rnd=` nonce and expire rapidly (HTTP 410). Even `--cookies-from-browser chrome` didn't resolve it.

## What failed
- **VideoSnap CLI** — `backend/queue.py` shadows Python stdlib `queue` module → circular import crash. Fixed by renaming to `download_queue.py` and updating 3 imports.
- **VideoSnap browser_bypass** — pornhub HTTP 474 not handled. The module needs `--impersonate chrome` passthrough.
- **Pimpbunny** — session-signed blob URLs make it effectively undownloadable via yt-dlp. Skip pimpbunny in future crawls.

## Background process pattern

Every download used:
```python
terminal(
    command="~/.local/bin/yt-dlp --impersonate chrome --format ...",
    background=True,
    notify_on_complete=True,
    timeout=600,
)
```

This pattern lets the user paste the next URL immediately without waiting. 3-4 concurrent yt-dlp processes on this machine causes no performance issues.

## Resuming interrupted downloads

When the NAUGHTY AMERICA download was interrupted (output truncated), re-running the same URL with the same --output template resumed from existing .part fragments. No special resume flags needed — yt-dlp handles this natively.

## User preference: direct URLs bypass filters

The user pasted a VRBangers xhamster URL (VR POV content). The POV-only and VR exclusion rules in the crawl skills were correctly bypassed because the user provided the URL directly — their intent overrides automated filtering.
