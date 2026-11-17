---
name: recursive-self-improvement
description: Recursive Self-Improvement system — a 0.5B model that trains itself from codebase + Synapse Memory
---

# Recursive Self-Improvement (RSI) System

Located at: `~/Documents/recursive-self-improve/`

## What it does

A Qwen2.5-0.5B-Instruct model that improves itself over time by:
1. Indexing code from dev directories → instruction-response pairs
2. Pulling high-importance memories from Synapse Memory
3. Extracting conversation sessions as training data
4. Running LoRA fine-tuning (8.8M trainable params out of 502M)
5. Deploying the improved model for daily inference

The cycle: use → collect data → train → deploy → better model.

## Machines

### kubuntux (RX 580 8GB — primary GPU target)
```bash
ssh root@100.93.75.87

# NOTE: The CIFS share is mounted at /mnt/development1, not /media/kubuntux/DEVELOPMENT1
# The old path /media/kubuntux/DEVELOPMENT1 no longer exists.
cd /mnt/development1/rsi

# ⚠️ The NAS-hosted .venv has broken symlinks and CIFS permission issues.
# Do NOT use it directly. Create a local venv:
uv venv /tmp/rsi-venv --python 3.12 --seed
uv pip install --python /tmp/rsi-venv torch --index-url https://download.pytorch.org/whl/cpu
uv pip install --python /tmp/rsi-venv transformers peft trl datasets accelerate bitsandbytes pyyaml

# CPU training (active):
/tmp/rsi-venv/bin/python3 rsi_loop.py

# GPU training (when ROCm torch works):
HSA_OVERRIDE_GFX_VERSION=8.0.3 /tmp/rsi-venv/bin/python3 rsi_loop.py
```
- i7-6700 CPU, 8 threads — **~30s/step** CPU (30 ex × 1 epoch = 7 steps = ~3.5 min)
- Dev disk: CIFS share at `/mnt/development1/` (nounix mount — write restrictions apply!)
- Ollama+Vulkan serves RX 580 for inference
- **NOTE: The CIFS mount uses `nounix` — you may not be able to write to the share.** Direct adapter output to `/tmp/rsi-adapters/` as a workaround.
- **NOTE: This disk may not be mounted on the lin machine** — the RSI code lives at `~/Documents/recursive-self-improve/` there
- Cron: daily 3am (job: rsi-cycle-kubuntux) — **runs ON kubuntux** via SSH from lin, not locally.
  The cron prompt SSHs into 100.93.75.87 and executes the RSI loop there.
- **The entire `/media/kubuntux/DEVELOPMENT1` is the training data source** — never limit code_dirs
  to a handful of subdirectories. The 67+ repos/dirs across the dev share produce richer training
  signal than a curated subset.

### lin (MX150 4GB — GPU via `.venv_py311`, CPU via `.venv`)

Two venvs with different torch builds:

| Venv | Python | Torch | GPU Support | Use Case |
|------|--------|-------|-------------|----------|
| `.venv` | 3.14 (linuxbrew) | 2.13.0+cu130 (CC 7.5+) | ❌ sm_61 unsupported | CPU fallback |
| `.venv_py311` | 3.11 (uv-managed) | 2.6.0+cu124 (CC 6.1+) | ✅ MX150 works | **GPU training (preferred)** |

**GPU mode (preferred — ~20 min):**
```bash
cd ~/Documents/recursive-self-improve
. .venv_py311/bin/activate
python3 rsi_loop.py
```

**CPU mode (fallback — ~46–62 min):**
```bash
cd ~/Documents/recursive-self-improve
CUDA_VISIBLE_DEVICES="" bash -c 'source .venv/bin/activate && exec python3 rsi_loop.py'
```

- GPU timing (MX150, torch 2.6.0+cu124): ~6-10s/step → **~20 min** (200 samples, 3 epochs = 135 steps)
- CPU timing (torch 2.13.0): ~18-35s/step → **~46–68 min**
- Use `background=true + notify_on_complete=true` then poll with `process(action='wait', timeout=60)` in a loop — Capped at 60s per call
- Actual path: `/home/lin/Documents/recursive-self-improve/`
- The kubuntux dev disk may not be mounted on lin — always check existence before assuming path

