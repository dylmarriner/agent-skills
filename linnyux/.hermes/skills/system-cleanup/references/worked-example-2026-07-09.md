# Worked Example — 2026-07-09

**Situation:** 219G root disk at 88% (27G free). User asked "clear up harddrive space."

**Challenge:** `du` commands kept timing out due to slow filesystem I/O (possibly many small files or disk contention).

**Approach taken:**
1. Used `find -size +500M` to locate large files directly (bypassing du directory recursion)
2. Used `ncdu -x / -o-` JSON export for machine parsing (faster than du)
3. Targeted known space-hog locations individually
4. Used `execute_code` (Python wrapper) for multi-step operations with shorter timeouts

**Items recovered:**

| Target | Size | Method |
|--------|------|--------|
| `~/.cache/uv` | 6.1G | `rm -rf ~/.cache/uv/*` |
| `~/.config/google-chrome/OptGuideOnDeviceModel/` | 4.0G | `rm -rf` |
| `~/.cache/google-chrome` | 1.2G | `rm -rf` |
| `~/.cache/pip` | 300M | `rm -rf` |
| Rust build artifacts (`~/vibe-kanban/target` + `~/openhuman/target`) | 8.1G | `rm -rf` |
| Docker build cache + unused images | 1.4G | `docker builder prune -af && docker image prune -af` |
| Old Claude versions (2.1.193, 2.1.195) | 485M | Kept latest only |
| **Total freed** | **~21.5G** | |

**Result:** 27G free → 46G free (79%).

**Notable:**
- Journalctl `--vacuum-size=200M` didn't free space — active journals too large. `--vacuum-time=3d` didn't help either. Likely needs reboot or service restart.
- `df -h` delta (19G) was less than itemised sum (~21.5G) — filesystem metadata/overhead.
- Removing Rust `target/` dirs was the single biggest gain at 8.1G.
