# NVIDIA GPU Textfile Collector Script

Place at `/usr/local/bin/nvidia_gpu_metrics.sh` on the machine with an NVIDIA GPU.

```bash
#!/bin/bash
OUTPUT_DIR="${1:-/var/lib/node_exporter/textfile_collector}"
mkdir -p "$OUTPUT_DIR"
TMP=$(mktemp)

if command -v nvidia-smi &>/dev/null; then
  nvidia-smi --query-gpu=index,name,temperature.gpu,utilization.gpu,memory.total,memory.used,power.draw,fan.speed --format=csv,noheader,nounits 2>/dev/null | while IFS=, read -r idx name temp util mem_total mem_used power fan; do
    idx=$(echo "$idx" | xargs)
    gpu_name=$(echo "$name" | xargs | tr " /" "__")

    # Temp and util are always numeric
    echo "nvidia_gpu_temp_celsius{gpu=\"$idx\",name=\"$gpu_name\"} $(echo "$temp" | xargs)"
    echo "nvidia_gpu_utilization_percent{gpu=\"$idx\",name=\"$gpu_name\"} $(echo "$util" | xargs)"

    # Memory values
    mt=$(echo "$mem_total" | xargs)
    mu=$(echo "$mem_used" | xargs)
    echo "nvidia_memory_bytes{gpu=\"$idx\",name=\"$gpu_name\",type=\"total\"} $mt"
    echo "nvidia_memory_bytes{gpu=\"$idx\",name=\"$gpu_name\",type=\"used\"} $mu"
    if [ "$mt" -gt 0 ] 2>/dev/null; then
      pct=$(echo "scale=2; $mu * 100 / $mt" | bc 2>/dev/null || echo 0)
      echo "nvidia_memory_usage_percent{gpu=\"$idx\",name=\"$gpu_name\"} $pct"
    fi

    # Power and fan may return [N/A] on mobile GPUs — extract numeric or use 0
    pwr=$(echo "$power" | xargs | grep -oE '^[0-9.]+' || echo 0)
    fan=$(echo "$fan" | xargs | grep -oE '^[0-9.]+' || echo 0)
    echo "nvidia_power_watts{gpu=\"$idx\",name=\"$gpu_name\"} $pwr"
    echo "nvidia_fan_speed_percent{gpu=\"$idx\",name=\"$gpu_name\"} $fan"
  done
fi > "$TMP"

# CRITICAL: chmod 644 so node_exporter user can read it
chmod 644 "$TMP"
mv "$TMP" "${OUTPUT_DIR}/nvidia_gpu.prom"
```

**Setup:**
```bash
chmod +x /usr/local/bin/nvidia_gpu_metrics.sh
mkdir -p /var/lib/node_exporter/textfile_collector
(crontab -l 2>/dev/null; echo "* * * * * /usr/local/bin/nvidia_gpu_metrics.sh") | crontab -
```

**Verify:**
```bash
/usr/local/bin/nvidia_gpu_metrics.sh
cat /var/lib/node_exporter/textfile_collector/nvidia_gpu.prom
curl -s http://localhost:9100/metrics | grep nvidia | head -5
```

**Metrics produced:**
- `nvidia_gpu_temp_celsius{gpu="0",name="NVIDIA_GeForce_MX150"}` — GPU temperature
- `nvidia_gpu_utilization_percent{gpu="0"}` — GPU compute utilization
- `nvidia_memory_bytes{gpu="0",type="total|used"}` — VRAM in MiB
- `nvidia_memory_usage_percent{gpu="0"}` — VRAM usage %
- `nvidia_power_watts{gpu="0"}` — Power draw (0 if N/A)
- `nvidia_fan_speed_percent{gpu="0"}` — Fan speed (0 if N/A)
