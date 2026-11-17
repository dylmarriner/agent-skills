---
name: runpod-model-deploy
description: "Deploy open-weight GGUF models (especially uncensored/abliterated variants) on cloud GPU VMs (RunPod, Linode, Vast.ai, Lambda, etc.) as OpenAI-compatible API endpoints and wire them to Hermes as custom providers."
version: 1.1.0
platforms: [linux, macos]
---

# Cloud GPU Model Deployment

Deploy large GGUF models on cloud GPU VMs as OpenAI-compatible API endpoints and connect them to Hermes as custom providers. Covers RunPod (primary), Linode GPU, and a generic pattern for any provider that exposes raw VMs with NVIDIA GPUs (Vast.ai, Lambda Labs, CoreWeave, etc.).

The class of work: provision GPU VM → install CUDA + llama.cpp → download GGUF → serve OpenAI-compatible API → wire as Hermes custom provider. Provider-specific quirks are below; the rest of the workflow is identical across clouds.

## When to Pick Which Provider

| Provider | Best for | Hourly cost (24GB+ GPU) | Billing | Reachability |
|----------|----------|-------------------------|---------|--------------|
| RunPod | Fastest deploy, biggest GPU selection (A100, H100, B200) | $0.44–$4+ | Per-second, can stop/resume | Public IP per pod |
| Linode GPU | Predictable pricing, regional choice (SG, Tokyo, etc.), Tailscale-friendly | $0.52–$3.57 | Hourly, easy to attach to tailnet | Public IP per VM |
| Vast.ai | Cheapest spot rates, community bidding | $0.20+ | Spot (can be evicted) | Public IP per instance |
| Lambda Labs | Reserved capacity, research-friendly | $0.50+ | Hourly, persistent hosts | Public IP per VM |

Default to RunPod if you don't have a reason not to. Pick Linode when you need: a specific region (Singapore, Tokyo), persistent monthly billing, or seamless Tailscale integration. Pick Vast.ai only for non-critical short jobs.

## Common Workflow (applies to every cloud)

1. **Pick the model and quant** — find a GGUF on HuggingFace. Default to Q4_K_M for ≤13B, Q5_K_M for 13–30B, Q4_K_M for 30B+ unless the user asks for higher quality.
2. **Size the GPU** — model weights + KV cache at the target context + 2 GB overhead. Use the "KV Cache Math" section below.
3. **Provision the VM/pod** with a publicly reachable IP and SSH access.
4. **Install CUDA driver + llama.cpp** — Ubuntu 22.04/24.04 LTS, install NVIDIA driver, then either `pip install llama-cpp-python` (slow if compiling) or grab the prebuilt `llama.cpp:full-cuda` binary.
5. **Download the GGUF** from HuggingFace (use `huggingface-cli` or direct wget).
6. **Start llama-server** with the right `-c` (context), `--cache-type-k/v q8_0` (memory), `-ngl -1` (all layers on GPU).
7. **Wire to Hermes** as a custom provider pointing at the VM's public IP + port 8080 (or whatever llama-server is on).
8. **Set up an idle shutdown** so an hourly-billed VM doesn't run away. A simple cron or systemd timer that powers off the VM after N hours of zero traffic is enough.

## Linode GPU Deployment

Linode's GPU line uses a per-second billed model with hourly display prices. GPU types in the `g2-gpu-*` class.

### GPU Type IDs (g2 generation)

| ID | GPUs | vCPU | RAM | Disk | $/hr |
|----|------|------|-----|------|------|
| `g2-gpu-rtx4000a1-s` | 1× RTX 4000 Ada | 4 | 16 GB | 512 GB | 0.52 |
| `g2-gpu-rtx4000a1-m` | 1× RTX 4000 Ada | 8 | 32 GB | 512 GB | 0.67 |
| `g2-gpu-rtx4000a1-l` | 1× RTX 4000 Ada | 16 | 64 GB | 512 GB | 0.96 |
| `g2-gpu-rtx4000a1-xl` | 1× RTX 4000 Ada | 32 | 128 GB | 512 GB | 1.53 |
| `g2-gpu-rtx4000a2-s` | 2× RTX 4000 Ada | 8 | 32 GB | 1 TB | 1.05 |
| `g2-gpu-rtx4000a2-m` | 2× RTX 4000 Ada | 16 | 64 GB | 1 TB | 1.34 |
| `g2-gpu-rtx4000a2-hs` | 2× RTX 4000 Ada | 16 | 64 GB | 2 TB | 1.49 |
| `g2-gpu-rtx4000a4-s` | 4× RTX 4000 Ada | 32 | 128 GB | 2 TB | 2.96 |
| `g2-gpu-rtx4000a4-m` | 4× RTX 4000 Ada | 48 | 196 GB | 2 TB | 3.57 |

