# Subconscious Plugin — Tick Interaction

## Location

The subconscious plugin may live at any of these locations — check each:

- `~/.hermes/plugins/subconscious/` (user-installed — primary path on most setups)
- `~/.hermes/plugins.local/subconscious/` (user-installed — alternate path on some setups)
- `/mnt/hermes-profile-nfs/plugins/subconscious/` (NFS-mounted shared profile)
- `~/.hermes/hermes-agent/plugins/subconscious/` (packaged with Hermes)

There is also an empty directory at `~/.hermes/subconscious/` — ignore it; that's the *state store*, not the plugin module. The real `__init__.py` is in one of the plugin paths above.

## State files

- `~/.hermes/subconscious/state.json` — tick count, last tick timestamp, last diff summary, baseline checkpoint
- `~/.hermes/subconscious/goals.json` — goal store (empty = no active goals)
- `~/.hermes/subconscious/briefing.md` — generated brief output

## Import patterns

### Preferred (sys.path + bare import)
Works when the plugin's parent dir is on `sys.path`. The parent dir may be
`plugins/` or `plugins.local/` — check both:
```python
import sys
# Try plugins first (common), then plugins.local (alternate)
sys.path.insert(0, '/home/lin/.hermes/plugins')

import subconscious
result = subconscious.tick()
state = subconscious.get_state()
goals = subconscious.get_goals()
```

### Fallback (importlib.util.spec_from_file_location)
Robust when the plugin lives outside `sys.path` (e.g. NFS mount, or the `plugins/` parent dir has no `__init__.py` so dotted-path imports fail). Works regardless of package structure:
```python
import sys
import importlib.util

plugin_path = "/mnt/hermes-profile-nfs/plugins/subconscious/__init__.py"
spec = importlib.util.spec_from_file_location("subconscious", plugin_path)
mod = importlib.util.module_from_spec(spec)
sys.modules["subconscious"] = mod
spec.loader.exec_module(mod)

result = mod.tick()
state = mod.get_state()
goals = mod.get_goals()
```

NOT `from subconscious.__init__ import tick` — that raises `ModuleNotFoundError` because `__init__` is implicit; use the bare module name.

## What tick() returns

Returns a diff string like `"Tick #187 at 2026-07-15 07:40: 0 active goals"`.

The tick increments `tick_count` in state.json regardless of whether goals exist.

## Full Plugin API

The subconscious plugin exposes these functions for programmatic use:

| Function | Purpose |
|---|---|
| `tick()` | Execute observe → reflect → commit cycle. Returns diff string. |
| `get_state()` | Read `state.json` dict. Keys: `last_tick_at`, `tick_count`, `last_diff_summary`, `brief_updated_at`, `baseline_checkpoint_id`. |
| `save_state(state)` | Write `state.json` dict. |
| `get_goals()` | Read `goals.json` — returns list of goal dicts. |
| `save_goals(goals)` | Write `goals.json`. |
| `add_goal(title, description="", priority="medium", tags=None)` | Create and persist a new active goal. Priority must be one of: `critical`, `high`, `medium`, `low`. Returns the goal dict with auto-generated `id` (e.g. `"g1742178000"`). |
| `update_goal(goal_id, title=..., description=..., priority=..., state=..., tags=..., note=...)` | Update a goal's fields or append a progress note (via `note=`). Valid states: `active`, `paused`, `completed`, `abandoned`. Returns the goal dict or `None` if not found. |
| `list_active_goals()` | Return active goals sorted by priority order. |

### Hook registration

```python
def register(ctx):
    """Register the Subconscious pre_llm_call hook."""
    _ensure_dirs()
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
```

The `pre_llm_call` hook injects a `[SUBSCONSCIOUS — Active Goals]` block into the LLM prompt. It runs on a 5-minute cooldown (`_INJECTION_COOLDOWN = 300`) and only fires when active goals exist. Cooldown is global (module-level `_LAST_INJECTION` variable), so it persists across imports within the same process.

### Plugin metadata

From `plugin.yaml`:
```yaml
name: subconscious
version: "1.0.0"
hooks:
  - pre_llm_call
provides_hooks:
  - pre_llm_call
```

## When the goal store is empty

- `tick()` still runs and increments tick_count
- `get_goals()` returns `[]`
- No brief is generated
- The `pre_llm_call` hook quietly returns None (cooldown check passes, but no goals to inject)
