---
name: monitoring-observability
description: Set up monitoring, logging, and observability for applications and infrastructure. Use when implementing health checks, metrics collection, log aggregation, or alerting systems. Handles Prometheus, Grafana, ELK Stack, Datadog, and monitoring best practices.
metadata:
  tags: monitoring, observability, logging, metrics, Prometheus, Grafana, alerts, infrastructure, GPU, Loki
  platforms: Claude, ChatGPT, Gemini
---

# Monitoring & Observability

## When to use this skill

- **Deploying the monitoring stack**: Setting up Prometheus/Grafana/Loki on bare metal or Docker
- **Before Production Deployment**: Essential monitoring system setup
- **Hardware/GPU Monitoring**: AMD or NVIDIA GPU metrics via node_exporter textfile collector
- **Performance Issues**: Identify bottlenecks
- **Incident Response**: Quick root cause identification
- **SLA Compliance**: Track availability/response times

## Instructions

### Step 0: Deploy the Monitoring Stack (Docker Compose)

Deploy Prometheus, Grafana, and Loki on any Docker host. This provides the collection infrastructure before you instrument anything.

**Directory layout**:
```
monitoring/
├── docker-compose.yml
├── prometheus/
│   └── prometheus.yml
├── loki/
│   └── loki-config.yml
└── grafana/
    └── provisioning/
        └── datasources/
            └── datasource.yml
```

**Key choices**:
- Map Prometheus container port 9090 to a host port that doesn't conflict (check with `ss -tlnp | grep 909` first — many hosts run Cockpit on 9090, Transmission on 9091)
- Grafana → host port 3000 (standard), Loki → host port 3100
- Pre-provision Grafana datasources so dashboards work immediately
- Use named Docker volumes for data persistence

**docker-compose.yml** (see `references/docker-compose-monitoring-stack.yml` in this skill for the full file).

Run on the target:
```bash
docker compose up -d
# Verify:
curl -s http://localhost:9092/-/healthy      # Prometheus → 200
curl -s http://localhost:3000/login           # Grafana → 200
curl -s http://localhost:3100/ready           # Loki → "ready"
```

**PITFALL — Loki v3 removed boltdb_shipper**: Loki `latest` is now v3.x, which removed the `boltdb-shipper` storage backend. Using the old config produces:
```
field shared_store not found in type boltdb.IndexCfg
```
**Fix**: Use `tsdb` store with schema `v13` instead:
```yaml
schema_config:
  configs:
    - from: 2020-01-01
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h
```
See `references/loki-config-v3.yml` for the complete working config.

**PITFALL — Port conflicts on deployment target**: Always scan the target host before picking host ports:
```bash
ss -tlnp | grep -E '909[0-9]|3000|3100'
```
Common conflicts: Cockpit (9090), Transmission RPC (9091), existing Docker services. Remap freely — just remember the new port.

**PITFALL — Docker daemon may be inactive**: On Raspberry Pi / server installs, Docker is often installed but not enabled. Check with `systemctl status docker` and enable with:
```bash
sudo systemctl enable --now docker
```

**Grafana provisioning**:
```yaml
# datasource.yml — mount to /etc/grafana/provisioning/datasources/
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
```

### Hardware/GPU Monitoring (node_exporter textfile collector)

For GPU metrics (or any custom hardware stats), use the node_exporter `--collector.textfile.directory` flag. This avoids needing a separate exporter daemon.

**Setup steps**:
1. Create a textfile collector directory: `sudo mkdir -p /var/lib/node_exporter/textfile_collector`
2. Update node_exporter systemd service to add the flag:
   ```
   ExecStart=/usr/local/bin/node_exporter --collector.textfile.directory=/var/lib/node_exporter/textfile_collector
   ```
3. Create a periodic script that writes `.prom` files to that directory
4. Add a cron job to run the script every minute

**Script pattern** — write metrics to a temp file, then atomically `mv` to the collector dir (prevents Prometheus from reading a partially-written file):
```bash
OUTPUT_DIR="${1:-/var/lib/node_exporter/textfile_collector}"
mkdir -p "$OUTPUT_DIR"
TMP=$(mktemp)
# Make readable by node_exporter (cron jobs run as root; node_exporter runs as unprivileged user)
chmod 644 "$TMP"
# Atomic write — prevents partial reads by Prometheus
mv "$TMP" "${OUTPUT_DIR}/amd_gpu.prom"
```

**AMD GPU script** — see `scripts/amd-gpu-metrics.sh` in this skill. Uses sysfs (`/sys/class/drm/card*/device/`) for GPU busy %, VRAM, temperature, fan RPM, power draw. No AMD driver tools required.

