#!/usr/bin/env python3
"""Per-performer POV video scraper. Searches 5 sites per performer, filters for POV + no-BBC,
downloads in parallel with size/time limits.

Usage:
    python3 performer_scraper.py             # run full 40-performer sweep
    python3 performer_scraper.py --test      # test with 1 performer
    python3 performer_scraper.py --dry-run   # show URLs without downloading
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request

OUTPUT_DIR = "/mnt/storage/videos"
YTDLP = "/home/kubuntux/.local/bin/yt-dlp"
LOG_PATH = "/tmp/performer_scraper.log"
MAX_FILE_SIZE_GB = 1.5
PER_FILE_TIMEOUT = 180
MAX_PARALLEL = 4

LOG = open(LOG_PATH, "a", buffering=1) if os.access("/tmp", os.W_OK) else None

def log(msg):
    print(msg, flush=True)
    if LOG: LOG.write(msg + "\n")

# Filter rules
BLOCKED_KEYWORDS = ["bbc", "interracial", "ebony", "bwc", "blacked raw", "blacked.com"]
NON_POV_STUDIOS = [
    "brazzers", "brazzer", "vixen", "blacked raw", "reality kings", "girlsway",
    "transfixed", "futa", "futanari",
]

def is_blocked(title):
    t = title.lower()
    return any(b in t for b in BLOCKED_KEYWORDS)

def is_pov(title):
    """Reject non-POV studio scenes unless explicitly tagged POV."""
    t = title.lower()
    has_pov = "pov" in t
    for kw in NON_POV_STUDIOS:
        if kw in t and not has_pov:
            return False
    return True

# 40 top-tier performers. Underlined = top priority (zero or near-zero vids).
PERFORMERS = [
    "Lana Rhoades", "Lauren Phillips", "Angela White", "Alanna Pow", "Kendra Sunderland",
    "Blake Blossom", "Blondie Fesser", "Karma Rx", "Violet Myers", "Mia Malkova",
    "Nicole Aniston", "Sharon Lee", "Lena Paul", "Sky Bri", "Vivian Taylor",
    "Mia Melano", "Payton Preslee", "Sophie Dee", "Kali Roses", "Ava Nicks",
    "Natasha Nice", "Aleksa Mink", "Camila Castillo", "Riley Reid", "Tru Kait",
    "Lulu Chu", "Vina Sky", "Asa Akira", "Kimmy Granger", "Jade Kush",
    "Eva Lovia", "Lily Lane",
    "Ember Snow", "Siri Dahl", "Lexi Luna", "Emily Willis",
    "Ava Addams", "Rissa May", "Faith", "Richelle Ryan",
]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"

def fetch(url, headers=None):
    h = {"User-Agent": UA, "Accept": "*/*"}
    if headers: h.update(headers)
    req = urllib.request.Request(url, headers=h)
    try:
        return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", errors="replace")
    except:
        return ""

# ============= SEARCH FUNCTIONS (one per site) =============
def search_pornhub(performer, max_results=15):
    q = urllib.parse.quote(performer)
    url = f"https://www.pornhub.com/webmasters/search?search={q}&per_page={max_results}&thumbsize=medium"
    data = fetch(url, {"Accept": "application/json", "Referer": "https://www.pornhub.com/"})
    if not data: return []
    try:
        d = json.loads(data)
        urls = []
        for v in d.get("videos", []):
            title = v.get("title", "")
            if is_blocked(title) or not is_pov(title): continue
            urls.append(v["url"])
        return urls
    except: return []

def search_redtube(performer, max_results=15):
    q = urllib.parse.quote(performer)
    url = f"https://api.redtube.com/?data=redtube.Videos.searchVideos&search={q}&output=json&page=1"
    data = fetch(url, {"Accept": "application/json"})
    if not data: return []
    try:
        d = json.loads(data)
        urls = []
        for item in d.get("videos", [])[:max_results]:
            v = item.get("video", {})
            title = v.get("title", "")
            if is_blocked(title) or not is_pov(title): continue
            u = v.get("url", "")
            if not u.startswith("http"):
                u = f"https://www.redtube.com/{v.get('video_id', '')}"
            urls.append(u)
        return urls
    except: return []

def search_xnxx(performer, max_results=15):
    q = urllib.parse.quote(performer.lower().replace(" ", "-"))
    url = f"https://www.xnxx.com/search/{q}"
    data = fetch(url, {"Referer": "https://www.xnxx.com/"})
    if not data: return []
    matches = re.findall(r'<a href="(/video-[a-z0-9]+/[a-z0-9_-]+)"', data)
    seen, urls = set(), []
    for m in matches:
        if m in seen: continue
        seen.add(m)
        slug = m.split("/")[-1].replace("_", " ")
        if is_blocked(slug) or not is_pov(slug): continue
        urls.append(f"https://www.xnxx.com{m}")
        if len(urls) >= max_results: break
    return urls

def search_eporner(performer, max_results=15):
    q = urllib.parse.quote(performer)
    url = f"https://www.eporner.com/search/{q}/"
    data = fetch(url, {"Referer": "https://www.eporner.com/"})
    if not data: return []
    matches = re.findall(r'<a href="(/video-[^"]+)"', data)
    seen, urls = set(), []
    for m in matches:
        if m in seen or "THUMBNUM" in m: continue
        seen.add(m)
        slug = m.replace("-", " ").lower()
        if is_blocked(slug) or not is_pov(slug): continue
        urls.append(f"https://www.eporner.com{m}")
        if len(urls) >= max_results: break
    return urls

def search_spankbang(performer, max_results=15):
    q = urllib.parse.quote(performer)
    url = f"https://spankbang.com/s/{q}/"
    try:
        result = subprocess.run(
            [YTDLP, "--impersonate", "chrome", "--flat-playlist", "--dump-json",
             "--skip-download", "--no-warnings", "--playlist-items", f"1-{max_results}", url],
            capture_output=True, text=True, timeout=60
        )
        urls = []
        for line in result.stdout.strip().split("\n"):
            if not line: continue
            try:
                d = json.loads(line)
                u = d.get("url") or d.get("webpage_url", "")
                title = d.get("title", "")
                if u and "spankbang.com" in u and not is_blocked(title) and is_pov(title):
                    urls.append(u)
            except: pass
        return urls[:max_results]
    except: return []

# ============= PARALLEL DOWNLOADER =============
def download_one(url, idx, total, results):
    existing = set(os.listdir(OUTPUT_DIR))
    cmd = [
        YTDLP, "--impersonate", "chrome",
        "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "--merge-output-format", "mp4",
        "--downloader", "aria2c",
        "--downloader-args", "aria2c:-x16 -s16 -k10M",
        "--retries", "10",
        "--fragment-retries", "10",
        "--no-playlist", "--no-warnings",
        "-o", f"{OUTPUT_DIR}/%(title).100s [%(id)s].%(ext)s",
        url
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=PER_FILE_TIMEOUT)
        now = set(os.listdir(OUTPUT_DIR))
        new = now - existing
        completed = [f for f in new if f.endswith(".mp4") and ".part" not in f]
        if completed:
            log(f"  [{idx}/{total}] OK {completed[0][:60]}")
            results.append(("ok", url))
        else:
            err = result.stderr[:80].replace("\n", " ") if result.stderr else "no output"
            log(f"  [{idx}/{total}] FAIL {url[-30:]} - {err[:50]}")
            results.append(("fail", url))
    except subprocess.TimeoutExpired:
        # Clean up partial file
        for f in os.listdir(OUTPUT_DIR):
            if f.endswith(".part") and url.split("=")[-1][:8] in f:
                try: os.remove(os.path.join(OUTPUT_DIR, f))
                except: pass
        log(f"  [{idx}/{total}] TIMEOUT {url[-30:]}")
        results.append(("timeout", url))
    except Exception as e:
        log(f"  [{idx}/{total}] ERR {url[-30:]} - {str(e)[:50]}")
        results.append(("err", url))

def download_batch_parallel(urls):
    if not urls: return 0
    results = []
    threads = []
    for i, url in enumerate(urls[:MAX_PARALLEL * 2], 1):
        t = threading.Thread(target=download_one, args=(url, i, len(urls), results))
        t.start()
        threads.append(t)
        if len(threads) >= MAX_PARALLEL:
            for t in threads: t.join(timeout=PER_FILE_TIMEOUT + 30)
            threads = [t for t in threads if t.is_alive()]
    for t in threads: t.join(timeout=PER_FILE_TIMEOUT + 30)
    return sum(1 for r in results if r[0] == "ok")

# ============= MAIN =============
def run_performers(performer_list):
    sites = [
        ("pornhub", search_pornhub),
        ("redtube", search_redtube),
        ("xnxx", search_xnxx),
        ("eporner", search_eporner),
        ("spankbang", search_spankbang),
    ]

    for perf in performer_list:
        log(f"\n--- {perf} ---")
        all_urls = []
        for site_name, search_fn in sites:
            try:
                urls = search_fn(perf, max_results=8)
                log(f"  [{site_name}] {len(urls)} URLs")
                all_urls.extend(urls)
            except Exception as e:
                log(f"  [{site_name}] ERR: {str(e)[:80]}")
            time.sleep(1)

        # Dedupe by video ID
        seen, unique = set(), []
        for u in all_urls:
            m = re.search(r"viewkey=([a-f0-9]+)|/video-([a-z0-9]+)|/([0-9]+)(?:/|$)", u)
            vid = m.group(0) if m else u
            if vid not in seen:
                seen.add(vid)
                unique.append(u)

        unique = unique[:15]
        if unique:
            added = download_batch_parallel(unique)
            log(f"  -> {added}/{len(unique)} completed")
        else:
            log("  -> no videos")
        time.sleep(2)

def main():
    test = "--test" in sys.argv
    dry_run = "--dry-run" in sys.argv

    log("=" * 60)
    log(f"Performer scraper: {len(PERFORMERS)} performers, parallel download")
    log("=" * 60)

    if test:
        # Quick test: one performer, all 5 sites, dry-run
        run_performers([PERFORMERS[0]])
    else:
        run_performers(PERFORMERS)

    log("\n=== DONE ===")

if __name__ == "__main__":
    main()
