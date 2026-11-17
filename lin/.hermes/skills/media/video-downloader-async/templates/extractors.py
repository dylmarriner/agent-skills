"""
Extractor templates for video-downloader-async.

Copy this file into your service, then customize the SITE_STRATEGIES dict
in `extract(url)`. Each function returns {title, url, ext} on success or
raises RuntimeError on failure. Wrap in try/except at the call site.
"""

import html as html_module  # NOTE: do NOT name local var `html`
import re
import subprocess
from urllib.parse import urlparse

import httpx

YTDLP = "/home/kubuntux/.local/bin/yt-dlp"
NODE_SERVICE = "http://localhost:3001"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

# ── Generic helpers ──────────────────────────────────────────────────────────

def detect_site(url: str) -> str:
    d = urlparse(url).netloc.replace("www.", "").lower()
    for s in ("pornhub", "youporn", "xhamster", "xnxx", "redtube", "spankbang",
              "pimpbunny", "borntobefuck", "eporner", "porntn"):
        if s in d:
            return s
    return "generic"


def viewkey(url: str) -> str | None:
    m = re.search(r"viewkey=([a-f0-9]+)", url)
    return m.group(1) if m else None


def has_viewkey(vk: str, outdir: str) -> bool:
    if not vk:
        return False
    import os
    for f in os.listdir(outdir):
        if f.endswith(".mp4") and vk in f:
            return True
    return False


# ── Strategy 1: yt-dlp native (fastest for unprotected sites) ───────────────

def extract_ytdlp(url: str, timeout: int = 20) -> dict:
    """
    Run yt-dlp --dump-json. Returns {title, url, ext, duration}.
    Works for: youporn, xhamster, most non-CF sites.
    Fails for: pornhub (needs PhantomJS in latest version), CF-protected sites.
    """
    r = subprocess.run(
        [YTDLP, "--dump-json", "--no-warnings",
         "--socket-timeout", "8", "--max-sleep-interval", "0", "--sleep-interval", "0",
         url],
        capture_output=True, text=True, timeout=timeout,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:200])
    info = __import__("json").loads(r.stdout)
    fmts = info.get("formats") or []
    best = next(
        (f["url"] for f in reversed(fmts)
         if f.get("vcodec") not in (None, "none") and f.get("url")),
        None,
    )
    return {
        "title": info.get("title", "video"),
        "url": best or info.get("url", ""),
        "ext": info.get("ext", "mp4"),
        "duration": info.get("duration"),
    }


# ── Strategy 2: Puppeteer sniff (CF bypass via Chromium) ────────────────────

def extract_puppeteer(url: str, timeout: int = 60) -> dict | None:
    """
    Use node_service /sniff-video to load the page in Puppeteer-stealth,
    intercept network traffic, and return discovered video URLs.

    Returns None if the service is down, the page returns no videos,
    or all sniffed URLs are ad/tracking endpoints.
    """
    try:
        r = httpx.post(f"{NODE_SERVICE}/sniff-video", json={"url": url}, timeout=timeout)
        if r.status_code != 200:
            return None
        data = r.json()
        if not data.get("success"):
            return None

        # Filter out ad/tracking URLs
        AD_DOMAINS = ("trafficjunky", "adtng", "doubleclick", "googlesyndication")
        videos = [
            v for v in data.get("videos", [])
            if not any(ad in v.get("url", "") for ad in AD_DOMAINS)
        ]
        if not videos:
            videos = data.get("videos", [])  # last resort

        if not videos:
            return None

        best = max(videos, key=lambda v: v.get("score", 0) or 0)
        vid_url = best["url"]
        ext = vid_url.split(".")[-1].split("?")[0]
        if len(ext) > 5:
            ext = "mp4"
        title = re.sub(
            r"\s*[-|]\s*(Pornhub|XHamster|XNXX|RedTube|YouPorn|SpankBang|Eporner)\s*.*$",
            "", data.get("page_title", "video"), flags=re.IGNORECASE,
        ).strip()
        return {"title": title or "video", "url": vid_url, "ext": ext}
    except Exception:
        return None


# ── Strategy 3: Puppeteer cookies + curl (for CF sites that yt-dlp can't) ──

