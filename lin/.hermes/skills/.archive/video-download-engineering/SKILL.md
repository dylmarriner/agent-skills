---
name: video-download-engineering
description: >-
  Build video download infrastructure: yt-dlp integration, custom per-site
  extractors for bot-protected sites, Puppeteer stealth bypass, proxy rotation,
  download queues, ffmpeg VR→flat conversion with GPU acceleration, and SMB
  upload. Use when working on any video download toolchain.
domain: backend
tags:
  - video-download
  - yt-dlp
  - puppeteer
  - ffmpeg
  - vaapi
  - extractors
  - smb
version: 1.0.0
author: agent
---

# Video Download Engineering

Build reliable video download infrastructure that handles bot-protected sites,
VR conversion, GPU-accelerated encoding, and SMB delivery.

## When to Use

- Downloading videos from sites that block yt-dlp (pimpbunny, borntobefuck, etc.)
- Building a download queue with background workers
- Converting VR (180°/360°) videos to flat MP4
- Using AMD GPU (VAAPI) acceleration for encoding
- Uploading results to an SMB share
- Setting up a Puppeteer-based page extraction service

## Architecture Overview

```
User URL → Custom Extractor (registry pattern)
             ↓
         yt-dlp (direct URL + cookies + referer)
             ↓
         ffmpeg VR→flat (VAAPI GPU encode)
             ↓
         SMB upload (smbclient put)
             ↓
         Queue DB (SQLite async worker)
```

## Custom Per-Site Extractors

For sites yt-dlp can't handle, build a registered extractor module.

### Registry Pattern

```python
# backend/extractors/__init__.py
import re

_extractors: list[tuple[re.Pattern, callable]] = []

def register(pattern: str):
    def wrap(fn):
        _extractors.append((re.compile(pattern, re.IGNORECASE), fn))
        return fn
    return wrap

async def extract(url: str) -> dict | None:
    for pat, fn in _extractors:
        if pat.search(url):
            result = await fn(url)
            if result:
                return result
    return None
```

### Extractor Contract

Each extractor returns `dict` with keys: `url`, `title`, `ext`, `source`, `cookie_file?`, `referer?`
Or `None` if it can't handle the URL.

### Puppeteer Page Extraction

For sites that require JavaScript execution:

1. Node microservice at `backend/node_service/index.js`
2. Endpoints: `POST /extract-cookies`, `POST /extract-page` (returns full HTML after JS)
3. Python client at `backend/browser_bypass.py` with `extract_page(url)` method
4. Parse the HTML for video URLs: JSON-LD `contentUrl`, `get_file` URLs, `<video>` tags

**Puppeteer launch flags for stealth:**
```
--no-sandbox --disable-setuid-sandbox --disable-dev-shm-usage
--disable-accelerated-2d-canvas --no-first-run --no-zygote --disable-gpu
```

**Set CHROMIUM_PATH env var** since Puppeteer may not find Chrome by default:
```bash
CHROMIUM_PATH=/usr/bin/chromium-browser node index.js
```

### Page HTML Video URL Extraction Order

1. JSON-LD: `<script type="application/ld+json">` → parse `contentUrl`
2. `get_file` URLs: `get_file_1080p.mp4`, `get_file_720p.mp4`, `get_file_src.mp4`
3. Direct `.mp4` URLs in scripts or data attributes
4. `<video src="...">` tags

## VR→Flat Conversion with ffmpeg

### Format Detection (ffprobe)

```python
def _detect_vr_format(w: int, h: int) -> str:
    ratio = w / h
    if ratio >= 2.5:      return "sbs"       # side-by-side
    if h >= 2 * w:        return "ou"        # over-under
    if 1.8 <= ratio <= 2.2: return "equirect" # 360° equirect
    return "flat"                              # already flat
```

### Filter Chains by Format

| Format | Filter Chain |
|--------|-------------|
| SBS  | `crop=w/2:h:0:0,scale=1920:1080` |
| OU   | `crop=w:h/2:0:0,scale=1920:1080` |
| Equirect | `v360=equirect:flat:h_fov=120:v_fov=80,scale=1920:1080` |
| Flat | `scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2` |

