# Remote GPU Backend (RunPod + Ollama)

Pattern: deploy an inference server on a cloud GPU (RunPod), tunnel it to localhost, wire Hermes as a custom provider.

## Setup Sequence

### 1. Create RunPod pod
```bash
# Image: runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04
# GPU: A40 (48GB), A6000 (48GB), L40S (48GB)
# Expose: 22/tcp only (port 8000 externally kills the pod if setup takes time)
# Docker CMD: "sleep infinity"
# SSH key: set PUBLIC_KEY env var matching local ~/.ssh/id_ed25519.pub
```

### 2. Install Ollama on pod
```bash
ssh -p <port> root@<ip>
apt-get update -qq && apt-get install -y -qq zstd
curl -fsSL https://ollama.com/install.sh | sh
```

### 3. Import GGUF model into Ollama
```bash
# Download via hf CLI (NOT huggingface-cli — deprecated)
hf download <repo>/<model> <filename>.gguf --local-dir /workspace

# Create Modelfile
cat > /workspace/Modelfile << 'EOF'
FROM /workspace/<filename>.gguf
PARAMETER num_ctx <context_length>
EOF

# Create + serve
OLLAMA_HOST=0.0.0.0:8000 ollama serve &
OLLAMA_HOST=0.0.0.0:8000 ollama create <model-name> -f /workspace/Modelfile
```

### 4. Handle Qwen thinking mode (if applicable)
Qwen3.x models output thinking in `<think>` tags via Ollama's `/api/generate` but return empty `content` via `/api/chat`. Solution: a proxy on the pod that:

- Takes OpenAI-compatible `/v1/chat/completions` requests
- Converts to Ollama `/api/generate` with explicit prompt construction using `<|im_start|>` tokens
- Strips `<think>` tags and returns clean content
- Optionally passes through reasoning in a `reasoning` field

```python
# Key proxy pattern — convert chat messages to prompt for /api/generate
prompt = ''
for m in msgs:
    r,c = m['role'], m.get('content','')
    if r=='system': prompt += f'<|im_start|>system\\n{c}<|im_end|>\\n'
    elif r=='user': prompt += f'<|im_start|>user\\n{c}<|im_end|>\\n'
    elif r=='assistant': prompt += f'<|im_start|>assistant\\n{c}<|im_end|>\\n'
prompt += '<|im_start|>assistant\\n'

# Call Ollama
req = {'model': model, 'prompt': prompt, 'stream': False,
       'options': {'num_predict': max_tokens, 'stop': ['<|im_end|>']}}

# Clean response
clean = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
```

### 5. SSH tunnel to local
```bash
ssh -L <local_port>:localhost:<pod_port> -p <ssh_port> root@<pod_ip> sleep 86400
```
Keep this running in background. Tunnel auto-drops if local machine restarts — use systemd or autossh for persistence.

### 6. Configure Hermes
⚠️ CRITICAL: `custom_providers` must be a proper YAML list, NOT set via `hermes config set` (which writes JSON string scalars that break parsing).

Add to `~/.hermes/config.yaml` manually:
```yaml
custom_providers:
- name: <provider-name>
  api_key: not-needed
  base_url: http://localhost:<local_port>/v1
  api_mode: chat_completions
  models:
  - <model-name>
```

Then:
```bash
hermes config set model.default <model-name>
hermes config set model.provider custom:<provider-name>
hermes config set model.context_length <context-length>
```

Also update model caches:
```bash
python3 -c "
import json, time, os
entry = {'fp': 'custom:<provider>', 'at': time.time(), 'models': ['<model-name>']}
for p in ['~/.hermes/provider_models_cache.json', '~/.hermes/models_dev_cache.json']:
    with open(os.path.expanduser(p), 'w') as f:
        json.dump({'custom:<provider>': entry}, f)
"
```

## Model VRAM Estimates (A40 48GB, Q4_K_P)

| Model | Weights | KV cache (1M ctx, Q8) | Total | Fits? |
|-------|---------|----------------------|-------|-------|
| Qwen3.6-35B-A3B (MoE) | ~23 GB | ~10 GB | ~33 GB | ✓ comfortable |
| Yi-34B | ~20 GB | ~30 GB | ~50 GB | ✗ at 1M (try 32K) |
| Llama-3-70B | ~40 GB | ~60 GB | ~100 GB | ✗ (needs 2x A40) |

## Pitfalls
- `huggingface-cli` is deprecated — use `hf` CLI instead
- No HF_TOKEN severely rate-limits downloads
- `hermes config set custom_providers` writes JSON strings, not YAML lists — edit config.yaml directly for list values
- Qwen thinking mode: stripping hidden reasoning content frustrates users who chose Qwen for its chain-of-thought — keep `reasoning` field or at minimum preserve the `<think>` content
