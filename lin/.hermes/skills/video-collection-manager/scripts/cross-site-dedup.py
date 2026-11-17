#!/usr/bin/env python3
"""
Cross-site dedup for url2video queue — fast mode.

Two-phase extraction:
  Phase 1 — Pornhub URLs: extract viewkey from URL, match against [viewkey] in
    existing MP4 filenames. Instant — no HTTP needed. Pornhub blocks both curl
    (Cloudflare challenge, ~1459 byte page) and yt-dlp (requires PhantomJS).
  Phase 2 — Non-pornhub URLs: curl (8s timeout) to fetch HTML and extract
    <title>/OG tags + duration metadata. Fast for youporn, xhamster, xnxx,
    redtube, pimpbunny, borntobefuck, etc. Fallback: yt-dlp --dump-json (15s).

Also checks queued URLs against existing MP4s on disk (filename matching)
and finds same-site dupes within the queue.

Usage:
    python3 cross-site-dedup.py
"""
import html
import json
import os
import re
import sqlite3
import subprocess
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

YTDLP = os.path.expanduser("~/.local/bin/yt-dlp")
DB_PATH = "/mnt/storage/videos/.url2video.db"
OUTDIR = "/mnt/storage/videos"
MAX_WORKERS = 15
CURL_TIMEOUT = 8
YTDLP_TIMEOUT = 15


def title_key(t):
    t = t.lower().strip()
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t[:80]


def duration_bucket(d):
    if not d or d <= 0:
        return 0
    return round(d / 5) * 5


def extract_viewkey(url):
    """Extract PH viewkey from URL. Returns None for non-pornhub URLs."""
    m = re.search(r'viewkey=([a-f0-9]+)', url)
    return m.group(1) if m else None


def is_pornhub(url):
    return "pornhub" in urlparse(url).netloc.replace("www.", "")


def fetch_title_via_curl(url):
    """Fetch page title+duration via curl with aggressive timeout.
    Much faster than yt-dlp for known tube sites."""
    try:
        r = subprocess.run(
            ["curl", "-sS", "--max-time", str(CURL_TIMEOUT), "-L",
             "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
             url],
            capture_output=True, text=True, timeout=CURL_TIMEOUT + 2
        )
        if r.returncode != 0 or not r.stdout:
            return None, None
        h = r.stdout

        title = None
        m = re.search(r'<meta\s+property\s*=\s*["\']og:title["\']\s+content\s*=\s*["\']([^"\']+)["\']', h, re.IGNORECASE)
        if m:
            title = html.unescape(m.group(1))
        if not title:
            m = re.search(r'<meta\s+name\s*=\s*["\']twitter:title["\']\s+content\s*=\s*["\']([^"\']+)["\']', h, re.IGNORECASE)
            if m:
                title = html.unescape(m.group(1))
        if not title:
            m = re.search(r'<title>([^<]+)</title>', h, re.IGNORECASE)
            if m:
                title = html.unescape(m.group(1))

        duration = None
        m = re.search(r'<meta\s+property\s*=\s*["\']video:duration["\']\s+content\s*=\s*["\'](\d+)["\']', h, re.IGNORECASE)
        if m:
            duration = int(m.group(1))
        if not duration:
            m = re.search(r'"duration"\s*:\s*"PT(\d+)M(\d+)S"', h)
            if m:
                duration = int(m.group(1)) * 60 + int(m.group(2))
        if not duration:
            m = re.search(r'"duration"\s*:\s*"PT(\d+)M"', h)
            if m:
                duration = int(m.group(1)) * 60
        if not duration:
            m = re.search(r'<meta\s+itemprop\s*=\s*["\']duration["\']\s+content\s*=\s*["\']PT(\d+)M(\d+)S["\']', h, re.IGNORECASE)
            if m:
                duration = int(m.group(1)) * 60 + int(m.group(2))
        if not duration:
            m = re.search(r'"duration"\s*[:=]\s*"?(\d+)"?', h)
            if m:
                duration = int(m.group(1))

        if title:
            title = re.sub(r'\s*[-|]\s*(Pornhub|XHamster|XNXX|RedTube|YouPorn|SpankBang|Borntobefuck|Pimpbunny|Eporner).*$', '', title, flags=re.IGNORECASE)
            title = title.strip()

        return title, duration
    except Exception:
        return None, None


def fetch_via_ytdlp(url):
    """Fallback: yt-dlp --dump-json for non-standard sites."""
    try:
        r = subprocess.run(
            [YTDLP, "--dump-json", "--no-warnings",
             "--socket-timeout", "5", "--max-sleep-interval", "0", "--sleep-interval", "0",
             url],
            capture_output=True, text=True, timeout=YTDLP_TIMEOUT
        )
        if r.returncode != 0:
            return url, None, None
        d = json.loads(r.stdout)
        return url, d.get("title"), d.get("duration", 0)
    except Exception:
        return url, None, None


