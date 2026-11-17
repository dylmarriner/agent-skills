# PimpBunny curl extraction (proven working 2026-07-10)

## Why yt-dlp fails

PimpBunny's `get_file` URLs redirect through `remote_control.php` on `stXX.pimpbunny.com`.
yt-dlp's generic extractor can't parse this — even with `--cookies` and `--referer`,
it errors: "Requested format is not available".

## Working pipeline

### 1. Start Puppeteer node service (if not running)
```bash
cd /media/kubuntux/DEVELOPMENT1/video-downloader/backend/node_service
NODE_PATH=$(pwd)/node_modules node index.js
```
Health check: `curl -s http://localhost:3001/health`

### 2. Extract page with Puppeteer
```bash
curl -s http://localhost:3001/extract-page -X POST \
  -H "Content-Type: application/json" \
  -d '{"url":"https://pimpbunny.com/videos/<slug>/"}' \
  -o /tmp/extract.json
```

### 3. Parse JSON-LD for contentUrl and title
```python
import json, re
with open('/tmp/extract.json') as f:
    data = json.load(f)
html = data.get('html', '')
cookies = data.get('cookies', [])

for m in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL):
    obj = json.loads(m.group(1))
    content_url = obj.get('contentUrl', '').rstrip('/?')
    title = obj.get('name', '')
    break
```

**Must use contentUrl from JSON-LD** — this has the valid session token.
Other `get_file` URLs in the page (1080p, source, 4k variants) have different
hash tokens that return HTTP 400 with the current session cookies.

Despite being labelled `_720p.mp4`, the JSON-LD contentUrl is the ONLY reliably
working video URL. Video size is typically 600-700MB.

### 4. Write cookies with expiry fix
Puppeteer returns `expires=-1` for PHPSESSID session cookies.
Netscape cookie file format requires non-negative int:
```python
expires = c.get("expires", 0) or 0
try: expires_int = int(float(expires))
except: expires_int = 0
if expires_int < 0: expires_int = 0
```

### 5. Download with curl
```bash
curl -fL --retry 3 --max-time 600 \
  --cookie cookies.txt \
  -H "Referer: https://pimpbunny.com/videos/<slug>/" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  -o "/mnt/storage/videos/<title>.mp4" \
  "https://pimpbunny.com/get_file/.../<id>_720p.mp4"
```

Redirect chain: `get_file` → 302 `remote_control.php?...` → 206 `video/mp4` from `stXX.pimpbunny.com`

### 6. Cleanup
Remove temp cookie file after download.

## What does NOT work

| Approach | Result |
|----------|--------|
| yt-dlp direct | "Requested format is not available" |
| yt-dlp + --cookies --referer | Same error |
| curl on 1080p URL from HTML | HTTP 400 (wrong token) |
| curl without cookies | Cloudflare challenge / redirect to login |
| yt-dlp --force-generic-extractor | Falls into flashvars error |

## Standalone script

`/tmp/pimp_dl2.py` — self-contained (no `backend/` imports), handles full pipeline.