The `g1-gpu-rtx6000-*` types (older Quadro RTX 6000) also exist at similar pricing for older-gen workloads.

### GPU-capable Regions

Only core sites with `GPU Linodes` in their capabilities list can host GPU VMs. Asia-Pacific: Singapore 2 (`sg-sin-2`), Jakarta (`id-cgk`), Tokyo 3 (`jp-tyo-3`), Osaka (`jp-osa`), Mumbai 2 (`in-bom-2`), Chennai (`in-maa`). Americas: Los Angeles, Miami, Seattle, Washington, Dallas, Atlanta, Chicago, Newark, Toronto. EMEA: London 2, Frankfurt 2, Paris 2, Amsterdam, Stockholm, Madrid, Milan.

### Create the Linode (via Linode MCP)
### CRITICAL: GPU plans are account-gated — request access BEFORE deploying

Linode blocks ALL `g2-gpu-*`/`g1-gpu-*` plans behind a per-account support
approval. `create_instance` returns HTTP 400 — *"A limit on your account is
preventing the deployment of the selected Linode plan. To request access to the
plan, please contact Support and provide the Linode plan name."* — until you open
a support ticket naming the plan + region. The VM is NOT created and you are NOT
billed. **Open the ticket first**, then deploy. Full transcript + ticket template
in `references/linode-gpu-deploy-session.md`.

### Create the Linode (via Linode MCP)

```mcp__linode__create_instance(
  label="mythos-sg-01",
  region="sg-sin-2",
  type="g2-gpu-rtx4000a2-m",
  image="linode/ubuntu22.04",
  root_pass="<generate-a-STRONG-24-char-random-one>",
  authorized_keys=["ssh-ed25519 AAAA...dylan"],
  booted=true,
  backups_enabled=false
)
```

**Tool name is `create_instance`, NOT `create_linode`.** If it isn't directly
invokable from your tool surface, load it with `tool_describe` first, then call
it through the generic `tool_call` wrapper with the full args dict.

**`root_pass` MUST meet strength rules** (7–128 chars incl. uppercase, lowercase,
numbers, AND special chars). A weak password like `admin` is rejected with a 400 —
always generate a strong one:

```bash
python3 -c "import secrets,string;p=''.join(secrets.choice(string.ascii_letters+string.digits+'!@#%^&*') for _ in range(28));print(p)"
```

**Always deploy an SSH key AND set a strong root password.** The password is a fallback for the API/Lish console; key auth is the primary path. Stash the generated password at `~/.hermes/sessions/linode_<label>_rootpw` (chmod 600) or show the user once. Note: the `patch`/`write_file` tools refuse to edit config.yaml, but `hermes config set mcp_servers.<name>.command "..."` (nested dotted keys) IS the sanctioned path to add MCP servers — see the Tailscale MCP note below and `references/linode-gpu-deploy-session.md`.

**Always confirm with the user before creating an hourly-billed VM.** $1.34/hr adds up fast if it gets left running.

### Linode Firewall

