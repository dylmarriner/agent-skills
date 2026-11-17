# Dedup Strategy

Mandatory after every Phase 1 crawl. Without dedup, a 40-performer × 10-site crawl produces 800+ raw URLs but the same videos appear under different slugs per site.

## Why dedup matters

821 raw URLs → 555 truly new. Of the 266 removed, 234 are cross-site duplicates (same video, different URL slug per site) and 32 are already in the library. **The 70% rate is normal** because:
- Each site uses different URL slug format (`/view_video.php?viewkey=ABC` vs `/videos/title-id` vs `/video-EJjN0iBx9XC/title/`)
- Filenames on disk use `[id]` brackets where the ID is the site's internal video ID — different from the URL's viewkey
- Most library files (700+) don't have matching IDs in the queue at all — different naming pipeline

## Pipeline

### Step 1: Load the queue
```python
items = []
with open('/tmp/video_queue_deduped.txt') as f:
    for line in f:
        parts = line.strip().split('|')
        if len(parts) >= 3:
            items.append({'performer': parts[0], 'site': parts[1], 'url': '|'.join(parts[2:])})
```

### Step 2: Extract slugs from URLs
```python
def extract_slug(url):
    if 'viewkey=' in url:
        m = re.search(r'viewkey=([a-f0-9]+)', url)
        return f"ph:{m.group(1)}" if m else url
    elif '/watch/' in url:
        m = re.search(r'/watch/\d+/([a-z0-9_-]+)', url)
        return m.group(1) if m else url.split('/')[-1]
    elif '/video/' in url or '/videos/' in url:
        parts = url.rstrip('/').split('/')
        for p in reversed(parts):
            if p and not p.isdigit():
                return p
        return parts[-1]
    return url.split('/')[-1]
```

### Step 3: Title normalization (for fuzzy match)
```python
def clean(s):
    for k, v in [('4','a'),('3','e'),('1','i'),('0','o'),('5','s'),('7','t'),('8','b')]:
        s = s.replace(k, v)
    s = re.sub(r'[^a-z0-9\s]', '', s.lower())
    s = re.sub(r'\s+', ' ', s).strip()
    return s
```

### Step 4: Match against library by bigram overlap
```python
def bigrams(s):
    return set(s[i:i+2] for i in range(len(s)-1))

# Build library bigram index
lib_titles = {}
for f in os.listdir('/mnt/storage/videos'):
    if f.endswith('.mp4') and '.part' not in f:
        c = clean(f.replace('[', '').replace(']', '').replace('.mp4', ''))
        if c and len(c) > 5:
            lib_titles[c] = bigrams(c)

# Match each queue URL
for q in queue:
    slug = clean(extract_slug(q['url']))
    slug_bg = bigrams(slug)
    best = 0
    for lib_clean, lib_bg in lib_titles.items():
        if abs(len(lib_clean) - len(slug)) > 30: continue
        common = len(slug_bg & lib_bg)
        score = common / max(len(slug_bg), len(lib_bg), 1)
        if score > best: best = score
    if best > 0.4:  # dupe
        queue.remove(q)
```

### Step 5: Cross-site dedup
If two queue URLs have the same normalized slug, keep only the highest-priority site:
```python
SITE_RANK = {'pornhub': 1, 'spankbang': 2, 'xvideos': 3, 'redtube': 4, 'xnxx': 5,
             'youporn': 6, 'eporner': 7, 'porntn': 8, 'tnaflix': 9, 'xhamster': 10}
```

## Why metadata resolution is the better approach (but slow)

`yt-dlp --dump-json --skip-download` returns the actual title of each video, enabling near-perfect dedup via exact match. But:
- It runs at ~6 URLs/min on Pornhub (Cloudflare-throttled)
- 555 URLs = 90+ minutes to resolve all
- Phase 2 download blocks waiting for full metadata

**Solution: don't block on it.** Run the metadata resolver in the background as a separate process. Phase 2 starts immediately with slug-fuzzy dedup (acceptable ~13% false-negative rate). When metadata arrives, re-dedup new entries as a background task.

## Per-performer cap (the real lever)

The biggest queue bloat is **top performers** — Vina Sky alone had 42 URLs in one crawl. Slug-fuzzy dedup won't fix this. Hard-cap per performer:
```python
# Cap to 8 URLs per performer
from collections import defaultdict
counts = defaultdict(int)
filtered = []
for q in sorted(queue, key=lambda x: -x['priority']):  # high priority first
    if counts[q['performer']] < 8:
        filtered.append(q)
        counts[q['performer']] += 1
```

Combined with priority order (zero-vid performers first), this brings queue size from 555 to ~100-150 actionable URLs.
