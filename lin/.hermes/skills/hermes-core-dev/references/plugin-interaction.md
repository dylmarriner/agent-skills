# Loading Hermes Plugin Modules from Cron/Sandbox Context

When a cron job or any context needs to call a Hermes plugin's functions (e.g.,
`subconscious.tick()`), the `execute_code` sandbox cannot import plugin modules
because its `sys.path` is isolated — it only contains the sandbox itself and
stdlib paths.

## The Working Pattern

Use `importlib.util.spec_from_file_location` from a `terminal()` python3 -c
one-liner, not from `execute_code`:

```python
import importlib.util
spec = importlib.util.spec_from_file_location('module_name', '/abs/path/to/__init__.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
result = mod.function()
```

## Concrete Example (subconscious plugin)

```bash
python3 -c "
import importlib.util
spec = importlib.util.spec_from_file_location('subconscious', '/home/lin/.hermes/plugins/subconscious/__init__.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
result = mod.tick()
print('TICK:', result)
"
```

## Why `execute_code` Doesn't Work

- The `execute_code` sandbox creates an isolated temp directory — `sys.path`
  does not include Hermes plugin paths like `/home/lin/.hermes/plugins/`.
- Even calling `sys.path.insert(0, '/home/lin/.hermes/plugins/subconscious')`
  inside `execute_code` fails because the sandbox's Python process has no
  access to the filesystem paths outside its sandbox root.
- `terminal()` runs as the user directly and has full filesystem access.

## When to Use This

- Cron jobs that need to call plugin lifecycle functions (`tick()`, `sync()`)
- Pre-LLM-call hook testing / verification
- Plugin state inspection from CLI tooling
- Any script that needs to interact with plugin-managed state (goals, memory,
  diff tracking) outside a live Hermes session
