#!/usr/bin/env python3
"""Per-site performer scraper. Priority-sorted (lowest count first). POV only. No BBC.

Template for /tmp/performer_scraper.py on this system. Copy and customize.
"""
import json
import os
import re
import subprocess
import threading
import time
import urllib.parse
import urllib.request

OUTPUT_DIR = "/mnt/storage/videos"
LOG_PATH = "/tmp/performer_scraper.log"
YTDLP = "/home/kubuntux/.local/bin/yt-dlp"
PER_FILE_TIMEOUT = 300
MAX_PARALLEL = 4

LOG = open(LOG_PATH, "a", buffering=1)
def log(msg):
    print(msg, flush=True)
    LOG.write(msg + "\n")

# === FILTERS ===
BLOCKED = ["bbc", "interracial", "ebony", "bwc", "blacked raw", "blacked.com",
           "big white dick", "big black dick", "cuck", "cucks", "white cock for asian",
           "brazzers bbc", "interracial creampie", "interracial anal"]

NON_POV_STUDIOS = ["brazzers", "vixen", "blacked", "reality kings", "girlsway",
                   "transfixed", "futa", "futanari", "family sinners", "pure taboo",
                   "mommy's girl", "new sensations", "tushy", "tushyraw", "mofos",
                   "private", "digital playground"]

def is_blocked(t): return any(b in t.lower() for b in BLOCKED)

def is_pov(t):
    t = t.lower()
    has_pov = "pov" in t
    for kw in NON_POV_STUDIOS:
        if kw in t and not has_pov: return False
    return True

# === PERFORMER LIST (edit per session) ===
PERFORMERS = [
    "Lana Rhoades", "Lauren Phillips", "Angela White", "Alanna Pow",
    "Kendra Sunderland", "Blake Blossom", "Blondie Fesser", "Karma Rx",
    "Violet Myers", "Mia Malkova", "Nicole Aniston", "Sharon Lee",
    "Lena Paul", "Sky Bri", "Vivian Taylor",  # Tier 1
    "Mia Melano", "Payton Preslee", "Sophie Dee", "Kali Roses",
    "Ava Nicks", "Natasha Nice", "Aleksa Mink", "Camila Castillo",
    "Riley Reid", "Tru Kait", "Lulu Chu", "Vina Sky", "Asa Akira",
    "Kimmy Granger", "Jade Kush", "Eva Lovia", "Lily Lane",  # Tier 2
    "Ember Snow", "Siri Dahl", "Lexi Luna", "Emily Willis",
    "Ava Addams", "Rissa May", "Faith", "Richelle Ryan",  # Tier 3
]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"

def fetch(url, headers=None):
    h = {"User-Agent": UA, "Accept": "*/*"}
    if headers: h.update(headers)
    req = urllib.request.Request(url, headers=h)
    try:
        return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", errors="replace")
    except: return ""

# === SITE-SPECIFIC SEARCH FUNCTIONS ===
# Each returns list of full video page URLs

def search_pornhub(performer, max_results=10):
    """webmasters API"""
    q = urllib.parse.quote(performer)
    data = fetch(f"https://www.pornhub.com/webmasters/search?search={q}&per_page={max_results}&thumbsize=medium",
                 {"Accept": "application/json", "Referer": "https://www.pornhub.com/"})
    if not data: return []
    try:
        d = json.loads(data)
        return [v["url"] for v in d.get("videos", [])
                if not is_blocked(v.get("title", "")) and is_pov(v.get("title", ""))]
    except: return []

def search_redtube(performer, max_results=10):
    """Public JSON API"""
    q = urllib.parse.quote(performer)
    data = fetch(f"https://api.redtube.com/?data=redtube.Videos.searchVideos&search={q}&output=json&page=1",
                 {"Accept": "application/json"})
    if not data: return []
    try:
        d = json.loads(data)
        urls = []
        for item in d.get("videos", [])[:max_results]:
            v = item.get("video", {})
            t = v.get("title", "")
            if is_blocked(t) or not is_pov(t): continue
            u = v.get("url", "")
            if not u.startswith("http"):
                u = f"https://www.redtube.com/{v.get('video_id', '')}"
            urls.append(u)
        return urls
    except: return []

def search_xnxx(performer, max_results=10):
    """HTML scrape"""
    q = urllib.parse.quote(performer.lower().replace(" ", "-"))
    data = fetch(f"https://www.xnxx.com/search/{q}", {"Referer": "https://www.xnxx.com/"})
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

