# CPU CIFS RSI Cycle — 2026-07-14 (kubuntux)

## Context

First RSI cycle on kubuntux since the dev disk mount point changed from `/media/kubuntux/DEVELOPMENT1` to `/mnt/development1`. The CIFS share had several blockers that needed workarounds.

## Issues Resolved

### 1. Stale config paths
- `config.yaml` had `code_dirs: [/media/kubuntux/DEVELOPMENT1]` → fixed to `/mnt/development1`
- `output.adapter_dir` pointed to `/media/kubuntux/DEVELOPMENT1/rsi/adapters` → fixed
- Search for `/media/kubuntux` also found hits in `trainer_state.json` (checkpoint metadata) and `training_manifest.json`

### 2. Broken NAS .venv
- Symlinks (python3, pip) missing inside `.venv/bin/` — created on a different machine
- Files owned by different server-side UID despite `uid=1000` on mount
- `nounix` mount option prevents deleting/recreating the dir even as root
- **Solution**: `uv venv /tmp/rsi-venv --python 3.12 --seed` then install deps

### 3. CIFS nounix write barrier
- The `adapters/` directory exists but `touch test_write` fails — `nounix` in fstab disables UNIX permission extensions
- Even sudo can't write — file ownership is enforced server-side
- **Solution**: Point `output.adapter_dir` to `/tmp/rsi-adapters`

## Results

| Metric | Value |
|--------|-------|
| Code files indexed | 50 (config limit) |
| Raw examples | 325 |
| After dedup | 300 |
| Trained on | 30 (config max_samples) |
| Model | Qwen/Qwen2.5-0.5B-Instruct |
| Training time | 210s (3m30s) |
| Steps | 7 (1 epoch) |
| Hardware | i7-6700 CPU, 8 threads |
| Eval loss trajectory | 2.86 → 2.338 → 2.019 → 1.841 → 1.733 → 1.679 → **1.663** |
| Train loss trajectory | 2.498 → 2.334 → 2.08 → 1.735 → 1.381 → 1.489 |
| Adapter size | 33.6 MB (safetensors) |
| Inference verification | PASS (linked list, is_prime) |

## Commands Used

```bash
# Mount share
sudo mount /mnt/development1

# Fix config — two YAML paths fixed:
#   /media/kubuntux/DEVELOPMENT1 → /mnt/development1 (code_dirs)
#   /media/kubuntux/DEVELOPMENT1/rsi/adapters → /tmp/rsi-adapters (adapter_dir)

# Create local venv (not on CIFS)
uv venv /tmp/rsi-venv --python 3.12 --seed
uv pip install --python /tmp/rsi-venv torch --index-url https://download.pytorch.org/whl/cpu
uv pip install --python /tmp/rsi-venv transformers peft trl datasets accelerate bitsandbytes pyyaml

# Run cycle
/tmp/rsi-venv/bin/python3 rsi_loop.py
```
