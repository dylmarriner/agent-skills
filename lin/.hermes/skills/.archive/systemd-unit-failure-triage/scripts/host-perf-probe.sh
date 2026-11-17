#!/usr/bin/env bash
# Read-only host performance / failure probe.
# One pass: load, PSI, memory, top CPU+RAM, swap hogs, disk, FAILED UNITS, boot blame,
# pstate/EPP, thermals, zram, network mounts. Changes nothing (no root needed for most of it).
#
#   bash host-perf-probe.sh
#
# Filters with awk rather than grep/head so a shell wrapper or grep alias cannot swallow the output.
set -u

sec() { printf '\n=== %s ===\n' "$1"; }
rd()  { for f in "$@"; do [ -r "$f" ] && printf '%s = %s\n' "$(basename "$f")" "$(<"$f")"; done; }

sec "LOAD / UPTIME"
uptime

sec "PSI (nonzero 'full' = real stall)"
for f in /proc/pressure/cpu /proc/pressure/io /proc/pressure/memory; do
  [ -r "$f" ] && printf '%s: %s\n' "$(basename "$f")" "$(tr '\n' ' ' < "$f")"
done

sec "MEMORY / SWAP"
free -h

sec "TOP CPU"
ps -eo pcpu,pmem,rss,comm --sort=-%cpu --no-headers | awk 'NR<=12'

sec "TOP RAM"
ps -eo pmem,pcpu,rss,comm --sort=-%mem --no-headers | awk 'NR<=12'

sec "SWAP HOGS (kB)"
for p in $(ps -eo pid --no-headers); do
  s=$(awk '/^VmSwap/{print $2}' "/proc/$p/status" 2>/dev/null)
  [ -n "${s:-}" ] && [ "$s" -gt 20000 ] && echo "$s $(tr -d '\0' < "/proc/$p/comm" 2>/dev/null)"
done | sort -rn | awk 'NR<=10'

sec "DISK"
df -h -x tmpfs -x devtmpfs -x squashfs

sec "FAILED UNITS  <-- start here"
systemctl --failed --no-legend || true

sec "BOOT BLAME (includes dependency wait)"
systemd-analyze blame 2>/dev/null | awk 'NR<=12'

sec "BOOT TIME"
systemd-analyze 2>/dev/null

sec "CPU / INTEL_PSTATE STATE"
lscpu 2>/dev/null | awk -F: '/model name|^CPU\(s\)|MHz/'
rd /sys/devices/system/cpu/intel_pstate/no_turbo \
   /sys/devices/system/cpu/intel_pstate/max_perf_pct \
   /sys/devices/system/cpu/intel_pstate/min_perf_pct \
   /sys/devices/system/cpu/cpu0/cpufreq/scaling_driver \
   /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor \
   /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference \
   /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq
printf 'power-profile = %s\n' "$(powerprofilesctl get 2>/dev/null || echo n/a)"
printf 'tuned = %s\n' "$(systemctl is-active tuned 2>/dev/null || echo n/a)"
printf 'thermald = %s\n' "$(systemctl is-active thermald 2>/dev/null || echo n/a)"

sec "THERMALS"
sensors 2>/dev/null | awk '/Package id|Composite|temp1/' | awk 'NR<=8'

sec "ZRAM"
zramctl 2>/dev/null | awk 'NR<=4'

sec "NETWORK MOUNTS (autofs = lazy mount, healthy)"
findmnt -l 2>/dev/null | awk '/cifs|nfs|autofs/'
systemctl list-units --all --no-legend '*.mount' 2>/dev/null | awk '/failed/'

sec "FSTAB NETWORK ENTRIES"
awk '$3 ~ /^(cifs|nfs|nfs4)$/ {print $1, $2}' /etc/fstab 2>/dev/null | awk 'NR<=20'