## Key Commands

```bash
cd ~/Documents/recursive-self-improve

# Activate (lin GPU: .venv_py311, lin CPU: .venv, kubuntux: /tmp/rsi-venv)
. .venv_py311/bin/activate

# Full RSI cycle (collect → train → save) — GPU mode (lin: .venv_py311)
python3 rsi_loop.py

# Full RSI cycle — CPU mode (lin .venv fallback)
CUDA_VISIBLE_DEVICES="" bash -c 'source .venv/bin/activate && exec python3 rsi_loop.py'

# Check training history
python3 -c "import json; m=json.load(open('training_manifest.json')); print(f'Runs: {len(m)}, Last: {m[-1][\"timestamp\"]}')"

# Interactive inference with latest model
python3 infer.py

# One-shot
python3 infer.py "What's in my codebase?"
```

## Initial Setup (lin machine — GPU-compatible torch)

Two paths:

**`.venv_py311` (already has GPU-compatible torch 2.6.0+cu124 — preferred):**
```bash
cd ~/Documents/recursive-self-improve
. .venv_py311/bin/activate
python3 rsi_loop.py  # works with MX150 GPU
```

**`.venv` (needs reinstall for GPU, CPU-only as-is):**
```bash
cd ~/Documents/recursive-self-improve
. .venv/bin/activate

# Install all ML dependencies
uv pip install pyyaml
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124  # for MX150 sm_61
uv pip install transformers peft accelerate bitsandbytes trl datasets scipy
```

Dependencies: pyyaml, torch 2.6.0+cu124, transformers, peft, accelerate, bitsandbytes, trl, datasets, scipy.

⚠️ `torch` alone is ~733MB — ensure sufficient disk space (~4GB free) and use `timeout=600` or background mode for the install.

> **Current state (2026-07-15)**: `.venv` has `torch 2.13.0+cu130` (incompatible with MX150 — CPU only). `.venv_py311` has `torch 2.6.0+cu124` (works with MX150 for GPU training). Default to `.venv_py311` on the lin machine for GPU training.

## Data Source Principle

**Train on the ENTIRE dev share, not specific subdirectories.** The user explicitly corrected: when RSI trains on your data, it must cover the full `/mnt/development1` or `/media/kubuntux/DEVELOPMENT1` folder — every repo, config, script, project. The config's `code_dirs` list must never be a hand-picked subset; always point to the root of the dev share.

| Machine | code_dirs | Notes |
|---------|-----------|-------|
| kubuntux | `/mnt/development1, /root` | Local physical drive `/dev/sdc1` (220GB) |
| lin | `/mnt/development1` | CIFS mount of kubuntux's share |

Never reference `/media/kubuntux/DEVELOPMENT1` directly in config — it's superseded by `/mnt/development1`. This ensures the 0.5B model learns from ALL your code (67+ repos/dirs), not a curated sample of 3-4 codebases.

## Data Collection Notes

- **Synapse Memory**: 0 examples collected if no Synapse/Nexus memory server is running. This is expected — the system currently relies on code indexing for training data.
- **Session history**: 0 examples collected — the session DB reader is not yet connected to the Hermes conversation store.
- **Code indexing**: Produces ~1,400 examples from 100 files across configured code dirs. Missing directories are logged as warnings and skipped. The dedup ratio is consistently ~1,415 raw → 1,279 deduped across cycles.
- **Foreground timeout**: 600s covers <15% of a CPU training run (killed at ~19/135 steps). Always use `background=true + notify_on_complete` for training cycles.
- **Dedup**: Reduces ~1,415 raw examples to ~1,279 after deduplication.

## Timing Reference

| Config | Steps | Time | Hardware |
|--------|-------|------|----------|
| 200 samples, 3 epochs, max_seq_len=2048, QLoRA 4-bit | 135 steps | ~17 min (~6-10s/step) | MX150 GPU (torch 2.6.0+cu124) |
| 200 samples, 3 epochs, max_seq_len=2048, CPU float32 | 135 steps | ~46–68 min (~18–35s/step) | i7-6700 CPU (torch 2.13.0, sm_61 incompatible) |
| 30 samples, 1 epoch, max_seq_len=1024, CPU float32 | 7 steps | ~3.5 min (~30s/step) | i7-6700 CPU (local /tmp venv, torch 2.13.0+cpu) |

