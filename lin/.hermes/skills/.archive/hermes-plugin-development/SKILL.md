---
name: hermes-plugin-development
description: "Design, build, and debug Hermes plugins — hooks, tools, memory providers, plugin.yaml, and best practices for extending the agent."
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [hermes, plugins, hooks, tools, development, integration]
    related_skills: [hermes-agent, hermes-agent-skill-authoring]
---

# Hermes Plugin Development

Build Hermes plugins that add tools, lifecycle hooks, and platform integrations. This skill covers the architecture, available hook points, tool registration, and the full workflow from idea to enabled plugin.

## Overview

A Hermes plugin is a directory under `~/.hermes/plugins/<name>/` containing:

```
~/.hermes/plugins/<name>/
├── plugin.yaml       # Manifest — name, version, hooks, env requirements
├── __init__.py       # Entry point — register() function is the contract
├── tools.py          # (optional) Tool handler implementations
├── schemas.py        # (optional) Tool JSON schemas for LLM
└── cli.py            # (optional) CLI subcommand definitions
```

The contract is minimal: a plugin **must** have a `plugin.yaml` and an `__init__.py` with a `def register(ctx)` function. Everything else is optional.

## Plugin Manifest (plugin.yaml)

```yaml
name: my-plugin
version: "1.0.0"
description: "What this plugin does in one line."
author: Your Name
hooks:
  - pre_tool_call
  - post_tool_call
provides_hooks:
  - pre_tool_call
  - post_tool_call
requires_env:
  - name: MY_API_KEY
    description: "API key for the external service"
    secret: true
```

Fields:
- `name`: lowercase, hyphens, must match directory name
- `hooks`: list of hook names the plugin registers (informational)
- `provides_hooks`: same as hooks — both are informational, not enforced
- `requires_env`: env vars the plugin needs, shown in `hermes tools` diagnostics

## Register Function (__init__.py)

Every plugin exports a `register(ctx)` function called once at load time:

```python
import logging
logger = logging.getLogger(__name__)

def register(ctx):
    """Called by Hermes when the plugin is loaded."""
    ctx.register_hook("pre_tool_call", my_pre_hook)
    ctx.register_hook("post_tool_call", my_post_hook)
    ctx.register_tool(
        name="my_tool",
        toolset="my-plugin",
        schema=MY_TOOL_SCHEMA,
        handler=my_tool_handler,
        emoji="🔧",
    )
    logger.info("my-plugin: registered")
```

`ctx` is a `PluginContext` instance with these registration methods:

| Method | Purpose |
|--------|---------|
| `register_hook(name, callback)` | Lifecycle observer |
| `register_tool(name, toolset, schema, handler, ...)` | New model-visible tool |
| `register_cli_command(name, help, setup_fn, handler_fn)` | `hermes <subcommand>` |
| `register_command(name, handler, description)` | In-session `/slash` command |
| `register_skill(name, path, description)` | Plugin-provided skill |
| `register_middleware(kind, callback)` | Behavior-changing middleware |
| `register_auxiliary_task(key, display_name, description, defaults)` | LLM task routing |
| `register_platform(name, ...)` | New messaging channel |

## Available Hook Points

From `hermes_cli/plugins.py::VALID_HOOKS`:

### Tool Lifecycle
- `pre_tool_call(tool_name, args, ...)` — **can mutate args**. Used by RTK rewrite, security checks.
- `post_tool_call(tool_name, result, ...)` — observe results after execution.
- `transform_terminal_output(output, ...)` — **return a string to replace** terminal stdout. First non-None wins.
- `transform_tool_result(result, tool_name, ...)` — **return a string to replace** any tool result. First non-None wins.
- `transform_llm_output(...)` — modify LLM response text before it reaches the user.

### LLM Lifecycle
- `pre_llm_call(...)` — **return `{"context": "..."}` to inject into the user message** before LLM call. Used for memory prefetch, goal injection.
- `post_llm_call(...)` — observe LLM response.

### API Lifecycle
- `pre_api_request(request, ...)` — observe outbound API calls.
- `post_api_request(response, ...)` — observe API responses.
- `api_request_error(error, ...)` — observe API errors.

