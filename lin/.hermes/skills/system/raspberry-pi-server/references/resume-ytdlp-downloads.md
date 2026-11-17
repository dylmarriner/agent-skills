# Resuming yt-dlp Downloads on a Remote Pi

Pattern for resuming interrupted yt-dlp downloads on a remote machine running over Tailscale relay SSH, where SSH sessions are prone to dropping.

## The Problem

`tailscale-ssh: process died: signal: terminated` — the SSH connection drops while yt-dlp is running, killing the download. The `.part` file survives and can be resumed, but the sequential `&&` chain of downloads aborts at the failure point.

## Resuming .part Files

yt-dlp auto-resumes `.part` files if you run the same URL with `--continue`:

```bash
yt-dlp --retries 10 --continue --no-overwrites 'https://example.com/video-url'
```

- `--continue` — resume existing `.part` files instead of starting over
- `--no-overwrites` — don't re-download completed files
- `--retries 10` — retry up to 10 times on connection errors

## Finding URLs from Log Files

When the original download URL is lost, check log files saved alongside the `.part` files:

```bash
# Check log files
ls *.log

# Extract URLs from logs
grep -h "Extracting URL:" *.log 2>/dev/null | awk '{print $NF}'
```

Log files typically contain:
```
[Eporner] Extracting URL: https://www.eporner.com/video-XXXXXX/video-name/
[download] Destination: /path/to/video.mp4
[download]   5.7% of    2.85GiB at  114.87KiB/s ETA 06:48:46
```

## Running Downloads That Survive SSH Death

### Method 1: Write a Script, Then Execute

Write a script on the remote machine, then run it:

```bash
# Write the script
ssh user@host "cat > /tmp/resume.sh << 'SCRIPT'
#!/bin/bash
cd /path/to/download/dir

yt-dlp --retries 10 --continue --no-overwrites 'URL1'
yt-dlp --retries 10 --continue --no-overwrites 'URL2'
# ... repeat for each URL ...
echo 'ALL DONE'
SCRIPT
chmod +x /tmp/resume.sh"

# Execute with long timeout (runs even if SSH drops between commands)
# Use terminal(background=true, timeout=86400)
ssh user@host "bash /tmp/resume.sh"
```

### Method 2: Sequential Downloads (One Per SSH Call)

For very slow connections where even the script approach drops, run one URL per SSH call:

```bash
ssh user@host "yt-dlp 'URL1' --retries 10 --continue --no-overwrites"
# After it finishes or SSH drops, check progress and resume next:
ssh user@host "ls *.part 2>/dev/null | wc -l"
ssh user@host "yt-dlp 'URL2' --retries 10 --continue --no-overwrites"
```

### Method 3: Background with nohup (on the Pi)

From the Pi directly (or via SSH), detach the process from the SSH session:

```bash
nohup bash /path/to/script.sh > /dev/null 2>&1 &
disown
```

This survives SSH disconnect but you can't get status updates without checking the log.

## Checking Progress

```bash
# Check if yt-dlp is still running
ps aux | grep yt-dlp | grep -v grep

# Check download log for latest progress
tail -5 eporner_run.log

# Check how many .part files remain
ls *.part 2>/dev/null | wc -l

# Check how many completed files
ls *.mp4 2>/dev/null | wc -l
```

## Handling Rate-Limited Sites

Some sites (like eporner.com) aggressively rate-limit with `HTTP Error 429: Too Many Requests`. yt-dlp retries automatically with exponential backoff, but speeds can drop to 50-200 KiB/s (from peaks of 1-2 MiB/s).

Key observations from eporner.com downloads:
- Initial burst at 500-1000 KiB/s for ~1-2% of file
- Then drops to 100-400 KiB/s sustained
- Frequent "Got error: Downloaded X bytes, expected Y bytes. Retrying (N/10)..."
- Each retry resets to very slow (~1 KiB/s) then ramps back up over 10-30 seconds
- A single 2.85GB file takes 2-3 hours at sustained 320 KiB/s
- Format `2160p_4K__HD` is ~2.85GB; lower quality formats would be faster
