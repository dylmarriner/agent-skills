# Finding Unfinished Downloads Across Machines

Systematic approach to finding stale/partial downloads across multiple machines in a tailnet.

## Common Download Tools and Their Signatures

| Tool | Partial File Patterns | Active Process |
|------|----------------------|----------------|
| yt-dlp | `*.part`, `*.ytdl`, `*.frag` | `/usr/bin/python3 ... yt-dlp` |
| Browser | `*.crdownload`, `*.download` | Browser process |
| wget | `*.tmp` | `wget` |
| Transmission | `.part` files in incomplete dir | `transmission-daemon` |
| curl | `*.tmp` | `curl` |

## Detection Strategy

### 1. Check Active Processes
```bash
ps aux | grep -iE "yt-dlp|youtube-dl|transmission-daemon|wget.*http"
```

### 2. Check Partial Files
```bash
find /home -maxdepth 5 \( -name "*.part" -o -name "*.ytdl" -o -name "*.crdownload" -o -name "*.frag" \) 2>/dev/null \
  | grep -v "node_modules\|\.cache\|\.npm\|\.cargo\|snap\|\.local\|\.config\|\.hermes"
```

### 3. Check Transmission
```bash
# Get credentials from settings (hashed passwords won't help)
sudo grep -E 'rpc-password|download-dir|rpc-port|rpc-username' /etc/transmission-daemon/settings.json
# Try common password
transmission-remote 9091 -n 'transmission:transmission' -l
```

### 4. Check Large Download Directories
```bash
# Common download locations
for d in ~/Downloads /mnt/torrents /mnt/shared/videos; do
  [ -d "$d" ] && echo "$d: $(ls "$d" | wc -l) files, $(du -sh "$d" | cut -f1)"
done
```

## Verifying Download State

For a `.part` file, check:
- **Age**: `stat` modification time — stale if > 1 hour with no active process
- **Size**: Partial size vs expected — `*.part` under 100M likely incomplete
- **Process**: Is there a yt-dlp/wget/curl process for this URL?
- **Log files**: Look for `*.log` files alongside the `.part` files with progress info

## Cross-Machine Search Pattern

When searching across multiple machines in a tailnet:

```bash
# For each reachable machine, check:
for host in "rabuntu" "kubuntux" "lin" "macuntu"; do
  echo "=== $host ==="
  ssh $host "ps aux | grep -iE 'yt-dlp|youtube-dl' | grep -v grep"
  ssh $host "find /home -maxdepth 3 -name '*.part' -not -path '*node_modules*' -not -path '*.cache*' 2>/dev/null"
done
```

### Focus on Video Downloads Only

When the user says "videos I downloaded by URL", filter for:
- **yt-dlp** running with video formats (NOT `-x --audio-format mp3` which extracts audio)
- **.part files** in video directories (stale = no matching process)
- **Log files** alongside .part files showing progress/errors
- **Batch scripts** that orchestrate multiple downloads

Ignore:
- Music downloads (yt-dlp with `-x --audio-format mp3`)
- Transmission/BitTorrent downloads (those are peer-to-peer, not URL-based)
- Browser `.crdownload` files (unless specifically asked)

```bash
# Remove stale partials (no matching process)
rm -f /path/to/stale/file.part
```
