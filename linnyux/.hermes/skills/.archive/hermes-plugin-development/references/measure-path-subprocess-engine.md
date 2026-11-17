# measure-path + Subprocess Engine Integration Pattern

Concrete reference for bundling an external Python engine into a Hermes plugin without copying the engine itself. Used to integrate Token Optimizer into the obelisk plugin.

## Plugin Directory Layout (After Integration)

```
~/.hermes/plugins/obelisk/
├── __init__.py              # Merged registration: obelisk tools + TO hooks
├── plugin.yaml              # Declares both obelisk and TO hooks
├── README.md
├── schemas.py               # Obelisk tool schemas (unchanged)
├── tools.py                 # Obelisk tool handlers (unchanged)
├── hermes_hook_bridge.py    # Copied from TO — shells to measure.py
├── hermes_state.py          # Copied from TO — reads ~/.hermes/state.db
├── hermes_session.py        # Copied from TO — normalizer + quality scorer
├── runtime_env.py           # Copied from TO — runtime detection
├── token_estimate.py        # Copied from TO — char→token estimator
├── utf8_io.py               # Copied from TO — UTF-8 enforcement
├── measure-path             # LOCATOR FILE — one line, absolute path to measure.py
└── skills/
    ├── pack-context.md
    ├── inspect-symbol.md
    ├── compact-output.md
    └── restore-context.md
```

## measure-path Locator Content

A single-line text file:

```
/home/lin/Documents/token-optimizer/skills/token-optimizer/scripts/measure.py
```

The bridge reads it with `.strip()` so trailing newlines are harmless.

## Bridge Resolution Strategy (hermes_hook_bridge.py)

The bridge checks sources in this order:

1. **Sibling `measure.py`** — `Path(__file__).parent / "measure.py"` (dev mode, when working from the repo checkout directly)
2. **`measure-path` locator** — reads the one-line file for the canonical engine path
3. **Fallback paths** — hardcoded list for the install tree

Result is cached ONLY on success. A `None` (missing file) is never cached so subsequent calls retry the stat. This is deliberate: during install the file may not yet exist.

## Hooks Registered

| Hook | Purpose | Returns |
|------|---------|---------|
| `post_api_request` | Accumulate token usage per session | None (observer) |
| `pre_llm_call` | Context-fill nudge when >70% | `{"context": "..."}` or None |
| `on_session_finalize` | Rollup to trends.db (first guard) | None |
| `on_session_end` | Rollup to trends.db (H4 double-fire guard) | None |

## H4 Double-Rollup Guard

Both `on_session_finalize` and `on_session_end` may fire for the same session. A `_ROLLED_UP` set (thread-safe, protected by `_LOCK`) ensures only the first caller spawns the subprocess. The second is a no-op.

## Key Lessons

- **Never copy the engine**. `measure.py` is 1.5MB and updates independently. The locator keeps the plugin pointing at the canonical checkout.
- **Add plugin dir to sys.path** so sibling modules are importable. Append, don't prepend — Hermes core modules keep precedence.
- **Lazy bridge import** so a missing engine doesn't crash Hermes at plugin load time. Cache only on success.
- **`PYTHONUTF8=1` in subprocess env** ensures clean output from the engine subprocess.
- **`start_new_session=True`** for fire-and-forget subprocesses (rollups) so they don't get killed when Hermes exits.
