---
name: linux-performance-tuning
description: Push a Linux desktop past stock specs — I/O schedulers, GPU clock forcing, kernel sysctl tuning, GRUB boot params, and persistent config. Use when user asks to 'speed up', 'optimize', 'maximize performance', 'overclock', or 'tune' a Linux desktop/workstation.
---

# Linux Performance Tuning

Tune a Linux system for maximum performance over stock specs, ignoring cooling/power/longevity concerns unless the user explicitly constrains them. Covers I/O, GPU, kernel VM, scheduler, and boot parameters.

## When to Use

- User says "maximize performance", "speed up this device", "exceed manufacturer specs"
- User reports system feels laggy despite good hardware
- User wants GPU pushed past auto clocks (RX 580, Radeon, NVIDIA)
- User wants aggressive disk I/O tuning (HDD especially)
- User asks about kernel boot params for low-latency/high-throughput

## Process

### 0. Remote diagnosis — when you can't SSH in

If direct shell access is blocked (e.g. Tailscale ACL, firewall, SSH disabled) but the target exposes **Prometheus** and/or **Node Exporter** on an open port (typically 9100), you can still extract full system diagnostics via HTTP metrics:

```bash
# Quick health from metrics endpoint
curl -s http://<target>:9100/metrics | grep -E "^node_load1|^node_load5|^node_memory_MemAvailable|^node_filesystem_avail"
```

This technique works for any Linux machine running Node Exporter, even if SSH, web UI, and all other services are inaccessible. See `references/remote-diagnosis-via-metrics.md` for the complete playbook: metric extraction commands, latency calculation formulas, process-level CPU/memory breakdown, and a full worked example.

**Preconditions for this approach:**
- Target runs Node Exporter on port 9100 (or a known port)
- The metrics port is not blocked by the same ACL that blocks SSH
- Ideally also Process Exporter (port 9256) for per-process stats
- Prometheus (port 9090) for target discovery and query API

**What you can extract without SSH:**
- CPU load averages, governor, scaling frequency, core count
- Memory total, available, swap usage
- Root and boot disk fullness percentage
- Disk I/O latency per device (read/write average times)
- CPU temperature and fan RPM
- Named processes and their resident memory / cumulative CPU usage
- Network traffic per interface

**What you get from process_exporter port 9256:**
- Per-process-group CPU seconds (user + system)
- Per-process-group resident memory (MB)
- Process-level swapped memory

### 1. Diagnose hardware (local or via SSH)

Start with a full inventory before touching anything:

```bash
# CPU
echo "=== CPU ==="
cat /proc/cpuinfo | grep "model name" | head -1
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq

# GPU
echo "=== GPU ==="
lspci -nn | grep -E "VGA|3D"
for c in /sys/class/drm/card*/device; do
  echo "$(basename $(dirname $c)): vendor=$(cat $c/vendor 2>/dev/null) device=$(cat $c/device 2>/dev/null) driver=$(basename $(readlink $c/driver 2>/dev/null) 2>/dev/null)"
done

# Disk
echo "=== DISK ==="
lsblk -d -o NAME,ROTA,SCHED,MIN-IO,OPT-IO | head
cat /sys/block/sda/queue/read_ahead_kb
cat /sys/block/sda/queue/nr_requests

# Memory & swap
echo "=== MEMORY ==="
free -h
swapon --show
cat /proc/sys/vm/swappiness
```

### 2. Tune I/O scheduler

For **single consumer-grade HDDs** (rotational), the `none` scheduler bypasses the block layer queue entirely — minimal overhead, best throughput for a single device.

For **SSDs/NVMe**: `none` is also optimal — no merging needed.

```bash
# Set none (immediate)
echo none > /sys/block/sda/queue/scheduler

# Verify
cat /sys/block/sda/queue/scheduler   # Expect: [none] mq-deadline
```

**read_ahead_kb**: 8192 (8MB) is a good aggressive prefetch for HDDs with sequential workloads. Higher values (16384) may help for large-file workloads.

```bash
echo 8192 > /sys/block/sda/queue/read_ahead_kb
```

**nr_requests**: With the `none` scheduler, this is fixed at the device minimum (typically 32 for HDDs) and cannot be increased. This is expected — the queueless scheduler passes I/O directly to the driver.

