---
name: llm-finetune-dataset-authoring
description: Author and validate LLM fine-tuning JSONL datasets.
---

# LLM Fine-Tune Dataset Authoring

Build real, validated JSONL training data — not filler. Applies the user's
zero-stub / real-execution bar to datasets: every entry must be substantive,
technically accurate content, and every output must be machine-validated
before it's called done.

## When to use
- User asks for a "training jsonl", "fine-tune dataset", "SFT data", or data
  for axolotl / TRL (SFTTrainer) / unsloth / llama-factory.
- You need to pick the right record shape for a target trainer, or verify an
  existing dataset parses and is well-formed.
- You are expanding an existing dataset (adding a new domain/topic section).

## Decide the format first (driven by the trainer)
The two common record shapes:
- **ChatML / `messages`** — `{"messages": [{"role":..,"content":..}, ...]}`.
  Accepted directly by axolotl, TRL SFTTrainer, unsloth, llama-factory, and
  most modern fine-tuners. This is the safest default.
- **`instruction`/`output`** — `{"instruction":.., "output":..}` (optionally
  `input`). Older alpaca-style format; many trainers convert it internally,
  but prefer ChatML unless the user explicitly names a trainer that wants
  the flat shape.

Default to **ChatML with a system prompt** prepended to every record. Ask
only if the trainer/format is genuinely ambiguous — the user prefers that you
just pick the standard and go.

## Authoring rules (the user's bar)
- Real content, never placeholder/filler. An entry that's a stub or a
  paraphrased one-liner is a defect, same as a code stub.
- Match content to the domain the user actually works in, not generic
  surface knowledge. For a technical user, entries should read like a senior
  practitioner answering: exact partition names, real commands, named tools,
  real offsets/IDs, stated risks. Depth over breadth.
- Keep assistant answers substantive (several hundred chars each) but don't
  pad. Each answer should stand alone with no hallucinated specifics.
- Group entries into labeled sections so the file stays maintainable and you
  can extend one domain without touching the rest.

## Build pattern: generator + validator
Do NOT hand-write the raw .jsonl. Keep a small Python builder script that
holds the curated content as a data structure and writes valid JSONL, then
re-validate on every run. This makes expansion (add to the list, rerun) and
reproducibility trivial. See `scripts/validate_finetune_jsonl.py` for the
validator half.

```python
SYSTEM = "..."   # one consistent system prompt for every record
DATA = [         # list of (role, content) turns; system prepended in build()
    [("user", "Q1"), ("assistant", "A1...")],
    ...
]
def build():
    with open(OUT, "w") as fh:
        for turns in DATA:
            msgs = [{"role":"system","content":SYSTEM}]
            for role, content in turns:
                msgs.append({"role":role, "content":content})
            fh.write(json.dumps({"messages":msgs}) + "\n")
```

## Validation invariants (always run before "done")
Check every line:
- Line parses as JSON (reject on `json.JSONDecodeError`).
- `messages` is a non-empty list.
- First role is `system`.
- Every role is one of `{system, user, assistant}`.
- Every `content` is a non-empty string.
- File has at least one record; report count + total size.

## Pitfalls
- **Pipe trap**: don't validate by `head -1 file | python -c "json.loads(...)"`
  — stdin/pipe handling makes this flaky and produces confusing errors. Read
  the file directly in a script and loop lines.
- **Format mismatch**: a record in `instruction/output` shape fed to a trainer
  expecting ChatML (or vice versa) silently degrades. State the format
  explicitly.
- **Count != quality**: a validated record count is necessary, not sufficient.
  Eyeball a sample record's assistant length and subject depth before signing
  off.
- **Expanding an existing dataset**: use `patch` on the builder's DATA list
  (match the exact tail text) and rerun — never hand-append to the .jsonl.

## Support files
- `scripts/validate_finetune_jsonl.py` — generic re-runnable JSONL dataset
  validator (the invariants above). Run it on any dataset before training.
- `references/format-by-trainer.md` — which record shape each trainer expects,
  and the ChatML spec details.
- `references/example-technical-dataset.md` — worked example: how a firmware/
  RE domain dataset was structured (the Android firmware + reverse-engineering
  set), showing sectioning and depth per entry.