def extract_cookies_then_curl(url: str, timeout: int = 30) -> dict:
    """
    1. POST /extract-cookies to node_service → get valid CF cookies + UA
    2. Fetch the page with curl using those cookies
    3. Parse HTML for og:video, <source>, or .mp4/.m3u8 URLs

    Works for: xnxx, redtube, spankbang, eporner, porntn
    """
    r1 = httpx.post(f"{NODE_SERVICE}/extract-cookies", json={"url": url}, timeout=60)
    if r1.status_code != 200:
        raise RuntimeError("cookie extraction failed")
    ctx = r1.json()
    cookies = ctx.get("cookies", [])
    if not cookies:
        raise RuntimeError("no cookies returned")
    headers = ctx.get("headers", {"User-Agent": UA})
    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)

    r2 = subprocess.run(
        ["curl", "-sS", "--max-time", str(timeout), "-L",
         "-H", f"User-Agent: {headers.get('User-Agent', UA)}",
         "-H", f"Cookie: {cookie_str}",
         url],
        capture_output=True, text=True, timeout=timeout + 5,
    )
    if r2.returncode != 0 or len(r2.stdout) < 5000:
        raise RuntimeError("curl with cookies failed")
    page = r2.stdout

    title = None
    for pat in (r'<meta\s+property\s*=\s*["\']og:title["\']\s+content\s*=\s*["\']([^"\']+)["\']',
                r'<title>([^<]+)</title>'):
        m = re.search(pat, page, re.IGNORECASE)
        if m:
            title = html_module.unescape(m.group(1))
            break
    if not title:
        raise RuntimeError("no title in cookied page")

    vid_url = None
    for pat in (r'<meta\s+property\s*=\s*["\']og:video["\']\s+content\s*=\s*["\']([^"\']+)["\']',
                r'<source\s+[^>]*src\s*=\s*["\']([^"\']+\.(?:mp4|m3u8|webm))["\']',
                r'["\'](https?://[^"\']+\.(?:mp4|m3u8|webm)(?:\?[^"\']*)?)["\']'):
        m = re.search(pat, page, re.IGNORECASE)
        if m:
            vid_url = m.group(1)
            if vid_url.startswith("//"):
                vid_url = "https:" + vid_url
            break
    if not vid_url:
        raise RuntimeError("no video URL in cookied page")

    title = re.sub(r"\s*[-|]\s*\w+.*$", "", title, flags=re.IGNORECASE).strip()
    ext = vid_url.split(".")[-1].split("?")[0]
    if ext not in ("mp4", "webm", "mkv"):
        ext = "mp4"
    return {"title": title, "url": vid_url, "ext": ext}


# ── Strategy 4: Custom 2-step (borntobefuck / pimpbunny style) ──────────────

def extract_two_step(url: str, embed_pattern: str, video_pattern: str,
                     timeout: int = 25) -> dict:
    r"""
    Generic template for sites where the main page contains an embed/player
    iframe, and the video URL is in the iframe.

    Args:
        url: main page URL
        embed_pattern: regex for iframe src (e.g. r'/embed/(\d+)')
        video_pattern: regex for video URL on embed page (e.g. r'\.m3u8' or r'get_file/...\.mp4')
    """
    r = subprocess.run(
        ["curl", "-sS", "--max-time", "15", "-L",
         "-A", UA, url],
        capture_output=True, text=True, timeout=20,
    )
    if r.returncode != 0:
        raise RuntimeError("main page fetch failed")

    # Title from main page
    title = None
    m = re.search(r'<meta\s+property\s*=\s*["\']og:title["\']\s+content\s*=\s*["\']([^"\']+)["\']',
                  r.stdout, re.IGNORECASE)
    if m:
        title = html_module.unescape(m.group(1))

    # Find embed URL
    m = re.search(embed_pattern, r.stdout, re.IGNORECASE)
    if not m:
        raise RuntimeError("no embed found")
    embed_url = m.group(1)
    if embed_url.startswith("/"):
        embed_url = "https://" + urlparse(url).netloc + embed_url

    # Fetch embed with referer
    r2 = subprocess.run(
        ["curl", "-sS", "--max-time", "15", "-L",
         "-A", UA, "-H", f"Referer: {url}", embed_url],
        capture_output=True, text=True, timeout=20,
    )
    if r2.returncode != 0 or len(r2.stdout) < 100:
        raise RuntimeError("embed fetch failed")

    m = re.search(video_pattern, r2.stdout, re.IGNORECASE)
    if not m:
        raise RuntimeError("no video URL in embed")
    vid_url = m.group(0).rstrip("'\",;)")
    if not vid_url.startswith("http"):
        vid_url = "https://" + urlparse(url).netloc + (vid_url if vid_url.startswith("/") else "/" + vid_url)

    return {
        "title": (title or "video").split("|")[0].strip(),
        "url": vid_url,
        "ext": "mp4",
    }


