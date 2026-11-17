---
name: parsec-trim
description: Compact this Codex session — a deterministic needed-set trim plus standing directives
---
<!-- parsec-managed-skill: written by `parsec setup codex`; removed by `parsec disable codex`. -->

Two steps, both through the parsec binary. NEVER summarize the session yourself — step 1 is deterministic and step 2 is the only part you write.

1. Run `~/.parsec/bin/parsec trim --tool codex || parsec trim --tool codex`. It computes which parts of this session were actually re-read, edited, or used later and stages them. Exit code 2 means there is nothing worth compacting yet — say so and stop. Its token numbers are chars/4 ESTIMATES; never present them as measured.

2. Write a STANDING DIRECTIVES block from your own context — the durable rulings, constraints, and scope decisions of this session, NOT a summary of the work — and pipe it in:

```
printf '%s' "<your directives>" | ~/.parsec/bin/parsec trim --finalize
```

Then tell the user to start a fresh Codex session: the staged trim is injected once, at the next session start, and expires unused after 30 minutes. Do not start that session yourself.