def search_eporner(performer, max_results=10):
    """HTML scrape, skip THUMBNUM placeholders"""
    q = urllib.parse.quote(performer)
    data = fetch(f"https://www.eporner.com/search/{q}/", {"Referer": "https://www.eporner.com/"})
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

def search_xvideos(performer, max_results=10):
    """HTML scrape, watch for .red mirrors"""
    q = urllib.parse.quote(performer)
    data = fetch(f"https://www.xvideos.com/?k={q}", {"Referer": "https://www.xvideos.com/"})
    if not data: return []
    matches = (re.findall(r'href="(https?://www\.xvideos\.com/video[a-z0-9]+/[a-z0-9_-]+)"', data)
               + re.findall(r'href="(/video[a-z0-9]+/[a-z0-9_-]+)"', data))
    seen, urls = set(), []
    for m in matches:
        if m in seen: continue
        seen.add(m)
        full = m if m.startswith("http") else f"https://www.xvideos.com{m}"
        slug = m.split("/")[-1].replace("-", " ").replace("_", " ")
        if is_blocked(slug) or not is_pov(slug): continue
        urls.append(full)
        if len(urls) >= max_results: break
    return urls

def search_youporn(performer, max_results=10):
    """HTML scrape"""
    q = urllib.parse.quote(performer)
    data = fetch(f"https://www.youporn.com/search/?query={q}", {"Referer": "https://www.youporn.com/"})
    if not data: return []
    matches = re.findall(r'href="(/watch/[0-9]+/[a-z0-9_-]+/?)"', data)
    seen, urls = set(), []
    for m in matches:
        if m in seen: continue
        seen.add(m)
        slug = m.replace("-", " ").replace("_", " ").lower()
        if is_blocked(slug) or not is_pov(slug): continue
        urls.append(f"https://www.youporn.com{m}")
        if len(urls) >= max_results: break
    return urls

def search_porntn(performer, max_results=10):
    """HTML scrape"""
    q = urllib.parse.quote(performer)
    data = fetch(f"https://www.porntn.com/search/{q}/", {"Referer": "https://www.porntn.com/"})
    if not data: return []
    matches = re.findall(r'href="(https?://(?:www\.)?porntn\.com/video/[0-9]+/[a-z0-9_-]+)"', data)
    seen, urls = set(), []
    for m in matches:
        if m in seen: continue
        seen.add(m)
        slug = m.split("/")[-1].replace("-", " ").lower()
        if is_blocked(slug) or not is_pov(slug): continue
        urls.append(m)
        if len(urls) >= max_results: break
    return urls

def search_tnaflix(performer, max_results=10):
    """HTML scrape - note: use ' '.join() not m.split().join()"""
    q = urllib.parse.quote(performer)
    data = fetch(f"https://www.tnaflix.com/search.php?what={q}", {"Referer": "https://www.tnaflix.com/"})
    if not data: return []
    matches = re.findall(r'href="(https?://www\.tnaflix\.com/[^"]+/video[0-9]+)"', data)
    seen, urls = set(), []
    for m in matches:
        if m in seen: continue
        seen.add(m)
        slug = " ".join(m.split("/")[-2:]).replace("-", " ").lower()
        if is_blocked(slug) or not is_pov(slug): continue
        urls.append(m)
        if len(urls) >= max_results: break
    return urls

def search_spankbang(performer, max_results=10):
    """yt-dlp impersonate (Cloudflare-protected)"""
    q = urllib.parse.quote(performer)
    slug = performer.lower().replace(" ", "-")
    for url in [f"https://spankbang.com/{slug}/", f"https://spankbang.com/s/{q}/"]:
        try:
            result = subprocess.run(
                [YTDLP, "--impersonate", "chrome", "--flat-playlist", "--dump-json",
                 "--skip-download", "--no-warnings", "--playlist-items", f"1-{max_results}", url],
                capture_output=True, text=True, timeout=60)
            urls = []
            for line in result.stdout.strip().split("\n"):
                if not line: continue
                try:
                    d = json.loads(line)
                    u = d.get("url") or d.get("webpage_url", "")
                    t = d.get("title", "")
                    if u and "spankbang.com" in u and not is_blocked(t) and is_pov(t):
                        urls.append(u)
                except: pass
            if urls: return urls[:max_results]
        except: continue
    return []

