# Multi-Machine Download Investigation via SSH

When you have Hermes/OpenClaw installed on multiple machines (e.g., kubuntux, macuntu, rabuntu, lin) linked via Tailscale, use this workflow to check download status across all devices.

## Prerequisites
- Tailscale SSH configured between machines
- Known hostname mappings (check ~/.ssh/config or /etc/hosts)
- Jump host configuration if direct SSH is blocked

## Machine Inventory (from user's setup)
- **kubuntux**: Primary machine (current session)
- **macuntu@100.75.23.127**: Can SSH directly, serves as jump host
- **rabuntu@100.68.0.96**: Accessible via macuntu jump host
- **lin@100.91.55.113**: Accessible via macuntu jump host
- **root@100.102.4.39**: Direct SSH (VR conversion project)

## Workflow

### 1. Direct SSH (when permitted)
```bash
ssh user@host "command to check downloads"
```

### 2. Via Jump Host (when direct SSH blocked by Tailscale policy)
```bash
# Syntax: ssh -J jump_host user@target_host "command"
ssh -J macuntu@100.75.23.127 rabuntu@100.68.0.96 "ps aux | grep -E '(yt-dlp|spotify|music)' | grep -v grep"
```

### 3. Common check commands
```bash
# Check for active video/audio downloads
ps aux | grep -E '(yt-dlp|ffmpeg|spotify|music|youtube)' | grep -v grep

# Check download directory for recent files
ls -lt ~/videos/*.mp4 | head -5

# Check for partial files
ls -la ~/videos/*.part ~/videos/*.ytdl 2>/dev/null || echo "No partials"

# Check disk space on video storage
df -h /path/to/video/storage
```

### 4. Specific examples from this session
```bash
# Check rabuntu music download (via jump host)
ssh -J macuntu@100.75.23.127 rabuntu@100.68.0.96 "ps aux | grep -E '(music|yt-dlp|youtube)' | grep -v grep"

# Check lin for downloads (direct SSH worked)
ssh lin@100.91.55.113 "ps aux | grep -E '(music|yt-dlp|youtube)' | grep -v grep"

# Check root VR project machine
ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no root@100.102.4.39 "ps aux | grep yt-dlp | grep -v grep"
```

### 5. Process identification tips
- yt-dlp: Usually shows as `/usr/bin/python3 /home/user/.local/bin/yt-dlp ...`
- ffmpeg: Shows as `ffmpeg -i ...` or `/usr/bin/ffmpeg ...`
- Spotify/music: Look for `spotify`, `music`, or `yt-dlp -x` (audio extraction)
- Background processes: Often show `Ss` or `Sl` state in ps output

### 6. When you find a stuck download
1. Note the PID and command
2. Check if it's making progress (check file size over time)
3. If stuck, consider killing and restarting with a different approach
4. Always verify output file integrity before declaring complete

## Safety Notes
- Never kill processes blindly - check if they're making progress first
- When cleaning partial files, ensure no download is active for that target
- Use `kill -9` only as last resort after normal `kill` doesn't work