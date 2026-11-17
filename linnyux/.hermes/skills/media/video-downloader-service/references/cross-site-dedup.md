# Cross-Site Dedup Patterns

## Strategy Comparison

| Approach | Speed | Accuracy | Best For |
|----------|-------|----------|----------|
| Viewkey match | Instant | 100% | Pornhub URLs vs MP4s with [viewkey].mp4 |
| Title+duration match | Slow (yt-dlp per URL) | ~90% | Cross-site dupes (same video on different sites) |
| Filename normalized match | Fast | ~85% | Check queued URL titles against existing MP4 files |

## Viewkey Dedup (Pornhub)

Extract the viewkey from the URL: `re.search(r'viewkey=([a-f0-9]+)', url)`
Check if any MP4 filename contains `[viewkey].mp4`:
```python
for f in os.listdir(OUTDIR):
    if f.endswith(".mp4") and vk in f:
        return True  # dupe, skip
```

Only 161 out of 709 MP4s had viewkeys in filenames (old clean_downloader.py format had `%(title).120s [%(id)s].%(ext)s`). The url2video downloader.py uses `%(title).100s.%(ext)s` (no viewkey in filename), so newer downloads won't have viewkeys.

## Title+Duration Match (Cross-Site)

1. Extract title and duration from each queued URL (yt-dlp --dump-json or curl HTML)
2. Normalize title: `re.sub(r'[^a-z0-9\s]', '', t.lower())[:80]`
3. Bucket duration: `round(duration / 5) * 5` (5-second windows)
4. Group by (normalized_title, duration_bucket)
5. In each group with >=2 URLs from different sites: keep one, cancel rest

## Filename Match (Against Existing MP4s)

Strip the `[viewkey].mp4` pattern from existing filenames:
```python
title_part = re.sub(r'\s*\[[^\]]+\]\.mp4$', '', f)
title_part = re.sub(r'\.mp4$', '', title_part)
disk_titles[title_key(title_part)] = f
```

Then match queued URL titles against disk titles using normalized key.

## Smart Dedup Script

The full dedup script at `/tmp/smart_dedup.py` handles all three strategies:
1. Phase 1: Pornhub viewkey dedup (instant)
2. Phase 2: Non-Pornhub URLs — curl title extraction, match against disk MP4s and each other