### Session Lifecycle
- `on_session_start(session_id, ...)` — session begins.
- `on_session_end(...)` — session ends (cleanup here).
- `on_session_finalize(...)` — session fully finalized.
- `on_session_reset(...)` — session reset.

### Approval & Verifications
- `pre_approval_request(command, description, ...)` — user approval prompt about to fire.
- `post_approval_response(choice, ...)` — user made a choice.
- `pre_verify(...)` — agent about to verify/finish editing code.

### Subagent Lifecycle
- `subagent_start(...)` — subagent spawned.
- `subagent_stop(...)` — subagent finished.

### Gateway
- `pre_gateway_dispatch(event, gateway, ...)` — incoming message before routing. Can return `{"action": "skip"}`, `{"action": "rewrite", "text": "..."}`, or `None`.

### Kanban
- `kanban_task_claimed(task_id, ...)` — dispatcher claims a task.
- `kanban_task_completed(task_id, summary, ...)` — worker completes a task.
- `kanban_task_blocked(task_id, reason, ...)` — task is blocked.

## Plugin Architecture Patterns

### Pattern 1: Transform Hook (inject/compress output)

Best for: compression, canonicalization, formatting.

```python
def register(ctx):
    ctx.register_hook("transform_terminal_output", my_transform)

def my_transform(output: str, **kwargs) -> str | None:
    """Return None to leave unchanged, return str to replace."""
    if not output or len(output) < 512:
        return None
    # ... compression logic ...
    if compressed_bytes >= original_bytes * 0.95:
        return None  # Don't make it worse
    return compressed
```

**Signature rules:**
- Return `None` → leave output unchanged (no-op).
- Return `str` → replace the output entirely.
- First non-None return among all registered plugins wins.

### Pattern 2: Pre-LLM Context Injection

Best for: memory prefetch, goal injection, tool memory rules.

```python
def register(ctx):
    ctx.register_hook("pre_llm_call", my_context)

def my_context(**kwargs) -> dict | None:
    return {"context": "[GOALS] Implement OAuth2 flow [/GOALS]"}
```

The `context` string is appended to the user message before it reaches the LLM.

### Pattern 3: Pre-Tool Mutation

Best for: command rewriting, argument validation, security gates.

```python
def register(ctx):
    ctx.register_hook("pre_tool_call", my_modifier)

def my_modifier(tool_name=None, args=None, **kwargs):
    if tool_name != "terminal" or not isinstance(args, dict):
        return
    command = args.get("command", "")
    args["command"] = rewritten_command
```

### Pattern 4: Memory Provider

Best for: custom memory backends (requires implementing `MemoryProvider` ABC).

See: `agent/memory_provider.py` for the abstract base class.
Plugins go in `~/.hermes/plugins/memory/<name>/` (not `~/.hermes/plugins/`).

### Pattern 6: Bundled Subprocess Engine (measure-path + Bridge)

Best for: delegating heavy work to an external Python engine (token tracking, dashboard serving, complex rollup logic) without embedding the engine directly in the plugin.

Architecture: a thin Hermes plugin → bridge module → subprocess → shared engine.

```
plugin/__init__.py        # register() — hooks + slash commands
plugin/hermes_bridge.py   # locates & shells to measure.py via subprocess
plugin/hermes_state.py    # read-only DB reader (sibling module, not engine)
plugin/measure-path       # ONE-LINE FILE: absolute path to the engine's measure.py
external/measure.py        # THE SHARED ENGINE (not copied — version drift risk)
```

**Key decisions:**

1. **Do NOT copy the engine into the plugin dir.** Copying `measure.py` means the plugin runs a stale copy until the user remembers to re-install. Instead, write a one-line locator file (`measure-path`) containing the absolute path of the canonical `measure.py` in the checkout. The bridge reads it at call time.

2. **Bundle only the thin runtime modules.** The plugin copies small sibling modules (`hermes_state.py`, `hermes_session.py`, `runtime_env.py`) that the bridge needs at import time. These are stable enough to bundle; the main engine stays unhooked.

