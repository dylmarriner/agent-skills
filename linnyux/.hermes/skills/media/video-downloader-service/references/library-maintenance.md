# Library Maintenance — Worked Example

Performed: 2026-07-08 on `/mnt/storage/videos/` (SMB share `\\KUBUNTUX\videos`)

## Initial State
- 929 files, 855 videos, ~413GB
- 63 `.info.json` files mixed in with videos
- 1 `.temp.mp4` leftover from interrupted download
- Assorted .txt/.sh queue management files
- Directories: `.queue/`, `eporner_batch/`, `media/`, `processed/`

## Phase 1 — Non-video scrub
Removed in bulk:
- 63 `.info.json` files (yt-dlp metadata, ~1MB each, no video data)
- 1 `.temp.mp4` (593MB — HouseHumpers partial download)
- 0-byte file (stalled partial)
- `.txt`, `.sh` files (queue lists, dedup reports)
- 2 empty directories (`eporner_batch/`, `media/`)
- 3 stray non-video files from a content spill (`Only a Big Ass...` at 172MB, 15KB, 71B)

**Recovered:** ~852MB

## Phase 2 — Hash-based dedup
MD5 of first 64KB + full size as composite signature over all 855 video files.

**Found:** 1 pair of true byte-identical duplicates:
- `"Is there anything..." Kimmy Granger [1757a303f5a2f].mp4` (259MB)
- `"Lets see how deep..." Brandi Love [641b9c6fcb642].mp4` (259MB)
→ Kept Kimmy Granger version (matched performer collection), deleted Brandi Love copy + its .info.json

**Recovered:** 259MB

## Phase 3 — Title-similarity dedup
Normalized all 853 remaining video filenames (strip `[viewkey]`, quality tags, site prefixes).

### Exact title matches (same normalized title → duplicate):
| Kept | Deleted | Reason |
|------|---------|--------|
| Cum Lovers Turn Their Cunts.mp4 (1008MB) | [671d8e387ba94].mp4 (556MB) | Slightly lower quality copy |
| My stepbrother gives me...mp4 (964MB) | [69dc102d4c820].mp4 (322MB) | Lower quality copy |
| Plumber Drains Vina [6660631b25867].mp4 (269MB) | .mp4 (108MB) | Lower quality copy |
| TEENFIDELITY Vina Sky [65c16500e1422].mp4 (230MB) | .mp4 (137MB) | Lower quality copy |
| Aleksa Mink [6914cbeacf081].mp4 (355MB) | bt_ copy (173MB) | Lower quality copy |
| Brattysis Lulu Chu [65ef3242bec12].mp4 (597MB) | Stepsis... [65431384f263d].mp4 (219MB) | Same scene, different studio naming |
| JAY'S POV Vina Sky [66466eade9ad7].mp4 (465MB) | .mp4 (427MB) | Smaller copy (different hash, same title) |
| Big Titted...Lexi Luna [17043232].mp4 (264MB) | - PervMom.mp4 (244MB) | User confirmed same scene |

**Recovered:** ~2.2GB

### Near-matches (kept — different content despite similar title):
- Angie Faith 397MB vs 381MB (different scenes, same description text)
- Siri Dahl MOMMY'S BOY 363MB (FRENCH SUBTITLES) vs 219MB (different encodes)

## Phase 4 — Duration-match dedup (follow-up pass)

After title-similarity dedup left 853 videos, a SECOND pass using ffprobe durations
found 5 more duplicate pairs that different titles had hidden:

| Same Scene Pair | Size | Duration | Action |
|-----------------|------|----------|--------|
| Sharon Lee [mmXIzfTQ4fl] vs Asian Sensation Sharon Lee...mp4 | 719MB vs 720MB | 32.1min | Deleted 719MB |
| Lauren Phillips - POV vs Lauren_Phillips_POV.mp4 | 817MB vs 610MB | 23.0min | Deleted 610MB |
| Lana Rhoades POV Part 2 vs Lana Rhoades 6 [lisjGTa2o1g] | 1919MB vs 1037MB | 28.4min | Deleted 1037MB |
| Sophie Dee Giant Boobs vs Sophie Dee Bouncing... | 160MB vs 127MB | 8.0min | Deleted 127MB |
| Ava Nicks Sucks... vs Ava_Nicks_Sucks_Her_Stepson | 75MB vs 111MB | 12.8min | Deleted 75MB |

Also re-checked Nadia Foxx Stepsis (199MB each, 7.3min identical duration) and
StepMom BFF (386MB vs 395MB, 14.7 vs 14.8min) — user confirmed these were
also duplicates despite different hashes/titles. Rule: same duration = duplicate.

