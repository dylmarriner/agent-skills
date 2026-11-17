# Crash Diagnosis — LLM Inference GPU VRAM Overcommit

How to diagnose a Linux desktop crash caused by AI inference processes (llama-server, ollama) overcommitting GPU VRAM, then fix it.

## Symptoms

- System freezes or display server (SDDM/GDM) dies mid-inference
- GPU driver resets — screen goes blank then display manager restarts
- Chromium/Chrome GPU faults alongside inference processes
- Machine is responsive to SSH/Ping but display is dead

## Quick Triage

```bash
# 1. Uptime — did the system recently crash/reboot?
uptime

# 2. Memory pressure
free -h                    # Total RAM used vs available
swapon --show              # Swap usage

# 3. Kernel errors — GPU ring timeouts, hung tasks
sudo dmesg -T | grep -iE 'amdgpu|hung_task|ring.*timeout|VBLANK|parser -125|VM fault'

# 4. Check for multiple llama-server / inference processes
ps aux | grep -E 'llama-server|llama\.cpp' | grep -v grep

# 5. Check Docker containers running inference
docker ps --format '{{.Names}} {{.Image}} {{.Status}}'

# 6. Check disk health (secondary — can cause freezes too)
sudo smartctl -a /dev/sdX | grep -E 'Pending|Reallocated|Uncorrectable'
```

## Key Error Signatures

### AMD GPU (amdgpu) VRAM exhaustion
```
amdgpu: ring comp_1.1.1 timeout, signaled seq=X, emitted seq=Y
amdgpu: ring gfx timeout, but soft recovered
amdgpu:   Process llama-server pid NNNN thread llama-server pid NNNN
amdgpu: [drm] *ERROR* Failed to get VBLANK!
amdgpu: [drm] *ERROR* Failed to initialize parser -125!
amdgpu: VM fault at page XXXX, read from 'TC3'
```

**What it means:** The GPU compute ring timed out because a process couldn't get VRAM. The driver resets → VBLANK fails → parser fails → display output dies → DM restarts → user sees "crash".

### Hung tasks (system RAM pressure)
```
INFO: task llama-server:NNNN blocked for more than 122 seconds.
```
**What it means:** System RAM exhausted, process can't get memory pages. Common with `--no-mmap` (model fully in RAM).

## VRAM Budget — 8GB card (RX 580)

| Model | Weights (Q4) | KV at 2048 | KV at 4096 | KV at 8192 |
|---|---|---|---|---|
| Qwen3:4b | ~2.5GB | ~0.5GB | ~1GB | ~3GB |
| Llama 3.1 8B | ~5GB | ~0.5GB | ~1GB | ~3GB |
| Mistral 7B | ~4GB | ~0.5GB | ~1GB | ~3GB |

**Killers:** multiple processes loading same model on same GPU (each gets own VRAM copy), Chrome GPU acceleration (+0.5-2GB), `--no-mmap` duplicates model in system RAM.

## Fix Patterns

### 1. Kill duplicate inference processes
```bash
docker ps | grep llama
docker stop <container> && docker rm <container>
kill <pid>          # SIGTERM
kill -9 <pid>       # SIGKILL if stuck in D state
```

### 2. Check for auto-restart loops
Processes respawning = something is managing them:
```bash
docker inspect <container> | grep RestartPolicy
systemctl list-units --type=service | grep -E 'llama|ollama'
ls /etc/systemd/system/<service>.service.d/
```

### 3. Reduce context size — single highest-impact VRAM fix
```
-c 8192  →  -c 4096    # saves ~1-2GB VRAM
-c 4096  →  -c 2048    # saves ~0.5-1GB VRAM
```

### 4. Enable flash-attention
```
--flash-attn on
```

### 5. Free GPU from other apps
```bash
# Chrome GPU processes
ps aux | grep chrome | grep -i gpu
google-chrome --disable-gpu
```

### 6. Check compose file for the real config
```bash
cat docker-compose.yml                # single source of truth
docker compose up -d <service>        # recreate after patching args
```

## Common Cause Patterns

| Pattern | Detection | Fix |
|---|---|---|
| Two Docker containers, same GPU, same model | `docker ps` shows 2 llama containers | Stop + remove duplicate |
| Docker + systemd both running | `docker ps` + `ps aux` | Stop one source |
| Manual `docker run` alongside compose | 1 service in compose but 2 containers | `docker rm` the orphan |
| Context too large for VRAM | `dmesg` shows ring timeouts | Reduce `-c` or enable flash-attn |
| Chrome using GPU during inference | `ps aux` shows chrome:gpu | `--disable-gpu` or close Chrome |
| Bad disk sectors causing freezes | `smartctl` Pending_Sector > 0 | Replace disk, backup data |
