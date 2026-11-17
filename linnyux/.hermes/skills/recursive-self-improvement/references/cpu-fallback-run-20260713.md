# CPU Fallback Run — 2026-07-13

## Context
Third RSI cycle on `lin`. Same environment as the 2026-07-10 CPU run: `.venv` with torch 2.13.0+cu130, i7-6700 CPU, MX150 GPU incompatible.

## Key Difference from Previous Runs
The `export` approach was tried and **confirmed working** as an alternative to the `bash -c` wrapper:

```bash
# Previously documented (bash -c wrapper):
CUDA_VISIBLE_DEVICES="" bash -c 'source .venv/bin/activate && exec python3 rsi_loop.py'

# Also works — export propagates through && chain:
export CUDA_VISIBLE_DEVICES="" && . .venv/bin/activate && python3 rsi_loop.py
```

## Timing
- **Hardware**: i7-6700 (8 threads), 32GB RAM
- **Model**: Qwen2.5-0.5B-Instruct, float32 (CPU)
- **Steps**: 135 (200 sampled from 1,279 deduped, 3 epochs, batch_size=4, micro_batch=1)
- **Per step**: ~18-33s (varies with token count)
- **Total**: 3,681s (~61 min) — longer than previous ~46 min, likely due to heavier average context length in this cycle's training data
- **Data**: 200 samples from 1,279 deduped code examples (indexed 100 files → 1,415 raw)

## Training Results
- **Train loss trend**: 3.0 → 0.25 at best
- **Eval metrics**: 5 eval checkpoints across 3 epochs
  - Epoch 1 eval: entropy=0.93, acc=0.81
  - Epoch 2 eval: entropy=0.65, acc=0.83
  - Epoch 3 eval: entropy=0.57, acc=0.83
- **Mean token accuracy peak**: 0.936

## Outputs
- **Adapter**: `adapters/rsi_20260713_052534/`
- **Merged model**: `models/rsi_merged_20260713_052543/`
- **Latest symlinks**: `adapters/latest` and `models/latest` updated

## Inference Test
All 3 prompts produced coherent responses:
1. "What is a linked list?" → reasonable data structure definition
2. "Write a function to check if a number is prime" → Python code referencing actual project path (`MUTS/check_prime.py`) — model learned from codebase
3. "What's in my codebase?" → Helpful but appropriately cautious response

## Data Sources This Cycle
- **Code indexer**: 1,415 raw → 1,279 deduped (100 files, ForgeKeeper-mcp dir missing)
- **Synapse Memory**: 0 (no Nexus server on lin)
- **Session history**: 0 (DB reader not connected)

## Crank vs Previous CPU Run (2026-07-10)
| Metric | 2026-07-10 | 2026-07-13 |
|--------|-----------|-----------|
| Time | ~46 min (2,756s) | ~61 min (3,681s) |
| Raw examples | 1,357 → 1,227 | 1,415 → 1,279 |
| Steps | 135 | 135 |
| Best eval entropy | 0.57 | 0.57 |
| Path | `export` or `bash -c` | `export` confirmed working |