### 3. Tune GPU (amdgpu / Polaris+)

**Force highest performance level:**

```bash
echo "high" > /sys/class/drm/card1/device/power_dpm_force_performance_level
```

This locks the GPU into maximum P-state regardless of load.

**Force max core and memory clocks:**

```bash
# Force core to highest state
echo "7" > /sys/class/drm/card1/device/pp_dpm_sclk

# Force memory to highest state (may fail on some kernels — see pitfall below)
echo "2" > /sys/class/drm/card1/device/pp_dpm_mclk
```

**Pitfall — order matters plus kernel-dependent behavior:** On some kernels (Ubuntu 22.04 / 6.8.x with amdgpu), a direct write to `pp_dpm_mclk` returns "Invalid argument" even after setting `power_dpm_force_performance_level` to `high`. The **reliable** approach is cycling the perf level:

```bash
echo auto > /sys/class/drm/card1/device/power_dpm_force_performance_level
sleep 0.5
echo high > /sys/class/drm/card1/device/power_dpm_force_performance_level
sleep 0.5
# After this cycle, memory should be at max state automatically
```

**Check power cap:**

```bash
cat /sys/class/drm/card1/device/hwmon/hwmon*/power1_cap
cat /sys/class/drm/card1/device/hwmon/hwmon*/power1_cap_max
```

Write the max value to unlock full power budget.

**Overclocking beyond stock on Polaris (RX 400/500 series):**

The `pp_od_clk_voltage` sysfs file allows voltage/frequency curve overrides, but only if the amdgpu kernel module was loaded with `amdgpu.ppfeaturemask=0xffff7fff` (OverDrive bit 8 set). Check:

```bash
cat /sys/module/amdgpu/parameters/ppfeaturemask | grep -o '0x[0-9a-f]*'
```

Expected result format: `0xfff7bfff` — bit 8 is NOT set. Without OverDrive, overclocking via sysfs is blocked. Options:
- Add `amdgpu.ppfeaturemask=0xffff7fff` to GRUB_CMDLINE_LINUX_DEFAULT and reboot
- Or accept stock max clocks (for RX 580: 1411MHz core, 2000MHz memory at 180W)

### 4. Tune kernel sysctls

```bash
# Aggressive memory tuning
sysctl -w vm.swappiness=1            # Only swap when absolutely forced
sysctl -w vm.dirty_ratio=10          # Cap dirty page cache at 10% (flush sooner)
sysctl -w vm.dirty_background_ratio=3 # BG flusher kicks in at 3%
sysctl -w vm.vfs_cache_pressure=200  # Reclaim dentry/inode caches more aggressively
sysctl -w vm.min_free_kbytes=131072  # Keep 128MB free for emergency allocations
sysctl -w vm.page-cluster=3          # Larger swap I/O chunks

# Scheduler tuning (single-socket)
sysctl -w kernel.numa_balancing=0    # No NUMA benefits on single-socket
sysctl -w kernel.sched_autogroup_enabled=0  # No per-TTY scheduling groups
```

### 5. Remount root with noatime

```bash
mount -o remount,noatime /
```

Saves a metadata write on every file read. Confirm with `mount | grep " / " | grep noatime`.

### 6. GRUB boot parameters (requires reboot)

Add these to `GRUB_CMDLINE_LINUX_DEFAULT` in `/etc/default/grub`:

```
processor.max_cstate=1        # Limit deep idle states — reduces wake latency
intel_idle.max_cstate=0       # Disable intel_idle, fallback to ACPI idle (C1 only)
preempt=full                  # Full kernel preemption for lower scheduling latency
transparent_hugepage=always   # Reduces TLB misses
```

After editing, run `update-grub` and `reboot`.

### 7. Make persistent

**sysctl — write to /etc/sysctl.d/:**
```bash
cat > /etc/sysctl.d/99-zzzz-hermes-performance.conf << "EOF"
vm.swappiness=1
vm.dirty_ratio=10
vm.dirty_background_ratio=3
vm.vfs_cache_pressure=200
vm.min_free_kbytes=131072
vm.page-cluster=3
kernel.numa_balancing=0
kernel.sched_autogroup_enabled=0
EOF
```

