# CPU Fallback Run — 2026-07-15

## Context
Fifth RSI cycle on `lin`. Routine cron job. `.venv` with torch 2.13.0+cu130 on i7-6700 CPU. No infrastructure changes since the 2026-07-14 run. First attempt at 600s foreground timeout was killed at 14% (19/135 steps); second attempt in background mode completed fully.

## Command
```bash
cd ~/Documents/recursive-self-improve && CUDA_VISIBLE_DEVICES="" bash -c 'source .venv/bin/activate && python3 rsi_loop.py'
```
Used `bash -c` wrapper (confirmed approach). Background process with `notify_on_complete=true`, polling loop via repeated `process(action='wait', timeout=60)`.

## Timing
- **Hardware**: i7-6700 (8 threads), 32GB RAM
- **Model**: Qwen2.5-0.5B-Instruct, float32 (CPU)
- **Steps**: 135 (200 sampled from 1,279 deduped, 3 epochs, batch_size=4, micro_batch=1)
- **Per step**: ~22-36s avg ~28s (slower than previous 25s avg; possibly background overhead or system load)
- **Total**: 4,077s (~68 min) — new upper bound, ~6 min slower than 2026-07-14

## Failed First Attempt
```bash
# Foreground with timeout=600 — killed at 14%
terminal(timeout=600, command="cd ~/Documents/recursive-self-improve && CUDA_VISIBLE_DEVICES=\"\" bash ...")
```
Result: killed at 19/135 steps after 600s. Lesson: 600s foreground timeout covers <15% of a CPU training run. Always use background mode.

## Training Results
- **Train loss trend**: 2.966 → 0.1827 final (best: 0.073 at step 78, epoch 1.733)
- **Mean token accuracy**: 55.1% start → **95.6% peak** (step 92), 94.5% final
- **Entropy**: 1.917 → 0.2277 best (step 134)
- **Eval checkpoints** (every ~22 steps):
  | Step | Epoch | Eval Loss | Eval Acc | Runtime |
  |------|-------|-----------|----------|---------|
  | 22   | 0.49  | 1.104     | 77.7%    | 41.4s   |
  | 44   | 0.98  | 0.957     | 81.0%    | ~37s    |
  | 66   | 1.47  | 0.957     | 81.0%    | 41.8s   |
  | 88   | 1.96  | 0.808     | 83.8%    | ~39s    |
  | 110  | 2.44  | 0.947     | 81.0%    | 44.2s   |
  | 132  | 2.93  | 0.893     | 80.9%    | ~44s    |
  | 135  | 3.00  | 0.947     | 80.9%    | ~44s    |

  **Note**: Eval accuracy degraded slightly from previous cycles (80.9% final vs 84.0% on 2026-07-14), possibly due to different train/eval split randomization.

## Outputs
- **Adapter**: `adapters/rsi_20260715_052814/`
- **Merged model**: `models/rsi_merged_20260715_052821/`
- **Latest symlinks**: `adapters/latest` → `rsi_20260715_052814`, `models/latest` → `rsi_merged_20260715_052821`
- **Manifest**: 6th entry in `training_manifest.json`

## Inference Test
All 3 prompts produced coherent but less structured responses:
1. **"What is a linked list?"** → "A linked list is a data structure that consists of a sequence of elements, where each element has a ..." — standard definition, truncated
2. **"Write a function to check if a number is prime"** → Valid Python function with docstring `is_prime(num: int) -> bool`
3. **"What's in my codebase?"** → "Hello there! I'm Qwen, an AI language model designed to assist you with your coding questions and pr..." — generic self-introduction, less codebase-aware than previous cycle

## Data Sources (consistent with prior runs)
- **Code indexer**: 1,415 raw → 1,279 deduped (100 files from 3 of 4 configured dirs; ForgeKeeper-mcp missing)
- **Synapse Memory**: 0 (no Nexus/Synapse server running on lin)
- **Session history**: 0 (DB reader found no qualifying sessions)

## Comparison to Previous CPU Runs
| Metric | 2026-07-10 | 2026-07-13 | 2026-07-14 | 2026-07-15 |
|--------|-----------|-----------|-----------|-----------|
| Time | ~46 min | ~61 min | ~62 min | ~68 min |
| Raw/deduped | 1,357→1,227 | 1,415→1,279 | 1,415→1,279 | 1,415→1,279 |
| Steps | 135 | 135 | 135 | 135 |
| Best eval acc | 81.7% | 83.6% | 84.4% | 83.8% |
| Peak train acc | — | 93.6% | 95.2% | **95.6%** |
| Final train loss | — | — | 0.373 | **0.183** |
| Total cycle time | ~2,760s | ~3,672s | ~3,696s | **4,077s** |