| Cycle | Date | Time | Peak Train Acc | Final Loss | Data (raw→dedup) |
|-------|------|------|----------------|------------|-------------------|
| CPU #1 | 2026-07-10 | ~46 min | — | — | 1,357→1,227 |
| CPU #2 | 2026-07-13 | ~61 min | 93.6% | — | 1,415→1,279 |
| GPU #1 | 2026-07-15 AM | ~20 min | — | 0.35 | 1,415→1,279 |
| CPU #3 | 2026-07-14 | ~62 min | 95.2% | 0.373 | 1,415→1,279 |
| CPU #4 | 2026-07-15 PM | ~68 min | **95.6%** | **0.183** | 1,415→1,279 |

## Recommended Background Execution

Training takes >600s on MX150 and >3600s on CPU. **Always use background mode:**

```bash
# lin GPU mode (preferred):
cd ~/Documents/recursive-self-improve
. .venv_py311/bin/activate && python3 rsi_loop.py
# Then poll with: process(action='wait', timeout=60) in a loop

# lin CPU fallback or kubuntux:
CUDA_VISIBLE_DEVICES="" bash -c 'source .venv/bin/activate && exec python3 rsi_loop.py'
```

Or use Hermes `terminal(background=true, notify_on_complete=true)` with `process(action='wait', timeout=60)` in a polling loop. The process notification fires on exit; `process(action='log')` shows final full output.

On GPU (MX150 with `.venv_py311`): just activate and run, no env var needed.

## Data Sources

| Source | ~Count per cycle | Notes |
|--------|-----------------|-------|
| Code indexer | 3,000+ (from full dev share) | 67+ repos across /mnt/development1, 50-100 files sampled per cycle |
| Synapse Memory | Varies | Importance ≥ 0.6 only |
| Session history | Varies | Recent conversations from SQLite DB |

The full dev share produces significantly more diverse training signal than
a handful of specific directories. Expect raw counts of 3,000+ examples
before sampling down to max_samples.

## Architecture

```
code_indexer.py / memory_collector.py    rsi_loop.py (collect)
        │                                       │
        └───────────→ trainer.py ←──────────────┘
                        │
                    adapters/ + models/
                        │
                    infer.py
```

## Trainer Parameter Gotchas (TRL 1.7+)

| Wrong | Right | Reason |
|-------|-------|--------|
| `tokenizer=` | `processing_class=` | TRL 1.7+ renamed |
| `evaluation_strategy=` | `eval_strategy=` | |
| `TrainingArguments(...)` | `SFTConfig(...)` | New config class with TRL defaults |
| `max_seq_length=` in SFTConfig | `max_length=` | SFTConfig uses `max_length` |
| `warmup_ratio=0.03` | `warmup_steps=N` | warmup_ratio deprecated in v5.2 |
| `packing=` in SFTConfig | Remove (SFTTrainer handles it) | Not a TrainingArgs param |
| `no_cuda=True` | `CUDA_VISIBLE_DEVICES=""` env var | removed from TrainingArgs |
| `2e-4` in config YAML | `0.0002` | YAML parses `2e-4` as string |

## Pitfalls

