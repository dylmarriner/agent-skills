# Concurrent Downloader App — `/home/kubuntux/concurrent_downloader.py`

The user's primary video download tool. An async Python app that wraps yt-dlp with concurrent downloads, proxy rotation, and browser bypass for protected sites.

## Quick start

```bash
# Edit the URL list in the script, then run:
cd /home/kubuntux && ./venv/bin/python3 concurrent_downloader.py
```

## Architecture

### Entry point: `concurrent_downloader.py`

- Async main with `asyncio.run(main())`
- Defaults: 3 concurrent downloads, output to `/mnt/storage/videos/`
- URLs currently hardcoded in the `main()` function (around line 77)
- Each download gets a separate proxy via `ProxyManager`

### Core: `/home/kubuntux/downloader.py` — `VideoDownloader` class

**Quality presets** (via `QUALITY_MAP`):
- `"best"` — bestvideo+bestaudio (unlimited)
- `"1080p"` — max height 1080
- `"720p"`, `"480p"`, `"360p"` — respective limits
- `"audio"` — audio only

**Key method: `download(url, output_dir, quality, proxy, cookie_file, headers)`**

Returns an async generator of events:
```python
{"type": "progress", "percent": 45.2, "speed": "2.3MiB/s", "eta": "01:23"}
{"type": "complete", "filename": "video_title.mp4"}
{"type": "error", "message": "HTTP Error 403"}
```

**Performance tuning in yt-dlp opts:**
- `concurrent_fragment_downloads: 16` — max parallel fragments
- `buffer_size: 131072` (128KB)
- `http_chunk_size: 10485760` (10MB)
- `retries: 50`, `fragment_retries: 50`, `extractor_retries: 20`
- `socket_timeout: 120`, `connect_timeout: 60`
- `nocheckcertificate: True`
- Random User-Agent rotation from a pool of 4 real browser UAs

### Proxy support: `/home/kubuntux/proxy_manager.py`

- Provides `get_healthy_proxy()` → returns proxy or None for direct connection
- `mark_bad(proxy)` to rotate out failed proxies

### Browser bypass: `/home/kubuntux/browser_bypass.py`

- `get_context(url, proxy)` → returns cookies + headers from a real browser session
- `write_cookie_file(cookies)` → writes Netscape-format cookie file for yt-dlp
- Needed for sites that block headless requests (e.g. eporner, borntobefuck)

## How to feed URLs to it

Currently URLs are hardcoded in `concurrent_downloader.py`. To add new URLs:

1. **Edit the file** and add URLs to the `urls` list in `main()`
2. **Or create a wrapper** that accepts CLI args and passes them into the async download function

The app runs under the venv at `/home/kubuntux/venv/bin/python3`.

## Dependencies

- `yt-dlp` (system, in PATH)
- `aiohttp` for async HTTP (proxy manager)
- `playwright` for browser bypass (browser_bypass.py)

## Known pitfall: .php redirect URLs fail

The `VideoDownloader` hardcodes `merge_output_format: "mp4"` which triggers yt-dlp's extension safety check. Sites like pimpbunny.com that redirect through `remote_control.php` cause the error: `ERROR: The extracted extension ('php') is unusual and will be skipped`.

**Workaround**: For sites that serve direct MP4 files via a PHP redirect handler, download with curl instead:
```bash
curl -L --connect-timeout 60 --max-time 3600 \
  -H "Referer: <site_base_url>" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  -o "<output_dir>/<filename>.mp4" "<direct_video_url>"
```
