---
name: music-deduplication
description: "Find and remove duplicate music files on external drives. Two-pass approach: binary-exact via jdupes, then fuzzy name/ID3 matching."
category: media
tags: [duplicates, mp3, flac, dedup, jdupes, music-library]
triggers: [duplicate, duplicate songs, same song twice, dedup, clean music library, rescan dupes]
---

# Music File Deduplication

Find and remove duplicate music files (MP3, FLAC, WAV, M4A, etc.) from USB drives or library directories.

## Workflow

### Step 1: Identify the target drive

```bash
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,LABEL,MODEL | grep -E "sd[b-z]|nvme"
df -h | grep -E "/media|/mnt|/run/media"
```

Count music files:
```bash
find /media/lin/XXXX-XXXX -type f \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.wav" -o -iname "*.m4a" -o -iname "*.aac" -o -iname "*.ogg" -o -iname "*.wma" -o -iname "*.opus" -o -iname "*.aiff" \) | wc -l
```

### Step 2: Binary-exact dedup with jdupes

```bash
sudo apt-get install -y -qq jdupes
jdupes -r -q -S /media/lin/XXXX-XXXX
```

### Step 3: Fuzzy name analysis

Python script approach:
1. Group by file size, MD5-hash same-size files
2. Strip track numbers and years from filenames
3. Find same-title files with different sizes (different sources)
4. Optionally use mutagen for ID3 artist+title matching

Score function to decide which copy to keep:
```python
def score(name):
    s = 0
    if re.search(r'\(\d{4}\)', name): s += 10
    s += len(name) / 100.0
    return s
```

### Step 4: Generate deletion script

Use `shlex.quote()` for safe shell escaping. Keep the copy with year-in-name.

### Step 5: Verify

```bash
jdupes -r -q /media/lin/XXXX-XXXX
```

## Output format

Present: summary (totals, space wasted) + a runnable script. If user says "rescan", output is too verbose.

## Reference files

- `references/gen-dedup-script.py`: Standalone Python script that generates the deletion bash script. Update MUSIC_DIR path, then run it.

## Pitfalls

- **-iname vs -name**: Use `-iname` for counts (catches `.MP3` uppercase).
- **Shlex.quote()**: Required for filenames with `$`, `'`, `&`, parens.
- **AlbumArt jpgs**: Skipped unless asked (trivial size).
- **.Trash dirs**: Drive may have a recycle bin with recoverable files.
