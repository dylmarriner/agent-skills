# Parallel Content Verification via yt-dlp --get-title

## Why This Exists

URL-slug-only content filtering is CIRCULAR — it re-checks the same text that was used during the crawl. The 2026-07-09 session proved this: the slug-only pass claimed zero violations, but the user confirmed the library was "a fucking mess" with BBC and non-POV content.

**Real verification requires fetching the actual page title from the live site.** This document covers the parallel batch method.

## The Core Pattern

```bash
#!/bin/bash
# verify_single.sh — called once per URL via xargs -P
url="$1"
outfile="${2:-/tmp/verify_results.txt}"

title=$(yt-dlp --impersonate chrome --get-title "$url" 2>/dev/null | head -1)
[ -z "$title" ] && title="(no title / error)"

title_lower=$(echo "$title" | tr '[:upper:]' '[:lower:]')

# BBC/black/interracial detection
flag=""
echo "$title_lower" | grep -qiE '(bbc|interracial|black.?cock|black.?dick|big.?black|black.?bf|black.?guy|black.?man|black.?bull|blacked|blackedraw|bwc|ebony|monster.?dick|chocolate.?pussy)' && flag="FLAG_BBC"

# POV detection
pov=""
echo "$title_lower" | grep -q 'pov' && pov="POV"

# Big tits detection
tits=""
echo "$title_lower" | grep -qiE '(big.?tit|busty|huge.?tit|massive.?tit|boobs|breast|juggs)' && tits="BIGTITS"

echo "$url|$title|$pov|$tits|$flag" >> "$outfile"
```

## Running in Parallel

```bash
# 8 concurrent workers — adjust based on your connection
cat /tmp/urls_to_verify.txt | xargs -P 8 -I{} /tmp/verify_single.sh "{}" /tmp/results.txt
```

**Progress tracking:** `wc -l /tmp/results.txt` against total.

## Analyzing Results

```python
from pathlib import Path

results = Path("/tmp/results.txt").read_text().strip().split('\n')
total = len(results)
flagged = [r for r in results if 'FLAG_BBC' in r]
pov = [r for r in results if '|POV|' in r]
bigtits = [r for r in results if 'BIGTITS' in r]
errors = [r for r in results if '(no title / error)' in r]

print(f"Total: {total}")
print(f"BBC flagged: {len(flagged)}")
print(f"Has POV in title: {len(pov)}")
print(f"Has BIG TITS in title: {len(bigtits)}")
print(f"yt-dlp errors (may be removed/dead): {len(errors)}")

# Show flagged
for r in flagged:
    parts = r.split('|')
    print(f"  FLAG: {parts[0][:70]} => '{parts[1][:50]}'")
```

## Performance

- **Pornhub:** ~3-4s per URL (browser wrapper overhead). 703 URLs × 4s / 8 workers = ~6 min.
- **Eporner:** ~2-3s per URL. 626 URLs × 3s / 8 workers = ~4 min.
- **Redtube:** ~2s per URL. 167 URLs / 8 workers = ~40s.
- **XNXX/XHamster:** ~3s per URL. 158 total / 8 workers = ~1 min.

**Total for 1,794 video URLs at 8 workers:** ~12-15 min end-to-end.

## Key Cautions

1. **Don't claim verification is done until every URL has been hit.** 35/1794 spot checks is not verification — it's a sniff test. The user will call you on it.

2. **Rate limits are real.** Eporner starts returning 503s at 4+ simultaneous requests. Pornhub throttles at ~10/min total regardless of workers. XHamster is bouncy. If you see a burst of errors, drop parallel count or add a small delay.

3. **Some URLs will be dead** (removed by uploader, deleted by site). These return empty titles. Track them separately — they should be removed from queue files but aren't BBC violations.

4. **The keyword check is a fast filter, not a guarantee.** A title saying "Asian Hottie Gets Destroyed" without "BBC" or "black" in it could still be interracial by the video content. There is no substitute for actually watching the video. But title filtering is the best automated pass you can do.

5. **False positives happen.** A pornhub viewkey like `64c3bbc516493` contains "bbc" in the hex hash. The actual video may be clean. Title check resolves this — but flag the URL for review regardless since the viewkey itself suggests the video was scraped from a BBC-tagged context.

## Related

- `pov-video-crawler` SKILL.md — step 3 has the keyword lists and the warning
- `scripts/verify_urls.py` — runnable version of this pattern
