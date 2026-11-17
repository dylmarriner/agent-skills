---
name: gpu-compatibility-troubleshooting
description: >-
  Diagnose and resolve GPU compatibility issues for ML training — AMD ROCm
  Polaris (gfx803) incompatibility with ROCm 6.x, GPU probe patterns that
  catch phantom devices, CPU fallback, and environment variable workarounds.
version: 1.0.0
metadata:
  tags: [gpu, rocm, amd, polaris, gfx803, compatibility, training, fallback, hip, troubleshooting]
---

# GPU Compatibility Troubleshooting

Diagnose and resolve GPU compatibility issues for ML training — especially AMD ROCm on older hardware.

## The Problem: Polaris (RX 470/480/570/580/590) on ROCm 6.x

AMD GPUs using the **GCN 4th gen** architecture (Polaris/Ellesmere, gfx803) are detected by ROCm 6.x as available (`torch.cuda.is_available()=True`) but **lack HIP compute kernels** for modern transformer architectures.

### Symptom

```
RuntimeError: HIP error: invalid device function
HIP kernel errors might be asynchronously reported at some other API call
```

Crash location: `peft/peft_model.py` → `_cast_adapter_dtype` → `param.data.to(torch.float32)`.

### Root Cause

- ROCm 6.x **dropped gfx803 (Polaris) support**. The HIP runtime still enumerates the device, but kernels for operations like PEFT adapter dtype casting are absent from the compiled library.
- `torch.zeros(1).cuda()` passes (trivial memory allocation), leading to a false-positive "GPU available" signal.
- `HSA_OVERRIDE_GFX_VERSION=8.0.3` does NOT fix this — it only overrides the arch tag, not the missing kernels.

## Detection: Real Compute Probe

The standard `torch.zeros(1).cuda()` probe is insufficient. Use an actual matmul:

```python
def gpu_is_usable() -> bool:
    """True only if GPU passes a real compute test."""
    if not torch.cuda.is_available():
        return False
    try:
        torch.zeros(1).cuda()
    except Exception:
        return False
    try:
        a = torch.randn(64, 64, device="cuda")
        b = torch.randn(64, 64, device="cuda")
        _ = (a @ b).sum().item()
        return True
    except RuntimeError:
        return False
```

## Workarounds

### 1. Force CPU Fallback (Recommended for Polaris)

```bash
export ROCR_VISIBLE_DEVICES=""
unset HSA_OVERRIDE_GFX_VERSION
```

Then run normally — entire PyTorch stack falls back to CPU.

**Performance reference**: Qwen2.5-0.5B LoRA training, 30 samples, seq_len=1024, r=16, 8-core machine → **~86s training time**.

### 2. Upgrade Hardware

- **Works**: AMD RDNA (RX 6000+), all NVIDIA, AMD CDNA (MI-series)
- **Partial**: AMD Vega (gfx900) — some ops may still fail
- **Broken**: AMD Polaris (gfx803) on ROCm 6.x

### 3. Downgrade to ROCm 5.7.x

ROCm 5.7 still supports gfx803. Requires full driver + PyTorch stack downgrade.

## Environment Variables Reference

| Variable | Effect |
|----------|--------|
| `ROCR_VISIBLE_DEVICES=""` | Hides all AMD GPUs from HIP — most reliable CPU fallback |
| `HIP_VISIBLE_DEVICES=""` | Same effect on HIP layer |
| `CUDA_VISIBLE_DEVICES=""` | Works on NVIDIA, may be ignored on AMD ROCm builds |
| `HSA_OVERRIDE_GFX_VERSION=8.0.3` | gfx803 compat override — does NOT fix missing kernels |

## GPU Compatibility Chart

| GPU Series | Architecture | ROCm 5.x | ROCm 6.x |
|------------|-------------|----------|----------|
| RX 470/480/570/580/590 | Polaris (gfx803) | ✅ | ❌ HIP kernels missing |
| RX 550/560 | Polaris (gfx803) | ✅ | ❌ HIP kernels missing |
| Vega 56/64 | Vega (gfx900) | ✅ | ⚠️ partial |
| RX 5500/5600/5700 | RDNA 1 (gfx1010) | ✅ | ✅ |
| RX 6600+ / 7600+ | RDNA 2/3 | ✅ | ✅ |
| MI-series | CDNA | ✅ | ✅ |
| All NVIDIA | CUDA | ✅ | ✅ |

## Trainer Integration Pattern

Add this to your training script's GPU detection:

```python
import os

def detect_device(config) -> str:
    """Return 'cuda' or 'cpu' with real compute validation."""
    if not torch.cuda.is_available():
        return "cpu"
    try:
        torch.zeros(1).cuda()
        gpu_name = torch.cuda.get_device_name(0)
    except Exception:
        return "cpu"
    # Real compute probe
    try:
        a = torch.randn(64, 64, device="cuda")
        b = torch.randn(64, 64, device="cuda")
        _ = (a @ b).sum().item()
    except RuntimeError as e:
        print(f"GPU {gpu_name} detected but real compute failed: {e}")
        return "cpu"
    return "cuda"
```
