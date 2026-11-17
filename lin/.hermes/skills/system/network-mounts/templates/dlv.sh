#!/usr/bin/env bash
# dlv — Download video to network-mounted videos folder
# Usage: dlv <url>                   — max 1080p
#        dlv -l <url>               — list formats
#        dlv -f <format> <url>      — specific format
#        dlv -a <url>               — audio only (mp3)
#
# Set VIDEOS_DIR to your network mount's videos path.

VIDEOS="${VIDEOS_DIR:-/mnt/pivideos/videos}"

# systemd-automount handles mounting on access
if ! [ -d "$VIDEOS" ]; then
    echo "Waiting for mount..." >&2
    ls "$(dirname "$VIDEOS")" >/dev/null 2>&1 || {
        echo "ERROR: Mount not reachable" >&2
        exit 1
    }
fi

case "${1:-}" in
    -l|--list)
        shift
        exec yt-dlp -F "$@"
        ;;
    -a)
        shift
        exec yt-dlp -f bestaudio --extract-audio --audio-format mp3 \
            -o "$VIDEOS/%(title)s.%(ext)s" "$@"
        ;;
    -f)
        fmt="$2"
        shift 2
        exec yt-dlp -f "$fmt" --merge-output-format mp4 \
            -o "$VIDEOS/%(title)s.%(ext)s" "$@"
        ;;
    *)
        # Max 1080p: best video+audio combo at or below 1080p
        exec yt-dlp -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" \
            --merge-output-format mp4 \
            -o "$VIDEOS/%(title)s.%(ext)s" "$@"
        ;;
esac
