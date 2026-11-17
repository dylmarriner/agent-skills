---
name: backup-system
description: Automated backup system for your Docker stack, configs, and databases. Runs locally and across your fleet.
author: custom-built
version: 1.0.0
triggers:
  - "backup"
  - "backup docker"
  - "backup volumes"
  - "backup config"
  - "snapshot"
  - "restore"
---

# Backup System

Automated backup for your entire stack — Docker volumes, configs, databases, and server configs.

## What Gets Backed Up

| Source | Location | Method |
|--------|----------|--------|
| Docker Volumes | `prometheus-data`, `grafana-data`, `loki-data`, `portainer_data` | Volume export |
| Docker Config | `/srv/stack/` (compose.yaml + configs) | Tarball + git |
| Pi Config | `/etc/`, SSH keys, crontabs | Tarball |
| PostgreSQL (kubuntux) | All databases | `pg_dump` via SSH |
| Redis (kubuntux) | RDB dump | `redis-cli save` + copy |
| SSH Keys | `~/.ssh/` | Tarball |

## Quick Commands

### One-Button Backup (Everything)
```bash
bash <workspace>/skills/backup-system/scripts/backup-all.sh
```
Backs up everything to `/home/rabuntu/backups/<date>/`

### Docker Volume Backups
```bash
# Single volume
docker run --rm -v prometheus-data:/source -v /home/rabuntu/backups:/dest alpine \
  tar czf /dest/prometheus-data-$(date +%Y%m%d).tar.gz -C /source .

# All volumes
for vol in $(docker volume ls -q | grep -E "prometheus|grafana|loki|portainer"); do
  docker run --rm -v $vol:/source -v /home/rabuntu/backups:/dest alpine \
    tar czf /dest/$vol-$(date +%Y%m%d).tar.gz -C /source .
done
```

### Config Backup (Git Tracked)
```bash
# Initialize git tracking
cd /srv/stack && git init && git add -A && git commit -m "Initial stack config"

# Backup with timestamp
cd /srv/stack && git add -A && git commit -m "Config snapshot $(date +%Y%m%d-%H%M)"
cd /home/rabuntu/backups && git clone /srv/stack config-$(date +%Y%m%d)
tar czf config-$(date +%Y%m%d).tar.gz config-$(date +%Y%m%d)
```

### PostgreSQL Backup (Kubuntux)
```bash
# Single DB
ssh root@kubuntux-to-be-filled-by-o-e-m.tail2c15c8.ts.net \
  "pg_dump -U postgres -d mydb --file=/tmp/mydb-$(date +%Y%m%d).sql"

# Copy to Pi
scp root@kubuntux-to-be-filled-by-o-e-m.tail2c15c8.ts.net:/tmp/mydb-*.sql /home/rabuntu/backups/

# All databases
ssh root@kubuntux-to-be-filled-by-o-e-m.tail2c15c8.ts.net \
  "su - postgres -c 'pg_dumpall --file=/tmp/full-backup-$(date +%Y%m%d).sql'"
scp root@kubuntux-to-be-filled-by-o-e-m.tail2c15c8.ts.net:/tmp/full-backup-*.sql /home/rabuntu/backups/
```

### Server Config Backup
```bash
# Kubuntux config
ssh root@kubuntux-to-be-filled-by-o-e-m.tail2c15c8.ts.net \
  "tar czf /tmp/kubuntux-etc-$(date +%Y%m%d).tar.gz /etc/nginx /etc/postgresql /etc/redis /etc/ssh"
scp root@kubuntux-to-be-filled-by-o-e-m.tail2c15c8.ts.net:/tmp/kubuntux-*.tar.gz /home/rabuntu/backups/

# Cloud server config
ssh -i ~/.ssh/id_ed25519 root@100.102.4.39 \
  "tar czf /tmp/cloud-etc-$(date +%Y%m%d).tar.gz /etc/ssh /etc/apt 2>/dev/null"
scp -i ~/.ssh/id_ed25519 root@100.102.4.39:/tmp/cloud-*.tar.gz /home/rabuntu/backups/
```

## Restore Instructions

### Restore Docker Volume
```bash
# List available backups
ls /home/rabuntu/backups/*.tar.gz

# Restore a volume
docker run --rm -v prometheus-data:/dest -v /home/rabuntu/backups:/source alpine \
  tar xzf /source/prometheus-data-20260501.tar.gz -C /dest
```

### Restore PostgreSQL (Kubuntux)
```bash
scp /home/rabuntu/backups/full-backup-*.sql \
  root@kubuntux-to-be-filled-by-o-e-m.tail2c15c8.ts.net:/tmp/
ssh root@kubuntux-to-be-filled-by-o-e-m.tail2c15c8.ts.net \
  "su - postgres -c 'psql -f /tmp/full-backup-*.sql postgres'"
```

### Restore Configs
```bash
# Extract stack config
tar xzf /home/rabuntu/backups/config-*.tar.gz
cp -r config-*/compose.yaml /srv/stack/
```

## Retention Policy

| Type | Keep | 
|------|------|
| Daily backups | 7 days |
| Weekly backups | 4 weeks |
| Monthly backups | 3 months |
| DB dumps | 14 days |

Add this cron job for automated cleanup:
```bash
# Remove backups older than 30 days
find /home/rabuntu/backups -name "*.tar.gz" -mtime +30 -delete
find /home/rabuntu/backups -name "*.sql" -mtime +14 -delete
```