def extract_meta(url):
    """Extract (url, title, duration) from a URL.
    Pornhub: returns just the viewkey as title (matched later in Phase 1).
    Others: curl HTML extraction, fallback to yt-dlp."""
    if is_pornhub(url):
        vk = extract_viewkey(url)
        return url, vk, None  # viewkey — matched against filenames in Phase 1
    # Non-pornhub: curl HTML extraction (fast)
    title, dur = fetch_title_via_curl(url)
    if title:
        return url, title, dur
    # Fallback
    return fetch_via_ytdlp(url)


def main():
    print("=== CROSS-SITE DEDUP (FAST) ===")

    # 1. Load existing MP4s from disk — build BOTH title and viewkey index
    mp4s = [f for f in os.listdir(OUTDIR) if f.endswith(".mp4")]
    disk_titles = {}
    disk_by_viewkey = {}
    for f in mp4s:
        title_part = re.sub(r'\s*\[[^\]]+\]\.mp4$', '', f)
        title_part = re.sub(r'\.mp4$', '', title_part)
        disk_titles[title_key(title_part)] = f
        # Extract viewkey from [viewkey] pattern in filename
        m = re.search(r'\[([a-f0-9]+)\]\.mp4$', f)
        if m:
            disk_by_viewkey[m.group(1)] = f
    print(f"MP4s on disk: {len(mp4s)}")
    print(f"  Indexed by title:   {len(disk_titles)}")
    print(f"  Indexed by viewkey: {len(disk_by_viewkey)}")

    # 2. Get queued URLs from DB
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, url, status FROM jobs WHERE status IN ('queued','downloading')"
    ).fetchall()
    url_to_job = {r["url"]: r for r in rows}
    all_urls = list(url_to_job.keys())

    site_counts = defaultdict(int)
    for url in all_urls:
        d = urlparse(url).netloc.replace("www.", "").split(".")[0]
        site_counts[d] += 1
    print(f"Queued URLs: {len(all_urls)}")
    print(f"By site: {dict(sorted(site_counts.items(), key=lambda x: -x[1]))}")

    if not all_urls:
        print("Nothing to dedup — queue is empty")
        conn.close()
        return

    # === PHASE 1: Pornhub viewkey dedup (instant, no HTTP) ===
    ph_count = site_counts.get("pornhub", 0)
    ph_cancelled = 0
    if ph_count > 0:
        print(f"\nPhase 1 — Pornhub viewkey dedup ({ph_count} URLs against {len(disk_by_viewkey)} indexed MP4s)...")
        for r in rows:
            url = r["url"]
            if not is_pornhub(url):
                continue
            vk = extract_viewkey(url)
            if vk and vk in disk_by_viewkey:
                conn.execute(
                    "UPDATE jobs SET status='cancelled', error='viewkey dupe' WHERE id=? AND status IN ('queued','downloading')",
                    (r["id"],)
                )
                if conn.total_changes > 0:
                    ph_cancelled += 1
        cancelled += ph_cancelled
        print(f"  Cancelled {ph_cancelled} pornhub URLs (already on disk by viewkey)")
        # Remove cancelled from the extraction list
        still_pending = []
        for r in rows:
            if r["status"] not in ("queued", "downloading") or conn.execute(
                "SELECT status FROM jobs WHERE id=?", (r["id"],)
            ).fetchone()["status"] == "cancelled":
                continue
            still_pending.append(r)
        rows = still_pending
        all_urls = [r["url"] for r in rows]
        print(f"  Remaining URLs after Phase 1: {len(all_urls)}")

    # === PHASE 2: HTTP title extraction for remaining URLs ===
    print(f"\nExtracting {len(all_urls)} URLs ({MAX_WORKERS} workers)...")
    print(f"  Primary: curl ({CURL_TIMEOUT}s) for known sites")
    print(f"  Fallback: yt-dlp ({YTDLP_TIMEOUT}s) for others")
    results = {}
    done = 0
    start = time.time()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        fut_map = {ex.submit(extract_meta, url): url for url in all_urls}
        for fut in as_completed(fut_map):
            url, title, dur = fut.result()
            results[url] = (title, dur)
            done += 1
            if done % 25 == 0:
                elapsed = time.time() - start
                rate = done / elapsed if elapsed > 0 else 0
                resolved = sum(1 for t, d in results.values() if t)
                print(f"  [{done}/{len(all_urls)}] {rate:.1f}/s resolved={resolved}")

    elapsed = time.time() - start
    resolved = sum(1 for t, d in results.values() if t)
    print(f"\nResolved: {resolved}/{len(all_urls)} ({elapsed:.0f}s, {len(all_urls)-resolved} timed out)")

    cancelled = 0

    # 4. Check against existing MP4s on disk (title match)
    disk_count = len(disk_titles)
    print(f"\n=== Check against {disk_count} MP4s on disk ===")
    disk_hits = 0
    for url, (title, dur) in results.items():
        if not title:
            continue
        tk = title_key(title)
        if tk in disk_titles:
            jid = url_to_job[url]["id"]
            conn.execute(
                "UPDATE jobs SET status='cancelled', error='on-disk dupe' WHERE id=? AND status IN ('queued','downloading')",
                (jid,)
            )
            if conn.total_changes > 0:
                cancelled += 1
                disk_hits += 1
                print(f"  CANCEL (on disk): {title[:65]}")
    print(f"  Disk-dupe cancellations: {disk_hits}")

    # 5. Cross-site dedup within queued URLs
    print("\n=== Cross-site dedup within queue ===")
    groups = defaultdict(list)
    for url, (title, dur) in results.items():
        if not title:
            continue
        k = (title_key(title), duration_bucket(dur))
        groups[k].append(url)

    cross_hits = 0
    for key, urls in sorted(groups.items(), key=lambda x: -len(x[1])):
        if len(urls) < 2:
            continue
        tk, _ = key
        # Skip if any of these are already on disk (already cancelled above)
        already_disk = any(title_key(results.get(u, (None,))[0] or "") in disk_titles for u in urls)
        if already_disk:
            continue
        sites = set()
        for u in urls:
            d = urlparse(u).netloc.replace("www.", "").split(".")[0]
            sites.add(d)
        title_sample = results.get(urls[0], ("",))[0]
        if len(sites) > 1:
            for u in urls[1:]:
                jid = url_to_job[u]["id"]
                conn.execute(
                    "UPDATE jobs SET status='cancelled', error='cross-site dupe' WHERE id=? AND status IN ('queued','downloading')",
                    (jid,)
                )
                if conn.total_changes > 0:
                    cancelled += 1
                    cross_hits += 1
            print(f"  CANCEL {len(urls)-1} cross-site: {title_sample[:60]} ({', '.join(sites)})")

    print(f"  Cross-site cancellations: {cross_hits}")

    # 6. Same-site dupes within queue
    print("\n=== Same-site dupes ===")
    same_hits = 0
    for key, urls in sorted(groups.items(), key=lambda x: -len(x[1])):
        if len(urls) < 2:
            continue
        tk, _ = key
        already_disk = any(title_key(results.get(u, (None,))[0] or "") in disk_titles for u in urls)
        if already_disk:
            continue
        sites = set()
        for u in urls:
            d = urlparse(u).netloc.replace("www.", "").split(".")[0]
            sites.add(d)
        if len(sites) > 1:
            continue  # already handled
        title_sample = results.get(urls[0], ("",))[0]
        for u in urls[1:]:
            jid = url_to_job[u]["id"]
            conn.execute(
                "UPDATE jobs SET status='cancelled', error='same-site dupe' WHERE id=? AND status IN ('queued','downloading')",
                (jid,)
            )
            if conn.total_changes > 0:
                cancelled += 1
                same_hits += 1
        print(f"  CANCEL {len(urls)-1} same-site: {title_sample[:60]}")
    print(f"  Same-site cancellations: {same_hits}")

    conn.commit()

    # 7. Final stats
    final = conn.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status").fetchall()
    print("\n=== FINAL DB STATE ===")
    for row in final:
        print(f"  {row['status']}: {row['COUNT(*)']}")
    print(f"\n=== TOTAL CANCELLED: {cancelled} ===")

    # 8. Clean queue file if it exists
    queue_path = "/tmp/video_queue_deduped_final.txt"
    if os.path.exists(queue_path):
        with open(queue_path) as f:
            lines = f.read().strip().splitlines()
        cancelled_urls = set()
        for url, (title, dur) in results.items():
            if url_to_job.get(url) and conn.execute(
                "SELECT status FROM jobs WHERE id=?", (url_to_job[url]["id"],)
            ).fetchone()["status"] == "cancelled":
                cancelled_urls.add(url)
        filtered = [l for l in lines if l.split("|")[-1].strip() not in cancelled_urls]
        if len(filtered) != len(lines):
            with open(queue_path, "w") as f:
                f.write("\n".join(filtered) + "\n")
            print(f"Cleaned queue file: {len(lines)} -> {len(filtered)} lines")

    conn.close()


if __name__ == "__main__":
    main()
