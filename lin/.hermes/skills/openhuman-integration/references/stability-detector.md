# Learning Stability Detector

The stability detector is the core of the learning plugin's Phase 2. It converts
a stream of evidence (from the buffer) into durable, scored facets.

## Scoring Formula

```
stability = min(1.0, total_weight × 0.1 × best_share × recency)
```

Where:
- **total_weight** = Σ(evidence_weight × decay) for all evidence matching (class, key)
- **evidence_weight** = family weight × decay factor
- **family weights**: explicit=1.0, structural=0.9, behavioral=0.7, recurrence=0.6
- **decay** = 2^(-age / half_life) — exponential decay with 300s half-life
- **best_share** = highest value's weighted_count / total_weight — confidence that the winning value is correct
- **recency** = 2^(-age / (half_life × 6)) — slow decay for facet freshness

## Conflict Resolution

When multiple values exist for the same (class, key), the value with the highest
weighted support wins. Example:

```
Evidence for (style, verbosity):
  "concise" via explicit family × decay 0.9 = 0.9
  "concise" via behavioral family × decay 0.7 = 0.7
  "verbose" via behavioral family × decay 0.5 = 0.35
  → total_weight = 1.95
  → "concise" share = (0.9 + 0.7) / 1.95 = 0.82
  → "verbose" share = 0.35 / 1.95 = 0.18
  → "concise" wins
```

## Per-Class Budgets

| Class   | Budget |
|---------|--------|
| style   | 10     |
| identity| 8      |
| tooling | 8      |
| veto    | 5      |
| goal    | 5      |
| channel | 3      |

When a class exceeds its budget, only the top-N facets by stability score are retained.

## Pruning Threshold

Facets with score < 0.15 are pruned — they represent weak or contradictory signals
that haven't accumulated enough evidence to be reliable.

## Context Injection

Stable facets are rendered into a context block injected via the `pre_llm_call` hook:
```
[Learning Profile]
  Communication style: concise
  Tooling: uses pnpm
  Identity: developer
[/Learning Profile]
```

This block is updated every `rebuild_interval` seconds (default: 300) when new
buffer evidence exists. Empty sections (no stable facets) are omitted.
