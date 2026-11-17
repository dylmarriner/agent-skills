# AMD GPU Textfile Collector Script

Place at `/usr/local/bin/amd_gpu_metrics.sh` on the machine with an AMD GPU.

```bash
#!/bin/bash
# AMD GPU Prometheus metrics via textfile collector
OUTPUT_DIR="${1:-/var/lib/node_exporter/textfile_collector}"
mkdir -p "$OUTPUT_DIR"
TMP=$(mktemp)

# All output goes to temp file
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

  # Temperature, fan, power from hwmon
  for hwmon in /sys/class/drm/card*/device/hwmon/hwmon*/; do
    if [ -d "$hwmon" ]; then
      name_file="${hwmon}name"
      if [ -f "$name_file" ]; then
        hwmon_name=$(cat "$name_file" | tr -d '\n')
        for t in "${hwmon}"temp*_input; do
          if [ -f "$t" ]; then
            tlabel="${t%_input}_label"
            label=""
            [ -f "$tlabel" ] && label=$(cat "$tlabel")
            temp=$(cat "$t" 2>/dev/null | awk '{printf "%.1f", $1/1000}')
            echo "amdgpu_temp_celsius{hwmon=\"$hwmon_name\",sensor=\"$label\"} $temp"
          fi
        done
        for f in "${hwmon}"fan*_input; do
          if [ -f "$f" ]; then
            speed=$(cat "$f" 2>/dev/null || echo 0)
            fname=$(basename "$f" | sed 's/_input//')
            echo "amdgpu_fan_rpm{fan=\"$fname\"} $speed"
          fi
        done
        for p in "${hwmon}"power*_average; do
          if [ -f "$p" ]; then
            pwr=$(cat "$p" 2>/dev/null | awk '{printf "%.2f", $1/1000000}')
            echo "amdgpu_power_watts{type=\"average\"} $pwr"
          fi
        done
      fi
    fi
  done
} > "$TMP"

# CRITICAL: chmod 644 so node_exporter user can read it
chmod 644 "$TMP"
mv "$TMP" "${OUTPUT_DIR}/amd_gpu.prom"
```

**Setup:**
```bash
chmod +x /usr/local/bin/amd_gpu_metrics.sh
mkdir -p /var/lib/node_exporter/textfile_collector
(crontab -l 2>/dev/null; echo "* * * * * /usr/local/bin/amd_gpu_metrics.sh") | crontab -
```

**Verify:**
```bash
sudo /usr/local/bin/amd_gpu_metrics.sh
cat /var/lib/node_exporter/textfile_collector/amd_gpu.prom
curl -s http://localhost:9100/metrics | grep amdgpu | head -5
```

**Metrics produced:**
- `amdgpu_gpu_busy_percent{gpu="card1"}` — GPU utilization 0-100%
- `amdgpu_vram_bytes{gpu="card1",type="total|used"}` — VRAM in bytes
- `amdgpu_vram_usage_percent{gpu="card1"}` — VRAM usage %
- `amdgpu_temp_celsius{hwmon="amdgpu",sensor="edge|junction|mem"}` — GPU temperatures
- `amdgpu_fan_rpm{fan="fan1"}` — Fan speed in RPM
- `amdgpu_power_watts{type="average"}` — Power draw in watts
