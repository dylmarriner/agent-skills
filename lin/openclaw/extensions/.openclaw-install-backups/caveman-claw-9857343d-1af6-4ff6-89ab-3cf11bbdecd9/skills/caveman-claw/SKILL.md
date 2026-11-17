---
name: caveman-claw
description: Activate and manage caveman-speak output mode to reduce token cost. Handles /cc activation, /cc compress for context file shrinking, and /cc stats for savings reporting.
---

# Caveman Claw

Caveman Claw reduces LLM token usage by making the AI respond in terse, fragment-based caveman-speak.

## Commands

- `/cc` or `/cc full` — activate full caveman mode (default)
- `/cc lite` — drop filler only, keep full sentences
- `/cc ultra` — maximum compression with abbreviations
- `/cc compress <file>` — compress a context file in-place
- `/cc stats` — show token savings report
- `normal` or `stop caveman` — deactivate caveman mode

## Reference

- [Caveman mode rules](references/caveman-mode.md)
- [File compression](references/compress.md)
- [Savings stats](references/stats.md)
