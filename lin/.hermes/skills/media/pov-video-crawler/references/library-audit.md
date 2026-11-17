# Library Audit Workflow

## When to Run This

After any crawl, bulk deletion, or when the user asks "how many videos do I have for each model" or "clean up my library."

## The Four-Phase Audit Loop

### Phase 1: COUNT — Scan existing files by performer

```python
from pathlib import Path
from collections import defaultdict

# Exhaustive performer name patterns (underscore, leetspeak, unicode variants)
ALL_CATEGORIES = [
    ("Mia Malkova", ["mia malkova", "mia_malkova", "mia-malkova", "miamalkova"]),
    ("Kali Roses", ["kali r", "kali_rose", "kali rose", "kali_roses"]),
    # ... all performers with ALL known filename variants
]

counts = defaultdict(int)
uncategorized = []

for f in videos_dir.iterdir():
    if f.suffix.lower() not in ['.mp4', '.webm', '.mkv']:
        continue
    name_lower = f.stem.lower()
    # Try 3 cleaning strategies for matching
    name_clean1 = re.sub(r'\s*\[[a-zA-Z0-9_-]+\]', '', name_lower)
    name_clean2 = name_lower.replace('_', ' ')
    name_clean3 = name_lower.replace('.', ' ')
    
    found = False
    for perf, patterns in ALL_CATEGORIES:
        for p in patterns:
            if p in name_lower or p in name_clean1 or p in name_clean2 or p in name_clean3:
                counts[perf] += 1
                found = True
                break
        if found:
            break
    if not found:
        uncategorized.append(f.name)
```

**Key technique:** Try THREE cleaning strategies per filename — raw stem, underscore→space, dot→space. This catches leetspeak, underscores, unicode zero-width spaces, and JAV codes.

### Phase 2: CATEGORIZE — Recover performers from uncategorized files

Iterative passes:

1. **Pass 1 (substring):** Check ALL known performer names as substrings in the filename
2. **Pass 2 (regex):** Use regex patterns for leetspeak variants (bl4k3 → blake, l4n4 → lana)
3. **Pass 3 (manual):** For remaining, check if filename contains known words (studio names, series prefixes like `dd_`, `bt_`, `am_`)
4. **Pass 4 (URL lookup):** For files with [viewkey] IDs, try yt-dlp --get-title to identify performer

Known prefixes to identify performers:
- `dd_` = Dan Dangler
- `bt_` = Bubblebratz or generic "big tits"
- `am_` = Atlanta Moreno
- `pb_` = PimpBunny (performer in title)
- `eporner_` = site-stamped, check title/studio in name

### Phase 3: CLEAN — Bulk delete by criteria

Apply in this order:

1. **Hash filenames:** Match `^[a-z0-9]{10,40}(?:_flat|_source|_720p|_1080p)?$` — these are corrupt partials or renamed fragments
2. **Partial downloads:** `*.part`, `*.part-Frag*`, `*.ytdl`, `*.info.json`, `*.temp*`
3. **Sub-100MB videos:** `find -size -100M` — these are corrupt stubs, clips, or low-res garbage
4. **VR videos:** `-iname "*vr*"` with specific prefix checks. **WARNING:** Do NOT use `*[Vv][Rr]*` glob — this matches viewkey hashes containing vR. Use explicit: `-iname "vr*" -o -iname "*vr*"` with human review.
5. **Named performers the user deleted:** Check user memory for removed performers (Vina Sky, Emily Willis, Tomie Tang)

**Performer deletions are file-system operations, not just directory edits.** When the user says "remove X performer":
- Delete all files matching that performer's name patterns
- Update the performer_directory.txt to remove them
- Update count docs

### Phase 4: VERIFY — Confirm content compliance

URL-slug-only verification is circular — it re-checks the crawl filter. **Real verification requires yt-dlp --get-title on every URL:**

```bash
# Per-URL verification script
cat /tmp/urls.txt | xargs -P 8 -I{} /tmp/verify_single.sh "{}" /tmp/results.txt
```

See `parallel-verification.md` for the full method and `scripts/verify_urls.py` for the runnable script.

**Don't spot-check a sample and claim clean.** A 35/1794 sample found nothing, but the actual library had BBC content. Every URL needs a title fetch.

## Deletion Safety

When doing bulk deletions by criteria (size, hash pattern, VR), use `rm -v` so the deleted files are logged. The user may need to re-download something caught by a too-broad pattern.

The VR pattern bug (`*[Vv][Rr]*` matching viewkeys) is the most common over-deletion. Files matching this pattern should be listed for user review before deletion.

## Output Files

- `/mnt/storage/videos/.queue/performer_directory.txt` — canonical performer list with sites
- `/mnt/storage/videos/.queue/video_counts_by_performer.txt` — current count per performer
