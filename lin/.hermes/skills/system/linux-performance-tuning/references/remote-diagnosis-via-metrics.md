# Remote System Diagnosis via Prometheus/Node Exporter (When SSH is Blocked)

When SSH is blocked by a tailnet ACL, firewall, or other policy, you can still diagnose a Linux system's resource and performance state if it runs **Prometheus** and **Node Exporter** (or just Node Exporter). This technique turns the standard Prometheus scrape endpoint into a read-only diagnostic channel.

## Preconditions

- The target machine has **Node Exporter** on a known port (default 9100) exposing `/metrics`
- Ideally also **Prometheus** (port 9090) for structured target discovery and query API
- Optionally **Process Exporter** (port 9256) for per-process CPU/memory breakdown
- The Prometheus/Node Exporter port is accessible from your machine (no firewall blocking port 9100/9090 even if SSH is blocked)

## Quick Health Check

```bash
# System identity and uptime
curl -s http://<target>:9100/metrics | grep -E "^node_uname_info|^node_time_seconds|^node_boot_time_seconds"

# CPU load
curl -s http://<target>:9100/metrics | grep -E "^node_load1|^node_load5|^node_load15|^node_cpu_online|^node_procs_running|^node_procs_blocked"

# Memory
curl -s http://<target>:9100/metrics | grep -E "^node_memory_MemTotal|^node_memory_MemFree|^node_memory_MemAvailable|^node_memory_SwapTotal|^node_memory_SwapFree|^node_memory_Cached|^node_memory_Buffers"

# Disk space (root and boot)
curl -s http://<target>:9100/metrics | grep -E "node_filesystem_avail_bytes|node_filesystem_size_bytes" | grep 'mountpoint="/"\|mountpoint="/boot'

# Disk I/O stats
curl -s http://<target>:9100/metrics | grep -E "^node_disk_(read_bytes|written_bytes|reads_completed|writes_completed|read_time|write_time|io_time|io_time_weighted)" | head -20

# Thermal and fan
curl -s http://<target>:9100/metrics | grep -E "^node_hwmon_temp|^node_hwmon_fan"

# Network
curl -s http://<target>:9100/metrics | grep -E "^node_network_receive_bytes|^node_network_transmit_bytes" | grep -E "eth0|wlan0|tailscale0|enp"
```

## Interpreting the Metrics

### Load Averages

```
node_load1 3.5
node_load5 2.97
node_load15 1.39
```

On a 4-core system, load1 > 4 means the CPU is saturated. On an 8-core system, load1 > 8 means saturation. Values between core count * 0.6 and core count indicate moderate to heavy load.

### Memory Pressure

```
node_memory_MemTotal_bytes      8.45e9   (8.0 GB)
node_memory_MemAvailable_bytes  4.26e9   (4.0 GB available)
node_memory_SwapTotal_bytes     5.37e8   (512 MB swap)
node_memory_SwapFree_bytes      3.50e8   (350 MB swap free → 160 MB swap used)
```

If `MemAvailable` is less than 10-15% of `MemTotal`, the system is memory-constrained. Heavy swap usage (>50% of swap) combined with high load suggests memory pressure is causing swapping.

### Disk Fullness as a Performance Problem

```
node_filesystem_avail_bytes{device="/dev/sda2",mountpoint="/"}  1.39e10  (13.9 GB)
node_filesystem_size_bytes{device="/dev/sda2",mountpoint="/"}  2.36e11  (235 GB)
```

Calculate fullness: (size - avail) / size. For the example above: (235 - 13.9) / 235 = **94% full**.

A disk at >90% fullness causes degraded performance on both SSDs and HDDs. SSDs need free space for wear leveling and garbage collection; HDDs struggle with fragmentation and metadata allocation. Always check disk fullness first — it's often the primary bottleneck.

### Disk I/O Performance

```
# Read performance (sda = root SSD)
node_disk_read_time_seconds_total{device="sda"}    106.7
node_disk_reads_completed_total{device="sda"}      120814
# Average read latency: 106.7 / 120814 = 0.88 ms  (good for SSD)

# Write performance
node_disk_write_time_seconds_total{device="sda"}   39.8
node_disk_writes_completed_total{device="sda"}     13238
# Average write latency: 39.8 / 13238 = 3.0 ms  (moderate)

# USB HDD comparison
node_disk_read_time_seconds_total{device="sdb"}    461.3
node_disk_reads_completed_total{device="sdb"}      26889
# Average read latency: 461.3 / 26889 = 17.2 ms  (slow USB HDD)
```

