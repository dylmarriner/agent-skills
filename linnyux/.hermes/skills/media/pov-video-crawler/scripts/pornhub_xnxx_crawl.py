#!/usr/bin/env python3
"""
Pornhub + XNXX combo crawl for POV big tits content per performer.
Max 20 per performer including existing on disk.

Usage:
  python3 -u pornhub_xnxx_crawl.py

Sites:
  - Pornhub: yt-dlp --flat-playlist --dump-json on search URL
  - XNXX:    curl HTML scrape of search page, extract href="/video-XXX/slug"

Filters:
  - BBC/interracial/BWC/ebony/blacks.on blocked via regex on title
  - Scoring: +3 POV, +2 big tits keywords, +1 performer match, -5 compilation
  - Min score 0 required to be included

Output: /mnt/storage/videos/.queue/pov_crawl_<timestamp>.txt
"""

import json, re, subprocess, sys, time, urllib.request
from pathlib import Path

OUTPUT_DIR = Path("/mnt/storage/videos/.queue")
VIDEOS_DIR = Path("/mnt/storage/videos")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BLOCKED = re.compile(
    r'\b(bbc|interracial|black\s*cock|black\s*dick|big\s*black|black\s*bf|'
    r'blacked|blackedraw|bwc|ebony|blacks?\.?on|monster\s*dick|gangbang|dp\s?dvp|'
    r'cuckold|trans|futa|shemale|tgirl|vr\b|vr90|vr\s*porn'
    r'|compilation|best\s*of|pmv)', re.I)

PREFER_POV = re.compile(r'pov', re.I)
PREFER_TITS = re.compile(r'(big\s*tit|busty|huge\s*tit|boobs|tits|breast|juggs)', re.I)

PERFORMERS = [
    ("Mia Malkova", 18), ("Kali Roses", 18), ("Aleksa Mink", 15),
    ("Lana Rhoades", 21), ("Lena Paul", 12), ("Angela White", 12),
    ("Payton Preslee", 11), ("Lauren Phillips", 10), ("Karma RX", 10),
    ("Tru Kait", 9), ("Lexi Luna", 9), ("Asa Akira", 9),
    ("Blake Blossom", 9), ("Siri Dahl", 8), ("Nicole Doshi", 8),
    ("Violet Myers", 8), ("Richelle Ryan", 8), ("Angie Faith", 8),
    ("Blondie Fesser", 8), ("Alanna Pow", 7), ("Vivian Taylor", 7),
    ("Sky Bri", 7), ("Rissa May", 7), ("Riley Reid", 6),
    ("Natasha Nice", 5), ("Sharon Lee", 5), ("Kendra Sunderland", 5),
    ("Ava Addams", 5), ("Ava Nicks", 4), ("Ember Snow", 4),
    ("Jade Kush", 4), ("Mia Melano", 4), ("Kimmy Granger", 3),
    ("Sophie Dee", 2), ("Lulu Chu", 2), ("Eva Lovia", 1), ("Lily Lane", 1),
]

# NOTE: Update current counts from disk before each run.
# Use: scripts/count_performers.py to get fresh counts.

def get_existing_viewkeys():
    existing = set()
    for f in VIDEOS_DIR.iterdir():
        if f.suffix.lower() in ['.mp4', '.webm', '.mkv']:
            m = re.search(r'\[([a-zA-Z0-9]+)\]', f.stem)
            if m: existing.add(m.group(1))
    return existing

def search_pornhub(performer, limit=30):
    results, seen = [], set()
    for q in [f"pov+{performer.replace(' ', '+')}+big+tits", f"pov+{performer.replace(' ', '+')}"]:
        url = f"https://www.pornhub.com/video/search?search={q}"
        try:
            out = subprocess.check_output(
                ["yt-dlp", "--flat-playlist", "--dump-json", "--playlist-end", str(limit),
                 "--impersonate", "chrome", url],
                stderr=subprocess.DEVNULL, timeout=25)
            for line in out.decode().strip().split('\n'):
                if not line: continue
                try:
                    d = json.loads(line)
                    t, vk, u = d.get('title',''), d.get('id',''), d.get('webpage_url','')
                    if vk and vk not in seen:
                        seen.add(vk); results.append((t, u, vk))
                except: continue
        except: continue
    return results

def search_xnxx(performer, limit=30):
    results, seen = [], set()
    q = f"pov {performer}".replace(' ', '+').replace('++', '+')
    url = f"https://www.xnxx.com/search/{q}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='replace')
        for h in re.findall(r'href="(/video-\w+/[^"]*)"', html):
            if h in seen: continue
            seen.add(h)
            slug = h.split('/')[-1].replace('_', ' ').replace('-', ' ')
            full_url = f"https://www.xnxx.com{h}"
            if len(results) >= limit: break
            results.append((slug, full_url, h.split('/')[-2]))
    except Exception as e:
        print(f"    XNXX error: {e}", file=sys.stderr)
    return results

def score_title(title, performer):
    tl = title.lower()
    if BLOCKED.search(tl): return -10
    s = 0
    if PREFER_POV.search(tl): s += 3
    if PREFER_TITS.search(tl): s += 2
    if performer.lower() in tl: s += 2
    if re.search(r'(compilation|best\s*of|pmv)', tl): s -= 5
    return s

def main():
    existing_vks = get_existing_viewkeys()
    crawl_file = OUTPUT_DIR / f"pov_crawl_{int(time.time())}.txt"

    with open(crawl_file, 'w') as f:
        f.write(f"# POV Big Tits Crawl - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("# Sites: Pornhub + XNXX\n# No BBC/Interracial, POV + Big Tits preferred\n#\n")

        total = 0
        global_seen = set(existing_vks)
        for name, current in PERFORMERS:
            needed = max(0, 20 - current)
            if needed <= 0: continue

            print(f"\n{name}: has {current}, need {needed}")
            f.write(f"\n# {name} (need {needed})\n")
            pool = []

            for t, u, vk in search_pornhub(name):
                if vk not in global_seen:
                    pool.append((score_title(t, name), t, u, vk, 'PH'))
            for t, u, vid in search_xnxx(name):
                if vid not in global_seen:
                    pool.append((score_title(t, name), t, u, vid, 'XX'))

            pool.sort(key=lambda x: -x[0])
            taken = 0
            for score, title, url, vid, src in pool:
                if taken >= needed: break
                if score <= -10: continue
                f.write(f"{url}\n"); global_seen.add(vid); total += 1; taken += 1
                print(f"  + [{src}][{score}] {title[:80]}")

            if taken == 0: print(f"  (nothing new found)")

    print(f"\n\nSaved: {crawl_file} ({total} URLs)")

if __name__ == "__main__":
    main()