def search_xhamster(performer, max_results=10):
    """HTML scrape"""
    q = urllib.parse.quote(performer)
    data = fetch(f"https://xhamster.com/search/{q}", {"Referer": "https://xhamster.com/"})
    if not data: return []
    matches = re.findall(r'href="(https?://xhamster\.com/videos/[a-z0-9_-]+-[0-9]+)"', data)
    seen, urls = set(), []
    for m in matches:
        if m in seen: continue
        seen.add(m)
        slug = m.split("/")[-1].replace("-", " ").lower()
        if is_blocked(slug) or not is_pov(slug): continue
        urls.append(m)
        if len(urls) >= max_results: break
    return urls

# === DOWNLOADER ===
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
        "--no-playlist",
        "--no-warnings",
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
            # Clean up partials on size/format rejection
            for p in [f for f in new if f.endswith(".part")]:
                try: os.remove(os.path.join(OUTPUT_DIR, p))
                except: pass
            log(f"  [{idx}/{total}] FAIL {url[:50]}")
            results.append(("fail", url))
    except subprocess.TimeoutExpired:
        # Clean up
        vid = url.split("=")[-1] if "=" in url else url.split("/")[-1]
        for f in os.listdir(OUTPUT_DIR):
            if f.endswith(".part") and vid[:10] in f:
                try: os.remove(os.path.join(OUTPUT_DIR, f))
                except: pass
        log(f"  [{idx}/{total}] TIMEOUT {url[:50]}")
        results.append(("timeout", url))
    except Exception as e:
        log(f"  [{idx}/{total}] ERR {url[:50]} {str(e)[:50]}")
        results.append(("err", url))

def download_batch_parallel(urls, label):
    if not urls: return 0
    results = []
    threads = []
    for i, url in enumerate(urls, 1):
        t = threading.Thread(target=download_one, args=(url, i, len(urls), results))
        t.start()
        threads.append(t)
        if len(threads) >= MAX_PARALLEL:
            for t in threads: t.join(timeout=PER_FILE_TIMEOUT + 30)
            threads = [t for t in threads if t.is_alive()]
    for t in threads: t.join(timeout=PER_FILE_TIMEOUT + 30)
    return sum(1 for r in results if r[0] == "ok")

# === PRIORITY SORT ===
def get_priority_sorted():
    """Sort performers by current video count ascending"""
    def unleet(s):
        for k, v in [('4','a'),('3','e'),('1','i'),('0','o'),('5','s'),('7','t'),('8','b')]:
            s = s.replace(k, v)
        return s
    files = os.listdir(OUTPUT_DIR)
    counts = {}
    for p in PERFORMERS:
        pl = unleet(p.lower())
        counts[p] = sum(1 for f in files if pl in unleet(f.lower()))
    return [p for p, _ in sorted(counts.items(), key=lambda x: x[1])]

# === MAIN ===
def main():
    performers = get_priority_sorted()
    log("=" * 60)
    log(f"Scraper: {len(performers)} performers (priority-sorted), 10 sites")
    log("  Filter: BBC BLOCKED, POV only")
    log("=" * 60)

    sites = [
        ("pornhub", search_pornhub),
        ("redtube", search_redtube),
        ("xnxx", search_xnxx),
        ("xvideos", search_xvideos),
        ("youporn", search_youporn),
        ("porntn", search_porntn),
        ("tnaflix", search_tnaflix),
        ("eporner", search_eporner),
        ("spankbang", search_spankbang),
        ("xhamster", search_xhamster),
    ]

    for perf in performers:
        log(f"\n--- {perf} ---")
        all_urls = []
        for site_name, search_fn in sites:
            try:
                urls = search_fn(perf, max_results=6)
                if urls: log(f"  [{site_name}] {len(urls)}")
                all_urls.extend(urls)
            except Exception as e:
                log(f"  [{site_name}] ERR: {str(e)[:60]}")
            time.sleep(0.8)

        # Dedupe by video ID
        seen, unique = set(), []
        for u in all_urls:
            m = re.search(r"viewkey=([a-f0-9]+)|/video-?([a-z0-9]+)|/watch/([0-9]+)|/([0-9]+)(?:/|$)", u)
            vid = m.group(0) if m else u
            if vid not in seen:
                seen.add(vid)
                unique.append(u)
        unique = unique[:15]

        if unique:
            added = download_batch_parallel(unique, perf)
            log(f"  -> {added}/{len(unique)} done")
        else:
            log("  -> no videos")
        time.sleep(2)

    log("\n=== DONE ===")

if __name__ == "__main__":
    main()
