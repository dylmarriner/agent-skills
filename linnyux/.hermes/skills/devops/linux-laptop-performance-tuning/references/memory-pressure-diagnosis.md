# Memory Pressure Diagnosis & Recovery

When a system feels slow and the user says "I have nothing open," the culprit is often background services, Docker containers, or filesystem cache — not user-facing applications.

## Step 1: Check the real memory picture

```bash
free -h
```

The `available` column is the real number — memory the kernel can free immediately. `used` includes filesystem cache (`buff/cache`). Don't panic at high `used` if `available` is healthy.

Check swap pressure:
```bash
swapon --show
# If swap usage is high (>50%), the system has been under memory pressure
```

## Step 2: Identify what's eating RAM

**Processes >100MB:**
```bash
ps aux --sort=-%mem | awk '$4 > 0.5' | awk '{printf "%5.1f%%  %-6s  %s\n", $4, $1, $11}'
```

**Docker containers (often the biggest hidden hogs):**
```bash
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

Common resource hogs:
- **Elasticsearch**: ~2GB RAM. Kill if not actively searching.
- **Frigate**: ~500MB + GPU. Camera surveillance AI.
- **Honcho/RAG stacks**: 4+ containers, ~500MB total.
- **Minio**: S3 storage. Kill if not actively storing.

## Step 3: Drop filesystem cache

```bash
sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches
```

This frees `buff/cache` without affecting running processes. The kernel will re-cache as needed. Safe to run anytime.

## Step 4: Check swap composition

Linux uses zram for compressed swap (fast, in-RAM) plus disk swapfile. High zram usage means the system has been swapping — not necessarily a problem if the pages are cold.

```bash
cat /proc/meminfo | grep -E "^(MemTotal|MemFree|MemAvailable|Buffers|Cached|SwapCached|Active|Inactive)"
```

If `Active(anon)` is high and `Available` is low, the system genuinely needs more RAM or fewer processes.

## Step 5: Kill the biggest offenders

```bash
# Stop all Docker containers
docker stop $(docker ps -q)

# Or target specific ones
docker stop docker-es01-1 frigate honcho_api_1

# Free cache after stopping
sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches
```

Expect 2-4GB recovered from killing Elasticsearch + Frigate + Honcho alone.

## What NOT to do

- Don't `kill -9` system daemons — they auto-restart.
- Don't disable swap entirely — the kernel needs it for memory overcommit protection.
- Don't set `vm.swappiness=0` — this can cause OOM kills under pressure. `vm.swappiness=10` is the safe aggressive minimum.
