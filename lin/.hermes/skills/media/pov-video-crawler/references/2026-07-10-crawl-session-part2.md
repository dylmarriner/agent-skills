# 2026-07-10 Crawl Session — Part 2: Verification + Alexis Texas + Downloads

This extends references/2026-07-10-crawl-session.md with the second pass findings.

## Post-Crawl Live Verification

After the initial crawl (450 URLs), a live yt-dlp --get-title verification was
run on EVERY URL in parallel (xargs -P 8) using /tmp/verify_one.sh:

```bash
#!/bin/bash
url="$1" outfile="$2"
title=$(yt-dlp --impersonate chrome --get-title "$url" 2>/dev/null | head -1)
title_lower=$(echo "$title" | tr '[:upper:]' '[:lower:]')
if echo "$title_lower" | grep -qiE '(bbc|interracial|black.?cock|black.?dick|big.?black|black.?bf|blacked|blackedraw|bwc|ebony|blacks.?on|monster.?dick)'; then
    exit 1  # BBC - skip
else
    echo "$url" >> "$outfile"
    exit 0
fi
```

### Results: 2 of 450 removed

| URL | Title | Why |
|-----|-------|-----|
| `pornhub.com/...?viewkey=66a6dc86d2a26` | "NATASHA NICE Shows Off Her Big Titties to Poolboy before Anal Fucked - BlacksOnBlondes" | Interracial studio "BlacksOnBlondes" |
| `pornhub.com/...?viewkey=6642b06d21d06` | "Inked Babe KARMA RX Gets a DP & Anal Creampie with her Food Order - BlacksOnBlondes" | Same studio |

**Key lesson:** "BlacksOnBlondes" was invisible at crawl time because:
- PornHub viewkey URLs have zero title info in the URL
- The regex `black\s*cock` does NOT match "BlacksOnBlondes" (needs a space before "cock")
- Fix: Add `blacks?\.?on` to the blocked pattern (catches "BlacksOnBlondes", "Blacks On Blondes", "blacks.on")

## New Performers Added

After the 37-performer crawl, the user also wanted:

### Alexis Texas (20 URLs)
Searched Pornhub + XNXX. Found 8 Pornhub results + 12 XNXX results with her name in the title. 1 explicit POV title ("Alexis Texas Big Booty in Your Face POV Fuck"). Added 20 to crawl file.

### Mia Melano (5 URLs)
Only 5 total POV results found across Pornhub (4) + XNXX (1). Her content is mostly VIXEN studio scenes (non-POV). Added all 5 to crawl.

## Final Crawl File

- **Path:** `/mnt/storage/videos/.queue/pov_crawl_clean.txt`
- **473 URLs** across 39 performers (37 original + Alexis Texas + Mia Melano)
- **2 removed** for BBC (BlacksOnBlondes)
- **0 duplicates** within file
- **0 duplicates** with existing downloads

## Download Workflow

**videosnap CLI is broken** — circular import error in `backend/queue.py` (name collision with Python stdlib `queue` module).
The server (`serve` command) was never tested. Fall back to direct yt-dlp.

### Download Script Pattern

Saved as /tmp/download_crawl.sh:

```bash
#!/bin/bash
CRAWL_FILE="$1"
MAX_PARALLEL="${2:-3}"

grep -oP 'https?://\S+' "$CRAWL_FILE" | sort -u > /tmp/download_queue.txt

cat /tmp/download_queue.txt | xargs -P "$MAX_PARALLEL" -I{} sh -c '
  url="{}"
  yt-dlp --impersonate chrome \
    --format "bestvideo[height<=1080]+bestaudio/best[height<=1080]" \
    --merge-output-format mp4 \
    --output "/mnt/storage/videos/%(title)s [%(id)s].%(ext)s" \
    --no-playlist --no-warnings --no-mtime \
    --retries 3 --fragment-retries 3 --socket-timeout 30 \
    "$url" > /dev/null 2>&1
'
```

**3 parallel downloads** recommended to avoid rate limiting on Pornhub/XNXX.

## Blacklist Updates (confirmed 2026-07-10)

Add to BLOCKED patterns:
- `blacks?\.?on` — catches "BlacksOnBlondes", "Blacks On Blondes", "blacks.on"
