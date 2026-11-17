#!/bin/bash
# AMD GPU Prometheus metrics via node_exporter textfile collector
# Reads from sysfs — no AMD tools required. Works on any AMD GPU (RX 400+ series)
# Usage: /usr/local/bin/amd_gpu_metrics.sh [/var/lib/node_exporter/textfile_collector]
# Output: atomically writes amd_gpu.prom to the collector directory

OUTPUT_DIR="${1:-/var/lib/node_exporter/textfile_collector}"
mkdir -p "$OUTPUT_DIR"
TMP=$(mktemp)

# Collect ALL metrics in a single block, then atomically mv
{
  # GPU utilization from sysfs
  for card in /sys/class/drm/card*/device/gpu_busy_percent; do
    if [ -f "$card" ]; then
      gpu=$(basename "$(dirname "$(dirname "$card")")")
      busy=$(cat "$card" 2>/dev/null || echo 0)
      echo "amdgpu_gpu_busy_percent{gpu=\"$gpu\"} $busy"
    fi
  done

  # VRAM usage from sysfs
  for mem in /sys/class/drm/card*/device/mem_info_vram_total; do
    if [ -f "$mem" ]; then
      gpu=$(basename "$(dirname "$(dirname "$mem")")")
      vram_total=$(cat "$mem" 2>/dev/null || echo 0)
      vram_used=$(cat "${mem%_total}_used" 2>/dev/null || echo 0)
      echo "amdgpu_vram_bytes{gpu=\"$gpu\",type=\"total\"} $vram_total"
      echo "amdgpu_vram_bytes{gpu=\"$gpu\",type=\"used\"} $vram_used"
      if [ "$vram_total" -gt 0 ]; then
        pct=$(echo "scale=2; $vram_used * 100 / $vram_total" | bc 2>/dev/null || echo 0)
        echo "amdgpu_vram_usage_percent{gpu=\"$gpu\"} $pct"
      fi
    fi
  done

  # Temperature, fan speed, power from hwmon
  for hwmon in /sys/class/drm/card*/device/hwmon/hwmon*/; do
    if [ -d "$hwmon" ]; then
      name_file="${hwmon}name"
      [ -f "$name_file" ] || continue
      hwmon_name=$(cat "$name_file" | tr -d '\n')

      for t in "${hwmon}"temp*_input; do
        [ -f "$t" ] || continue
        tlabel="${t%_input}_label"
        label=""
        [ -f "$tlabel" ] && label=$(cat "$tlabel")
        temp=$(cat "$t" 2>/dev/null | awk '{printf "%.1f", $1/1000}')
        echo "amdgpu_temp_celsius{hwmon=\"$hwmon_name\",sensor=\"$label\"} $temp"
      done

      for f in "${hwmon}"fan*_input; do
        [ -f "$f" ] || continue
        speed=$(cat "$f" 2>/dev/null || echo 0)
        fname=$(basename "$f" | sed 's/_input//')
        echo "amdgpu_fan_rpm{fan=\"$fname\"} $speed"
      done

      for p in "${hwmon}"power*_average; do
        [ -f "$p" ] || continue
        pwr=$(cat "$p" 2>/dev/null | awk '{printf "%.2f", $1/1000000}')
        echo "amdgpu_power_watts{type=\"average\"} $pwr"
      done
    fi
  done
} > "$TMP"

# Make readable by node_exporter (runs as unprivileged user; cron runs as root)
chmod 644 "$TMP"
# Atomic write — prevents partial reads by Prometheus
mv "$TMP" "${OUTPUT_DIR}/amd_gpu.prom"
