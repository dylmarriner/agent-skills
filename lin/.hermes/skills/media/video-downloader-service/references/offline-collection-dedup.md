# Offline Collection Dedup

**When to use:** An existing video collection (thousands of MP4s) needs cleaning — find real content duplicates regardless of filename or naming convention. This is different from queue-time dedup (which checks viewkeys before download). This is post-hoc cleanup of whatever's already on disk.

## Dedup Pipeline

### Phase 0: Inventory

Count files, check naming patterns:

```python
files = [f for f in os.listdir('.') if f.endswith(('.mp4','.mkv','.webm'))]
print(f"Total: {len(files)}")
```

### Phase 1: Viewkey/ID Match (instant)

Files from yt-dlp follow `Title [id].ext` format. Extract all IDs and group them:

```python
by_id = defaultdict(list)
for f in files:
    m = re.search(r'\[([a-zA-Z0-9_-]{8,})\]', f)
    if m:
        by_id[m.group(1)].append(f)

dups = {k:v for k,v in by_id.items() if len(v) > 1}
```

**Caveat:** Different viewkey != different content. The same video uploaded to different sites gets different viewkeys. This phase only catches the same file name.

### Phase 2: Exact Size Match (fast)

Group files by byte size. Same-size candidates warrant checking:

```python
by_size = defaultdict(list)
for f in files:
    sz = os.path.getsize(os.path.join('.', f))
    by_size[sz].append((f, sz))

# Only check sizes > 1KB (skip empty/thumbnail files)
dups = {k:v for k,v in by_size.items() if len(v) > 1 and k > 1024}
```

### Phase 3: Hash Verification (slow but definitive)

For each size-match group, do a quick hash (first 64KB) first to filter false positives instantly, then full hash only if the quick check passes:

```python
import hashlib

for sz, file_list in candidates.items():
    sig_map = defaultdict(list)
    for f, _ in file_list:
        with open(f, 'rb') as fh:
            quick = hashlib.md5(fh.read(65536), usedforsecurity=False).hexdigest()
        sig = f'{sz}:{quick}'
        sig_map[sig].append(f)

    # Any sig with 2+ files = content-identical (quick check is definitive
    # for same-size files: same first 64KB almost guarantees full match)
    for sig, fs in sig_map.items():
        if len(fs) > 1:
            # Optional: full MD5 to be certain
            with open(fs[0], 'rb') as fh:
                full = hashlib.md5(fh.read(), usedforsecurity=False).hexdigest()
            for f2 in fs[1:]:
                with open(f2, 'rb') as fh:
                    f2hash = hashlib.md5(fh.read(), usedforsecurity=False).hexdigest()
                if f2hash == full:
                    print(f"DUPE: {f} == {f2}")
```

### Phase 4: Normalized Name Match (bonus)

Some files from different downloaders differ by quality suffix (`_720p`, `_1080p`, `_source`, `_flat`), site prefix (`EPORNER.COM -`), or minor variations. Normalize and group:

```python
normalized = defaultdict(list)
for f in files:
    n = f.split('[')[0].strip()          # strip [viewkey]
    n = re.sub(r'( - \d+p|_\d+p|_source|_flat)', '', n)  # strip quality tags
    n = re.sub(r'^[A-Z.]+ - ', '', n)    # strip site prefix (EPORNER.COM - )
    n = n.strip().lower()
    normalized[n].append(f)

for base, fs in sorted(normalized.items()):
    if len(fs) > 1:
        print(f"NEAR-MATCH: {base[:60]}")
        for f in fs:
            sz = os.path.getsize(f) // 1024 // 1024
            print(f"  {sz}MB  {f[:70]}")
```

Phase 4 yields false positives (different scenes with similar titles). Verify with Phase 3 hash before deleting.

## What to Delete

**Salvage rule:** When two files match by full MD5, keep the one with the more descriptive filename (cleaner title, full viewkey, correct performer name). Delete the other + any orphaned `.info.json` for the deleted file.

**Temp files:** Also clean up:
- `*.temp.mp4` — leftover partial downloads from yt-dlp/aria2c (check that the real file exists first)
- `*.part` — aria2c partial files
- Orphaned `.info.json` with no matching MP4

## Real-World Results

On a collection of 855 MP4s (927 files with info.json):
- **Viewkey duplicates:** 0 (different upload sites = different viewkeys)
- **Exact size duplicates:** 1 pair (2 x 259MB files, different filenames, full MD5 matched)
- **Normalized name near-matches:** ~30 groups, but only 1 was a true duplicate
- **Temp files cleaned:** 1 (593MB `.temp.mp4` partial download)
- **Total waste:** ~852MB from 2 files out of 855

In practice, the offline collection is very clean — the viewkey-based dedup during download catches most duplicates before they land on disk.
