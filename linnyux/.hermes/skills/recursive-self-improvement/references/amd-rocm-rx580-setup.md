# AMD ROCm + RX 580 PyTorch Setup

## Detection

```python
is_amd = torch.version.hip is not None        # True if ROCm torch
use_gpu = torch.cuda.is_available()            # True on AMD too (HIP compat layer)
gpu_name = torch.cuda.get_device_name(0)       # "Radeon RX 580 Series"
```

## gfx803 (Polaris) Compatibility

RX 580 is Polaris architecture (gfx803). Needed for any AMD GPU compute:

```bash
export HSA_OVERRIDE_GFX_VERSION=8.0.3
export PYTORCH_ROCM_ARCH=gfx803
```

Set BEFORE starting Python — torch checks these at import time.

## ROCm Version vs PyTorch Version

| ROCm | torch version | Python | Notes |
|------|-------------|--------|-------|
| 7.2.2 | 2.5.1+rocm6.2 | 3.12 | Library mismatch: libroctx64.so not found |
| 7.2.2 | 2.13.0+rocm7.2 | 3.12 | Newer, may work better but untested |

## Key Finding: ROCm + PyTorch Version Mismatch

On kubuntux, ROCm **7.2.2** is installed but the only cached PyTorch ROCm wheel was **2.5.1+rocm6.2**. The library ABIs changed between ROCm 6.x and 7.x:

- `libroctx64.so` (ROCm 6.x) → `librocprofiler-sdk-roctx.so.1.1.0` (ROCm 7.x)
- symlinking works for roctx but other internal ABIs may also differ
- The torch binary crashes at `from torch._C import *` with `ImportError: libroctx64.so`

**Practical conclusion**: CPU training on the i7-6700 works adequately (~21s/step for 0.5B model with max_seq_length=1024). GPU training requires either:
1. Compiling torch from source matching ROCm 7.2.2
2. Using a docker container with pre-matched versions
3. Using Ollama+Vulkan for inference only (already configured)

## Disk Space Warning

The torc+rocm wheel is **3.9GB compressed / 5.5GB extracted**. On a 219GB root partition this can fill the disk quickly:
- /dev/sdb3 219G: went from 173G → 206G during torch install/uninstall cycles
- Always check df -h before installing
- Use /media/kubuntux/DEVELOPMENT1/ (95GB free) for venvs and model storage

## Library Mismatch Fix (ROCm 7.2 + torch 6.2)

```bash
# libroctx64.so renamed in ROCm 7.x — torch 6.2 build still expects old name
ln -sf /opt/rocm-7.2.2/lib/librocprofiler-sdk-roctx.so.1.1.0 /usr/lib/x86_64-linux-gnu/libroctx64.so
# OR add ROCm lib dir to ldconfig
echo '/opt/rocm-7.2.2/lib' > /etc/ld.so.conf.d/rocm-libs.conf
ldconfig
```

## Wheel Sizes

| Variant | Size | Install time |
|---------|------|-------------|
| torch+cpu | 900 MB | ~1 min |
| torch+rocm6.2 | 3.8 GB | ~5 min (extract) |
| torch+rocm7.2 | ~4 GB | ~5 min |

Over Tailscale SSH, 3.8GB downloads can take 10+ minutes and look stuck.

## Verification

```bash
python3 -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.version.hip)"
```

## Ollama GPU Inference (Vulkan)

kubuntux already has Ollama with Vulkan backend configured for the RX 580:

```bash
# /etc/systemd/system/ollama.service.d/override.conf
Environment="OLLAMA_VULKAN=1"
Environment="OLLAMA_NUM_GPU_LAYERS=999"
Environment="VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.json"

# Start
systemctl start ollama
ollama pull qwen2.5:0.5b   # or your fine-tuned GGUF
```
