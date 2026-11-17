#!/usr/bin/env python3
"""
Generate a cryptographically secure Monero wallet seed phrase using the
official Monero wordlist (1626 words from the Monero source code).

Usage:
    python3 generate-monero-seed.py

Output: 25-word Monero seed phrase + instructions

The wordlist is fetched live from the Monero GitHub repository. **WARNING:** The GitHub\nwordlist may differ from the wordlist embedded in the official Monero CLI release binary.\nAlways verify a generated seed by attempting restoration with\n`monero-wallet-cli --restore-deterministic-wallet` before using it.\nNo external dependencies beyond Python stdlib + curl.
"""

import subprocess
import re
import secrets
import hashlib
import sys

WORDLIST_URL = (
    "https://raw.githubusercontent.com/monero-project/monero/"
    "master/src/mnemonics/english.h"
)


def fetch_wordlist() -> list[str]:
    """Fetch the official Monero English wordlist from GitHub."""
    try:
        r = subprocess.run(
            ["curl", "-sL", WORDLIST_URL],
            capture_output=True, text=True, timeout=15,
        )
        r.check_returncode()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"Error fetching wordlist: {e}", file=sys.stderr)
        sys.exit(1)

    matches = re.findall(r'"([a-z]+)"', r.stdout)
    if len(matches) != 1626:
        print(f"ERROR: Expected 1626 words, got {len(matches)}", file=sys.stderr)
        sys.exit(1)
    return matches


def generate_seed(wordlist: list[str]) -> str:
    """Generate a 25-word Monero seed phrase."""
    word_count = len(wordlist)
    entropy = secrets.randbits(256)

    words = []
    remaining = entropy
    for _ in range(24):
        idx = remaining % word_count
        words.append(wordlist[idx])
        remaining //= word_count

    # Checksum word
    entropy_bytes = entropy.to_bytes(32, 'big')
    h = hashlib.sha256(entropy_bytes).digest()
    checksum_idx = h[0] % word_count
    words.append(wordlist[checksum_idx])

    return ' '.join(words)


def verify_seed(seed: str, wordlist: list[str]) -> bool:
    """Verify all words are in the official wordlist."""
    for i, word in enumerate(seed.split(), 1):
        if word not in wordlist:
            print(f"ERROR: Word {i} ('{word}') not in official wordlist!")
            return False
    return True


def main():
    print("Fetching official Monero wordlist...", file=sys.stderr)
    wordlist = fetch_wordlist()
    print(f"Verified: {len(wordlist)} words loaded.", file=sys.stderr)

    seed = generate_seed(wordlist)
    if not verify_seed(seed, wordlist):
        sys.exit(1)

    print()
    print("=" * 60)
    print("  MONERO WALLET SEED PHRASE")
    print("=" * 60)
    print()
    print(f"  {seed}")
    print()
    print("=" * 60)
    print()
    print("  WRITE THIS DOWN ON PAPER.")
    print("  This is the ONLY way to recover your funds.")
    print("  Never enter it into any website or digital device.")
    print()
    print("  Restore in Feather wallet:")
    print("  ./feather-wallet.AppImage --use-local-tor")
    print("  → 'Restore wallet from seed/keys'")
    print()


if __name__ == "__main__":
    main()
