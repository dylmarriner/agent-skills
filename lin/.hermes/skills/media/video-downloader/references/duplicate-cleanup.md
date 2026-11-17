# URL-encoded Duplicate Cleanup

## The problem

yt-dlp and other download tools sometimes save files with URL-encoded characters (%20 for spaces, %2C for commas) instead of decoding them to human-readable filenames. This leaves two copies of the same video:

- `EPORNER.COM - [1lbQXuy7Nrg] Huge load creampie for Asian busty stepmom (1080).mp4` (properly named)
- `EPORNER.COM%20-%20[1lbQXuy7Nrg]%20Huge%20load%20creampie%20for%20Asian%20busty%20stepmom%20(720).mp4` (URL-encoded duplicate)

The properly-named version is usually preferred (human readable). The %20 versions consume double disk space.

## How to identify

```bash
# List all files with URL-encoded characters
cd /mnt/pivideos/videos/
ls | grep '%'
```

Common patterns:
- `%20` → space
- `%2C` → comma  
- `%28` → `(`
- `%29` → `)`
- `%5B` → `[`
- `%5D` → `]`

## How to remove

```bash
cd /mnt/pivideos/videos/
# Remove all URL-encoded files (preserving the properly-named originals)
for f in *%*.mp4; do
  rm -f "$f"
done
```

## Safe removal check

Before bulk removal, verify the properly-named equivalents exist:

```bash
# Extract the URL-decoded name and verify
for f in *%*; do
  # URL-decode the filename and check if proper version exists
  decoded=$(python3 -c "import urllib.parse; print(urllib.parse.unquote('$f'))" 2>/dev/null)
  if [ -f "$decoded" ]; then
    echo "DUPLICATE (safe to remove): $f"
  else
    echo "UNIQUE (check first): $f"
  fi
done
```

## Also clean up

- `.part` files — leftover from interrupted HLS downloads
- `.ytdl` files — yt-dlp metadata files  
- `.part-Frag*` files — leftover HLS fragment stubs

```bash
rm -f *.part *.ytdl *.part-Frag* 2>/dev/null
```

## When NOT to clean

- **Any yt-dlp process is running**: `ps aux | grep yt-dlp | grep -v grep` — if any output, do NOT remove .part files
- **Downloads are still in progress**: Wait for all background processes to complete first
- **SMB mount is slow**: Deletion on slow SMB mounts can take a while; be patient