**CRITICAL — sysctl loading order gotcha:** The `99-zzzz-` prefix is deliberate. Many distros ship multiple 99-* sysctl files (e.g., `99-memory.conf`, `99-swappiness.conf`, `99-zzz-performance.conf`) plus `/etc/sysctl.conf` which loads **last** after all sysctl.d files. If your file is named `99-hermes-performance.conf`, it loads alphabetically before those and gets overridden. `99-zzzz-` ensures it sorts after all of them. Even so, `/etc/sysctl.conf` still loads last — you must also **remove conflicting lines** from sysctl.conf:

```bash
# Remove the settings that we now control via sysctl.d
sudo sed -i '/^vm\.swappiness=/d; /^vm\.vfs_cache_pressure=/d; /^vm\.dirty_ratio=/d; /^vm\.dirty_background_ratio=/d' /etc/sysctl.conf
```

**GPU/I/O at boot — use rc.local:**
```bash
cat > /etc/rc.local << "EOF"
#!/bin/bash
echo none > /sys/block/sda/queue/scheduler
echo 8192 > /sys/block/sda/queue/read_ahead_kb
echo "high" > /sys/class/drm/card1/device/power_dpm_force_performance_level
exit 0
EOF
chmod +x /etc/rc.local
systemctl enable rc-local
```

**fstab — add noatime:**
```bash
sed -i 's|errors=remount-ro|noatime,errors=remount-ro|' /etc/fstab
```

### 8. Verify everything

Run this checklist:

```bash
echo "=== I/O SCHEDULER ==="
cat /sys/block/sda/queue/scheduler
echo ""
echo "=== READAHEAD ==="
cat /sys/block/sda/queue/read_ahead_kb
echo ""
echo "=== GPU LEVEL ==="
cat /sys/class/drm/card1/device/power_dpm_force_performance_level
echo "Core: $(cat /sys/class/drm/card1/device/pp_dpm_sclk)"
echo "Mem:  $(cat /sys/class/drm/card1/device/pp_dpm_mclk)"
echo "Power cap: $(cat /sys/class/drm/card1/device/hwmon/hwmon*/power1_cap) uW"
echo ""
echo "=== SYSCTLS ==="
for s in vm.swappiness vm.dirty_ratio vm.dirty_background_ratio vm.vfs_cache_pressure vm.min_free_kbytes vm.page-cluster kernel.numa_balancing kernel.sched_autogroup_enabled; do
  printf "%-40s %s\n" "$s" "$(sysctl -n $s 2>/dev/null)"
done
echo ""
echo "=== MOUNT ==="
mount | grep " / " | grep -o "noatime" || echo "noatime NOT set"
echo ""
echo "=== GRUB (after reboot) ==="
grep GRUB_CMDLINE_LINUX_DEFAULT /etc/default/grub
```

## Pitfalls

- **`/etc/sysctl.conf` overrides sysctl.d:** Even the last-sorted sysctl.d file (`99-zzzz-*.conf`) is overridden by `/etc/sysctl.conf` because `sysctl --system` applies sysctl.conf LAST. Always check `/etc/sysctl.conf` for conflicting settings and remove them. On Ubuntu/Debian, this file commonly sets `swappiness`, `dirty_ratio`, `dirty_background_ratio`, and `vfs_cache_pressure` — all of which override your sysctl.d values if not removed.
- **Competing 99-* sysctl.d files:** Distros may ship multiple 99-* files that load alphabetically after your custom file. `99-hermes-performance.conf` sorts before `99-memory.conf`, `99-swappiness.conf`, `99-zzz-performance.conf`, etc. — so those override your settings. Always inspect all `/etc/sysctl.d/99-*.conf` for conflicts and name your file `99-zzzz-*` to sort last.
- **Verify by re-running `sysctl --system`** after making changes, not just by reading `/proc/sys/...`. The values may have been correct before the last file loaded.
- **`none` scheduler + nr_requests:** With the `none` (queueless) scheduler, `nr_requests` is fixed at the device minimum (~32) and **cannot** be raised. `echo 256 > nr_requests` returns "Invalid argument". This is expected and fine — `none` bypasses the request queue entirely.
- **GPU memory clock won't budge?** Force `power_dpm_force_performance_level` to "high" FIRST, then write to `pp_dpm_mclk`. If you write mclk while in "auto" or "manual", the write may silently succeed but the clock stays low (300MHz). Cycle through auto -> high to reset.
- **GPU overdrive blocked:** Even with `mitigations=off`, the amdgpu OverDrive bit may not be set by default. Check `ppfeaturemask` before claiming you can overclock. On most distro kernels, Polaris cards cannot be overclocked via sysfs without a kernel module parameter.
- **update-grub timeout:** Can take 30-90 seconds on systems with many kernels. Increase the terminal timeout to 120s.
- **Duplicate noatime in fstab:** If the mount was already toggled to noatime live and then sed runs on fstab, you may get `noatime,errors=remount-ro,noatime`. Clean with `sudo sed -i 's|noatime,errors=remount-ro,noatime|noatime,errors=remount-ro|' /etc/fstab`.
- **zram still used for swap:** If zram is active (7.8GB), swappiness=1 may not prevent it from filling; zram uses its own compression policy. This is fine for performance — zram compress/decompress is faster than disk swap.
- **Temperature monitoring:** Check before and after with `sensors`. RX 580 safe below 84°C junction. If temps exceed 90°C under sustained load after forcing "high" level, consider reverting to "auto" or "manual" (which allows throttling).