# ── Strategy 5: Generic curl HTML (last resort) ─────────────────────────────

def extract_curl(url: str, timeout: int = 15) -> dict:
    """Last-resort: fetch HTML, look for og:video or .mp4 URLs in scripts."""
    r = subprocess.run(
        ["curl", "-sS", "--max-time", str(timeout), "-L",
         "-A", UA, "-H", "Accept: text/html", url],
        capture_output=True, text=True, timeout=timeout + 5,
    )
    if r.returncode != 0 or len(r.stdout) < 2000:
        raise RuntimeError(f"page too small ({len(r.stdout)}B) or failed")
    page = r.stdout  # NOTE: don't name this `html` — shadows the module

    title = None
    for pat in (r'<meta\s+property\s*=\s*["\']og:title["\']\s+content\s*=\s*["\']([^"\']+)["\']',
                r'<title>([^<]+)</title>'):
        m = re.search(pat, page, re.IGNORECASE)
        if m:
            title = html_module.unescape(m.group(1))
            break
    if not title:
        raise RuntimeError("no title")

    vid_url = None
    for pat in (r'<meta\s+property\s*=\s*["\']og:video["\']\s+content\s*=\s*["\']([^"\']+)["\']',
                r'<source\s+[^>]*src\s*=\s*["\']([^"\']+\.(?:mp4|m3u8|webm))["\']',
                r'["\'](https?://[^"\']+\.(?:mp4|m3u8|webm)(?:\?[^"\']*)?)["\']'):
        m = re.search(pat, page, re.IGNORECASE)
        if m:
            vid_url = m.group(1)
            if vid_url.startswith("//"):
                vid_url = "https:" + vid_url
            break
    if not vid_url:
        raise RuntimeError("no video URL")

    return {"title": title, "url": vid_url, "ext": "mp4"}


# ── Dispatch with site-specific strategy chain ──────────────────────────────

def extract(url: str) -> dict | None:
    """Try all strategies in site-specific order. Returns dict or None."""
    site = detect_site(url)

    # Pre-check: viewkey dedup
    vk = viewkey(url)
    if vk and has_viewkey(vk, "/mnt/storage/videos"):
        return {"dupe": True, "viewkey": vk, "title": None}

    # Per-site strategy chains — fast/cheap first, fall through on failure
    CHAINS = {
        "pornhub":      [extract_puppeteer, extract_ytdlp],
        "borntobefuck": [extract_ytdlp, extract_cookies_then_curl, extract_puppeteer],
        "pimpbunny":    [extract_ytdlp, extract_cookies_then_curl, extract_puppeteer],
        "youporn":      [extract_ytdlp],
        "xhamster":     [extract_ytdlp],
        "xnxx":         [extract_ytdlp, extract_cookies_then_curl, extract_puppeteer],
        "redtube":      [extract_ytdlp, extract_cookies_then_curl, extract_puppeteer],
        "spankbang":    [extract_ytdlp, extract_cookies_then_curl, extract_puppeteer],
        "eporner":      [extract_ytdlp, extract_cookies_then_curl, extract_puppeteer],
        "porntn":       [extract_ytdlp, extract_cookies_then_curl, extract_puppeteer],
    }

    chain = CHAINS.get(site, [extract_ytdlp, extract_curl, extract_puppeteer])
    for fn in chain:
        try:
            result = fn(url)
            if result and not result.get("dupe"):
                return result
        except Exception:
            continue
    return None
