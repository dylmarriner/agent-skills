# Config Loader — Architecture Reference

## Config Paths

All resolve from `$HERMES_HOME` (default `~/.hermes/`):

| Path | Purpose |
|------|---------|
| `config.yaml` | Main config — model, providers, toolsets, agent settings |
| `.env` | Secrets & API keys |
| `/etc/hermes/config.yaml` | **Managed scope** (NixOS-declared overlays) |

## Load Pipeline (`_load_config_impl` in `hermes_cli/config.py`)

```
hardcoded DEFAULT_CONFIG → deepcopy → deep_merge(user YAML)
                                → normalize → expand $VARS
                                → deep_merge(managed scope)
                                → cache + return
```

1. **DEFAULT_CONFIG**: ~7000-line hardcoded dict in `config.py`
2. **User YAML**: `fast_safe_load()` parses `~/.hermes/config.yaml` (libyaml C parser)
   - Old `max_turns` root key migrated into `agent.max_turns` (back compat)
3. **Deep merge**: Recursive — nested dicts merge individually. Override only what you specify, keep defaults for the rest.
4. **Normalize**: Legacy flat keys → nested structure
5. **Env expansion**: `${VAR}` references in string values → resolved from `os.environ`. Unresolved refs kept verbatim.
6. **Managed scope**: `/etc/hermes/config.yaml` overlayed ON TOP (NixOS pins win at leaf level)

## Caching (`_LOAD_CONFIG_CACHE`)

Keyed on `(config_path, mtime_ns, size, managed_mtime_ns, managed_size)`:

- File unchanged → return cached deepcopy (~265µs)
- File changed → re-run full pipeline

Two entry points:
- `load_config()` → returns deepcopy (safe to mutate)
- `load_config_readonly()` → returns cached object directly (faster, but caller must NOT mutate)

## `read_raw_config()` — Bypass the Pipeline

Used by setup wizards and `hermes config set`. No defaults, no merge, no env expansion — just raw YAML dict or `{}`.

## Corruption Handling

When YAML parsing fails:
1. Snapshot corrupted file to `config.yaml.corrupt.<ts>.bak`
2. Log warning + print to stderr
3. Silently fall through to bare `DEFAULT_CONFIG`
4. **All user overrides lost** until YAML is fixed

Cache dedup ensures concurrent CLI/gateway don't spam stderr per tick.

## Save Pipeline (`save_config()`)

- Preserves `${VAR}` environment templates (writes template back, not expanded secret)
- Strips managed-scope keys before persisting
- Atomic write via `atomic_replace()` (temp file + rename)

## Env Var Denylist

`save_env_value()` blocks ~20 dangerous names from dashboard env writer:

```
LD_PRELOAD, LD_LIBRARY_PATH, PYTHONPATH, PYTHONHOME,
NODE_OPTIONS, PATH, SHELL, EDITOR, VISUAL, PAGER,
GIT_SSH_COMMAND, HERMES_HOME, HERMES_PROFILE, …
```

Write-only gate — existing values in `.env` still work. Must edit `.env` directly.

## Three-Process Architecture

Hermes runs as **three independent processes**, all reading the same `~/.hermes/config.yaml`:

| Process | Function | UI? |
|---------|----------|-----|
| `hermes gateway run` | Background daemon — routes messages from Telegram/Discord/etc., spawns agent sessions | Headless |
| `hermes dashboard` | FastAPI backend serving React frontend (port 9119) | Web UI |
| `hermes chat` / TUI | Interactive terminal agent session | Terminal |

**Key insight for debugging**: The dashboard is a management panel, NOT an agent session. It can show/enable/disable plugins but doesn't *load* them the way a running agent does. The `/api/dashboard/*` endpoints require auth (`_require_token`) — if auth fails silently, the UI shows empty states even though the CLI sees everything fine.

## Key Source Files

| File | Role |
|------|------|
| `hermes_cli/config.py` | Main config loader: load_config, save_config, read_raw_config |
| `hermes_cli/fallback_config.py` | Fallback model/provider config |
| `hermes_cli/tools_config.py` | Toolset configuration |
| `hermes_cli/mcp_config.py` | MCP server configuration |
| `hermes_cli/skills_config.py` | Skills configuration |
| `hermes_cli/moa_config.py` | Mixture-of-agents config |
| `hermes_cli/plugins.py` | Plugin load/discover logic |
| `hermes_cli/web_server.py` | Dashboard backend — FastAPI routes |
| `hermes_cli/profiles.py` | Profile management |
