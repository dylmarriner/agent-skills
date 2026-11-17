# CPU Fallback Run — 2026-07-10

## Context
Second RSI cycle on `lin`. The venv had been rebuilt from `.venv_py311` (CPython 3.11, torch 2.6.0+cu124) to `.venv` (linuxbrew CPython 3.14, torch 2.13.0+cu130). The new torch build only supports GPU CC ≥7.5, but MX150 is sm_61 — GPU mode is broken.

## The Problem
Trying to run with CUDA enabled produced:
```
Error named symbol not found at line 62 in file /src/csrc/ops.cu
```
This is bitsandbytes trying to load CUDA kernels for 4-bit quantization on an unsupported GPU architecture.

## The Fix
```bash
CUDA_VISIBLE_DEVICES="" bash -c 'source .venv/bin/activate && exec python3 rsi_loop.py'
```

Key details:
- The `bash -c` wrapper is essential — `CUDA_VISIBLE_DEVICES="" . .venv/bin/activate && python3 ...` does NOT reliably propagate the empty env var to the Python process
- `exec` prevents an extra shell process from staying resident
- CUDA_VISIBLE_DEVICES="" makes `torch.cuda.is_available()` return False, which triggers the CPU fallback path in `trainer.py` (line 117-123: device_map="cpu", torch_dtype=torch.float32, no BitsAndBytes)

## Timing
- **Hardware**: i7-6700 (8 threads), 32GB RAM
- **Model**: Qwen2.5-0.5B-Instruct, float32
- **Steps**: 135 (180 train × 20 eval, 3 epochs, batch_size=4, micro_batch=1)
- **Per step**: ~16-23s (varies with token count per batch)
- **Total**: 2,756s (~46 min)
- **Data**: 200 samples sampled from 1,227 deduped code examples

## Training Results
- **Final train loss**: ~0.35 at last step
- **Eval losses**: 0.83 (epoch 1) → 0.69 (epoch 2) → 0.50 (epoch 3 — final)
- **Mean token accuracy**: 0.93 at best (up from 0.49 at step 1)

## Outputs
- **Adapter**: `adapters/rsi_20260710_051043/`
- **Merged model**: `models/rsi_merged_20260710_051048/`
- **Latest symlink**: `adapters/latest` → `adapters/rsi_20260710_051043/`

## Inference Test (on merged model)
All 3 prompts passed:
1. "What is a linked list?" → coherent data structure definition
2. "Write a function to check if a number is prime" → valid Python with docstring
3. "What's in my codebase?" → referenced MUTS directory structure

## Process Management Pattern
Since training takes ~46 min on CPU, foreground mode times out at 600s:
```python
# Hermes pattern for >600s training:
# 1. Start with background=true, notify_on_complete=true
# 2. Poll in a loop:
process(action='wait', session_id='...', timeout=60)  # capped at 60s
# 3. Repeat until status == 'exited'
# 4. Read final output with process(action='log')
```

## Comparison with GPU Run (earlier today)
| Metric | GPU (torch 2.6.0+cu124) | CPU (torch 2.13.0+cu130) |
|--------|------------------------|--------------------------|
| Time | ~17 min | ~46 min |
| Best eval loss | 0.6883 | 0.50 |
| Per-step | ~6-10s | ~16-23s |
| Quantization | QLoRA 4-bit (nf4) | float32 |

## Data Sources This Cycle
- **Code indexer**: 1,357 raw → 1,227 deduped (100 files from MUTS, SCOS, Anthropic-Cybersecurity-Skills)
- **Synapse Memory**: 0 (no Nexus server on lin)
- **Session history**: 0 (DB reader not connected)
- **ForgeKeeper-mcp dir**: missing on lin (logged as warning, skipped)
