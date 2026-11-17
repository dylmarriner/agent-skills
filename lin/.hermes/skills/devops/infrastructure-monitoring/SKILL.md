---
name: infrastructure-monitoring
description: Deploy and maintain Prometheus, Grafana, Loki, and Home Assistant monitoring stack on a server with node_exporter agents across multiple machines. Includes GPU monitoring, log shipping, and provisioned Grafana dashboards.
trigger: User asks to deploy monitoring, set up Grafana/Prometheus, monitor multiple machines, collect GPU metrics, ship logs to Loki, or create a monitoring dashboard.
---

# Infrastructure Monitoring Stack

Deploy a full monitoring stack (Prometheus + Grafana + Loki + Home Assistant) on a Docker host with node_exporter agents on every target machine.

## Architecture

- **Server** (Docker host): runs Prometheus, Grafana, Loki, Home Assistant
- **Agents** (every machine): node_exporter + promtail + GPU textfile collector
- **Network**: all machines communicate over Tailscale IPs

## Quick Start

### 1. Server Setup (Docker Compose)

Create the directory structure on the server:

```
/opt/docker/monitoring/
  docker-compose.yml
  prometheus/prometheus.yml
  grafana/provisioning/datasources/datasource.yml
  grafana/provisioning/dashboards/
  loki/loki-config.yml
/opt/docker/home-assistant/
  docker-compose.yml
```

**docker-compose.yml** (monitoring):
```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    volumes:
      - ./prometheus:/etc/prometheus
      - prometheus_data:/prometheus
    ports:
      - "9092:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: unless-stopped
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    ports:
      - "3000:3000"

  loki:
    image: grafana/loki:latest
    container_name: loki
    restart: unless-stopped
    volumes:
      - ./loki:/etc/loki
      - loki_data:/loki
    ports:
      - "3100:3100"
    command:
      - '-config.file=/etc/loki/loki-config.yml'

volumes:
  prometheus_data:
  grafana_data:
  loki_data:
```

**prometheus.yml**:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
  - job_name: 'node'
    static_configs:
      - targets:
        - '100.93.75.87:9100'   # machine1
        - '100.68.0.96:9100'    # machine2
        - '100.75.23.127:9100'  # machine3
        - '100.91.55.113:9100'  # machine4
```

**loki-config.yml** (working config for current Loki versions):
```yaml
auth_enabled: false
server:
  http_listen_port: 3100
ingester:
  wal:
    dir: /tmp/loki/wal
  lifecycler:
    ring:
      kvstore:
        store: inmemory
schema_config:
  configs:
    - from: 2020-01-01
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h
storage_config:
  boltdb_shipper:
    active_index_directory: /tmp/loki/index
    cache_location: /tmp/loki/cache
  filesystem:
    directory: /tmp/loki/chunks
limits_config:
  reject_old_samples: true
  reject_old_samples_max_age: 168h
```

**datasource.yml** (Grafana provisioning):
```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    uid: loki-datasource
    isDefault: false
```

**Home Assistant docker-compose.yml:**
```yaml
services:
  homeassistant:
    image: ghcr.io/home-assistant/home-assistant:stable
    container_name: homeassistant
    restart: unless-stopped
    volumes:
      - ./config:/config
      - /etc/localtime:/etc/localtime:ro
    ports:
      - "8123:8123"
    environment:
      - TZ=Pacific/Auckland
```

### 2. Install node_exporter on Each Machine

```bash
# Download latest for the architecture
curl -LO https://github.com/prometheus/node_exporter/releases/latest/download/node_exporter-1.11.1.linux-amd64.tar.gz
tar xzf node_exporter-*.tar.gz
sudo cp node_exporter-*/node_exporter /usr/local/bin/
sudo useradd --no-create-home --shell /bin/false node_exporter
```

**Systemd service** (`/etc/systemd/system/node_exporter.service`):
```ini
[Unit]
Description=Prometheus Node Exporter
After=network-online.target
Wants=network-online.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter --collector.textfile.directory=/var/lib/node_exporter/textfile_collector --collector.hwmon

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now node_exporter
```

### 3. GPU Monitoring (Textfile Collectors)

GPU metrics ship through node_exporter's textfile collector. Create a script, set up a cron job, and ensure file permissions.

**CRITICAL PERMISSIONS NOTE**: Textfile collector files must be readable by the node_exporter user. Scripts (run as root via cron) must `chmod 644` the output file, otherwise node_exporter runs as the `node_exporter` user and can't read root-owned files.

#### AMD GPU Script (`/usr/local/bin/amd_gpu_metrics.sh`):
See `references/amd-gpu-script.md` for the full script.

#### NVIDIA GPU Script (`/usr/local/bin/nvidia_gpu_metrics.sh`):
See `references/nvidia-gpu-script.md` for the full script.

**Setup:**
```bash
# Create textfile directory
sudo mkdir -p /var/lib/node_exporter/textfile_collector
sudo chown node_exporter:node_exporter /var/lib/node_exporter/textfile_collector

