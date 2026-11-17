---
name: sysctl-consolidate
description: Clean up conflicting sysctl config files across machines and consolidate into one clean dev-performance config
---

# Sysctl Consolidation & Performance Tuning

Use this when a machine has multiple conflicting `99-*.conf` files in `/etc/sysctl.d/` that override each other, or when tuning a machine for dev work.

## Detection

Check for conflicts:
```
ls /etc/sysctl.d/99-*
grep -rh '^vm\.\|^kernel\.\|^net\.\|^fs\.' /etc/sysctl.d/ /etc/sysctl.conf 2>/dev/null | grep -v '^#' | sort
```

If the same key appears with different values across files, there are conflicts.

## Cleanup

On the target machine, as root:

1. Remove ALL conflicting custom `99-*` files (keep system defaults like `10-*`)
2. Remove conflicting lines from `/etc/sysctl.conf`
3. Create ONE consolidated file `/etc/sysctl.d/99-dev-performance.conf`

### Consolidated config for dev tuning:
```
# Consolidated dev performance tuning
vm.swappiness=5
vm.vfs_cache_pressure=200
vm.dirty_ratio=20
vm.dirty_background_ratio=10
vm.dirty_writeback_centisecs=500
vm.dirty_expire_centisecs=3000
vm.page-cluster=0
vm.min_free_kbytes=262144
vm.watermark_scale_factor=250
vm.zone_reclaim_mode=0
vm.compaction_proactiveness=0
kernel.numa_balancing=0
net.core.default_qdisc=fq
net.ipv4.tcp_congestion_control=bbr
net.core.somaxconn=4096
net.core.netdev_max_backlog=16384
fs.inotify.max_user_watches=1048576
fs.inotify.max_user_instances=1024
fs.file-max=2097152
kernel.sched_autogroup_enabled=1
kernel.sched_child_runs_first=1
kernel.sched_migration_cost_ns=5000000
```

4. Apply: `sysctl --system`
5. Verify values take effect: `cat /proc/sys/vm/swappiness` etc.

## Pitfalls

- File loading order is alphabetical within each numbered prefix. `99-zzz*` loads AFTER `99-dev*` and will override values.
- `/etc/sysctl.conf` is loaded via `/etc/sysctl.d/99-sysctl.conf` symlink — it loads alphabetically among the `99-*` files.
- Always verify the FINAL value of each key after `sysctl --system` — don't assume your file's value is the one that stuck.
