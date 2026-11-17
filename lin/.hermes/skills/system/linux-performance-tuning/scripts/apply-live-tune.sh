#!/bin/bash
# linux-performance-tuning: apply all live changes
# Run with: sudo bash scripts/apply-live-tune.sh
set -euo pipefail

DISK="${1:-sda}"
GPU_CARD="${2:-card1}"

echo "=== 1. I/O SCHEDULER ==="
echo none > "/sys/block/${DISK}/queue/scheduler"
echo 8192 > "/sys/block/${DISK}/queue/read_ahead_kb"
echo "Scheduler: $(cat /sys/block/${DISK}/queue/scheduler)"
echo "Read-ahead: $(cat /sys/block/${DISK}/queue/read_ahead_kb) KB"

echo ""
echo "=== 2. GPU FORCE HIGH ==="
echo "high" > "/sys/class/drm/${GPU_CARD}/device/power_dpm_force_performance_level"
echo "Perf level: $(cat /sys/class/drm/${GPU_CARD}/device/power_dpm_force_performance_level)"

# Force max core and memory clocks
echo "7" > "/sys/class/drm/${GPU_CARD}/device/pp_dpm_sclk"

# Memory clock force may fail on some kernels (e.g. Ubuntu 6.8.x amdgpu);
# cycle perf level as a reliable fallback
if ! echo "2" > "/sys/class/drm/${GPU_CARD}/device/pp_dpm_mclk" 2>/dev/null; then
  echo "pp_dpm_mclk direct write failed — cycling perf level to lock max mem"
  echo auto > "/sys/class/drm/${GPU_CARD}/device/power_dpm_force_performance_level"
  sleep 0.5
  echo high > "/sys/class/drm/${GPU_CARD}/device/power_dpm_force_performance_level"
  sleep 0.5
fi

echo "Core:"
cat "/sys/class/drm/${GPU_CARD}/device/pp_dpm_sclk"
echo "Memory:"
cat "/sys/class/drm/${GPU_CARD}/device/pp_dpm_mclk"

# Max power cap
POWER_MAX=$(cat "/sys/class/drm/${GPU_CARD}/device/hwmon/hwmon*/power1_cap_max" 2>/dev/null | head -1)
if [ -n "$POWER_MAX" ]; then
  echo "$POWER_MAX" > "/sys/class/drm/${GPU_CARD}/device/hwmon/hwmon*/power1_cap" 2>/dev/null || true
  echo "Power cap set to ${POWER_MAX} uW"
fi

echo ""
echo "=== 3. KERNEL SYSCTLS ==="
sysctl -w vm.swappiness=1
sysctl -w vm.dirty_ratio=10
sysctl -w vm.dirty_background_ratio=3
sysctl -w vm.vfs_cache_pressure=200
sysctl -w vm.min_free_kbytes=131072
sysctl -w vm.page-cluster=3
sysctl -w kernel.numa_balancing=0
sysctl -w kernel.sched_autogroup_enabled=0

echo ""
echo "=== 4. REMOUNT noatime ==="
mount -o remount,noatime /
mount | grep " / " | head -1

echo ""
echo "=== DONE ==="
echo "Live changes applied. For persistent config across reboots:"
echo "  - sysctls: /etc/sysctl.d/99-zzzz-hermes-performance.conf (99-zzzz- sorts after other 99-* files)"
echo "  - boot:    /etc/rc.local"
echo "  - fstab:   add 'noatime' to root mount options"
echo "  - GRUB:    add boot params and run update-grub"