# Add cron job
(crontab -l 2>/dev/null | grep -v gpu_metrics; echo "* * * * * /usr/local/bin/amd_gpu_metrics.sh") | crontab -
(crontab -l 2>/dev/null | grep -v gpu_metrics; echo "* * * * * /usr/local/bin/nvidia_gpu_metrics.sh") | crontab -
```

**Known pitfalls:**
- `[N/A]` values from `nvidia-smi` break Prometheus format — replace with `0`
- Files created by root cron jobs have 600 permissions — script must `chmod 644` before moving
- If node_exporter service was already installed without `--collector.textfile.directory`, update the ExecStart line and restart

### 4. Log Shipping (Promtail)

Install promtail on every machine via the Grafana apt repo:

```bash
wget -q -O - https://apt.grafana.com/gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/grafana.gpg
echo 'deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://apt.grafana.com stable main' | sudo tee /etc/apt/sources.list.d/grafana.list
sudo apt-get update && sudo apt-get install -y promtail
```

**Config** (`/etc/promtail/promtail-config.yaml`):
```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0
positions:
  filename: /var/lib/promtail/positions.yaml
clients:
  - url: http://SERVER_IP:3100/loki/api/v1/push
scrape_configs:
  - job_name: system
    static_configs:
      - targets:
          - localhost
        labels:
          job: varlogs
          host: MACHINE_NAME
          __path__: /var/log/syslog   # Ubuntu
          # __path__: /var/log/messages  # Debian
```

The default apt-installed service expects config at `/etc/promtail/config.yml` — either copy your config there or update the service ExecStart line.

**Critical: Run promtail as root** — the default service runs as the `promtail` user which can't read system logs. Edit `/etc/systemd/system/promtail.service`:
```
User=root
```

**Distro log path differences:**
- **Ubuntu**: `/var/log/syslog`
- **Debian**: `/var/log/messages` (or use systemd journal)

### 5. Grafana Dashboard Provisioning

Place a dashboard JSON in `/opt/docker/monitoring/grafana/provisioning/dashboards/` with a provider config:

**Dashboard provider** (`dashboard.yml`):
```yaml
apiVersion: 1
providers:
  - name: 'Infrastructure'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    editable: true
    options:
      path: /etc/grafana/provisioning/dashboards
```

**Recommended panel queries:**

| Panel | Query |
|-------|-------|
| CPU Usage | `100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)` |
| Memory % | `100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))` |
| CPU Temp (Intel/AMD) | `node_thermal_zone_temp{type="x86_pkg_temp"}` |
| CPU Temp (Raspberry Pi) | `node_thermal_zone_temp{type="cpu-thermal"}` |
| GPU Temp (AMD) | `amdgpu_temp_celsius{sensor="edge"}` |
| GPU Temp (NVIDIA) | `nvidia_gpu_temp_celsius` |
| GPU Util (AMD) | `amdgpu_gpu_busy_percent` |
| GPU Util (NVIDIA) | `nvidia_gpu_utilization_percent` |
| Disk Usage | `100 * (1 - (node_filesystem_avail_bytes{fstype!~"overlay|tmpfs|devtmpfs|efivarfs"} / node_filesystem_size_bytes{fstype!~"overlay|tmpfs|devtmpfs|efivarfs"}))` |
| Error Logs (Loki) | `{job="varlogs"} |~ "(?i)(error|fail|critical|panic|exception)"` |

After adding/changing a dashboard JSON, restart Grafana: `docker compose restart grafana`.

## Grafana Dashboard JSON Template

See `templates/dashboard.json` for a complete 10-panel infrastructure overview dashboard with CPU, RAM, load, temperatures, GPU metrics, disk, and error logs.

## Pitfalls

- **LogQL vs PromQL operators**: PromQL uses `|=` for string-contains and `|=~` for regex. **LogQL uses different operators**: `|=` for string-contains (same) but **`|~`** for regex (no `=` sign, different from PromQL). Using `|=~` in a Loki query produces a Grafana syntax error with no helpful error message. Correct: `{job="varlogs"} |~ "(?i)error"`. Wrong: `{job="varlogs"} |=~ "(?i)error"`. Memory aid: Loki = `|~` (tilde), Prometheus = `|=~` (equals-tilde).
- **Port conflicts**: Check existing services before assigning ports. Transmission defaults to 9091.
- **GPU textfile permissions**: Files created by root cron need `chmod 644` — node_exporter runs as its own user.
- **Loki version config**: Old Loki configs with `shared_store` field break on new versions. Use the config above.
- **Promtail config path**: The deb package expects `/etc/promtail/config.yml`, not `/etc/promtail/promtail-config.yaml`.
- **Promtail log paths**: Ubuntu = `/var/log/syslog`, Debian = `/var/log/messages`. Empty files mean systemd-journald is primary — use journald input instead.
- **Prometheus regex**: The `|` pipe character in label matchers needs proper URL encoding. Use separate query entries instead of `chip=~"a|b"`.
- **Grafana chip labels**: `node_hwmon_temp_celsius` has chip labels like `platform_coretemp_0`, not `coretemp`. Use `node_thermal_zone_temp` for CPU temps instead.
- **Loki datasource in provisioned dashboards**: Log panels in provisioned Grafana dashboards must include an explicit `datasource` field referencing the Loki datasource UID. Without it, Grafana uses the default Prometheus datasource and LogQL queries fail silently (no error shown, no data rendered). Set a stable `uid` (e.g. `loki-datasource`) in the Loki datasource provisioning, then reference it in the panel and target.
