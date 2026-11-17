#!/usr/bin/env python3
"""
pimpbunny_download.py — Download videos from pimpbunny.com

Uses the Puppeteer node service (port 3001) to extract the JSON-LD contentUrl,
then downloads with curl (single) or aria2c (multi-connection + resume).

Usage:
  python3 pimpbunny_download.py <url> [url ...]

Requirements:
  - Node service running at http://localhost:3001 (backend/node_service/index.js)
  - curl and/or aria2c installed
  - Python 3 stdlib only (no backend imports — avoids circular import bug)
"""

import json, os, re, subprocess, sys, tempfile, urllib.request

NODE_SERVICE = "http://localhost:3001"
OUTPUT_DIR = "/mnt/storage/videos"
DOWNLOADER = "aria2c"  # 'curl' or 'aria2c'

def extract(url):
    data = json.dumps({"url": url}).encode()
    req = urllib.request.Request(f"{NODE_SERVICE}/extract-page", data=data,
        headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=120)
    return json.loads(resp.read())

def find_video(html):
    """Use contentUrl from JSON-LD (guaranteed working token)."""
    video_url = None
    title = None
    for m in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL):
        try:
            obj = json.loads(m.group(1))
            cu = obj.get("contentUrl") or (
                obj.get("video", {}) if isinstance(obj.get("video"), dict) else {}
            ).get("contentUrl", "")
            if cu:
                video_url = cu.rstrip("/?")
                title = obj.get("name") or obj.get("headline", "")
                break
        except Exception:
            pass
    if not video_url:
        for m in re.finditer(r'(https?://[^"\'\\s<>]*get_file[^"\'\\s<>]*\.mp4[^"\'\\s<>]*)', html):
            video_url = m.group(1).replace("\\", "").rstrip("/?")
            break
    if not title:
        tm = re.search(r'<title>([^<]+)', html)
        if tm:
            title = tm.group(1).split("|")[0].strip()
    return video_url, title

def write_cookies(cookies):
    """Write cookies to a Netscape-format cookie file."""
    lines = ["# Netscape HTTP Cookie File"]
    for c in cookies:
        domain = c.get("domain", ".pimpbunny.com")
        if not domain.startswith("."):
            domain = "." + domain
        secure = "TRUE" if c.get("secure", False) else "FALSE"
        expires = c.get("expires", 0) or 0
        try:
            expires_int = int(float(expires))
        except (TypeError, ValueError):
            expires_int = 0
        if expires_int < 0:
            expires_int = 0  # session cookie — clamp to 0
        lines.append(
            f"{domain}\tTRUE\t{c.get('path','/')}\t{secure}\t{expires_int}\t"
            f"{c.get('name','')}\t{c.get('value','')}"
        )
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
    f.write("\n".join(lines))
    f.close()
    return f.name

def download_curl(video_url, output, cookie_file, referer):
    """Download with curl (single connection)."""
    cmd = [
        "curl", "-fL", "--retry", "3", "--max-time", "1800",
        "--cookie", cookie_file,
        "-H", f"Referer: {referer}",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "-o", output, video_url,
    ]
    print(f"  Downloading via curl...")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if r.returncode == 0:
        size = os.path.getsize(output) if os.path.exists(output) else 0
        print(f"  OK: {output} ({size/1024/1024:.0f}MB)")
        return True
    print(f"  curl failed: {r.stderr[:200]}")
    return False

def download_aria2c(video_url, output, cookie_file, referer):
    """Download with aria2c (5 connections, resume)."""
    continue_flag = "--continue=true" if (
        os.path.exists(output) and os.path.getsize(output) > 0
    ) else "--continue=false"

    header_file = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False).name
    with open(header_file, "w") as f:
        f.write(f"Referer: {referer}\n")
        f.write("User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\n")

    cmd = [
        "aria2c",
        "--max-connection-per-server=5",
        "--split=5",
        "--min-split-size=1M",
        "--max-tries=3",
        "--retry-wait=5",
        "--timeout=120",
        "--max-time=0",
        continue_flag,
        "--allow-overwrite=true",
        f"--load-cookies={cookie_file}",
        f"--header-file={header_file}",
        "--auto-file-renaming=false",
        "-d", os.path.dirname(output),
        "-o", os.path.basename(output),
        video_url,
    ]
    print(f"  Downloading via aria2c...")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
    if r.returncode == 0:
        size = os.path.getsize(output) if os.path.exists(output) else 0
        print(f"  OK: {output} ({size/1024/1024:.0f}MB)")
        return True
    print(f"  aria2c failed: {r.stderr[:200]}")
    # Fallback: try curl
    return download_curl(video_url, output, cookie_file, referer)

def main():
    download = download_aria2c if DOWNLOADER == "aria2c" else download_curl
    for url in sys.argv[1:]:
        print(f"\n=== {url}")
        data = extract(url)
        html = data.get("html", "")
        cookies = data.get("cookies", [])
        if not html:
            print("  FAIL: no HTML (node service returned empty)")
            continue
        video_url, title = find_video(html)
        if not video_url:
            print("  FAIL: no video URL found in page")
            continue
        safe = re.sub(r'[^a-zA-Z0-9\s_-]', "", title or "video").strip().replace(" ", "_")[:80]
        output = os.path.join(OUTPUT_DIR, f"{safe}.mp4")
        print(f"  Title: {title}")
        cookie_file = write_cookies(cookies)
        download(video_url, output, cookie_file, url)
        try:
            os.unlink(cookie_file)
        except Exception:
            pass

if __name__ == "__main__":
    main()
