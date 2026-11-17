#!/usr/bin/env python3
"""
Parallel URL verification script.
Usage: python3 verify_urls.py <urls_file> [output_file] [parallel_workers]

Reads URLs from file, fetches page titles with yt-dlp --get-title,
checks for BBC/black/interracial content, POV, and big tits keywords.

Output: url|title|POV_flag|BIGTITS_flag|BBC_FLAG
"""

import sys
import subprocess
import re
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Keywords that trigger BBC flag (lowercase)
BBC_KEYWORDS = [
    'bbc', 'interracial', 'black.?cock', 'black.?dick', 'big.?black',
    'black.?bf', 'black.?guy', 'black.?man', 'black.?bull', 'blacked',
    'blackedraw', 'bwc', 'ebony', 'monster.?dick', 'chocolate.?pussy'
]
BBC_PATTERNS = [re.compile(k, re.IGNORECASE) for k in BBC_KEYWORDS]

POV_KEYWORDS = ['pov']
POV_PATTERNS = [re.compile(k, re.IGNORECASE) for k in POV_KEYWORDS]

TITS_KEYWORDS = ['big.?tit', 'busty', 'huge.?tit', 'massive.?tit', 'boobs', 'breast', 'juggs']
TITS_PATTERNS = [re.compile(k, re.IGNORECASE) for k in TITS_KEYWORDS]


def verify_url(url):
    """Get title and check keywords for a single URL."""
    try:
        result = subprocess.run(
            ['yt-dlp', '--impersonate', 'chrome', '--get-title', url],
            capture_output=True, text=True, timeout=30
        )
        title = result.stdout.strip().split('\n')[0] if result.stdout.strip() else '(no title)'
    except subprocess.TimeoutExpired:
        title = '(timeout)'
    except Exception as e:
        title = f'(error: {e})'

    t = title.lower()

    # BBC check
    flagged = any(p.search(t) for p in BBC_PATTERNS)

    # POV check
    has_pov = any(p.search(t) for p in POV_PATTERNS)

    # Big tits check
    has_tits = any(p.search(t) for p in TITS_PATTERNS)

    flags = []
    if flagged:
        flags.append('FLAG_BBC')
    if has_pov:
        flags.append('POV')
    if has_tits:
        flags.append('BIGTITS')

    flag_str = '|'.join(flags) if flags else 'CLEAN'
    return f"{url}|{title}|{flag_str}"


def main():
    urls_file = sys.argv[1] if len(sys.argv) > 1 else '/tmp/urls_to_verify.txt'
    output_file = sys.argv[2] if len(sys.argv) > 2 else '/tmp/verify_results.txt'
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 8

    urls = Path(urls_file).read_text().strip().split('\n')
    urls = [u.strip() for u in urls if u.strip() and not u.startswith('#')]
    total = len(urls)

    print(f"Verifying {total} URLs with {workers} parallel workers...")

    results = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(verify_url, url): i for i, url in enumerate(urls)}
        for i, future in enumerate(as_completed(futures)):
            result = future.result()
            results.append(result)
            if (i + 1) % 50 == 0:
                print(f"  Progress: {i+1}/{total}")

    Path(output_file).write_text('\n'.join(results) + '\n')

    # Summary
    flagged = [r for r in results if 'FLAG_BBC' in r]
    pov = [r for r in results if 'POV' in r.split('|')[-1]]
    tits = [r for r in results if 'BIGTITS' in r.split('|')[-1]]
    errors = [r for r in results if '(no title)' in r or '(timeout)' in r]

    print(f"\n=== RESULTS ===")
    print(f"Total:  {total}")
    print(f"BBC:    {len(flagged)}")
    print(f"POV:    {len(pov)}")
    print(f"BigTits:{len(tits)}")
    print(f"Errors: {len(errors)}")

    if flagged:
        print(f"\n--- Flagged URLs ---")
        for r in flagged:
            parts = r.split('|')
            print(f"  {parts[0][:70]} | {parts[1][:50]} | {parts[2]}")


if __name__ == '__main__':
    main()
