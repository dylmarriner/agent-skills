# Two-Phase Pipeline Architecture

Single-pass (search+download per performer) is **4x slower** than two-phase. This session proved the right approach.

## Phase 1: Crawler (`/tmp/phase1_crawler.py`)

- Loops through 40 performers × 10 sites
- Each site uses its specific mechanism (API or HTML scrape)
- Title-based BBC/POV filtering happens BEFORE adding to queue
- Dedup by video ID against existing files and queue
- Appends to `/tmp/video_queue.txt` in format: `performer_name|site|video_url`
- Runs in ~10 min for 40 performers
- Can run simultaneously with Phase 2

## Phase 2: Downloader (`/tmp/phase2_downloader.py`)

- Reads `/tmp/video_queue.txt`, skips URLs in `/tmp/video_done.txt`
- Downloads N=6 in parallel with 600s timeout per file
- Only writes to done file when `.mp4` actually created on disk
- Timeouts are NOT marked done — they get retried
- Runs until queue is empty AND Phase 1 is no longer running

## Key Edge Cases Handled

- **Orphaned `.part` files**: Cleaned up on timeout/failure
- **CDN speed variation**: Some sites give 5MB/s, others 800KB/s. 600s handles both.
- **Process lifecycle**: Phase 2 detects when Phase 1 is done (pgrep) and exits cleanly
- **Done-file resilience**: On restart, already-downloaded URLs are skipped
