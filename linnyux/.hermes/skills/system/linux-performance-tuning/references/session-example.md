# Example Session: i7-6700 + RX 580 + 1TB HDD Performance Tune

Hardware configuration from a real tuning session:

- **CPU:** Intel i7-6700 (4C/8T, max 4.0GHz)
- **GPU:** AMD RX 580 (device 0x67df, driver amdgpu, 1411MHz core, 2000MHz mem, 180W TDP)
- **Disk:** WD1001FALS-0 (1TB HDD, 7200RPM, /dev/sda, mq-deadline)
- **SSD:** /dev/sdb3 root filesystem (ext4)
- **Memory:** 16GB DDR4
- **Swap:** 16GB /swapfile + 7.8GB zram
- **Kernel:** 6.8.0-111-generic (Ubuntu 22.04)
- **GPU sysfs path:** /sys/class/drm/card1/device

## Order of Operations Used

1. Diagnosed hardware (sysfs reads, lspci, sensors)
2. Set I/O: `none` scheduler + 8192 readahead (skipped nr_requests — not writable with none)
3. GPU: `high` power_dpm_force_performance_level -> sclk=7 -> mclk=2 -> power cap 180W
4. Sysctls: swappiness=1, dirty_ratio=10, dirty_background_ratio=3, vfs_cache_pressure=200, min_free_kbytes=131072, page-cluster=3, numa_balancing=0, sched_autogroup_enabled=0
5. Remount root: noatime
6. GRUB: +processor.max_cstate=1 intel_idle.max_cstate=0 preempt=full transparent_hugepage=always
7. Persistence: /etc/sysctl.d/99-hermes-performance.conf, /etc/rc.local, /etc/fstab
8. Six-pass verification

## Memory Clock Stuck at 300MHz

Even after writing `echo 2 > pp_dpm_mclk`, the memory stayed at 300MHz state 0. The fix was cycling the force level:

```bash
echo auto > power_dpm_force_performance_level
sleep 0.5
echo high > power_dpm_force_performance_level
sleep 0.5
# Now mclk moves to 2000MHz state 2
```

Also, on this kernel (6.8.0-111-generic), the direct `echo 2 > pp_dpm_mclk` returned "Invalid argument" — the write was completely rejected by the driver. The auto->high cycle was the only reliable method.

## Sysctl Ordering Pitfall — ALL Overridden at Boot

Created `/etc/sysctl.d/99-hermes-performance.conf` with aggressive values. After reboot, the values were all defaults (swappiness=10, dirty_ratio=15, etc.). Root cause: `sysctl --system` loads sysctl.d files alphabetically, then loads `/etc/sysctl.conf` LAST.

Several competing files existed:
- `99-desktop-performance.conf` (swappiness=120!)
- `99-memory.conf` (swappiness=10, vfs_cache_pressure=50)
- `99-paperclip.conf` (swappiness=30)
- `99-storage.conf` (dirty_background_ratio=5, dirty_ratio=15)
- `99-swappiness.conf` (swappiness=30)
- `99-sysctl.conf` (swappiness=10, vfs_cache_pressure=50, dirty_ratio=15, dirty_background_ratio=5)
- `99-zzz-performance.conf` (swappiness=10, vfs_cache_pressure=50, dirty_ratio=10, dirty_background_ratio=5)
- `/etc/sysctl.conf` (swappiness=10, vfs_cache_pressure=50, dirty_ratio=15, dirty_background_ratio=5)

Fix applied:
1. Renamed to `99-zzzz-hermes-performance.conf` (sorts after 99-zzz-*)
2. Removed conflicting lines from `/etc/sysctl.conf` (loaded last)

## OverDrive Not Available

`ppfeaturemask` was `0xfff7bfff` — bit 8 (OverDrive) not set. Could not write to `pp_od_clk_voltage`. To enable, would need:

```
amdgpu.ppfeaturemask=0xffff7fff
```

in GRUB_CMDLINE_LINUX_DEFAULT, then reboot.

## Orphaned Agent Processes

Before tuning, needed to clean up ~15 orphaned `opencode run` processes consuming 20-27% CPU and 300-630MB RAM each. These were left behind when Paperclip was killed. `pkill -f "opencode run"` freed significant resources.

## Docker Disk Cleanup Pre-Tune

Root disk was at 100% (219GB/219GB). Freed ~40GB by:
1. `sudo apt-get clean`
2. `sudo journalctl --vacuum-size=200M`
3. Removed old log files from /var/log
4. `docker system prune -af && docker builder prune -af && docker image prune -af` (freed 43GB)
5. The HDD at /media/kubuntux/DEVELOPMENT1 had 1.9TB free — Docker images were the main culprit on root