- **Training >600s**: MX150 takes ~17 min for 200 samples × 3 epochs (GPU) or ~46–61 min (CPU). Use background mode with notify_on_complete or the `process(action='wait')` loop pattern — 600s foreground timeout will cut training short. `process(action='wait')` is capped at 60s per call; repeat it in a loop until the process exits.
- **CIFS nounix mount blocks writes on kubuntux**: The dev disk at `/mnt/development1` is a CIFS/SMB share mounted with `nounix`, which disables UNIX permission extensions. Even as root you cannot write to files/dirs created by a different UID on the server side. Symptoms: `PermissionError` on `README.md`, `training_manifest.json`, or any file in the old `.venv` or `adapters/` directory. **Workaround**: Point `output.adapter_dir` in config.yaml to a local path like `/tmp/rsi-adapters`, or remount without `nounix`. The adapter can be `cp -r` to the share afterward if needed.
- **CIFS venv broken (kubuntux)**: The `.venv` directory inside `/mnt/development1/rsi/` was created on a different machine and the symlinks (python3, pip) don't resolve on the current host. The CIFS `nounix` mount also prevents removing/recreating it. **Workaround**: Create a local venv at `/tmp/rsi-venv` and use its python binary directly (e.g. `/tmp/rsi-venv/bin/python3 rsi_loop.py`).
- **Config code_dirs must point to the full dev share root, not a curated subset**: The user explicitly corrected that RSI should train on the **entire** `/mnt/development1` (or `/media/kubuntux/DEVELOPMENT1`), not specific subdirectories like MUTS or SCOS. Only the full dev share gives the model enough diversity. Having only 3-4 narrow codebases as training data produces a model that doesn't generalize. This is the single most important config decision.\n- **Stale `/media/kubuntux/DEVELOPMENT1` path**:
- **Torch 2.13.0+cu130 incompatible with MX150 (sm_61)**: The `.venv` torch build only supports GPU CC ≥7.5 (sm_75+). MX150 has CC 6.1 — trying to run with CUDA enabled will crash with `Error named symbol not found at line 62 in file /src/csrc/ops.cu` from bitsandbytes. **Fix**: Use `.venv_py311` instead (torch 2.6.0+cu124 works with sm_61), or run with `CUDA_VISIBLE_DEVICES=""` (CPU mode via `.venv`), or reinstall torch 2.6.0+cu124 in `.venv`.
- **Disk full kills silently**: Pip installs of large wheels (torch = 733MB, nvidia-cudnn-cu12 = 634MB) fail silently when disk fills. Check `df -h` before large installs.
- **`CUDA_VISIBLE_DEVICES="" . .venv/bin/activate && python3 ...` doesn't propagate**: When chaining `source` with `&&`, the env var only scopes to the source command, not the python process. **Two working alternatives:**
  1. `CUDA_VISIBLE_DEVICES="" bash -c 'source .venv/bin/activate && exec python3 rsi_loop.py'` — explicit wrapper
  2. `export CUDA_VISIBLE_DEVICES="" && . .venv/bin/activate && python3 rsi_loop.py` — `export` creates a shell variable that propagates through the `&&` chain
- **process(action='wait') capped at 60s**: The `wait` action's timeout parameter is clamped to a configured limit of 60s. For long training runs, call `wait(timeout=60)` repeatedly in a loop until `status == "exited"`. Alternatively, poll with `process(action='poll')` to check progress without blocking.
- **Virtualenv name mismatch**: The cron wrapper `rsi_cron.sh` references `.venv` but the lin machine uses `.venv_py311`. Edit the script to match when running from cron.
- **ForgeKeeper-mcp dir missing**: The code_dirs in config.yaml reference `/home/lin/Documents/ForgeKeeper-mcp` which may not exist — this is logged as a warning and skipped.

## References

- `references/amd-rocm-rx580-setup.md` — GPU setup details for the RX 580
- `references/mx150-run-20260710.md` — First GPU RSI cycle on MX150 (torch 2.6.0+cu124)
- `references/mx150-run-20260715.md` — GPU RSI cycle via `.venv_py311` (cron, 20 min, confirmed working)
- `references/cpu-fallback-run-20260710.md` — CPU fallback RSI cycle (torch 2.13.0+cu130, sm_61 incompatible)
- `references/cpu-fallback-run-20260713.md` — CPU RSI cycle (2026-07-13, 61 min, `export` approach confirmed)
- `references/cpu-cifs-run-20260714.md` — CPU RSI cycle on kubuntux via CIFS (path fix, local venv workaround, nounix workaround)
- `references/cpu-fallback-run-20260715.md` — CPU RSI cycle (2026-07-15, 68 min, peak train acc 95.6%)
- `references/cpu-fallback-run-20260714.md` — CPU RSI cycle on lin (2026-07-14, 62 min, peak train acc 95.2%)

## Execution Style

When the user asks about or works with this system:
- No explanations, no narration, no listing alternatives
- Just execute the command and report the result concisely
- If something fails, silently try the next approach
- Report: what ran, what it produced (adapter path, loss, time), nothing else