3. **Add the plugin dir to `sys.path`** so bundled sibling modules resolve correctly whether loaded from the install tree or the repo checkout:
   ```python
   _PLUGIN_DIR = Path(__file__).parent.resolve()
   sys.path[:] = [p for p in sys.path if p != str(_PLUGIN_DIR)]
   sys.path.append(str(_PLUGIN_DIR))
   ```
   Append at the end so Hermes core modules keep import precedence.

4. **Lazy-import the bridge** so missing engine doesn't crash Hermes at load time:
   ```python
   _SENTINEL = object()
   _bridge_cache = _SENTINEL
   def _import_bridge():
       global _bridge_cache
       if _bridge_cache is not _SENTINEL:
           return _bridge_cache
       try:
           import hermes_bridge as b
           _bridge_cache = b
           return b
       except Exception:
           return None  # don't cache None — retry next call
   ```

5. **Bridge subprocess pattern** — use `subprocess.Popen` with `start_new_session=True` for fire-and-forget rollups, `subprocess.run` with `capture_output=True` for synchronous summaries. Set `PYTHONUTF8=1` in the env so the subprocess produces clean output.

6. **The measure-path locator** — a one-line text file in the plugin dir:
   ```
   /home/user/Documents/external-tool/scripts/measure.py
   ```
   The bridge checks for the sibling `measure.py` first (dev mode), then reads the locator, then checks fallback paths. Cache only on success so a transiently missing file is retried.

**Reference:** See `~/.hermes/plugins/obelisk/` for a complete example — obelisk tools (Rust CLI) + token-optimizer hooks (Python subprocess engine) merged into one plugin.
See `references/measure-path-subprocess-engine.md` for the full integration reference (file layout, bridge resolution, hooks, H4 guard).

### Pattern 5: REST API Client (5-Tool Integration)

Best for: connecting Hermes to external services with a REST API (RAGFlow, self-hosted tools, SaaS backends).

The canonical five-tool surface follows a health → list → create → search → chat progression:

```python
# 1. Health — check if server is running
service_health(args) -> str

# 2. List/Create — resource management
service_datasets(args) -> str

# 3. Upload — file/artifact ingestion
service_upload(args) -> str

# 4. Search — retrieve ranked results
service_search(args) -> str

# 5. Chat — conversational query with context
service_chat(args) -> str
```

**Plugin structure:**

```python
import os, requests

BASE_URL = os.environ.get("SERVICE_URL", "http://localhost:PORT")
API_KEY = os.environ.get("SERVICE_API_KEY", "")

def register(ctx):
    for name, schema, handler, emoji in _TOOLS:
        ctx.register_tool(name=name, toolset="service", schema=schema,
                         handler=handler, emoji=emoji)

def _request(method, path, **kwargs) -> dict:
    """Single request helper with auth, timeout, error handling."""
    headers = {"Authorization": f"Bearer {API_KEY}"}
    try:
        resp = requests.request(method, f"{BASE_URL}/api/v1{path}",
                                headers=headers, timeout=30, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {"error": f"Cannot connect to {BASE_URL}"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
```

**Tool schema pattern:**

```python
HEALTH_SCHEMA = {
    "name": "service_health",
    "description": "Check if the service is running.",
    "parameters": {"type": "object", "properties": {}},
}

LIST_SCHEMA = {
    "name": "service_list",
    "description": "List resources.",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "create"],
                "description": "list: show items. create: make a new one.",
            },
            "name": {"type": "string", "description": "Name (required for create)"},
        },
        "required": ["action"],
    },
}
```

**Pitfalls:**
- Error responses vary by service — wrap all calls in try/except with generic fallback
- API keys belong in env vars via `requires_env` in plugin.yaml, not in code
- Always set a timeout on requests (default 30s) to avoid hanging the tool loop
- File uploads need the `files=` parameter to requests, not `json=`
- Service may not be running when Hermes starts — the health tool should be the first thing the agent calls
- Schema descriptions are critical: the LLM reads them to decide when to use each tool

**Reference:** See `~/.hermes/plugins/ragflow/__init__.py` for a complete working example with all 5 tools, request helper, and per-tool error handling.

When integrating features from another agent framework (OpenHuman, TinyAgents, LangChain, etc.):

