#!/bin/bash
# NVIDIA GPU Prometheus metrics via node_exporter textfile collector
# Uses nvidia-smi. Requires NVIDIA drivers + nvidia-smi in PATH.
# Usage: /usr/local/bin/nvidia_gpu_metrics.sh [/var/lib/node_exporter/textfile_collector]
# Output: atomically writes nvidia_gpu.prom to the collector directory

OUTPUT_DIR="${1:-/var/lib/node_exporter/textfile_collector}"
mkdir -p "$OUTPUT_DIR"
TMP=$(mktemp)

if command -v nvidia-smi &>/dev/null; then
  nvidia-smi --query-gpu=index,name,temperature.gpu,utilization.gpu,memory.total,memory.used,power.draw,fan.speed --format=csv,noheader,nounits 2>/dev/null | while IFS=, read -r idx name temp util mem_total mem_used power fan; do
    idx=$(echo "$idx" | xargs)
    gpu_name=$(echo "$name" | xargs | tr ' /' '__')

    echo "nvidia_gpu_temp_celsius{gpu=\"$idx\",name=\"$gpu_name\"} $(echo "$temp" | xargs)"
    echo "nvidia_gpu_utilization_percent{gpu=\"$idx\",name=\"$gpu_name\"} $(echo "$util" | xargs)"

    mt=$(echo "$mem_total" | xargs)
    mu=$(echo "$mem_used" | xargs)
    echo "nvidia_memory_megabytes{gpu=\"$idx\",name=\"$gpu_name\",type=\"total\"} $mt"
    echo "nvidia_memory_megabytes{gpu=\"$idx\",name=\"$gpu_name\",type=\"used\"} $mu"

    if [ "$mt" -gt 0 ] 2>/dev/null; then
      pct=$(echo "scale=2; $mu * 100 / $mt" | bc 2>/dev/null || echo 0)
      echo "nvidia_memory_usage_percent{gpu=\"$idx\",name=\"$gpu_name\"} $pct"
    fi

    # PITFALL: Some GPUs report [N/A] for power/fan (e.g. mobile MX150)
    # grep -oE filters to numeric-only, defaulting to 0
    pwr=$(echo "$power" | xargs | grep -oE '^[0-9.]+' || echo 0)
    fan=$(echo "$fan" | xargs | grep -oE '^[0-9.]+' || echo 0)
    echo "nvidia_power_watts{gpu=\"$idx\",name=\"$gpu_name\"} $pwr"
    echo "nvidia_fan_speed_percent{gpu=\"$idx\",name=\"$gpu_name\"} $fan"
  done > "$TMP"
else
  echo "nvidia_smi_available 0" > "$TMP"
fi

# Make readable by node_exporter (runs as unprivileged user; cron runs as root)
chmod 644 "$TMP"
# Atomic write — prevents partial reads by Prometheus
mv "$TMP" "${OUTPUT_DIR}/nvidia_gpu.prom"
