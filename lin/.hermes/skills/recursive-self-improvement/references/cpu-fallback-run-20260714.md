# CPU Fallback Run — 2026-07-14

## Context
Fourth RSI cycle on `lin`. Same environment: `.venv` with torch 2.13.0+cu130, i7-6700 CPU, MX150 GPU incompatible. Routine cron cycle — no infrastructure changes.

## Command
```bash
cd ~/Documents/recursive-self-improve && CUDA_VISIBLE_DEVICES="" bash -c 'source .venv/bin/activate && python3 rsi_loop.py'
```
Used the `bash -c` wrapper (confirmed approach). Background process with `notify_on_complete=true`, polling loop via `process(action='wait', timeout=60)`.

## Timing
- **Hardware**: i7-6700 (8 threads), 32GB RAM
- **Model**: Qwen2.5-0.5B-Instruct, float32 (CPU)
- **Steps**: 135 (200 sampled from 1,279 deduped, 3 epochs, batch_size=4, micro_batch=1)
- **Per step**: ~20-35s avg ~25s (varies with token count; faster toward end of epoch)
- **Total**: 3,696s (~62 min) — at the upper end of the ~46–61 min range

## Training Results
- **Train loss trend**: 2.76 → 0.24 best (step 99, epoch 2.2), final 0.37
- **Mean token accuracy**: 55% start → **95.2% peak** (step 99), ~91% final
- **Entropy**: 1.89 start → 0.27 best (step 99)
- **Eval checkpoints** (every 22 steps):
  | Step | Epoch | Eval Loss | Eval Acc | Runtime |
  |------|-------|-----------|----------|---------|
  | 22   | 0.49  | 0.863     | 81.7%    | 40.5s   |
  | 44   | 0.98  | —         | 82.0%    | ~37s    |
  | 66   | 1.47  | 0.740     | 83.6%    | 32.8s   |
  | 88   | 1.96  | —         | 84.4%    | ~38s    |
  | 110  | 2.44  | 0.593     | 84.4%    | 37.6s   |
  | 132  | 2.93  | —         | 84.0%    | ~39s    |

## Outputs
- **Adapter**: `adapters/rsi_20260714_052041/`
- **Merged model**: `models/rsi_merged_20260714_052049/`
- **Latest symlinks**: `adapters/latest` → `rsi_20260714_052041`, `models/latest` → `rsi_merged_20260714_052049`
- **Manifest**: 4th entry in `training_manifest.json`

## Inference Test
All 3 prompts produced coherent responses:
1. **"What is a linked list?"** → "A linked list is a data structure that consists of a collection of elements (nodes) connected to each..." — standard definition
2. **"Write a function to check if a number is prime"** → Valid Python code with `is_prime(n: int) -> bool` signature and docstring
3. **"What's in my codebase?"** → "Welcome to explore our codebase! Our project is divided into 5 modules: `models`, `api`, `security`..." — structured response showing module awareness

**Notable**: The codebase question response is more structured than previous cycles, referencing specific modules rather than a generic answer. The model appears to be internalizing directory structure from code indexing.

## Data Sources
- **Code indexer**: 1,415 raw → 1,279 deduped (100 files from 3 of 4 configured dirs; ForgeKeeper-mcp missing — logged warning, skipped)
- **Synapse Memory**: 0 (no Nexus/Synapse server running on lin)
- **Session history**: 0 (DB reader found no qualifying sessions)

## Comparison to Previous Runs
| Metric | 2026-07-10 | 2026-07-13 | 2026-07-14 |
|--------|-----------|-----------|-----------|
| Time | ~46 min | ~61 min | ~62 min |
| Raw/deduped | 1,357→1,227 | 1,415→1,279 | 1,415→1,279 |
| Steps | 135 | 135 | 135 |
| Best eval acc | 81.7% | 83.6% | 84.4% |
| Peak train acc | — | 93.6% | **95.2%** |