### VAAPI GPU Encoding (AMD RX 580)

**Key rule: CPU filters first, then `format=nv12,hwupload` for VAAPI encoder.**

```bash
# CORRECT: CPU filters → upload to GPU → VAAPI encode
ffmpeg -i input.mp4 \
  -vf "crop=1920:1080:0:0,scale=1920:1080,format=nv12,hwupload" \
  -c:v h264_vaapi -global_quality 23 -vaapi_device /dev/dri/renderD128 \
  output.mp4

# WRONG: hardware decode + CPU filter combination fails
# -hwaccel vaapi -hwaccel_output_format nv12  ← incompatible
```

**Pitfalls:**
- `-hwaccel vaapi` makes the decoder output GPU surfaces → CPU filters (`crop`, `scale`, `v360`) can't operate on them. **Don't use `-hwaccel` for video with filter chains.**
- `crop` and other CPU filters must come BEFORE `hwupload`, never after.
- The `v360` filter is CPU-only — it can't run on VAAPI surfaces at all.
- Verify VAAPI support: `vainfo` should show the AMD driver and `h264_vaapi` entrypoint.
- Check `/dev/dri/renderD128` exists and the user has read/write access.

### Progress Tracking

Parse ffmpeg stderr for frame numbers:
```python
frame_re = re.compile(r"frame=\s*(\d+)")
total_frames = int(duration * fps)
for line in iter(proc.stderr.readline, ""):
    m = frame_re.search(line)
    if m and total_frames > 0:
        pct = min(int(m.group(1)) / total_frames * 100, 99)
        prog(pct)
```

## yt-dlp Integration

### Format Fallback Chain

yt-dlp can fail if the requested quality isn't available. Always try a fallback chain:

```python
formats_to_try = [
    f"bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]",
    "bestvideo+bestaudio/best",
    "best",
]
```

### Direct URL Passthrough

When custom extractors find a direct CDN URL, pass it to yt-dlp with cookies and Referer:
```python
ydl_opts["format"] = "best"          # Already direct
ydl_opts["cookiefile"] = cookie_file # Auth cookies
ydl_opts["http_headers"]["Referer"] = page_url
```

### Progress Hook (async safe)

```python
def _make_hook(queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    def hook(d: dict):
        if d["status"] == "downloading":
            raw = _strip_ansi(d.get("_percent_str", "")).replace("%", "")
            pct = float(raw) if raw else 0.0
            loop.call_soon_threadsafe(
                lambda: queue.put_nowait({"type": "progress", "percent": round(pct, 1)})
            )
    return hook
```

## Download Queue

### Architecture
- **Storage**: SQLite with WAL mode, `PRAGMA journal_mode=WAL`
- **State machine**: pending → running → completed / failed / cancelled
- **Worker**: async loop with Semaphore(max_concurrent=3)
- **Lifecycle**: worker starts/stops with the API server lifespan

### Key Patterns

See `production-code-hardening` skill's `references/queue-system-pattern.md` for the full pattern.

## SMB Upload

Use `smbclient` CLI (simpler and more reliable than Python smbprotocol):

```python
cmd = [
    "smbclient", f"//{SMB_SERVER}/{SMB_SHARE}",
    "-U", f"{SMB_USER}%{SMB_PASSWORD}",
    "-c", f"cd {SMB_PATH}; put {local_path} {filename}",
]
```

### SMB Troubleshooting

- `NT_STATUS_NOT_FOUND`: hostname doesn't resolve — use IP or Tailscale MagicDNS
- `NT_STATUS_BAD_NETWORK_NAME`: share path doesn't exist on the server — check `testparm -s` for actual paths
- `NT_STATUS_LOGON_FAILURE`: wrong username/password — check `.smbcredentials` files
- `NT_STATUS_ACCESS_DENIED`: permissions on the share directory — check `valid users` in smb.conf and filesystem ownership
- `write cache size` warning in smbclient output: harmless config mismatch between server and client versions

Always create a test file first to verify write access:
```bash
smbclient -U user%pass -c "put /tmp/test.txt test.txt; rm test.txt" //server/Share
```

## References

See `references/vr-conversion-matrix.md` for the complete VR format detection table and per-format filter chain reference.
