# Monero Wordlist Mismatch: GitHub Source vs Release Binary

## Discovery

During Monero wallet generation (June 2026), a critical discrepancy was found between the wordlist in the Monero GitHub source code and the wordlist embedded in the official release binary (v0.18.5.0 "Fluorine Fermi").

## The Problem

Words `either`, `tail`, and `locker` exist in the GitHub source's `english.h` but are **NOT** in the release binary's embedded wordlist. A seed generated with these words will fail verification with:

```
Error: Electrum-style word list failed verification
```

## Root Cause

The English wordlist at `src/mnemonics/english.h` in the Monero GitHub repository evolves over time. Words get added, removed, or changed between releases. The release binary (v0.18.5.0) contains a frozen snapshot of the wordlist that may differ from the current master branch.

## Fix

**Do NOT trust the GitHub wordlist for wallet generation.** Always use the release binary's embedded wordlist.

### Verification Method

Check each seed word against the actual binary:

```bash
for word in word1 word2 word3 ...; do
    found=$(strings /path/to/monero-wallet-cli | grep -c "^${word}$")
    echo "$word: $found"
done
```

### Reliable Wallet Generation

The only reliable method: use `monero-wallet-cli` (from the official release tarball) with `expect` to create the wallet non-interactively. See the main SKILL.md for the full procedure.

## Affected Versions

| Version | Wordlist Source | Words Found |
|---------|----------------|-------------|
| GitHub master (May 2026) | english.h | 1626 words incl. "either", "tail", "locker" |
| v0.18.5.0 release binary | embedded | 1626 words excl. those three |
| Any future release | embedded | Unknown — verify against the binary |

## Lesson

Wordlists extracted from GitHub source code are UNRELIABLE for seed generation. The release binary is the source of truth. Always verify generated seeds by attempting restoration with `monero-wallet-cli --restore-deterministic-wallet` before presenting them to the user.