## Files

- `scripts/apply-live-tune.sh` — Re-runnable script to apply all live changes in one shot. Takes optional args: `sudo bash scripts/apply-live-tune.sh [disk=sda] [gpu_card=card1]`.
- `references/session-example.md` — Full worked example: i7-6700 + RX 580 + 1TB HDD tuning session with all pitfalls encountered and resolved.
- `references/crash-diagnosis-ai-inference.md` — Diagnose and fix system crashes from LLM inference processes (llama-server) overcommitting GPU VRAM. Covers AMD GPU ring timeouts, duplicate Docker containers, context size tuning, and memory pressure. Use when the user says "my computer keeps crashing" or "the GPU keeps resetting" during AI inference.

## CPU Turbo Bottleneck Diagnosis

If the CPU won't reach its advertised max turbo frequency despite governor=performance and max_freq=4.0 GHz, use MSR-level register analysis. Full details and command reference in `references/cpu-turbo-debugging.md`.

### Quick diagnostic triage

```bash
# 1. Confirm turbo ratios (CPU capability)
sudo rdmsr 0x1ad    # e.g. 25262728 → 1c=40, 2c=39, 3c=38, 4c=37

# 2. Check what's LIMITING the CPU (THE KEY REGISTER)
sudo rdmsr -p 0 0x64f
# 0x00000000 = no limit (should reach max turbo)
# 0x00001000 = VR current limit active (most common — motherboard VRM bottleneck)
# bit 1 set = thermal throttling
# bit 2 set = power limit hit

# 3. Verify OS request vs actual delivery
sudo rdmsr -p 0 0x199   # IA32_PERF_CTL (what OS wants)
sudo rdmsr -p 0 0x198   # IA32_PERF_STATUS (what CPU delivers)

# 4. If power limited: raise PL2 (if MSR is unlocked)
sudo rdmsr -f 63:63 0x610   # 0 = not locked, can raise PL2
# See references/cpu-turbo-debugging.md for the full write procedure
```

### Common root causes

| MSR 0x64f pattern | Meaning | Action |
|--------------------|---------|--------|
| Lower 16 bits = `0x1000` (bit 12) | VR current limit — **motherboard VRM can't deliver enough current** | Hardware limit; undervolt CPU or replace motherboard |
| Lower 16 bits bit 1 or upper bits bit 9 | Thermal throttling | Check cooling, heatsink mounting, thermal paste |
| Lower 16 bits bit 2 or upper bits bit 10 | Power limit (PL1/PL2) | Raise RAPL power limits via MSR 0x610 (if unlocked) |
| Lower 16 bits = `0x0000` | No active limit — check BIOS turbo settings | CPU should reach max; check BIOS for turbo disable |

**Key insight:** On OEM/generic motherboards ("To-be-filled-by-O-E-M") with i7 CPUs, VR current limit is the most common bottleneck. The VRM is physically incapable of delivering the current needed for high turbo bins, regardless of software configuration. No kernel param, sysctl, or MSR write can overcome this.

## Related Skills

- `system-cleanup` — disk space recovery (run first if disk is >90% full; performance tuning needs headroom)
- `system-diagnostician` — project-level diagnostics (different class of work)
