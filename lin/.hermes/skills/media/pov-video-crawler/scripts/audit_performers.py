#!/usr/bin/env python3
"""Performer coverage audit for /mnt/storage/videos/.

Counts files per performer with leetspeak normalization, prints ranked list,
and flags anyone under 10. Use to drive the next crawl toward starved performers.

Usage:
    python3 audit_performers.py            # use default performer list
    python3 audit_performers.py /path/     # different video dir
    python3 audit_performers.py --json     # machine-readable output
"""
import json
import os
import sys
from collections import Counter

LEET_MAP = {'4': 'a', '3': 'e', '1': 'i', '0': 'o', '5': 's', '7': 't', '8': 'b'}

def unleet(s: str) -> str:
    for k, v in LEET_MAP.items():
        s = s.replace(k, v)
    return s

# Top-tier + Asian performers. First key = canonical name; values = name variants
# to match in filenames (case-insensitive, leet-normalized).
PERFORMERS = {
    "Lana Rhoades": ["lana rhoades", "lana"],
    "Angela White": ["angela white", "angela"],
    "Mia Malkova": ["mia malkova", "mia m"],
    "Lena Paul": ["lena paul", "lena"],
    "Violet Myers": ["violet myers", "violet"],
    "Kendra Sunderland": ["kendra sunderland", "kendra"],
    "Blake Blossom": ["blake blossom", "blake"],
    "Alanna Pow": ["alanna pow", "alanna"],
    "Lauren Phillips": ["lauren phillips", "lauren"],
    "Mia Melano": ["mia melano"],
    "Nicole Aniston": ["nicole aniston", "nicole"],
    "Karma Rx": ["karma rx", "karma"],
    "Payton Preslee": ["payton preslee", "payton"],
    "Blondie Fesser": ["blondie fesser", "blondie"],
    "Sophie Dee": ["sophie dee", "sophie"],
    "Sky Bri": ["sky bri", "sky"],
    "Natasha Nice": ["natasha nice", "natasha"],
    "Vivian Taylor": ["vivian taylor", "vivian"],
    "Tru Kait": ["tru kait", "tru"],
    "Riley Reid": ["riley reid", "riley"],
    "Wettmelons": ["wettmelons"],
    # Asian tops
    "Lulu Chu": ["lulu chu", "lulu"],
    "Asa Akira": ["asa akira", "asa"],
    "Kimmy Granger": ["kimmy granger", "kimmy"],
    "Jade Kush": ["jade kush", "jade"],
    "Vina Sky": ["vina sky", "vina"],
    "Eva Lovia": ["eva lovia", "eva"],
    "Lily Lane": ["lily lane", "lily"],
    # Extended
    "Lexi Luna": ["lexi luna", "lexi"],
    "Kali Roses": ["kali roses", "kali"],
    "Ava Addams": ["ava addams", "ava"],
    "Alexis Fawx": ["alexis fawx", "alexis"],
    "Emily Willis": ["emily willis", "emily"],
    "Rissa May": ["rissa may", "rissa"],
    "Aleksa Mink": ["aleksa mink", "aleksa"],
    "Faith Lianne": ["faith lianne", "faith"],
    "Camila Castillo": ["camila castillo", "camila"],
}

UNDER_10_THRESHOLD = 10

def main():
    video_dir = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else "/mnt/storage/videos"
    as_json = '--json' in sys.argv

    files = [f for f in os.listdir(video_dir) if f.lower().endswith('.mp4')]
    counts = Counter()
    matched_count = 0

    for f in files:
        f_norm = unleet(f.lower())
        for primary, aliases in PERFORMERS.items():
            if any(unleet(a.lower()) in f_norm for a in aliases):
                counts[primary] += 1
                matched_count += 1
                break

    if as_json:
        result = {
            "total_files": len(files),
            "matched_files": matched_count,
            "unmatched_files": len(files) - matched_count,
            "under_10": [p for p, c in counts.items() if c < UNDER_10_THRESHOLD],
            "zero": [p for p in PERFORMERS if counts.get(p, 0) == 0],
            "counts": dict(counts),
        }
        print(json.dumps(result, indent=2))
        return

    # Human-readable output
    print(f"=== {video_dir} ===")
    print(f"Total MP4s: {len(files)} | Matched: {matched_count} | Unmatched: {len(files) - matched_count}\n")

    print("=== Ranked counts ===")
    for p, c in counts.most_common():
        bar = "█" * min(c, 30)
        flag = f"  ⚠ <{UNDER_10_THRESHOLD}" if c < UNDER_10_THRESHOLD else ""
        print(f"  {c:3d}  {p:<20s} {bar}{flag}")

    under = [(p, c) for p, c in counts.items() if c < UNDER_10_THRESHOLD]
    if under:
        print(f"\n=== UNDER {UNDER_10_THRESHOLD} ({len(under)} performers) ===")
        for p, c in sorted(under, key=lambda x: x[1]):
            print(f"  {c:3d}  {p}")

    zeros = [p for p in PERFORMERS if counts.get(p, 0) == 0]
    if zeros:
        print(f"\n=== ZERO VIDEOS ({len(zeros)} performers) ===")
        for p in zeros:
            print(f"   0  {p}")

if __name__ == "__main__":
    main()
