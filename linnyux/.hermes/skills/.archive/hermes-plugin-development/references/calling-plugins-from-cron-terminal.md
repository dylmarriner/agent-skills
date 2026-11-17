# Calling Hermes Plugin Functions from Cron / Terminal Context

When a cron job or background task needs to invoke a Hermes plugin's exported
functions (e.g. `subconscious.tick()`, `get_state()`, `get_goals()`) directly
rather than through the agent loop, you must bootstrap the import path
manually — the Hermes sandbox (`execute_code`) does not have `~/.hermes/plugins/`
on its `sys.path`.

## Bootstrapping Steps

```bash
# 1. Activate the Hermes venv (path varies by install method — find yours)
source /home/lin/.hermes/hermes-agent/venv/bin/activate

# 2. Run the plugin function(s)
python3 -c "
import sys
sys.path.insert(0, '/home/lin/.hermes/plugins')
from subconscious import tick, get_state, get_goals

result = tick()
state = get_state()
goals = get_goals()

print('Tick result:', result)
print('Active goals:', len([g for g in goals if g.get('state') == 'active']))
"
```

## Venv Path Discovery

The venv might live at different paths depending on the Hermes version
and install method. Find yours at runtime:

```bash
# Method 1: check the standard Hermes venv
ls /home/lin/.hermes/hermes-agent/venv/bin/activate

# Method 2: which Python does Hermes use?
which python3  # may or may not be the Hermes venv python

# Method 3: from inside a Hermes session, the sys.path includes
# the venv site-packages — extract the prefix:
python3 -c "import sys; print([p for p in sys.path if 'hermes-agent/venv' in p])"
```

## Alternative: importlib.import_module (Recommended for execute_code)

When `plugins/` has a valid `__init__.py` (Hermes ships one at
`~/.hermes/plugins/__init__.py`), the cleanest approach from `execute_code`
is to add `~/.hermes` to `sys.path` and use `importlib.import_module`:

```python
import sys, os, importlib

plugins_parent = os.path.expanduser("~/.hermes")
sys.path.insert(0, plugins_parent)

mod = importlib.import_module("plugins.subconscious")
result = mod.tick()
```

This is more readable than `spec_from_file_location` and works for any
non-hyphenated plugin name. It also keeps the module reference in a named
variable so you don't pollute the namespace with all plugin symbols.

## Alternative: importlib.util (for hyphenated plugin names)

If the plugin directory has hyphens in its name (blocking `import` and
`importlib.import_module`), fall back to `importlib.util.spec_from_file_location`:

```python
import importlib.util
from pathlib import Path

plugin_path = Path.home() / '.hermes' / 'plugins' / 'my-plugin' / '__init__.py'
spec = importlib.util.spec_from_file_location('my_plugin', str(plugin_path))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
result = mod.tick()
```

(This is the same technique documented in the main skill's "Hyphenated plugin
dir names" pitfall — applies equally in cron context.)

## Alternative: execute_code (Hermes-Internal)

When invoking a plugin function from within a Hermes session (e.g. from the
agent's `execute_code` tool), no venv activation is needed — the sandbox
inherits Hermes's own Python environment. Only `sys.path` needs the plugin
dir:

```python
import sys
sys.path.insert(0, "/home/lin/.hermes/plugins")

from subconscious import tick, get_state, get_goals

result = tick()
state = get_state()
goals = get_goals()
print(f"Tick #{state['tick_count']}: {result}")
print(f"Active goals: {len([g for g in goals if g.get('state') == 'active'])}")
```

**Key difference from shell cron:** `execute_code` already runs in the right
Python (Hermes's own process or venv). Only `sys.path` needs the extra
entry — no shebang, no venv activation, no subprocess overhead.

## Pitfalls

- **Venv path hardcoding** — Do not hardcode the full venv path in a cron job
  that runs across machines. Use a wrapper script or env var.
- **Module state** — Importing a plugin module creates a new in-memory copy.
  If the plugin maintains module-level state (caches, cooldowns), that state
  is fresh for each cron invocation — it does NOT share state with the running
  Hermes session.
- **Two valid sys.path targets** — Use whichever target gives the import style you prefer:

  **Option A:** Add `~/.hermes/plugins` to use plugin names as top-level modules:
  ```python
  sys.path.insert(0, '/home/lin/.hermes/plugins')
  from subconscious import tick  # subconscious/ is top-level
  ```

  **Option B:** Add `~/.hermes` to access plugins via the `plugins` namespace
  (requires `plugins/__init__.py`, which Hermes ships as an empty file):
  ```python
  sys.path.insert(0, '/home/lin/.hermes')
  from plugins.subconscious import tick  # plugins/ is a namespace package
  ```

  Option B pairs naturally with `importlib.import_module("plugins.subconscious")`.
  Option A is simpler for direct `from subconscious import ...` imports.
  Both work — pick the one that feels more natural for your use case.
- **Shebangs** — When writing a standalone script for cron, use the full venv
  Python path in the shebang:
  ```
  #!/home/lin/.hermes/hermes-agent/venv/bin/python3
  ```
- **Lock files** — If the plugin writes state files (e.g. `state.json`),
  concurrent cron + Hermes access may cause races. Use lock files or the
  `cron/subconscious-tick` job path which handles serialization.