**NVIDIA GPU script** — see `scripts/nvidia-gpu-metrics.sh` in this skill. Uses `nvidia-smi --query-gpu=... --format=csv,noheader,nounits` for temperature, utilization, VRAM, power, fan speed.

**Cron entry** (run every minute):
```bash
* * * * * /usr/local/bin/gpu_metrics.sh /var/lib/node_exporter/textfile_collector
```

**PITFALL — NVIDIA [N/A] values break Prometheus textfile format**. On some GPUs (notably mobile MX150, GTX/RTX laptop GPUs), `nvidia-smi` reports `[N/A]` for power draw and fan speed when those sensors aren't exposed. `[N/A]` is not a valid Prometheus exposition value and causes the entire `.prom` file to be silently rejected — no GPU metrics appear at all. Fix: pipe the value through `grep -oE '^[0-9.]+' || echo 0` to replace non-numeric with 0. See `scripts/nvidia-gpu-metrics.sh` for the working pattern.

**PITFALL — Textfile collector files must be world-readable (644)**. The metrics scripts run via cron as root, so `mktemp` and `mv` produce files owned by root with 600 permissions. But `node_exporter` typically runs as an unprivileged user (`node_exporter`, `node_ex`, `nobody`). Result: `failed to open textfile data file: permission denied` with zero GPU data. Fix: always `chmod 644 "$TMP"` before `mv` to the collector directory. Both scripts in this skill now include this.

**PITFALL — Duplicate metric definitions from stale `.prom` files**: The textfile collector reads ALL `.prom` files in the directory. If you rename a script's output file, the old name's file is still read and can cause duplicate-metric errors. Clean up stale files when changing the output filename.

**Verification**:
```bash
# Check the metrics file was created and has correct permissions
ls -la /var/lib/node_exporter/textfile_collector/
# Restart node_exporter and check it's running with the flag
sudo systemctl restart node_exporter
journalctl -u node_exporter --no-pager -l | grep textfile
```

The metrics appear under the `node` job in Prometheus at the `/metrics` endpoint, with other node_exporter metrics.

### Multi-Machine Log Shipping (Promtail → Loki)

Ship system logs from multiple machines to a central Loki instance. Works across Ubuntu and Debian.

**Install** on each machine via the Grafana APT repo:
```bash
wget -q -O - https://apt.grafana.com/gpg.key | gpg --dearmor -o /etc/apt/keyrings/grafana.gpg
echo 'deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://apt.grafana.com stable main' > /etc/apt/sources.list.d/grafana.list
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y promtail
```

**Config** (`/etc/promtail/config.yml` — the apt-installed service reads `config.yml`, NOT `promtail-config.yaml`):
```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0
positions:
  filename: /var/lib/promtail/positions.yaml
clients:
  - url: http://<LOKI_IP>:3100/loki/api/v1/push
scrape_configs:
  - job_name: system
    static_configs:
      - targets: [localhost]
        labels:
          job: varlogs
          host: "<MACHINE_NAME>"
          __path__: /var/log/syslog
```

**PITFALL — Log file path differs by distro**:
| Distro | Path |
|--------|------|
| Ubuntu | `/var/log/syslog` |
| Debian (Pi, etc.) | `/var/log/messages` |
| systemd-only | Use `journal` input (below) |

