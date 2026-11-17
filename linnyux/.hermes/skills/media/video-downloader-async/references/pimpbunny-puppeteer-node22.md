# Pimpbunny blob-URL extraction + Puppeteer Node v22 failure (2026-07-08)

## Problem
User wanted to download from pimpbunny.com — all strategies failed:

1. **yt-dlp --impersonate chrome** → `Unable to extract flashvars` (generic extractor)
2. **Custom curl extractors** → Session-signed `get_file` URLs expired by extraction time (HTTP 410)
3. **yt-dlp --cookies-from-browser chrome** → `cannot decrypt v11 cookies: no key found`
4. **Puppeteer sniff** → `MODULE_NOT_FOUND: proxy-agent/dist/index.js` (broken dep on Node v22)
5. **Hermes browser tool** → Blob URL detected (`blob:https://pimpbunny.com/...`) but security sandbox blocked `document.cookie`, `fetch()`, `PerformanceObserver` for network inspection

## Root cause
Pimpbunny loads video via JavaScript `blob:` URL backed by a MediaSource. The underlying CDN URLs (`get_file/.../581977.mp4?rnd=...`) are session-signed with a timestamp nonce that expires rapidly (HTTP 410). Even if extracted, the URL is dead within seconds.

## Puppeteer fix (Node v22)
The installed packages (puppeteer-extra@3.3.6, puppeteer@21.7.0) have stale dependencies:
```
proxy-agent/package.json missing "main" entry
```

Fix: `npm install puppeteer@latest` (v23+) in the node_service directory.

Without fix: plain puppeteer also fails because its dep chain goes through the same broken proxy-agent package. Only upgrading resolves it.

## Workaround for this session
Skip pimpbunny. User accepted the failure and moved on to other sites. Pimpbunny is more trouble than it's worth — 90%+ failure rate across all strategies on this machine.
