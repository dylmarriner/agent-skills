# Case: Computer crash from duplicate llama-server Docker containers — qwen3:4b on RX 580

## Symptoms

- Screen freezes, display server dies (SDDM restart)
- System partially responsive (ssh still works) but desktop is dead
- GPU errors in kernel logs before display death
- No reboot — just display server crash

## Environment

- **Host:** Linux 6.8.0-124-generic, HP Pavilion (kubuntux)
- **GPU:** AMD RX 580 (Ellesmere, 8GB VRAM)
- **Model:** qwen3:4b (4-bit quant, ~2.5GB weights)
- **Backend:** llama-server via Docker containers
- **Compose:** `~/synapse-memory/docker-compose.yml` — single llama-server service defined
- **Memory:** 15GB RAM + 23GB swap

## What was happening

**3 separate llama-server processes**, all loading the same qwen3:4b model:

| Process | Owner | Port | Context | GPU | Source |
|---------|-------|------|---------|-----|--------|
| ollama llama-server | ollama | 127.0.0.1:40349 | 2048 | None | Systemd ollama service |
| root llama-server | root | 0.0.0.0:11434 | **8192** | Vulkan0 | Docker `nexus-llama-server-1` |
| root llama-server | root | 0.0.0.0:11434 | 2048 | Vulkan0 | Docker `llama-server` (orphan) |

The duplicate `llama-server` container was created outside compose (manual `docker run`) and had `restart: unless-stopped`, so killing the process just respawned it.

## Crash cascade

```
16:36 — GPU VM fault (Chrome) — first sign of VRAM pressure
16:36 — ring gfx timeout, soft recovered — temporary fix
16:39 — llama-server blocked for 122+ seconds — memory/thrashing
16:53 — ring comp_1.1.1 timeout (llama-server PID 2971984) — GPU compute crash
16:53 — Failed to get VBLANK! — display pipeline dead
16:53 — Failed to initialize parser -125 — GPU reset failed
16:53 — sddm-helper + xdg-desktop-portal-gtk fail — desktop dies
```

Root cause: **3 concurrent GPU consumers** (2 Docker llama-servers + Chrome) each allocating VRAM on the same 8GB card. The duplicate container's model weights + its 8192-context KV cache pushed past 8GB.

## System state during crash

- RAM: 15GB used / 15GB total (6.5GB available after cleanup)
- Swap: 9GB used / 23GB total
- 5 pending bad sectors on `/dev/sdc` (smartctl)
- Load average: ~2-3 on 8-core system

## Fix

```bash
# Identify duplicate
docker ps --format '{{.Names}} {{.Image}} {{.Status}}'

# Kill and remove duplicate
docker stop llama-server
docker rm llama-server

# Verify canonical compose service
docker inspect nexus-llama-server-1 --format '{{json .Config.Labels}}' | grep project.config_files
# → /home/kubuntux/synapse-memory/docker-compose.yml

# Result: 15GB → 9.1GB RAM used, swap 9GB → 6.4GB
```

## Lessons

- `docker ps` doesn't show port mappings for host-network containers — use `docker inspect` for full config
- `restart: unless-stopped` containers need explicit `docker stop + docker rm`, not just `kill`
- Multiple `--device Vulkan0` containers each get their own VRAM allocation — model weights aren't shared
- ollama's systemd-managed llama-server and Docker llama-servers are independent — they don't coordinate GPU usage
- `--no-mmap` holds model in both system RAM and VRAM simultaneously
- RX 580 with `-c 8192` on qwen3:4b works solo (~5-6GB VRAM) but fails with any other GPU consumer
