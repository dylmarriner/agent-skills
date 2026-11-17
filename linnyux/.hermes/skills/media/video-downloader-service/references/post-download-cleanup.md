# Post-Download Cleanup: Dedup, Content Filtering, Folder Maintenance

For Dylan's POV-only video collection at `/mnt/storage/videos/` (SMB share `\\KUBUNTUX\videos`).

## Core Rules

- **POV-only.** Anything that is clearly not POV gets removed.
- **No BBC/interracial/BWC/ebony** (unless the ebony clip is explicitly POV). Filename keywords: `bbc`, `interracial`, `bwc`, `black.*cock`, `black.*dick`, `black.*pussy`, `big.*black`, `blackzilla`, `ebony.*cock`.
- **1080p preferred.** Lower-quality copies of the same scene get deleted.
- **No metadata/temp/junk files.** `.info.json`, `.temp.mp4`, 0-byte files, `.txt`, `.sh`, non-video clutter all get removed.

## Duplicate Detection (in order of reliability)

### 1. Duration matching (PRIMARY method)
Same scene = same duration within 5 seconds. This catches identical content even when filenames/titles/viewkeys differ.

```
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 <file>
```

Compare all files. Round duration to nearest 5s bucket. Files in the same bucket with overlapping performer names are duplicates. **Duration match is definitive** — same hash not required.

### 2. Same filename after stripping [viewkey]
Strip `[a-zA-Z0-9_-]{6,}` patterns from filenames. If the remaining title matches exactly, they're the same video uploaded to different sites.

### 3. Same size + same first 64KB hash
Quick partial hash check. Same size + same leading content = duplicate.

### 4. Same viewkey in filename
Files like `Title [abc123].mp4` sharing `[abc123]` are the same video.

## Removal Policy

| Condition | Action |
|-----------|--------|
| Same duration, different size | Keep the LARGER file (higher quality) |
| Same duration, same size | Keep the file WITH a [viewkey] (has provenance) |
| Same title (strip [viewkey]) | Keep the larger file |
| Same viewkey | Keep the file with `1080p` in name, or the larger one |
| `.temp.mp4` or `.info.json` | Always delete |
| BBC/interracial in filename | Always delete regardless of POV tag |
| VR / compilation / gangbang / DP / trans / JAV / parody / cuckold | Delete immediately |
| 0-byte files | Delete immediately |

## Non-POV Detection Patterns

### Strong indicators (delete immediately):
- `\bvr\b`, `\bvirtual\b` — VR content
- `\bcompilation\b`, `\bcomp\b.*\bvideo\b`, `\bpmv\b` — compilations
- `\bfuta\b`, `\btrans\b.*\bgirl\b` — trans content
- `\bgangbang\b` — gangbang
- `\bdp\b`, `\bdvp\b`, `\bdouble\s+(anal|pen)\b` — double penetration
- `\bjav\b`, `\buncensored\b` — Japanese adult video
- `\bparody\b`, `\bhentai\b`, `\banime\b.*\bparody\b` — parody/hentai
- `\bcuck(old|ing|hold)\b` — cuckolding
- `\bblowpass\b` — compilation studio
- `\bbang\s+surprise\b` — Bang Surprise is a studio that packages clips
- `\bdouble\s+stuffed\b` — DP

### Likely non-POV (review each, delete unless clearly POV step-family):
- `\bgets\s+(fucked|pounded|nailed|rammed|destroyed|stuffed|filled|drilled)\b`
- `\btakes\s+(a|his|her|it|all|the)\b.*(cock|dick|load|cum|pound)`
- `\bfucks?\s+(her|him|a|the|my)\b`
- `\bhe\s+(fucks|eats|licks|sucks|rubs|slides|pushes)`
- `\bher\s+(ass|pussy|mouth|holes?|face)\s+(gets|is|was)`
- `\bfucked\s+(by|from|in\s+the)\b`
- `\bcreampie(d|ing)?\s+(her|his|the)\b`
- `\bthreesome\b` — unless step-family POV
- `\bhuge\s+(cock|dick|load|cumshot)`
- `\bmonster\s+(cock|dick)`
- `\brough\b`, `\bhardcore\b`
- `\bfill(ed|ing|s)?\s+(her|her\s+holes?|up)`
- `\bstuff(ed|ing)?\s+(her|her\s+holes?)`
- `\bdrill(ed|ing)?\s+(her|her\s+)`
- `\bslut(t?y)?\s+(gets|is|was)`, `\bwhore\b`
- `\bfacial\b`
- `\bswallow(s|ed|ing)`

### Step-family titles that ARE POV (likely keep):
- `\b(stepmom|stepson|stepdad|stepsis|stepbro|stepdaughter)\b` + descriptive title — usually POV from step-relative perspective
- `\b(mommy'?s boy|pervmom|familyxxx|taboo)\b` — these studios specialize in POV
- `\b(caught|walks in on|discovers)\b.*\b(step|mom|son|sis)\b` — POV framing

## Cleanup Workflow Script

```python
# Step 1: Strip non-video files
for f in os.listdir('.'):
    if f.endswith('.info.json') or f.endswith('.temp.mp4') or os.path.getsize(f) == 0:
        os.remove(f)

# Step 2: Remove BBC/interracial by filename
import re
BBC_PATTERNS = [r'\bbbc\b', r'\binterracial\b', r'\bbwc\b', r'\bblack\s+cock\b',
                r'\bblack\s+dick\b', r'\bblack\s+pussy\b', r'\big\s+black\b',
                r'\bblackzilla\b', r'\bblack\s+experience\b']
for f in os.listdir('.'):
    if any(re.search(p, f.lower()) for p in BBC_PATTERNS):
        os.remove(f)

# Step 3: Group by duration (ffprobe), keep largest in each group
# Step 4: Group by base title (strip [viewkey]), keep largest in each group
```

## Total Session Cleanup Reference

In one session (Jul 2026), ~45GB was recovered:
- 63 `.info.json` files removed
- 5 BBC/interracial files
- 45 non-POV files (VR, compilations, trans, DP, JAV, gangbang, parody)
- 20 duplicate videos (by duration matching)
- ~67 grey-area files flagged for review (16GB pending)
