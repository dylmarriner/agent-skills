# Multi-Machine Video Download Workflow

## Machine roles

| Machine | Tailscale IP | Role | Video downloader |
|---------|-------------|------|-----------------|
| **kubuntux** (local) | — | Coordinator, SSH client | `dlv` wrapper, `yt-dlp`, `megadl` |
| **macuntu** | 100.75.23.127 | Download node | `~/Documents/video-downloader/video_downloader.py`, `yt-dlp` |
| **root server** | 100.102.4.39 | Bulk download node | `yt-dlp`, VR conversion project |
| **rabuntu (Pi)** | 100.68.0.96 | Storage node | SMB share at `//100.68.0.96/shared` |
| **lin** | 100.91.55.113 | Download node (pimpbunny) | via SSH from macuntu |

## SMB share layout

The Pi's SMB share is mounted at `/mnt/pivideos/` on kubuntux. Videos go in `/mnt/pivideos/videos/`. Always verify with `df -h /mnt/pivideos/` before starting a download — share is 220GB total, ~92% full.

## When user says "use the version off X machine"

When the user says "use the downloader from macuntu" (or similar):
1. SSH into that machine: `ssh macuntu@100.75.23.127`
2. Check what download tools exist:
   - `which yt-dlp` / `command -v yt-dlp`
   - `ls ~/.local/bin/` for custom scripts
   - Look in `~/Documents/` for project-specific downloaders
3. Use the machine's local tools. Common approaches:
   - **yt-dlp** (macuntu): `/usr/bin/yt-dlp -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" --merge-output-format mp4 -o "/mnt/pi/shared/videos/%(title)s.%(ext)s" "<url>"`
   - **Custom downloader** (macuntu): `python3 ~/Documents/video-downloader/video_downloader.py <url> --output /mnt/pi/shared/videos/`
4. The Pi share is mounted at `/mnt/pi/shared/` on macuntu (verify with `df -h`).

## Checking for existing files before download

Before starting a download, check everywhere:
1. **Local disk** on kubuntux: `find /home/kubuntux/ -name "*<keyword>*" -type f`
2. **Pi SMB share**: `ls /mnt/pivideos/videos/ | grep -i "<keyword>"`
3. **Via macuntu**: `ssh macuntu "ls /mnt/pi/shared/videos/ | grep -i '<keyword>'"`
4. **Root server**: `ssh root@100.102.4.39 "find / -name '*<keyword>*' -type f 2>/dev/null | head -5"`

## Cron job setup for timed releases

Use the `cronjob` tool with `enabled_toolsets: ["browser","terminal","file"]`. Schedule 10-15 min after the timer expires.

## Verification

Always verify downloaded files:
```bash
ffprobe -v error -show_entries format=size,duration:stream=width,height -of default=noprint_wrappers=1 "<file>"
```

Compare duration to expected (e.g., 22 min vs 20 sec = preview). Check width/height for resolution.
