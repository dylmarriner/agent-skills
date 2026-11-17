# Batch Download Status Checking Workflow

When checking on background downloads started in previous sessions or currently running.

## CRITICAL: List ALL known job categories, not just the first one found

This user routinely runs **multiple simultaneous crawl/download jobs** across different categories. If they ask about "crawl jobs" or download status, you MUST enumerate every known batch category — not just the most recent one. A single answer is always incomplete.

Known batch categories to check:
1. **eporner tagged batches** (`am_` = Atlanta Moreno, `dd_` = Dan Dangler, `bt_` = Big Tits POV) — launched via queue_dl.py or similar
2. **epdl master batch** (loose Eporner_ prefixed files — Karma RX, Blake Blossom, Violet Myers, Mia Malkova, Lena Paul, Payton Preslee, etc.) — launched via eporner_master.sh in tmux
3. **Per-URL manual downloads** (single URLs sent by the user) — check for loose MP4s not matching any category prefix
4. **borntobefuck / pimpbunny / porntn / xxbrits / xhamster** batches

When the user says "have you finished your crawl job" or "check the status", do NOT:
- Assume they mean the most recent or most obvious job
- Answer with only one category's results
- Wait for them to say "and the other" — enumerate ALL upfront

**Correct answer format:**
```
Crawl 1 — eporner tagged (am_/dd_/bt_): X/Y ✓
Crawl 2 — epdl master: X/Y ✓
[more categories...]
Nothing running now.
```

## 1. List all category-prefixed files
```bash
echo "Atlanta Moreno:"; ls /mnt/storage/videos/am_*.mp4 2>/dev/null | wc -l
echo "Dan Dangler:"; ls /mnt/storage/videos/dd_*.mp4 2>/dev/null | wc -l
echo "Big Tits POV:"; ls /mnt/storage/videos/bt_*.mp4 2>/dev/null | wc -l
echo "Eporner_ prefixed:"; ls /mnt/storage/videos/Eporner_*.mp4 2>/dev/null | wc -l
echo "Total MP4s:"; ls /mnt/storage/videos/*.mp4 2>/dev/null | wc -l
echo "Disk:"; df -h /mnt/storage/videos/ | tail -1
```

## 2. Check for running download processes
```bash
ps aux | grep -iE 'yt-dlp|queue_dl|eporner_master' | grep -v grep
```

## 3. Look for leftover partial/queue files
```bash
ls -la /mnt/storage/videos/*.part /mnt/storage/videos/*.ytdl 2>/dev/null
cat /mnt/storage/videos/queue_done.txt 2>/dev/null | tail -5
cat /mnt/storage/videos/queue_failed.txt 2>/dev/null | tail -5
cat /mnt/storage/videos/queue_stdout.log 2>/dev/null | tail -10
```

## 4. Check old tmux sessions (may have long-running jobs)
```bash
tmux ls 2>/dev/null
```

## 5. Check completed files and their validity
```bash
# List recent MP4 files sorted by modification time
ls -lt /mnt/storage/videos/*.mp4 2>/dev/null | head -10

# Verify a specific file
ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1:nokey=1 "/target/directory/file.mp4"
```

## 6. Cross-check with session history
```bash
session_search(query="<category> crawl download", limit=3)
```

For original crawl task lists that may span old sessions, check:
```bash
cat /home/kubuntux/eporner_master.sh 2>/dev/null | head -5
ls /mnt/storage/videos/queue_dl.py 2>/dev/null
```

## 7. For multi-machine checks, use SSH with jump hosts
See references/ssh-multi-machine-investigation.md

## 8. Clean up only when safe
Only remove .part/.ytdl files when NO yt-dlp processes are running. See the "Pitfalls" section in the main skill for details.