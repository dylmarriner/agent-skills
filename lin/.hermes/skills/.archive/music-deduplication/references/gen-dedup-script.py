#!/usr/bin/env python3
"""Generate a deletion script for binary-identical music files.
Keeps the copy with year-in-name when available.

Usage:
    python3 gen-dedup-script.py > dedup.sh && chmod +x dedup.sh
    ./dedup.sh   # dry-run first by inspecting, then run
"""

import os, hashlib, re, shlex
from collections import defaultdict

MUSIC_DIR = "/media/lin/2FEB-4995"  # CHANGE THIS to your target

# Index all music files
files = []
for f in os.listdir(MUSIC_DIR):
    fp = os.path.join(MUSIC_DIR, f)
    if not os.path.isfile(fp):
        continue
    ext = os.path.splitext(f)[1].lower()
    if ext not in ('.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg', '.wma', '.opus', '.aiff'):
        continue
    files.append((f, fp, os.path.getsize(fp)))

# Group by size, hash same-size groups
size_groups = defaultdict(list)
for name, fp, size in files:
    size_groups[size].append((name, fp))

hash_groups = defaultdict(set)
for size, group in size_groups.items():
    if len(group) < 2:
        continue
    for name, fp in group:
        h = hashlib.md5(open(fp, 'rb').read()).hexdigest()
        hash_groups[h].add(name)


def score(name):
    """Higher score = better to keep. Prefers files with year in name."""
    s = 0
    if re.search(r'\(\d{4}\)', name):
        s += 10
    s += len(name) / 100.0  # longer names usually more descriptive
    return s


lines = []
total_freed = 0
total_pairs = 0

lines.append("#!/bin/bash")
lines.append("set -e")
lines.append('echo "=== Removing duplicate files ==="')

for h, names in hash_groups.items():
    if len(names) < 2:
        continue
    sorted_names = sorted(names, key=score, reverse=True)
    kept = sorted_names[0]
    for n in sorted_names[1:]:
        sz = os.path.getsize(os.path.join(MUSIC_DIR, n))
        total_freed += sz
        total_pairs += 1
        safe_path = shlex.quote(os.path.join(MUSIC_DIR, n))
        safe_kept = shlex.quote(os.path.join(MUSIC_DIR, kept))
        lines.append(f"# keep: {kept}")
        lines.append(f"rm {safe_path}")

lines.append(f'echo "=== Removed {total_pairs} duplicates, freed ~{total_freed / 1024 / 1024:.0f} MB ==="')

print("\n".join(lines))