**For systems where traditional syslog is absent** (empty file, or file doesn't exist), use journald:
```yaml
scrape_configs:
  - job_name: journal
    journal:
      max_age: 12h
      labels:
        job: varlogs
        host: "<MACHINE_NAME>"
    relabel_configs:
      - source_labels: ['__journal__hostname']
        target_label: 'host'
      - source_labels: ['__journal__systemd_unit']
        target_label: 'unit'
```

**PITFALL — Permission denied on syslog**. The default service runs as `promtail` user, but syslog is owned by `syslog:adm` (mode 640). Fix: run as root:
```bash
sed -i 's/User=promtail/User=root/' /etc/systemd/system/promtail.service
systemctl daemon-reload && systemctl restart promtail
```

**PITFALL — Wrong config path**. Check what the service expects:
```bash
grep ExecStart /etc/systemd/system/promtail.service
```
If it points to `/etc/promtail/config.yml`, copy your config there.

**Verify** logs are flowing from each machine:
```bash
curl -s 'http://<LOKI_IP>:3100/loki/api/v1/label/host/values' | python3 -c 'import sys,json; print(json.load(sys.stdin).get("data",[]))'
```

### Provisioned Grafana Dashboard

The skill reference `references/infrastructure-dashboard.json` contains a full multi-machine infrastructure dashboard covering all key metrics — CPU, RAM, load, disk, GPU (AMD + NVIDIA), and error logs from Loki. Deploy to Grafana's provisioning directory and restart.

**PITFALL — Non-default datasource panels need explicit `datasource` in the dashboard JSON**. If a panel (e.g. the Loki logs panel) doesn't specify a datasource, Grafana defaults to the default datasource (Prometheus). A LogQL query hitting Prometheus silently returns no data — no error, no logs, just blank panels. Fix: every panel and every target using a non-default datasource MUST include the datasource reference:

```json
{
  "panels": [{
    "title": "Error Logs",
    "type": "logs",
    "datasource": {"type": "loki", "uid": "P8E80F9AEF21F6940"},
    "targets": [{
      "expr": "{job=\"varlogs\"} |=~ \"(?i)error\"",
      "datasource": {"type": "loki", "uid": "P8E80F9AEF21F6940"}
    }]
  }]
}
```

(The Prometheus panels DON'T need this because Prometheus is `isDefault: true`.)

### CPU Temperature Queries

For infrastructure dashboards covering heterogeneous machines (Intel, AMD, Raspberry Pi), use `node_thermal_zone_temp` — it provides cleaner labels than `node_hwmon_temp_celsius`:

| Architecture | Query | Example values |
|-------------|-------|---------------|
| Intel/AMD x86 | `node_thermal_zone_temp{type="x86_pkg_temp"}` | 51°C (kubuntux), 55°C (macuntu) |
| Raspberry Pi | `node_thermal_zone_temp{type="cpu-thermal"}` | 57°C (rabuntu) |

These two queries in separate panel targets cover all 4 machines in a typical fleet. The `x86_pkg_temp` query returns one line per Intel/AMD host; `cpu-thermal` returns one for the Pi.

### Step 1: Metrics Collection (Prometheus)

**Application Instrumentation** (Node.js):
```typescript
import express from 'express';
import promClient from 'prom-client';

const app = express();

// Default metrics (CPU, Memory, etc.)
promClient.collectDefaultMetrics();

// Custom metrics
const httpRequestDuration = new promClient.Histogram({
  name: 'http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  labelNames: ['method', 'route', 'status_code']
});

const httpRequestTotal = new promClient.Counter({
  name: 'http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['method', 'route', 'status_code']
});

// Middleware to track requests
app.use((req, res, next) => {
  const start = Date.now();

  res.on('finish', () => {
    const duration = (Date.now() - start) / 1000;
    const labels = {
      method: req.method,
      route: req.route?.path || req.path,
      status_code: res.statusCode
    };

    httpRequestDuration.observe(labels, duration);
    httpRequestTotal.inc(labels);
  });

  next();
});

// Metrics endpoint
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', promClient.register.contentType);
  res.end(await promClient.register.metrics());
});

app.listen(3000);
```

**prometheus.yml**:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'my-app'
    static_configs:
      - targets: ['localhost:3000']
    metrics_path: '/metrics'

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['localhost:9093']

rule_files:
  - 'alert_rules.yml'
```

### Step 2: Alert Rules

**alert_rules.yml**:
```yaml
groups:
  - name: application_alerts
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          (
            sum(rate(http_requests_total{status_code=~"5.."}[5m]))
            /
            sum(rate(http_requests_total[5m]))
          ) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }}% (threshold: 5%)"

      # Slow response time
      - alert: SlowResponseTime
        expr: |
          histogram_quantile(0.95,
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
          ) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Slow response time"
          description: "95th percentile is {{ $value }}s"

      # Pod down
      - alert: PodDown
        expr: up{job="my-app"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Pod is down"
          description: "{{ $labels.instance }} has been down for more than 2 minutes"

      # High memory usage
      - alert: HighMemoryUsage
        expr: |
          (
            node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes
          ) / node_memory_MemTotal_bytes > 0.90
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value }}%"
```

### Step 3: Log Aggregation (Structured Logging)

**Winston (Node.js)**:
```typescript
import winston from 'winston';

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: {
    service: 'my-app',
    environment: process.env.NODE_ENV
  },
  transports: [
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.simple()
      )
    }),
    new winston.transports.File({
      filename: 'logs/error.log',
      level: 'error'
    }),
    new winston.transports.File({
      filename: 'logs/combined.log'
    })
  ]
});

// Usage
logger.info('User logged in', { userId: '123', ip: '1.2.3.4' });
logger.error('Database connection failed', { error: err.message, stack: err.stack });