Linode's firewall rules attach to a Linode via `create_firewall` + `create_firewall_device`. Default-deny inbound, allow:
- 22/tcp from Tailscale 100.64.0.0/10 (and/or the user's home IP)
- The llama-server port (8080/tcp by default) from Tailscale 100.64.0.0/10 only

**Do not expose the inference port to the public internet.** The `llama-server` binary has no built-in auth. Tailscale-only exposure + a bearer token in the custom provider config is the safe default.

### Provisioning Script (run after SSH is up)

```bash
#!/bin/bash
set -e
# Update + CUDA + llama.cpp
apt update && apt -y upgrade
apt install -y build-essential git curl wget
# NVIDIA driver (Ubuntu 22.04 default for g2-gpu-*)
apt install -y nvidia-driver-535 nvidia-cuda-toolkit
# Or use the Linode-recommended: install from CUDA repo
# (apt's driver is older but stable for the g2 hardware)

# Prebuilt llama.cpp (faster than pip compile)
wget -q https://github.com/ggerganov/llama.cpp/releases/download/b<latest>/llama-<ver>-bin-linux-x64-cuda.zip
unzip llama-*-bin-linux-x64-cuda.zip -d /opt/llama
ln -sf /opt/llama/build/bin/llama-server /usr/local/bin/llama-server

# Pull the model
mkdir -p /opt/models
cd /opt/models
huggingface-cli download <org>/<model> <filename> --local-dir .

# systemd service
cat > /etc/systemd/system/llama.service <<'EOF'
[Unit]
Description=llama.cpp server
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/llama-server \
  -m /opt/models/<file>.gguf \
  --host 0.0.0.0 --port 8080 \
  -c 131072 \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  -ngl -1
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable --now llama
```

### Tailscale MCP server (read-only tailnet management)

If the user wants you to query/manage the tailnet from Hermes, add the read-only
`paulsmith/tailscale-mcp-server` Go binary. It exposes status/devices/IPs/ping via
the local `tailscale` CLI and cannot escalate beyond what your API key allows:

```bash
go install github.com/paulsmith/tailscale-mcp-server@latest   # needs go >= 1.23.6
# binary at $(go env GOPATH)/bin/tailscale-mcp-server
# prereq: tailscale CLI installed + authenticated on the host (tailscale status works)
```

Add it to Hermes config via the sanctioned nested-key path (the `patch`/`write_file`
tools are hard-blocked on config.yaml):

```bash
hermes config set mcp_servers.tailscale.command "/home/kubuntux/go/bin/tailscale-mcp-server"
hermes config set mcp_servers.tailscale.connect_timeout 30
hermes config set mcp_servers.tailscale.enabled true
grep -A4 '  tailscale:' ~/.hermes/config.yaml   # verify
```

Store the control-plane key at `~/.hermes/sessions/tailscale_api_key` (chmod 600),
never printed. Do NOT set `agent.cross_profile_soft_guard false` hoping to bypass —
the config-file write guard is hardcoded in the runtime, not a flag; use
`hermes config set` nested keys instead.

### Tailscale Auth Key for Join

The Tailscale **API key** (`tskey-api-...`, control plane) does NOT work as a join auth key. You need a separate `tskey-auth-...` key generated at https://login.tailscale.com/admin/settings/keys → "Generate auth key" with reusable=off, ephemeral=off. Store at `~/.hermes/sessions/tailscale_linode_auth` chmod 600.
```bash
# In the provisioning script, after CUDA:
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up --authkey=tskey-auth-XXXXX
```

Or as a systemd unit that runs once and is then disabled.

### Linode Idle Shutdown

Hourly billing means a forgotten VM is a costly one. Add a simple watchdog that powers off the VM after N hours idle:

```bash
# /usr/local/bin/idle-shutdown.sh — counts minutes with no inference traffic
# Run via cron every 5 min; if llama-server hasn't seen a request in 240 min, shutdown
*/5 * * * * root /usr/local/bin/idle-shutdown.sh
```

Better: have the user's local cron ping the VM every 15 min when in use, and let the watchdog shutdown when the pings stop.

### Tailscale-only Custom Provider

```bash
hermes config set agent.custom_providers '[{"name":"linode-mythos","api_key":"<bearer-token>","base_url":"http://<tailscale-ip>:8080/v1","api_mode":"chat_completions","models":["mythos-9b"]}]'
hermes config set model.default mythos-9b
hermes config set model.provider custom:linode-mythos
```

`<tailscale-ip>` is the 100.x.x.x address the linode gets after `tailscale up`, NOT the public IP. `<bearer-token>` is whatever the llama-server `--api-key` is set to (set it to a strong random; llama-server enforces it as a bearer token).

## See Also

- `references/dolphin-yi-34b-runpod-session.md` — full RunPod deployment walkthrough
- `references/qwen3.6-runpod-deployment.md` — YaRN 1M context on RunPod
- `references/linode-gpu-deploy-session.md` — Linode RTX 4000 Ada walkthrough (account gating, tool-call specifics, Tailscale MCP, staged secrets, idle watchdog)

## Common Use Cases

- Deploy abliterated/uncensored models on cloud GPUs
- Run models that don't fit on local hardware (30B+ parameter)
- Set up long-context inference (262K–1M tokens)
- Wire remote model endpoints into Hermes as custom providers

## Critical Pitfall: Port Health Check

**RunPod kills any pod that exposes an HTTP port (e.g. `8000/http`) but doesn't start serving on it within seconds.** This is NOT a script failure — RunPod terminates the container. Symptoms:

- Pod transitions RUNNING → EXITED in 1–5 seconds
- Status shows "Exited by Runpod"
- Same script works fine if the port isn't exposed

### Workaround A: Background listener (preferred)

Start a dummy HTTP server on the port FIRST, then do the real setup in background:

```bash
# dockerStartCmd (single line for RunPod UI or MCP):
python3 -m http.server 8000 --bind 0.0.0.0 &>/dev/null & sleep 3 && pip install -q huggingface-hub llama-cpp-python 2>/dev/null && python3 -c "from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='ORG/MODEL', filename='MODEL.gguf', local_dir='/workspace')" && pkill -f 'http.server 8000' 2>/dev/null && exec python3 -m llama_cpp.server --model /workspace/MODEL.gguf --host 0.0.0.0 --port 8000 --n_ctx 1000000 --rope_scaling_type yarn --rope_freq_scale 4.0 --cache_type_k q8_0 --cache_type_v q8_0 --n_gpu_layers -1
```

Key points:
- `python3 -m http.server 8000` starts listening immediately
- `sleep 3` gives RunPod's health check time to pass
- Setup runs after the check, then kills the dummy server
- `exec` replaces the python3 process with llama-server

### Workaround B: SSH deployment (more reliable for complex setups)

1. Create pod WITHOUT port 8000 — just `22/tcp`:
   ```json
   dockerStartCmd: ["python3", "-c", "import time; time.sleep(999999)"]
   ```
2. Pod stays alive (no HTTP port to health-check)
3. SCP the setup script + SSH in to run it:
   ```bash
   ssh -o StrictHostKeyChecking=no root@<POD_IP> 'bash -s' < /path/to/setup.sh
   ```
4. Once the server is running, use `mcp_runpod_update_pod` to add port 8000:
   ```bash
   # Via the RunPod API or MCP tools
   update_pod(pod_id, ports=["8000/http", "22/tcp"])
   ```

## Pre-built Docker Images

Avoid building llama.cpp from source on the pod (time-consuming, may timeout). Use pre-built images:

| Image | Has | Use Case |
|-------|-----|----------|
| `ghcr.io/ggerganov/llama.cpp:full-cuda` | llama-server + CUDA | GGUF models, YaRN scaling |
| `runpod/pytorch:*` | PyTorch + CUDA + pip | General ML, needs `pip install` for serving |
| `runpod/pytorch:latest` | Latest PyTorch stack | May point to Ubuntu 24.04 — verify `python3` availability |

**Image pitfalls:** Tags like `runpod/pytorch:2.4.0-py3.11-cuda12.4.0-devel-ubuntu22.04` (CUDA 12.4.0) may be pruned/unpublished. The API accepts unknown tags at creation time — the pod fails silently during container startup with `IMAGE_NOT_FOUND`. Always use images validated in RunPod docs or on Docker Hub. Known-valid tags from RunPod docs: `runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04`, `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404`, `runpod/pytorch:1.0.3-cu1281-torch291-ubuntu2404`.

The llama.cpp `full-cuda` image has `llama-server` in PATH — just wget the GGUF and run:
```bash
wget -q <GGUF_URL> -O /workspace/model.gguf
exec llama-server -m /workspace/model.gguf --host 0.0.0.0 --port 8000 -c 1000000 -ngl 99
```

## KV Cache Math for Context Length

For models with hybrid architecture (Gated DeltaNet + attention layers), the KV cache is much smaller than naive estimates:

**Qwen3.5/3.6-35B-A3B** (40 layers, only 10 attention layers, 2 KV heads, head_dim 256):
- KV cache per token: **20,480 bytes** (FP16) — vs ~98K for a standard 30B GQA model
- At 262K context: ~5.1 GB (FP16) / ~2.6 GB (Q8_0)
- At 1M context: ~20 GB (FP16) / ~10 GB (Q8_0)

**48GB VRAM budget for Q4_K_P (~23GB) + 1M context at Q8_0 (~10GB):**
| Item | Size |
|------|------|
| Q4_K_P weights | ~23 GB |
| KV cache at Q8_0 (1M) | ~10 GB |
| Overhead (activations, etc.) | ~2 GB |
| **Total** | **~35 GB** |
| **Headroom** | **~13 GB** |

Always use `--cache-type-k q8_0 --cache-type-v q8_0` or `cache_type_k='q8_0' cache_type_v='q8_0'` with llama.cpp to minimize KV cache memory.

See `references/dolphin-yi-34b-runpod-session.md` for a concrete deployment walkthrough with all the failure modes and fixes.

## YaRN Scaling for Long Context

To extend native context beyond the model's default (e.g., 262K → 1M):

**llama-server CLI:**
```bash
llama-server ... -c 1000000 --rope-scaling yarn --rope-scale 4.0
```
- `--rope-scale 4.0` = target / original = 1,000,000 / 262,144

**llama-cpp-python (Python server):**
```bash
python3 -m llama_cpp.server ... --n_ctx 1000000 --rope_scaling_type yarn --rope_freq_scale 4.0
```

## Hermes Custom Provider Wiring

After the RunPod pod is running on port 8000:

```bash
# Add the custom provider
hermes config set agent.custom_providers '[{"name":"runpod-qwen","api_key":"not-needed","base_url":"http://<POD_IP>:8000/v1","api_mode":"chat_completions","models":["qwen3.6-35b"]}]'

# Switch to it
hermes config set model.default qwen3.6-35b
hermes config set model.provider custom:runpod-qwen
hermes config set model.context_length 1000000
```

Replace `<POD_IP>` with the pod's public IP from the RunPod dashboard. The key is `not-needed` since llama.cpp server doesn't require authentication.

## Recommended Quants for 48GB GPUs

| Quant | Size | Quality vs BF16 | VRAM Used (at 262K) | VRAM Used (at 1M) |
|-------|------|-----------------|---------------------|-------------------|
| Q4_K_M | ~21 GB | ~98% | ~28 GB | ~33 GB |
| Q4_K_P | ~23 GB | ~99% | ~30 GB | ~35 GB |
| Q5_K_M | ~25 GB | ~99% | ~32 GB | ~37 GB |
| Q6_K | ~29 GB | ~99.5% | ~36 GB | ~41 GB |

Q4_K_P offers the best quality/size tradeoff for 48GB cards with 1M context.

## SSH Access Setup

When creating the pod via MCP tools, set the `PUBLIC_KEY` env var to match the SSH key on the deployment machine:

```json
"env": {
  "PUBLIC_KEY": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA..."
}
```

This auto-provisions SSH access. The pod user is `root`.

## MCP Tool GPU Type IDs

When using `mcp_runpod_create_pod`, the `gpuTypeIds` parameter requires exact string matches. Valid 48GB+ options:
- `NVIDIA A40` (48GB, Ampere)
- `NVIDIA RTX A6000` (48GB, Ampere)  
- `NVIDIA L40` (48GB, Ada Lovelace)
- `NVIDIA L40S` (48GB, Ada Lovelace)
- `NVIDIA RTX 6000 Ada Generation` (48GB, Ada Lovelace)

Pass multiple for fallback:
```json
"gpuTypeIds": ["NVIDIA A40","NVIDIA RTX A6000","NVIDIA L40","NVIDIA L40S","NVIDIA RTX 6000 Ada Generation"]
```

## Community vs Secure Cloud

| Type | Cost (48GB GPU) | Availability | Notes |
|------|-----------------|-------------|-------|
| COMMUNITY | $0.44–0.74/hr | Less reliable | Spot instances, outbid risk |
| SECURE | $0.44–0.86/hr | More reliable | On-demand, guaranteed uptime |

Set `"cloudType": "COMMUNITY"` or `"cloudType": "SECURE"` in `create_pod`.

## Pitfalls

1. **Port health check kills pods** — Always start a listener on the exposed port first (Workaround A) or omit the HTTP port and deploy via SSH (Workaround B).
2. **`dockerStartCmd` with env var scripts fails** — Multi-line scripts stored in env vars get corrupted by JSON escaping. Use single-line `&&` chains or the background listener pattern instead.
3. **`set -e` causes silent exits** — Any command failure triggers pod shutdown. Use `|| true` on non-critical steps or avoid `set -e` entirely in dockerStartCmd.
4. **`dockerStartCmd` replaces CMD, not ENTRYPOINT** — If the Docker image has an ENTRYPOINT, your command is passed as arguments to it. Use `["bash","-c","..."]` to override this.
5. **GGUF downloads take time** — A 21GB Q4_K_P GGUF downloads in 2–5 minutes on a fast pod. Make sure the container can stay alive during this (use background listener pattern).
6. **llama-cpp-python with CUDA compiles from source** — If no pre-built wheel exists for the CUDA version, `pip install` will compile from source (5–10 min). The `llama.cpp:full-cuda` Docker image avoids this.
7. **Hermes config changes need restart** — CLI reads config at startup. After switching provider, restart the Hermes CLI session for it to pick up.
8. **MCP `create_pod` may silently drop `dockerStartCmd`** — The RunPod API accepts the request but the response's `dockerStartCmd` field is absent, meaning the CMD was not passed to the container. The pod runs the image's default CMD (`sleep infinity` for `runpod/pytorch` templates) instead. **Always verify**: after `create_pod`, check the response for a `dockerStartCmd` field. If missing, fall back to SSH deployment (Workaround B) instead of trying to debug script failures.
9. **Restart stopped pods instead of creating new ones** — `mcp_runpod_start_pod` is cheaper (no new provisioning fee), faster (machine already knows the pod), and reuses the existing IP/volume. Only create new pods when the machine has no capacity left or the region changed.