Calculate average latency: `read_time_seconds / reads_completed`. For SSDs, expect <1ms. For HDDs via USB, expect 10-20ms. Latencies significantly above these baselines suggest I/O contention or a near-full filesystem.

### CPU Governor and Frequency

```
node_cpu_scaling_governor{cpu="0",governor="performance"}  1
node_cpu_scaling_frequency_hertz{cpu="0"}                  2.8e+09  (2.8 GHz)
node_cpu_frequency_max_hertz{cpu="0"}                      2.8e+09  (2.8 GHz max)
node_cpu_frequency_min_hertz{cpu="0"}                      1.5e+09  (1.5 GHz min)
```

4 CPUs × governor=performance = already optimized for speed. If governor is `powersave` or `ondemand`, that's a first optimization opportunity.

## Process-Level Diagnostics (via Process Exporter)

If the target runs **Process Exporter** on port 9256 (or a custom port), you can get per-process CPU and memory breakdown without any shell access:

### Top CPU Consumers

```bash
curl -s http://<target>:9256/metrics | grep "namedprocess_namegroup_cpu_seconds_total.*user" | sort -t' ' -k2 -rn | head -10
```

### Top Memory Consumers (resident)

```bash
curl -s http://<target>:9256/metrics | python3 -c "
import sys, re
data = sys.stdin.read()
resident = {}
for m in re.finditer(r'namedprocess_namegroup_memory_bytes\{groupname=\"([^\"]+)\",memtype=\"resident\"\} ([\d.e+\-]+)', data):
    name, val = m.group(1), float(m.group(2))
    resident[name] = resident.get(name, 0) + val
for name, val in sorted(resident.items(), key=lambda x: -x[1])[:15]:
    print(f'{val/1e6:6.0f}MB  {name}')
"
```

### All Processes Sorted by CPU

```bash
curl -s http://<target>:9256/metrics | grep "namedprocess_namegroup_cpu_seconds_total.*user" | sort -t' ' -k2 -rn
```

This reveals unexpected CPU hogs like Suricata IDS, container orchestration overhead, or orphaned agent processes.

## Prometheus Target Discovery

If Prometheus is running on the target (port 9090), query its target state to find which other endpoints are scraped:

```bash
curl -s http://<target>:9090/api/v1/targets | python3 -c "
import sys,json
d=json.load(sys.stdin)
for t in d['data']['activeTargets']:
    print(t['labels']['job'], t['labels']['instance'], t['health'])
"
```

This reveals what monitoring infrastructure exists on the machine and any sibling machines being scraped.

## System Profile via Grafana

If Grafana is accessible (port 3000 on the target), browse to `http://<target>:3000` for pre-built dashboards showing CPU, memory, disk, and network time series. This gives historical context missing from raw metrics snapshots.

## Example: Full Diagnosis in One Command

```bash
# Comprehensive remote health check — run this first
curl -s http://<target>:9100/metrics | grep -E "^node_(load1|load5|load15|.*MemTotal|.*MemAvailable|.*SwapTotal|.*SwapFree|uname_info|time_seconds|boot_time|cpu_online|procs_running|procs_blocked|hwmon_temp|hwmon_fan)" | paste - - - - - - - - - -
```

## What You Can't Determine Remotely

- Running processes not captured by Process Exporter (most lightweight services won't show per-process stats unless specifically configured)
- Disk fragmentation levels
- Network latency/jitter
- Kernel ring buffer messages (`dmesg`)
- File descriptor limits in use
- Actual running container list (need Docker API or SSH)

These require either SSH access or additional exporter configuration on the target.

## Example Worked Session

In a May 2026 session, the Pi 5 "pi5-deflab" at 100.68.0.96:
- SSH blocked by Tailscale ACL
- Full diagnosis achieved via node_exporter (9100), process_exporter (9256), and Prometheus (9090)
- Discovered: 94% full root disk, Xfce desktop wasting 400MB RAM on a server, dual ad-blockers (Pi-hole + AdGuardHome), heavy monitoring stack (Grafana + Alloy + Loki + Prometheus = 643MB), Suricata IDS, Ollama + LiteLLM, and 15+ other services
- No shell access needed — all data extracted from raw metrics endpoints
