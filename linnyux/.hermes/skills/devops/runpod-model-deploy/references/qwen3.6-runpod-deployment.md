# Qwen3.6-35B-A3B Aggressive on RunPod Deployment Guide

Session-specific breakdown for deploying this model on an A40/A6000/L40S (48GB VRAM).

## Model Info

| Property | Value |
|----------|-------|
| HF repo | `HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive` |
| Total params | 35B (MoE, 3B active) |
| Architecture | 40 layers: 30 Gated DeltaNet + 10 Gated Attention |
| Attention layers | Only 10 (the rest are linear attention — no KV cache growth) |
| Native context | 262,144 tokens |
| YaRN max | ~1,010,000 tokens |
| Modality | Text + vision (needs mmproj for vision) |
| Chat template | Built-in GGUF metadata, use `--jinja` flag |

## Available GGUFs on HuggingFace

| File | Quant | Size |
|------|-------|------|
| `...Q8_K_P.gguf` | Q8_K_P | 44 GB |
| `...Q6_K_P.gguf` | Q6_K_P | 31 GB |
| `...Q5_K_P.gguf` | Q5_K_P | 28 GB |
| `...Q4_K_P.gguf` | Q4_K_P | 23 GB |
| `...Q4_K_M.gguf` | Q4_K_M | 21 GB |
| `...Q3_K_P.gguf` | Q3_K_P | 19 GB |
| `...Q2_K_P.gguf` | Q2_K_P | 15 GB |

## VRAM Budget for 48GB Cards

At Q4_K_P (23GB) with 1M context at Q8_0 KV cache:

```
Q4_K_P weights:       ~23 GB  (35B params × 4.88 bpw / 8)
KV cache at Q8_0/1M:  ~10 GB  (10 attn layers × 2 KV heads × 256 head_dim × 1M / 1B)
Overhead:              ~2 GB
Total:                ~35 GB
Headroom:             ~13 GB
```

At Q5_K_P (28GB) with 262K context at Q8_0:
```
Q5_K_P weights:       ~28 GB
KV cache at Q8_0/262K: ~2.6 GB
Overhead:              ~2 GB
Total:                ~32.6 GB
Headroom:             ~15.4 GB
```

## Full dockerStartCmd (RunPod Web UI paste)

Single line for the **Docker Command** field:

```bash
pip install -q huggingface-hub llama-cpp-python 2>/dev/null && python3 -c "from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive', filename='Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-Q4_K_P.gguf', local_dir='/workspace')" && exec python3 -m llama_cpp.server --model /workspace/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-Q4_K_P.gguf --host 0.0.0.0 --port 8000 --n_ctx 1000000 --rope_scaling_type yarn --rope_freq_scale 4.0 --cache_type_k q8_0 --cache_type_v q8_0 --n_gpu_layers -1
```

**If using port health check workaround** (RunPod kills pods without immediate port listener), prefix with:

```bash
python3 -m http.server 8000 --bind 0.0.0.0 &>/dev/null & sleep 3 && pip install ...
```

## Hermes Config

After the pod is running at `http://<IP>:8000/v1`:

```bash
hermes config set agent.custom_providers '[{"name":"runpod-qwen","api_key":"not-needed","base_url":"http://<IP>:8000/v1","api_mode":"chat_completions","models":["qwen3.6-35b"]}]'
hermes config set model.default qwen3.6-35b
hermes config set model.provider custom:runpod-qwen
hermes config set model.context_length 1000000
```
