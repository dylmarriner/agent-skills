---
name: server-management
description: Unified management for your personal server fleet — check status, run commands, monitor health across all machines. Use when managing kubuntux, macuntu, cloud server, or this Pi.
author: custom-built
version: 1.0.0
triggers:
  - "check server"
  - "run on"
  - "server status"
  - "fleet status"
  - "ssh to"
---

# Server Management

Unified control for your personal server fleet.

## Fleet Overview

| Host | Tailscale IP | Access | Role | Specs |
|------|-------------|--------|------|-------|
| **pi5-deflab** (this Pi) | 100.68.0.96 | local | Main node, Docker stack | ARM64, 8GB RAM |
| **kubuntux** | 100.93.75.87 | `root@kubuntux-to-be-filled-by-o-e-m` | Docker + DB | x86_64, 15GB, 8c |
| **macuntu** | 100.75.23.127 | `macuntu@100.75.23.127` | Desktop | x86_64, 7.7GB, 4c |
| **cloud** | 100.102.4.39 | `root@100.102.4.39` | Cloud VPS | x86_64, 30GB, 16c |

## Quick Commands

### Fleet Status
```bash
# Check all servers at once
bash <workspace>/skills/server-management/scripts/fleet-status.sh
```

### SSH Aliases
```bash
alias skub="ssh root@kubuntux-to-be-filled-by-o-e-m.tail2c15c8.ts.net"
alias smac="ssh -i ~/.ssh/id_ed25519 macuntu@100.75.23.127"
alias scloud="ssh -i ~/.ssh/id_ed25519 root@100.102.4.39"
```

### Per-Server Tasks

**Kubuntux:**
```bash
# General
skub "htop"                              # Live resource monitor
skub "docker ps -a"                       # List containers
skub "systemctl status postgresql"        # PostgreSQL status
skub "journalctl -u docker -n 20 --no-pager"  # Docker logs
skub "df -h"                              # Disk usage
skub "free -h && uptime"                  # Memory + uptime

# PostgreSQL
skub "su - postgres -c 'psql -c \"SELECT * FROM pg_stat_activity;\"'"
skub "pg_lsclusters"                      # List DB clusters

# Redis
skub "redis-cli ping"                     # Check if Redis is alive
skub "redis-cli info memory"              # Memory usage
```

**Macuntu:**
```bash
smac "uptime && free -h && df -h"         # Quick health check
smac "ps aux --sort=-%mem | head -10"     # Top processes
smac "ip addr"                            # Network info
smac "journalctl -p err -b"               # Boot errors
```

**Cloud Server:**
```bash
scloud "htop"                              # Live monitor
scloud "df -h && free -h && uptime"        # Quick health
scloud "netstat -tlnp"                     # Open ports
scloud "apt list --upgradable"             # Pending updates
```

### Docker Management (This Pi)
```bash
cd /srv/stack && docker compose ps        # Stack status
cd /srv/stack && docker compose logs --tail=20  # Recent logs
docker system df                           # Docker disk usage
docker volume ls                           # List volumes
```

## SSH Troubleshooting & User Resolution

If standard SSH fails with `failed to look up local user`, explicitly prefix the command with the known correct username for the remote host.

- Use `ssh <user>@<ip>`: The agent should verify the correct user (often not the local `lin` user) on the remote machine if the connection fails initially.
- Verify user: Use `ssh <ip> "whoami"` to confirm the remote username before running long commands.
- Check permissions: Ensure your SSH key is authorized for the specific user on the target machine.

# Server Specifics
- **kubuntux**: Current tailscale IP `100.93.75.87`. Note: Avoid generic `root@` connections if a specific user (e.g., the user's name) is required.


### Update & Upgrade
```bash
# Kubuntux
skub "apt update && apt upgrade -y && apt autoremove -y"

# Cloud server
scloud "apt update && apt upgrade -y && apt autoremove -y"

# Macuntu (via SSH)
smac "apt update && apt upgrade -y && apt autoremove -y"

# This Pi
sudo apt update && sudo apt upgrade -y && sudo apt autoremove -y
```

### Reboot Management
```bash
# Shutdown a server (with warning)
skub "shutdown -r +5 'Rebooting for updates — save your work!'"

# Cancel reboot
skub "shutdown -c"
```

### Copy Files Between Servers
```bash
# Pi → Kubuntux
scp /path/to/file root@kubuntux-to-be-filled-by-o-e-m.tail2c15c8.ts.net:/path/to/dest

# Kubuntux → Pi
scp root@kubuntux-to-be-filled-by-o-e-m.tail2c15c8.ts.net:/path/to/file /path/to/dest

# Via macuntu to cloud (macuntu has both keys)
scp -oProxyJump=macuntu@100.75.23.127 /local/file root@100.102.4.39:/path/
```

## Troubleshooting

### Connection Failed
- Check if target is on tailnet: `tailscale ping <hostname>`
- Verify SSH key works: `ssh -v root@<ip>` 
- Check if target is online: `tailscale status | grep <hostname>`

### Server Unreachable
- Try pinging via tailscale: `tailscale ping <hostname>`
- If offline, check last seen time: `tailscale status`
- For critical servers, consider a wake-on-LAN schedule