### Step 1: Analyse the external feature
- Read the README, AGENTS.md, and module READMEs
- Identify the core mechanism (not the UI)
- Map to a Hermes pattern:
  - **Output transformation** → `transform_terminal_output` / `transform_tool_result`
  - **Background processing** → Cron job + state file
  - **Context injection** → `pre_llm_call` hook
  - **Memory/storage** → Memory provider plugin (`plugins/memory/`), or standalone SQLite
  - **Tool execution** → `register_tool()` with handler
  - **Command rewriting** → `pre_tool_call` hook

### Step 2: Build the plugin scaffold
```
mkdir -p ~/.hermes/plugins/<name>/
# plugin.yaml + __init__.py with register()
```

### Step 3: Implement one hook/tool at a time
- Keep each handler focused and self-contained
- Fail open: catch exceptions and log, never crash Hermes
- Use `logger` from `logging.getLogger(__name__)` for diagnostics

### Step 4: Enable in config.yaml
```bash
hermes config set plugins.enabled '["existing","new-plugin"]'
hermes config set new-plugin.some_option value
```

### Step 5: Bundle runtime dependencies (when delegating to an external engine)

If the external tool provides a large shared engine (dashboard, rollup, analytics) that would bloat or drift if copied:

- **Copy thin runtime modules** (bridge, DB reader, session normalizer) into the plugin dir
- **Write a `measure-path` locator** — one text file containing the absolute path to the external `measure.py`. The bridge reads it at call time to shell into the engine via subprocess
- **Do NOT copy the engine itself** — it would silently drift as the external repo updates
- Add the plugin dir to `sys.path` so bundled sibling modules resolve without Hermes core being affected

### Step 6: Verify
- Restart Hermes (CLI reads config at startup)
- Check logs for registration messages
- Confirm hooks fire by checking behavior

## Debugging Plugins

### Check if plugin loaded
```bash
hermes plugins list                 # Shows all discovered plugins
hermes plugins list --verbose       # With registration details
```

### Check specific hook status
```bash
hermes hooks list                   # Shows registered hooks
```

### Config validation
```bash
hermes config get plugins           # Check enabled/resolved state
```

### Logs
Plugin logs go to the Hermes log file. Enable debug logging:
```bash
hermes config set logging.level DEBUG
```

## Common Pitfalls

1. **Plugin not loading** — Check plugin.yaml name matches directory name. Check `plugins.enabled` in config.yaml includes the name. Restart Hermes.

2. **Hook not firing** — Verify hook name in `VALID_HOOKS`. `transform_terminal_output` fires per-terminal-call, not per-turn. `pre_llm_call` fires every LLM invocation. Some hooks only fire in gateway mode, not CLI.

3. **Tool not visible to model** — Tools registered via `register_tool()` appear in the model's tool list at session start. They do NOT appear mid-session. Restart Hermes.

4. **Return type mismatch** — `transform_terminal_output` and `transform_tool_result` expect `str | None`. `pre_llm_call` expects `dict | None` with `{"context": "..."}`. Wrong return type is silently ignored.

5. **`hermes config set` needed for arrays** — Pass JSON: `hermes config set plugins.enabled '["a","b"]'`. YAML-style brackets in shell need quoting.

6. **Plugin dir in wrong location** — User plugins go in `~/.hermes/plugins/<name>/`, NOT `~/.hermes/hermes-agent/plugins/`. The latter is for bundled/core plugins.

7. **Memory provider plugins are special** — They go in `~/.hermes/plugins/memory/<name>/` (not `~/.hermes/plugins/<name>/`), subclass `MemoryProvider`, and are single-select (only one active at a time).

8. **`global` declarations needed for module-level mutable state** — If a plugin caches state in module-level variables (e.g. `_cache = {}`, `_size = 0`), and a function both *reads* and *writes* that variable, Python requires `global <name>` inside the function. Reading without writing works; adding an assignment (`_size += data`) without `global` raises `UnboundLocalError`. Always declare `global` for any module-level name that gets assigned in a function body. See `~/.hermes/plugins/tokenjuice/__init__.py` for a working example with `_ccr_size`.

