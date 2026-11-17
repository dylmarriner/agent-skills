# V8 Code Cache Cleanup (`.d8b*` files)

## What They Are

Node.js / V8 creates compiled code cache files at runtime, stored as `.d8b*` ELF shared objects in `/tmp`. These are bytecode-to-native-code compilation artifacts that speed up subsequent runs of the same script — but they **never self-clean** and accumulate indefinitely.

## Size Profile

| Metric | Typical | Worst Observed |
|--------|---------|----------------|
| Size per file | ~8 MB | 8,191,776 bytes |
| Total files | 500-3,000 | 2,894 |
| Total space | 4-23 GB | 22.1 GB |

## Why They're Hard to Spot

These files **start with a dot** (`.d8b*`), so:

```bash
# This MISSES them:
du -sh /tmp/*

# This catches them:
du -sh /tmp/.[!.]*
# Or better, use find:
sudo find /tmp -name '.d8b*' -type f -exec rm -f {} +
```

## Safety

- No process holds these files open (confirmed via `lsof`)
- They are regenerated on next Node.js execution
- They are owned by the user, not root
- Can be deleted at any time with no side effects

## Cleanup Command

```bash
# Quick: delete all V8 caches
sudo rm -rf /tmp/.d8b* 2>/dev/null

# Thorough: also check for any other large hidden temp files
# (after regular /tmp/* dirs are cleared)
sudo find /tmp -maxdepth 1 -name '.*' -type f -size +1M -delete 2>/dev/null
```

## Detection

After cleaning visible `/tmp` dirs, check for remaining hidden space hogs:

```bash
sudo find /tmp -type f -printf '%s\n' 2>/dev/null | \
  awk '{sum+=$1; count++} END {printf "Remaining files: %d, Size: %.1f GB\n", count, sum/1024/1024/1024}'
```