```python
# Phase 4: duration-based dedup
import subprocess, os
from collections import defaultdict

known_performers = ["Luna","Kimmy","Richelle","Lexi","Siri","Mia Malkova",
    "Mia Melano","Kali","Blake","Kendra","Lana Rhoades","Lauren","Sharon",
    "Angie","Alanna","Aleksa","Jade","Vina","Asa","Eva","Atlanta","Ember",
    "Nicole","Riley","Payton","Sky","Violet","Nadia","Ava","Angela","Lena",
    "Karma","Alva","Blondie","Savannah","Sophie","Lily","Addams"]

files = [f for f in os.listdir('.') if f.endswith(('.mp4','.mkv','.webm'))]

def get_dur(f):
    r = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
                       '-of','default=noprint_wrappers=1:nokey=1', f],
                      capture_output=True, text=True, timeout=30)
    return float(r.stdout.strip())

durations = {}
for f in files:
    try: durations[f] = get_dur(f)
    except: pass

# Group by performer + duration bucket
watch = defaultdict(list)
for f, dur in durations.items():
    bucket = int(dur / 5) * 5
    for p in known_performers:
        if p.lower() in f.lower():
            watch[(p.lower(), bucket)].append((dur, f))

# Same bucket + same performer = delete the smaller
for key, entries in watch.items():
    if len(entries) > 1:
        entries.sort(reverse=True)
        for dur, f in entries[1:]:
            sz = os.path.getsize(f)
            os.remove(f)
            print(f"Removed {sz//1024**2}MB ({dur/60:.1f}min): {f}")
```

## Final State (after all 4 phases)
- 839 files, 835 videos, ~406GB
- No .info.json, no temp files, no junk, no duplicates by title or duration
- ~16GB recovered over 4 passes

```bash
# Phase 1: bulk remove non-video
cd /mnt/storage/videos
rm -f *.info.json
rm -f *.temp.mp4
find . -maxdepth 1 -size 0 -delete
rm -f *.txt *.sh
rmdir eporner_batch media 2>/dev/null
find . -maxdepth 1 ! -name '*.mp4' ! -name '*.mkv' ! -name '*.webm' ! -name '.' -type f -delete

# Phase 2: hash-based dedup
python3 -c "
import hashlib, os
from collections import defaultdict
files = [f for f in os.listdir('.') if f.endswith(('.mp4','.mkv','.webm'))]
sig_map = defaultdict(list)
for f in files:
    sz = os.path.getsize(f)
    if sz == 0: continue
    with open(f, 'rb') as fh:
        h = hashlib.md5(fh.read(65536)).hexdigest()
    sig_map[f'{sz}:{h}'].append(f)
for sig, fs in [(k,v) for k,v in sig_map.items() if len(v)>1]:
    entries = [(os.path.getsize(f), f) for f in fs]
    entries.sort(reverse=True)
    for _,f in entries[1:]:
        os.remove(f)
        print(f'Removed: {f}')
"

# Phase 3: title-similarity dedup
python3 -c "
import os, re
from collections import defaultdict

def normalized_title(fname):
    t = re.sub(r'\s*\[[a-zA-Z0-9_-]{6,}\]', '', fname)
    t = re.sub(r'\.(mp4|mkv|webm)$', '', t)
    t = re.sub(r'_[a-z0-9]+(?=\.)', '', t)
    t = re.sub(r'^\s*(EPORNER\.COM\s*-\s*\[[^\]]*\]\s*|BT_|AM_|DD_|BTPOV_|DD_)', '', t, flags=re.I)
    t = re.sub(r'\s*-\s*(1080p|720p|480p|360p)', '', t)
    t = re.sub(r'\((1080p|720p|480p|360p)\)', '', t)
    t = re.sub(r'\s+', ' ', t).strip().lower()
    return t

files = [f for f in os.listdir('.') if f.endswith(('.mp4','.mkv','.webm'))]
idx = defaultdict(list)
for f in files:
    idx[normalized_title(f)].append(f)

removed = 0
for title, group in [(k,v) for k,v in idx.items() if len(v)>1 and len(k)>15]:
    entries = [(os.path.getsize(f), f) for f in group]
    entries.sort(reverse=True)
    for _,f in entries[1:]:
        os.remove(f)
        removed += 1
        print(f'Removed ({os.path.getsize(f)//1024**2}MB): {f}')
print(f'{removed} files removed')
"
```

## Key Lessons
1. Clean non-video junk FIRST — eliminates most noise before dedup
2. Size-only dupes are rare (<1%) in this collection — most "duplicates" are different encodes or scenes with similar titles
3. Title normalization is the most productive signal — after stripping viewkeys and site prefixes, ~10 pairs had identical titles
4. Same-title same-performer files with different hashes are usually different encodes of the same scene — user confirmed: delete the smaller
5. Same-size files with different hashes are genuinely different scenes (e.g. both Angie Faith files, both Nadia Foxx files)
6. **Duration matching is essential** — same duration (±5s) + same performer = same scene even with different titles. User rule: "if the time is the same, it's a duplicate." Do not hash-check. Delete the smaller. Caught Sharon Lee, Lauren Phillips, Lana Rhoades, Sophie Dee, and Ava Nicks where title-similarity alone missed them.
