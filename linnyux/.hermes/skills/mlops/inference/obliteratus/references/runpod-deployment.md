# OBLITERATUS on RunPod

End-to-end workflow for abliterating models on a RunPod GPU pod when local hardware is insufficient.

## Prerequisites

- RunPod API key (set as `RUNPOD_API_KEY` env var or configurable via Hermes RunPod MCP)
- RunPod MCP tools enabled in Hermes

## Workflow

### 1. Spin up a GPU pod

Choose a GPU with enough VRAM for your target model:

| Model Size | Min VRAM | Recommended GPU | RunPod Type |
|:-----------|:---------|:----------------|:------------|
| 7-9B (4bit) | 8 GB | RTX 4090 | Community GPU |
| 30-35B (4bit) | 24 GB | A100 40GB / 2x RTX 4090 | Secure Cloud |
| 70-72B (4bit) | 48 GB | A100 80GB / 2x A6000 | Secure Cloud |
| 120B+ (4bit) | 80 GB | A100 80GB / H100 | Secure Cloud |

Using RunPod MCP:

```
# Via RunPod MCP: create_pod
# Template: "runpod/pytorch:latest" or any PyTorch image
# Ports: "8888/http" (for Jupyter), "22/tcp" (for SSH)
```

After creation, note the pod ID and public IP/port from the pod's connection info.

### 2. Install OBLITERATUS on the pod

SSH into the pod and install:

```bash
git clone https://github.com/elder-plinius/OBLITERATUS.git
cd OBLITERATUS
pip install -e .
```

### 3. Check hardware

```bash
python3 -c "
import torch
vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
print(f'GPU: {torch.cuda.get_device_name(0)}')
print(f'VRAM: {vram:.1f} GB')
"
```

### 4. Run abliteration

```bash
obliteratus obliterate <model_name> \
  --method advanced \
  --quantization 4bit \
  --output-dir ./abliterated-model \
  --verify-sample-size 30
```

For models at the VRAM limit, add `--large-model` for conservative defaults.

### 5. Verify results

```bash
# Check refusal rate and perplexity diff
cat ./abliterated-model/metrics.json
```

### 6. Download the model

```bash
# Option A: Upload to HuggingFace Hub
huggingface-cli upload <username>/<model>-abliterated ./abliterated-model

# Option B: Compress and download via SCP
tar czf abliterated-model.tar.gz ./abliterated-model
# Then SCP from RunPod's web terminal or SFTP
```

### 7. Clean up

Delete the pod via RunPod MCP to avoid ongoing charges. Pods bill while running, even if idle.

## Notes

- Use community GPUs for 4-bit quantized models under 30B (cheaper, faster availability)
- Use secure cloud for guaranteed availability on large models (30B+)
- Pod timeout: set a 2-4 hour timeout on the pod — abliteration rarely takes longer
- If SSH is unavailable, use RunPod's web terminal or Jupyter notebook instead
- Network volume is useful for persisting models across pod sessions