// Express middleware
app.use((req, res, next) => {
  logger.info('HTTP Request', {
    method: req.method,
    path: req.path,
    ip: req.ip,
    userAgent: req.get('user-agent')
  });
  next();
});
```

### Step 4: Grafana Dashboard

**dashboard.json** (example):
```json
{
  "dashboard": {
    "title": "Application Metrics",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{route}}"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status_code=~\"5..\"}[5m])",
            "legendFormat": "Errors"
          }
        ]
      },
      {
        "title": "Response Time (p95)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))"
          }
        ]
      },
      {
        "title": "CPU Usage",
        "type": "gauge",
        "targets": [
          {
            "expr": "rate(process_cpu_seconds_total[5m]) * 100"
          }
        ]
      }
    ]
  }
}
```

### Step 5: Health Checks

**Advanced Health Check**:
```typescript
interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  uptime: number;
  checks: {
    database: { status: string; latency?: number; error?: string };
    redis: { status: string; latency?: number };
    externalApi: { status: string; latency?: number };
  };
}

app.get('/health', async (req, res) => {
  const startTime = Date.now();
  const health: HealthStatus = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    checks: {
      database: { status: 'unknown' },
      redis: { status: 'unknown' },
      externalApi: { status: 'unknown' }
    }
  };

  // Database check
  try {
    const dbStart = Date.now();
    await db.raw('SELECT 1');
    health.checks.database = {
      status: 'healthy',
      latency: Date.now() - dbStart
    };
  } catch (error) {
    health.status = 'unhealthy';
    health.checks.database = {
      status: 'unhealthy',
      error: error.message
    };
  }

  // Redis check
  try {
    const redisStart = Date.now();
    await redis.ping();
    health.checks.redis = {
      status: 'healthy',
      latency: Date.now() - redisStart
    };
  } catch (error) {
    health.status = 'degraded';
    health.checks.redis = { status: 'unhealthy' };
  }

  const statusCode = health.status === 'healthy' ? 200 : health.status === 'degraded' ? 200 : 503;
  res.status(statusCode).json(health);
});
```

## Output format

### Monitoring Dashboard Configuration

```
Golden Signals:
1. Latency (Response Time)
   - P50, P95, P99 percentiles
   - Per API endpoint

2. Traffic (Request Volume)
   - Requests per second
   - Per endpoint, per status code

3. Errors (Error Rate)
   - 5xx error rate
   - 4xx error rate
   - Per error type

4. Saturation (Resource Utilization)
   - CPU usage
   - Memory usage
   - Disk I/O
   - Network bandwidth
```

## Constraints

### Required Rules (MUST)

1. **Structured Logging**: JSON format logs
2. **Metric Labels**: Maintain uniqueness (be careful of high cardinality)
3. **Prevent Alert Fatigue**: Only critical alerts

### Prohibited (MUST NOT)

1. **Do Not Log Sensitive Data**: Never log passwords, API keys
2. **Excessive Metrics**: Unnecessary metrics waste resources

## Best practices

1. **Define SLO**: Clearly define Service Level Objectives
2. **Write Runbooks**: Document response procedures per alert
3. **Dashboards**: Customize dashboards as needed per team

## References

- [Prometheus](https://prometheus.io/)
- [Grafana](https://grafana.com/)
- [Google SRE Book](https://sre.google/books/)
- `references/docker-compose-monitoring-stack.yml` — full Docker Compose file for Prometheus/Grafana/Loki stack
- `references/loki-config-v3.yml` — working Loki v3 config (tsdb schema v13)
- `references/grafana-datasource-provisioning.yml` — datasource provisioning YAML
- `references/infrastructure-dashboard.json` — full multi-machine dashboard (CPU, RAM, disk, GPU, error logs)
- `scripts/amd-gpu-metrics.sh` — AMD GPU metrics via sysfs
- `scripts/nvidia-gpu-metrics.sh` — NVIDIA GPU metrics via nvidia-smi

## Metadata

### Version
- **Current Version**: 1.2.0
- **Last Updated**: 2026-07-07
- **Compatible Platforms**: Claude, ChatGPT, Gemini

### Related Skills
- [deployment](../deployment/SKILL.md): Monitoring alongside deployment
- [security](../security/SKILL.md): Security event monitoring

### Tags
`#monitoring` `#observability` `#Prometheus` `#Grafana` `#logging` `#metrics` `#infrastructure` `#GPU` `#Loki`

## Examples

### Example 1: Deploy on a Raspberry Pi / server via Docker Compose
```
mkdir -p monitoring/{prometheus,loki,grafana/provisioning/datasources}
# Write docker-compose.yml, prometheus.yml, loki-config-v3.yml, datasource.yml
scp monitoring/* rabuntu@host:/srv/monitoring
ssh rabuntu@host 'cd /srv/monitoring && docker compose up -d'
```

### Example 2: Add GPU monitoring to a host
See `scripts/amd-gpu-metrics.sh` or `scripts/nvidia-gpu-metrics.sh` in this skill.
