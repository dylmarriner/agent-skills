# VideoSnap Custom Extractor Integration

Integrated 2026-07-08 per user request: "can you integrate the custom extractors into it"

## What was done

Added per-site video URL extractors from url2video into VideoSnap.

### New file: `backend/extractors.py`
Copied from `/home/kubuntux/video-downloader/new-backend/extractors.py` with cleanup:
- Site detection (pornhub, youporn, xhamster, xnxx, redtube, spankbang, pimpbunny, borntobefuck, eporner, porntn)
- Curl HTML extraction for pimpbunny/borntobefuck/eporner/porntn
- yt-dlp extraction for youporn/xhamster/xnxx/redtube/spankbang
- Puppeteer sniff for pornhub (via node_service :3001)
- Generic yt-dlp + curl fallbacks

### Modified: `backend/downloader.py`
- Added `resolve_url()` method — calls extractors as pre-flight
- Modified `get_info()` — tries extractors first, enriches with yt-dlp formats
- Modified `download()` — if extractors find a direct CDN URL, feeds it to yt-dlp

## Extractor chain priority
1. Per-site handler (site-specific strategy)
2. yt-dlp generic (for any site yt-dlp knows)
3. curl HTML generic (finds video URLs in raw HTML)
4. Puppeteer sniff (JavaScript-rendered pages)

## Integration point
The `VideoDownloader` class in `downloader.py` tries the custom extractors before falling back to yt-dlp. If the extractors return a direct CDN URL, `get_info()` includes a `direct_url` field. The `download()` method also pre-flights with extractors but still uses yt-dlp for the actual download (yt-dlp handles everything, including direct CDN URLs).
