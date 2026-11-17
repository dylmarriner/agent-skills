# Crawl & Download Techniques (2026-06-28 update)

## Eporner Tag Page Scraping

curl -s -L -H 'User-Agent: Mozilla/5.0' URL | grep -oP 'href="(/video-[^"]+)"' | sed 's|^|https://www.eporner.com|'

## Performer Tag URL Patterns

- https://www.eporner.com/tag/PERFORMER-pov/
- https://www.eporner.com/pornstar/PERFORMER-CODE/
- https://www.eporner.com/tag/big-tits-asian-pov/ (Asian big tits tag, 16K+ videos)

## Pornhub URL Extraction

- Viewkey format: https://www.pornhub.com/view_video.php?viewkey=XXXXX
- Requires `--impersonate chrome` for yt-dlp (Cloudflare)
- Search: web_search "pornhub [performer] pov"

## xnxx.com

- URL format: https://www.xnxx.com/video-XXXXXXX/title-slug/
- Works with standard yt-dlp + aria2c

## redtube.com

- URL format: https://www.redtube.com/NNNNNN
- Works with standard yt-dlp + aria2c

## BBC/Interracial Filter Keywords

bbc, bwc, interracial, black cock, black dick, black guy, black man, black girl, ebony, blacked, blackedraw, monster cock (when paired with BBC context)

## Cloudflare Bypass (spankbang.com, pornhub.com)

```bash
# Install requirement
pip install --break-system-packages --user curl_cffi

# Download with impersonation
yt-dlp --impersonate chrome -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" \
  --merge-output-format mp4 --retries 50 --no-playlist <URL>
```

## Puppeteer Sniff Service (pimpbunny.com, borntobefuck.com)

```bash
# Start service (background, port 3001)
cd /home/kubuntux/video-downloader/backend/node_service
CHROMIUM_PATH=/usr/bin/chromium-browser node index.js &

# Health check
curl -s -X POST http://localhost:3001/health -H 'Content-Type: application/json' -d '{}'

# Sniff video URL
curl -s -X POST http://localhost:3001/sniff-video \
  -H 'Content-Type: application/json' \
  -d '{"url": "VIDEO_PAGE_URL"}'

# Response: {success: bool, videos: [{url, score, source, ...}], page_title: str}
# Pick videos[0]['url'] (highest score) for download
```

## Dedup — CORRECT Video-ID Method

```python
def get_video_id(url):
    if 'viewkey=' in url:
        return url.split('viewkey=')[1].split('&')[0]
    if '/video-' in url:
        parts = url.split('/video-')
        if len(parts) > 1:
            return parts[1].split('/')[0][:12]
    return url.rstrip('/').split('/')[-1][:30]

# Match video ID against ALL existing filenames
for ef in existing_files:
    if vid_id.lower() in ef.lower():
        return True  # already have this exact video
```

DO NOT match by performer name — that's broken and flags everything as dupes.

## yt-dlp with aria2c (max speed)

--downloader aria2c --downloader-args "aria2c:-x16 -s16 -k10M --max-connection-per-server=16 --split=16 --min-split-size=10M"

- -x16 = max 16 connections per server
- -s16 = split file into 16 segments
- -k10M = 10MB per segment

## Post-Download Cleanup

### Find exact duplicates (fast MD5 of first 64KB):
Group files by size, then MD5-hash first 64KB of same-size files.

### Find corrupt/low-quality:
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,duration -of json FILE

Remove if: duration < 20s, width < 500 or height < 400 (but KEEP 406x720+ vertical POV encodes — those are normal eporner vertical videos), ffprobe exits non-zero.

### Amateur Asian trash to delete on sight:
abg, bocil, indonesia, bokep, jilbab, hijab, tante, pinay, desi, ngentot, indian in filename.

### BWC/BBC content that slipped through:
bwc, bbc, blacked, ebony, interracial in filename. User wants ZERO of these.

## Multi-Worker Strategy

Launch 1 yt-dlp worker per site. DO NOT launch 8 workers on the same site (they compete for CDN bandwidth and trigger rate limits). Example for 7 sites with 151 URLs:

| Worker | Site | URLs | Method |
|--------|------|------|--------|
| 1 | xnxx.com | 30 | direct + aria2c |
| 2 | xhamster.com | 32 | direct + aria2c |
| 3 | redtube.com | 31 | direct + aria2c |
| 4 | spankbang.com | 15 | impersonate chrome |
| 5 | pornhub.com | 18 | impersonate chrome |
| 6 | porntn.com | 19 | direct + aria2c |
| 7 | eporner.com | 6 | direct + aria2c |
