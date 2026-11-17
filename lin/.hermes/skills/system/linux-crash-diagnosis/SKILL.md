---
name: linux-crash-diagnosis
description: Diagnose Linux system crashes, freezes, and lockups from kernel logs, GPU errors, memory pressure, disk health, and process/container resource conflicts. Use when user says "computer is crashing", "system keeps freezing", "screen goes black and locks up", "computer hard locks", or "why did my system crash?".
---

# Linux Crash Diagnosis

Systematic methodology for diagnosing Linux system crashes, freezes, and lockups. Covers kernel panics, OOM kills, GPU driver crashes, disk hangs, and process/container resource exhaustion.

## Trigger conditions

Use this skill when the user reports:
- "Computer keeps crashing / freezing / locking up"
- "Screen goes black / display driver crashes"
- "System becomes unresponsive then recovers or reboots"
- "Everything hangs and I have to hard reset"
- "My desktop environment keeps dying"
- Kernel panics or kernel oops messages visible

## Diagnostic pipeline

Run these checks in order. Each narrows the root cause.

### 1) Kernel logs (dmesg) — primary crash evidence

```bash
sudo dmesg -T | tail -80
```

Look for (in priority order):

| Signal | Means |
|--------|-------|
| `amdgpu: ring comp_* timeout` | GPU compute ring timeout → driver reset imminent |
| `amdgpu: GPU fault detected` | VRAM page fault — GPU crashing |
| `amdgpu: [drm] *ERROR* Failed to get VBLANK` | Display pipeline dead — GPU reset in progress |
| `amdgpu: [drm] *ERROR* Failed to initialize parser -125` | Full GPU reset failed — system frozen |
| `ring gfx timeout, but soft recovered` | Temporary GPU recovery that won't last |
| `llama-server:* blocked for more than 122 seconds` | Hung task — process stuck in D state from resource starvation |
| `Out of memory: Killed process *` | OOM killer triggered — RAM exhaustion |
| `INFO: task * blocked for more than 120 seconds.` | Hung task warning — system is thrashing |
| `EXT4-fs error` / `I/O error` / `Buffer I/O error` | Disk failure causing system freezes |
| `watchdog: BUG: soft lockup` | CPU soft lockup — kernel can't schedule |

Cross-reference timestamps between GPU errors and display manager/service restarts (e.g., sddm-helper, gdm, xdg-desktop-portal). The GPU crash typically precedes the display death by 1-30 seconds.

### 2) Journalctl — user-space crash context

```bash
# Kernel messages
journalctl -k --no-pager | tail -80

# Critical-level errors in current boot
journalctl -p 3 -b --no-pager | tail -60

# Errors around a specific crash time (replace with actual timestamp)
journalctl --since "16:50" --until "17:00" -p 3 --no-pager
```

Look for: OOM kills, GPU errors, display manager failures, service crashes near crash timestamps.

### 3) Memory pressure check

```bash
free -h
cat /proc/meminfo | head -5
```

Key thresholds:
- **<1GB available** on a system with >8GB total → severe memory pressure
- **Swap usage >30% of total** → system is paging heavily
- **Available memory consistently <10%** → expect OOM or task hangs

If memory pressure is present, find the culprit:

```bash
# Top memory consumers
ps aux --sort=-%mem | head -10

# Check for multiple instances of the same process
ps aux | grep -E 'llama-server|inference' | grep -v grep
```

### 4) GPU diagnostics

```bash
# Identify GPU hardware
lspci -nn | grep -iE 'vga|3d|display|amdgpu|nvidia'

# Check VRAM usage (AMD)
cat /sys/class/drm/card0/device/mem_info_vram_used
cat /sys/class/drm/card0/device/mem_info_vram_total
```

Common GPU-related crash patterns:
- **Multiple processes sharing VRAM without coordination** — each allocates its own model copy
- **`--ngl 999` with large context** — pushes VRAM past capacity
- **Chrome/Electron GPU acceleration** + LLM inference = VRAM competition
- **GPU ring timeout** → driver reset → display server death

VRAM budget calculation for LLM inference:
- Model weights at 4-bit quant: ~2.5GB for 4B model, ~4.5GB for 7B model, ~6.5GB for 8B model
- KV cache: ~0.5GB at 2048 context, ~1GB at 4096, ~2-3GB at 8192
- `-c 8192` on an 8GB card with a 4B model = ~5-6GB total — tight but fits alone
- Two concurrent GPU processes double the weight allocation → guaranteed OOM

### 5) Docker container resource conflicts

```bash
# List all running containers
docker ps --format '{{.Names}} {{.Image}} {{.Status}}'

# Check if containers share GPU devices
docker inspect <container> --format '{{json .HostConfig.Devices}}'

# Check port conflicts
docker ps --format '{{.Names}} {{.Ports}}'
```

Common Docker crash pattern: **orphan/duplicate containers** running the same model on the same GPU. Check the compose file for the canonical service definition:

```bash
# Find the canonical compose file
docker inspect <container> --format '{{json .Config.Labels}}' | grep project.config_files
```

If a container exists outside compose (manual `docker run`), it's a duplicate that should be removed.

### 6) Disk health

```bash
sudo smartctl -a /dev/sdX | grep -iE 'pending|reallocated|current|uncorrect|raw_read|failed|health'
```

- **Current_Pending_Sector > 0** → disk is struggling to read sectors → can cause processes to hang in D state
- **Reallocated_Sector_Ct > 0** → disk has moved bad sectors, may continue failing
- SMART overall-health typically still says PASSED even with pending sectors

A disk with pending sectors won't cause GPU crashes, but it can cause concurrent system freezes that compound the problem.

### 7) Timestamp cross-referencing

Map the sequence of events:

```
16:36 — GPU VM fault (Chrome on GPU)
16:36 — ring gfx timeout, soft recovered
16:39 — llama-server blocked for 122+ seconds (memory pressure)
16:53 — ring comp_1.1.1 timeout (llama-server on GPU)
16:53 — Failed to get VBLANK (display pipeline dead)
16:53 — Failed to initialize parser -125 (GPU reset failed)
16:53 — sddm-helper / xdg-desktop-portal-gtk fails (display server crash)
```

**Crash cascade:**
1. VRAM exhausted by multiple GPU consumers
2. GPU ring times out → driver tries recovery
3. Recovery fails → display pipeline goes down
4. Display server loses GPU access → desktop environment crashes
5. User perceives "computer crash" / "screen freeze"

## Finding the root cause

Once you have evidence, identify which type of crash:

| Evidence pattern | Root cause |
|---|---|
| GPU errors + display server death | VRAM exhaustion from multiple GPU consumers |
| OOM kills + swap full + hung tasks | Memory leak or too many heavy processes |
| Pending sectors + D-state processes | Disk failure |
| No errors in any log, sudden reboot | Hardware (PSU, overheating) or kernel panic not logged |
| GPU errors + Chrome was running | GPU memory competition with browser |

## Fixes

### Duplicate/overlapping processes

```bash
# Stop and remove extra container
docker stop <duplicate_container>
docker rm <duplicate_container>

# Verify only canonical instances remain
docker ps --format '{{.Names}} {{.Image}} {{.Status}}'
```

### VRAM overload

- Reduce context size (`-c 4096` or `-c 2048`)
- Kill Chrome/Electron GPU acceleration when inferring
- Ensure only one llama-server instance uses `--device Vulkan0`
- Enable `--flash-attn on` to reduce KV cache overhead

### Memory pressure

- Kill unnecessary processes
- Reduce model count or use smaller models
- Check for `--no-mmap` on llama-server (holds full model in RAM + VRAM)

### VM overprovisioning (QEMU/KVM)

A QEMU/KVM Windows VM can silently consume more than half your host RAM. Combined with Chrome/Electron and desktop services, this causes swap thrashing that makes the entire machine feel frozen or unusably slow.

**Diagnostic signals:**
- `free -h` shows <20% available RAM and >30% swap usage
- `ps aux --sort=-%mem | head -5` shows `qemu-system-x86_64` at the top with 30%+ of host RAM
- `kswapd0` is consistently in the top CPU consumers
- Load average is high (5+ on a 4C/8T system) despite CPU idling — disk I/O from swap is the bottleneck

**Quick check:**
```bash
ps aux | grep qemu | grep -v grep | awk '{print "QEMU VM RAM: " $6/1024 " MB (" $4 "% of host)"}'
virsh dominfo <vm> | grep -E 'Max memory|Used memory'
free -h | grep Swap
```

**Fix — shrink the VM without reinstalling:**
```bash
virsh destroy <vm>
virsh setvcpus <vm> 2 --maximum --config
virsh setvcpus <vm> 2 --config
virsh setmaxmem <vm> 4194304 --config   # 4GB
virsh setmem <vm> 4194304 --config
virsh start <vm>
```

Cap VM at **2-4 vCPUs and 25-40% of host RAM** for RE tool workloads, not the 60%+ a VM installer defaults to. See `windows-re-vm-setup` skill for full sizing guidance.

## Pitfalls

- **docker ps may not show ports** if containers share host network — check with `docker inspect` for network mode
- **D state processes can't be killed** with SIGTERM — use `docker stop` / `docker rm` for container-bound processes, or SIGKILL for orphaned ones
- **SMART says PASSED but disk has pending sectors** — PASSED only means attribute thresholds haven't been exceeded, not that the disk is healthy
- **Multiple processes on same port** — Docker containers on host network can't share ports; one will fail to start silently (check `docker logs <container>`)
- **GPU appears healthy in lspci** even during a crash — the GPU hardware itself is fine, it's the driver/userspace that crashed
- **System uptime may show 6+ days** while crashes are recent — individual GPU resets don't reboot the machine; the display server restarts but `uptime` keeps counting
