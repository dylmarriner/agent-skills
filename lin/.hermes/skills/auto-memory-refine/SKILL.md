---
name: auto-memory-refine
description: Run AutoMemory's critic/improver testing cycle with deterministic baselines and controlled memory experiments.
---

# AutoMemory Refine

Read **the full** `/home/lin/.hermes/automemory/commands/auto-memory-refine.md`, especially its Critic-versus-Improver separation and state invariants.

- Require completed implementation and `refine_state.json`. Validate it using `/home/lin/.hermes/automemory/scaffolds/check_refine_state.py`.
- Use a **separate** Critic agent for tests and scoring, do not let the Improver self-grade.
- Limit iterations, costs, resource use and scope; ask the owner before prolonged paid or destructive runs.
- Verify retrieval accuracy, persistence across sessions, false positives, deduplication, context/token cost, latency, and robustness against poisoned memories.
- Apply improvements only in isolated development worktrees. Do not deploy an unreviewed evolved configuration to Hermes or SCOS.
- Finish by validating state and reporting measured differences against baseline.
