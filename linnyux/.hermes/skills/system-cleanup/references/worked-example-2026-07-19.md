# Worked Example — 2026-07-19: 97% → 90% (15G freed)

**Trigger**: 219G root drive at 97% (210G used, 6.7G free). I/O-bound — `du` commands timed out on large trees.

## Approach

Started tiered — diagnosed top consumers, then executed aggressively without asking (user said "aggressively clear").

## Space Hogs Found

| Directory | Size | Action |
|-----------|------|--------|
| `~/.local/lib/python3.12/site-packages/nvidia/` | 2.6G | NUKED — CUDA on AMD RX 580 |
| `~/.local/lib/python3.12/site-packages/flashinfer_cubin/` | 1.9G | NUKED — CUDA-only |
| `~/.local/lib/python3.12/site-packages/triton/` | 641M | NUKED — CUDA-only |
| `~/.local/lib/python3.12/site-packages/tokenspeed_triton/` | 275M | NUKED — CUDA-only |
| `~/.local/lib/python3.12/site-packages/paddle/` | 719M | NUKED — PaddlePaddle (not used) |
| `~/.local/lib/python3.12/site-packages/PyNvVideoCodec/` | 66M | NUKED — NVIDIA codec |
| `~/Documents/EIDOLON/target/` | 3.9G | NUKED — Rust build artifacts |
| `~/Documents/papatoetoe-funeral-cottage/node_modules/` | 1.4G | NUKED — reinstallable |
| Old kernels (6.8.0-124) | ~1G | apt autoremove --purge |
| `~/.local/share/claude/versions/2.1.{207,208,209}` | 744M | NUKED — kept 2.1.210 only |
| `~/.local/share/devin/cli/_versions/2026.{7.23,8.18}` | 255M | NUKED — kept current |
| `~/.cargo/registry/cache/`, `~/.cargo/git/` | 300M | Cleaned |
| pnpm store | 163M | Pruned via `pnpm store prune` |
| Snap old revisions (8 disabled) | ~few hundred MB | Removed |

**Total freed: 15G. 210G → 195G, 97% → 90%.**

## Key Technique: GPU Package Mismatch Detection

The biggest win (6.2G) came from identifying CUDA-only packages on an AMD RX 580 system:

```bash
# Check what GPU the system actually has
lspci | grep -i vga
# → AMD Radeon RX 580

# Find GPU-specific python packages
du -sh ~/.local/lib/python*/site-packages/{nvidia,flashinfer*,triton,tokenspeed*,paddle,PyNvVideoCodec,torch*}/ 2>/dev/null | sort -rh
# → 6.2G of completely useless nvidia/CUDA packages

# Safe to nuke them all
rm -rf ~/.local/lib/python3.12/site-packages/{nvidia,nvidia_nvjitlink*,flashinfer*,triton,tokenspeed_triton,paddle,PyNvVideoCodec}
```

## Not Touched (still on root)

- Snap: 16G (active: android-studio, chromium, thunderbird, node, cups, mesa)
- Flatpak: 9G (Easy Effects, Pieces, Telegram + runtimes)
- pnpm store: 5.2G at `~/.local/share/pnpm/store/`
- uv tools/python: 878M

## Pitfalls Hit

- `du -sh /home/kubuntux/*` timed out on 210G filesystem — switched to targeted subdirectory scans
- `snap list` returned empty from stdout but worked in explicit `set -x` script — likely snap output buffering
- `pip cache purge` showed "WARNING: No matching packages" — pip cache was already empty, but site-packages had 6.2G of CUDA bloat (persistent packages, not cached downloads)
