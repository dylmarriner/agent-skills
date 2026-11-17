# Read-only Linux host performance triage probe.
# Usage: bash probe.sh [port]        No writes, no sudo, safe on a live box.
# Prints the evidence needed before changing anything.

set -u

printf '== identity / uptime ==\n'
printf 'host: %s   kernel: %s\n' "$(uname -n)" "$(uname -r)"
uptime

printf '\n== memory ==\n'
free -h

printf '\n== disk (real filesystems) ==\n'
df -h -x tmpfs -x devtmpfs -x squashfs -x overlay 2>/dev/null

printf '\n== pressure stall (some>0 with full~0 = latency, full>0 = real stall) ==\n'
for f in /proc/pressure/cpu /proc/pressure/io /proc/pressure/memory; do
  [ -r "$f" ] && printf '%s: %s\n' "$(basename "$f")" "$(tr '\n' ' ' < "$f")"
done

printf '\n== top CPU ==\n'
ps -eo pcpu,pmem,rss,comm --sort=-%cpu --no-headers | awk 'NR<=10'

printf '\n== top RSS ==\n'
ps -eo pmem,pcpu,rss,comm --sort=-%mem --no-headers | awk 'NR<=10'

printf '\n== top swap consumers (KB) ==\n'
for p in $(ps -eo pid --no-headers); do
  s=$(awk '/VmSwap/{print $2}' "/proc/$p/status" 2>/dev/null)
  if [ -n "${s:-}" ] && [ "$s" -gt 20000 ]; then
    printf '%s %s\n' "$s" "$(tr -d '\0' < "/proc/$p/comm" 2>/dev/null)"
  fi
done | sort -rn | awk 'NR<=10'

printf '\n== failed units ==\n'
if command -v systemctl >/dev/null 2>&1; then
  systemctl --failed --no-legend 2>/dev/null || true
  printf '\n== boot timing (blame includes dependency waits) ==\n'
  systemd-analyze 2>/dev/null || true
  systemd-analyze blame 2>/dev/null | awk 'NR<=12' || true
fi

printf '\n== CPU power / frequency state ==\n'
for f in \
  /sys/devices/system/cpu/cpu0/cpufreq/scaling_driver \
  /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor \
  /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference \
  /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq \
  /sys/devices/system/cpu/intel_pstate/no_turbo \
  /sys/devices/system/cpu/intel_pstate/max_perf_pct \
  /sys/devices/system/cpu/intel_pstate/min_perf_pct ; do
  [ -r "$f" ] && printf '%s = %s\n' "$(basename "$f")" "$(cat "$f")"
done
if command -v powerprofilesctl >/dev/null 2>&1; then
  printf 'power profile = %s\n' "$(powerprofilesctl get 2>/dev/null)"
fi

printf '\n== thermals ==\n'
if command -v sensors >/dev/null 2>&1; then
  sensors 2>/dev/null | awk '/Package id 0|Core [0-9]|temp1/{print}' | awk 'NR<=8'
fi

printf '\n== listeners (full list - never pipe this through head) ==\n'
ss -ltn 2>/dev/null | awk 'NR==1 || /LISTEN/' | awk 'NR<=40'

if [ "$#" -ge 1 ]; then
  printf '\n== probe port %s ==\n' "$1"
  code=$(curl -s -o /dev/null -m 4 -w '%{http_code}' "http://127.0.0.1:$1/" 2>/dev/null) || code=000
  case "$code" in
    000) printf 'HTTP 000 - nothing listening (or refused)\n' ;;
    401|403) printf 'HTTP %s - listening, auth required (endpoint is alive)\n' "$code" ;;
    *) printf 'HTTP %s\n' "$code" ;;
  esac
fi