9. **Transform hooks: 95% threshold for pass-through** — If a transform hook compresses text but the result is 95% or more of the original size, return `None` (don't replace). The overhead of storing a compressed version that barely saves anything isn't worth it. Check: `if compressed_bytes >= original_bytes * 0.95: return None`.

10. **Different size thresholds per content kind** — Log output often has high repeat density even at small sizes; code and JSON need more mass before compression pays off. Use a separate `min_bytes` for logs (e.g. 512) vs generic content (e.g. 2048). Hard-coding one threshold for all kinds misses savings on dense logs and wastes cycles on tiny code blocks.

11. **Hyphenated plugin dir names block Python `import`** — `plugin.yaml` allows hyphens in `name`, and Hermes loads plugins by directory name regardless. But if you need to import a plugin's code for testing, `from synapse_memory import ...` fails because Python module names cannot contain hyphens. Use `importlib` instead:
    ```python
    import importlib
    spec = importlib.util.spec_from_file_location(
        'my_name', '~/.hermes/plugins/my-plugin/__init__.py'
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    result = mod.some_function({})
    ```
    When Hermes loads the plugin natively (not during manual testing), this is transparent — the plugin loader uses the directory name internally and doesn't care about Python import rules. The issue only surfaces when you try `from plugins.my_plugin import ...` from a Python REPL to test tool handlers. Name your plugin directory without hyphens to avoid it entirely.

12. **Canonical source is the repo, not the installed copy** — When a plugin's canonical source lives in a companion repo (e.g. `obelisk/plugins/hermes-obelisk/`), the repo IS the truth. The installed copy at `~/.hermes/plugins/<name>/` is a deployment artifact — changes there are lost on the next re-install. Edit in the repo, sync to the installed copy, commit. If you already edited the installed copy, diff-and-sync back to the repo before committing.

## Calling Plugin Functions from Cron / Terminal / execute_code

When a cron job, systemd timer, or Hermes `execute_code` block needs to invoke
a Hermes plugin's exported functions (e.g. `subconscious.tick()`,
`get_state()`, `get_goals()`) outside the agent session, the Hermes sandbox
(`execute_code`) does not have `~/.hermes/plugins/` on its `sys.path`. The
bootstrap pattern is:

```bash
source <hermes-venv>/bin/activate
python3 -c "
import sys
sys.path.insert(0, '/home/lin/.hermes/plugins')
from subconscious import tick; print(tick())
"
```

For `execute_code` blocks within a Hermes session, venv activation is
unnecessary — the sandbox inherits Hermes's Python environment. Only
`sys.path` needs the extra entry. Full reference with both approaches,
venv discovery, importlib fallback, and concurrency pitfalls:
`references/calling-plugins-from-cron-terminal.md`.

## Persistent Cache Patterns (CCR)

When building plugins that do lossy compression or information-dropping transformations, implement the **CCR (Compress-Cache-Retrieve)** pattern so the original data is recoverable:

```
compressed_output + "\n\n[PARTIAL view — full original ({size}B): tokenjuice_retrieve "{token}"]"
```

Key design decisions:
- **Content-addressed key**: SHA-256 prefix (32 hex chars) of the original content. Collision-infeasible and doubles as an unguessable capability token.
- **Two-tier storage**: In-memory dict (fast, bounded) + disk directory (persistent, survives restart). Disk is best-effort mirror.
- **FIFO eviction**: Bound by max entries and max total bytes. Evict oldest first when either limit is hit.
- **Per-block markers**: Beyond a full-original footer, each omitted gap can carry its own marker for block-level retrieval without fetching the whole payload.
- **Retrieval safety**: The retrieval tool is never re-compressed by the transform hook (check tool name and skip).
- **Lossy gating**: Only apply lossy compression when CCR is available. If CCR is full or disabled, fall back to lossless-only.

## Reference Examples

See `references/examples/openhuman-integration.md` for a real-world case study: porting TokenJuice compression, Subconscious background processing, and Memory Tree storage from OpenHuman into Hermes plugins.

See `~/.hermes/plugins/tokenjuice/` for working transform-hook plugin code.
See `~/.hermes/plugins/subconscious/` for working pre_llm_call hook plugin code.
See `~/.hermes/plugins/memory_tree/` for standalone SQLite-backed storage plugin code.
