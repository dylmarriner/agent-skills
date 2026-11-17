---
name: ai-provider-cross-config
description: Configure an AI provider (OpenRouter, OpenAI, Anthropic, etc.) across multiple agent tools simultaneously — Hermes, oh-my-pi, OpenCode, OpenClaw, Aider, and ACP/ACPX. Covers per-tool config formats, provider key distribution, ACP/ACPX delegation setup, and fallback wiring.
category: devops
emoji: 🔌
trigger: |
  User asks to connect an AI provider (OpenRouter, OpenAI, Anthropic, etc.)
  to multiple agents, set up a new model across tools, configure ACP
  delegation, wire a single API key into Hermes + omp + OpenCode +
  OpenClaw + Aider at the same time, or set up Aider with an API provider.
  Also triggered by "set up OpenRouter for all my agents",
  "setup aider", "connect (provider) to (tool list)", or "setup acp/acpx".
---

# AI Provider Cross-Configuration

Configure a single AI provider across multiple agent tools. Each tool has
a different config format and discovery mechanism. This skill covers the
canonical six: Hermes, oh-my-pi, OpenCode, OpenClaw, Aider, and ACP/ACPX.

## Discovery: Scavenge Existing Configs First

**Do NOT assume a provider is OpenRouter-routed.** When the user asks to
add a provider (e.g. "add Sakana Fugu provider"), first check existing
agent configs on this machine for the actual API endpoint and key. The
user keeps provider configurations in multiple tools — scavenge them:

1. **Codex CLI** — check `~/.codex/config.toml` for `[model_providers.<name>]`
   sections. Each has `base_url`, `env_key`, and `wire_api`. The API key
   lives in `~/.codex/.env` (same env var name as `env_key` in the toml).
   Model catalog files like `~/.codex/fugu.json` list models/slugs.
2. **OpenCode** — check `~/.opencode/.env` for provider env vars.
3. **omp** — check `~/.omp/agent/config.yml` for model roles.
4. **OpenClaw** — check `~/.openclaw/openclaw.json` for providers list.
5. **ACPX** — check `~/.acpx/config.json` for default provider routing.

**Workflow:** search for provider-specific variable names and endpoint fields, but redact secret values and never dump a `.env` file. The user prefers you find the answer rather than asking "which API?"

## Key Before You Start

Keep provider credentials in each tool's secret store or environment file, not in YAML/JSON configuration. For Hermes, use `key_env` and store the named variable in `~/.hermes/.env` with mode `0600`; Hermes resolves it without requiring the key to be copied into YAML. For other tools, use that tool's supported environment or `.env` mechanism. Avoid shell tracing and never print secret values.

## Per-Tool Configuration

### 1. Hermes

Hermes reads `~/.hermes/config.yaml`. Prefer the named `providers:` mapping; the older `custom_providers:` list remains compatible. Keep credentials in `~/.hermes/.env` and reference them with `key_env` rather than embedding keys in YAML:

```yaml
providers:
  my-provider:
    api: https://api.example.com/v1
    key_env: MY_PROVIDER_API_KEY
    transport: chat_completions
    discover_models: true
```

Write security-sensitive Hermes config through its CLI, then read back the exact fields:

```bash
hermes config set --force providers.my-provider.api https://api.example.com/v1
hermes config set --force providers.my-provider.key_env MY_PROVIDER_API_KEY
hermes config set --force providers.my-provider.transport chat_completions
hermes config set --force providers.my-provider.discover_models true
hermes config get providers.my-provider.api
hermes config get providers.my-provider.key_env
```

Store `MY_PROVIDER_API_KEY=<key>` in `~/.hermes/.env` with mode `0600`, preserving other entries. Never print, echo, or inline the key. Keep the provider slug exactly as requested when it differs from the service's brand name. Do not change `model.default` unless the user asks to switch defaults.

To verify actual Hermes discovery, use `hermes model --refresh`, inspect the provider and model list, then cancel before selecting a model for provider-addition-only requests; confirm `model.default` is unchanged. A raw successful `/v1/models` request validates endpoint/auth, not that Hermes' picker is loading the catalog.

**Non-interactive discovery check** (no picker, safe to script): run the code path the picker itself uses, under Hermes' own bundled interpreter — `hermes` is a shell wrapper around a pinned runtime at `~/.hermes/tools/python-*/bin/python3`, and the system `python3` lacks `ruamel.yaml` (the repo imports it as `hermes_yaml`), so plain `python3` dies on import.

```bash
HERMES_PY=$(ls -d ~/.hermes/tools/python-*/bin/python3 | head -1)
"$HERMES_PY" -I - <<'PY'
import sys; sys.path.insert(0, '/home/linnyux/.hermes/hermes-agent')
sys._hermes_pin_default_home = True
import hermes_bootstrap  # sets up the pinned HOME and dependencies
from hermes_cli.model_switch_providers import _discover_endpoint_models
from pathlib import Path
key = next(l.split('=', 1)[1] for l in Path.home().joinpath('.hermes/.env').read_text().splitlines()
           if l.startswith('MY_PROVIDER_API_KEY='))
models, _ = _discover_endpoint_models(
    key, 'https://api.example.com/v1', 'custom', False, headers=None,
    api_mode='chat_completions', probe_live=True, discovery_allowed=True, fast_custom_probe=False)
print(len(models), [m.get('id') for m in models])
PY
```

A printed model list proves the picker will populate; an empty list means the provider is configured but not discoverable.

**`~/.hermes/config.yaml` is guarded:** the generic `patch`/`write_file` tools refuse to touch it, so do every edit through `hermes config set --force` / `hermes config get` rather than hand-editing YAML.

**Set as default model:**
```bash
hermes config set model.default anthropic/claude-sonnet-4-6
hermes config set model.provider openrouter
```

**Set as fallback provider (auto-failover):**
```yaml
fallback_model:
  provider: openrouter
  model: deepseek/deepseek-v4-flash
```

### 2. oh-my-pi (omp)

omp uses YAML config at `~/.omp/agent/config.yml`. It uses `modelRoles`
to map roles to model names. Provider routing is implicit — model names
use the `provider/model` convention (e.g. `deepseek/deepseek-v4-flash`,
`anthropic/claude-sonnet-4-6`).

```yaml
modelRoles:
  default: deepseek/deepseek-v4-flash
  fast: deepseek/deepseek-v4-flash
  smart: anthropic/claude-sonnet-4-6
  creative: anthropic/claude-opus-4-6
```

omp resolves the provider from the model name prefix. For OpenRouter
models, the prefix is the provider name (e.g. `anthropic/`, `deepseek/`).

The provider API key must be set in the environment:
```bash
export OPENROUTER_API_KEY=sk-or-v1-...
```

Or added to `~/.omp/agent/.env` or loaded via a shell profile.

**Package manager note:** omp's monorepo uses **bun** exclusively. Do not
use `npm install` or `pnpm install` — the `catalog:` protocol in
`package.json` only works with bun. If you see `EUNSUPPORTEDPROTOCOL`
errors, use bun.

### 3. OpenCode

OpenCode reads config from `~/.opencode/.env`. Add:

```bash
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

OpenCode also supports the standard OpenAI env vars:
```bash
OPENAI_API_KEY=sk-or-v1-...       # Also works — OpenRouter is OpenAI-compatible
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

The existing `.env` may already have a different provider. Append to it
rather than overwriting.

### 4. OpenClaw

OpenClaw uses JSON config at `~/.openclaw/openclaw.json`. Add a provider
under `models.providers`:

```json
{
  "models": {
    "providers": {
      "openrouter": {
        "api": "openai-completions",
        "baseUrl": "https://openrouter.ai/api/v1",
        "apiKey": "sk-or-v1-...",
        "models": [
          {"id": "anthropic/claude-sonnet-4-6", "name": "Claude Sonnet 4.6",
           "contextWindow": 200000, "input": ["text", "image"], "maxTokens": 8192},
          {"id": "deepseek/deepseek-v4-flash", "name": "DeepSeek V4 Flash",
           "contextWindow": 128000, "input": ["text"], "maxTokens": 8192}
        ]
      }
    }
  }
}
```

Note: OpenClaw uses `openai-completions` API type for OpenRouter since
OpenRouter implements the OpenAI API spec.

### 5. ACP / ACPX Delegation

ACPX (`acpx`) is the Agent Client Protocol CLI — it lets agents delegate
tasks to other agents. Installed globally via npm:

```bash
npm install -g acpx
```

Binary at `~/.npm-global/bin/acpx`, symlinked to `~/.local/bin/acpx`.

**Supported agents (via `acpx <agent> <prompt>`):**
- `pi` — oh-my-pi
- `opencode` — OpenCode
- `openclaw` — OpenClaw
- `codex` — OpenAI Codex
- `claude` — Claude Code
- `copilot` — GitHub Copilot
- `gemini`, `cursor`, `kimi`, `qwen`, and more

**Wire into Hermes delegation:** In `~/.hermes/config.yaml`:

```yaml
delegation:
  acp_command: acpx
  acp_args: ['--agent', 'opencode']
  model: ''
  provider: openrouter
  base_url: https://openrouter.ai/api/v1
  inherit_mcp_toolsets: true
  max_iterations: 50
  child_timeout_seconds: 600
  max_concurrent_children: 3
```

This tells Hermes to spawn `acpx --agent opencode` when delegating tasks.

**Other ACP agents:** Change `acp_args` to delegate to different agents:
- `['--agent', 'opencode']` → OpenCode
- `['--agent', 'pi']` → oh-my-pi
- `['--agent', 'openclaw']` → OpenClaw
- `['--agent', 'claude']` → Claude Code (if installed)
- `['--agent', 'copilot']` → GitHub Copilot (if installed)

### ACPX System Config (advanced)

acpx has a global config file at `~/.acpx/config.json` for setting defaults
across all agents:

```json
{
  "defaultAgent": "codex",
  "defaultModel": "qwen/qwen3.6-plus",
  "defaultPermissions": "approve-all",
  "nonInteractivePermissions": "deny",
  "authPolicy": "skip",
  "ttl": 300,
  "agents": {
    "opencode": { "model": "qwen/qwen3.6-plus" },
    "codex":    { "model": "qwen/qwen3.6-plus" },
    "pi":       { "model": "qwen/qwen3.6-plus" },
    "claude":   { "model": "qwen/qwen3.6-plus" },
    "gemini":   { "model": "qwen/qwen3.6-plus" }
  }
}
```

**Cheap smart default (Qwen3.6 Plus):** At $0.30/M input and $1.80/M output,
Qwen3.6 is the cheapest smart model for acpx. Set it as `defaultModel` to
save tokens on routine tasks. Override inline for hard problems:
```bash
acpx opencode --model anthropic/claude-sonnet-4.6 "complex refactor"
```

**Setting per-agent models:** Add an `agents.<name>.model` entry for each
agent that should use a different model than the default. Useful when some
agents handle cheap tasks and others handle reasoning-heavy work.

### Claude via OpenRouter (no direct Anthropic key)

The `claude` ACP agent (`@agentclientprotocol/claude-agent-acp`) requires
`ANTHROPIC_API_KEY`. Route through OpenRouter instead:

```bash
export ANTHROPIC_API_KEY=sk-or-v1-...     # Your OpenRouter key
export ANTHROPIC_BASE_URL=https://openrouter.ai/api/v1
```

OpenRouter speaks Anthropic's API format, so the claude-agent-acp works
without a direct Anthropic subscription. Add to `~/.env` or the project
`.env` for persistence.

### 6. Aider (AI Pair Programming)

Aider (`aider`) is an AI pair-programming CLI that supports DeepSeek
directly, OpenRouter, and any OpenAI-compatible endpoint.

**DeepSeek (from Hermes secrets):**

The key lives in `~/.hermes/.env`. Source it in shell profiles:

```bash
if [ -f "$HOME/.hermes/.env" ]; then
    export DEEPSEEK_API_KEY="$(grep '^DEEPSEEK_API_KEY=' "$HOME/.hermes/.env" | cut -d= -f2-)"
fi
```

**Config file** (`~/.aider.conf.yml`):

```yaml
model: deepseek/deepseek-v4-flash
map-tokens: 2048
auto-commits: true
dirty-commits: true
git: true
yes-always: true
no-show-model-warnings: true
```

**Key points:**
- Model name format: `deepseek/<model-name>` (e.g. `deepseek/deepseek-v4-flash`)
- `yes-always: true` — skip interactive prompts for script use
- `no-show-model-warnings: true` — suppress "unknown context window" warnings
- Git index version 4 warnings (`Unsupported git index version 4...`) are
  cosmetic — Aider still works fine
- Aider uses litellm under the hood, so any litellm-supported model works

**One-shot usage:**
```bash
aider --model deepseek/deepseek-v4-flash --message "describe the changes"
```

**Alternative — OpenRouter:**
```bash
export OPENROUTER_API_KEY=sk-or-v1-...
aider --model openrouter/deepseek/deepseek-v4-flash
```

### 7. Sakana (Fugu / Fugu Ultra)

Sakana AI's Fugu models are available via direct API (OpenAI-compatible)
or through OpenRouter.

**Direct API (`https://api.sakana.ai/v1`):**

```yaml
providers:
  sakana:
    api: https://api.sakana.ai/v1
    key_env: SAKANA_API_KEY
    transport: chat_completions
    discover_models: true
```

The `SAKANA_API_KEY` currently lives in `~/.codex/.env`; make it available to Hermes through its process environment or `~/.hermes/.env` before selecting the provider.

**OpenRouter route:** model `sakana/fugu-ultra`, $5/$30 per 1M.

**Fugu quirks:**
- 1M context window, only `high`/`xhigh`/`max` reasoning effort
- Minimum `max_tokens` of 16 (lower returns 400 error)
- Multi-agent orchestration — burns ~1260 orchestration tokens per request
- Standard chat completions endpoint (`/v1/chat/completions`)
- Codex CLI configs (`~/.codex/fugu.config.toml` + `~/.codex/fugu.json`)
  are the canonical model metadata source for this user

## Verification

```bash
# Hermes — verify safe provider fields; substitute the requested slug
PROVIDER=my-provider
hermes config get "providers.$PROVIDER.api"
hermes config get "providers.$PROVIDER.key_env"
hermes model --refresh  # inspect discovery, then cancel if default must stay unchanged
hermes config get model.default

# omp — check model roles
grep 'modelRoles' -A4 ~/.omp/agent/config.yml

# OpenCode — check env
grep OPENROUTER ~/.opencode/.env

# OpenClaw — check provider
grep -A3 'openrouter' ~/.openclaw/openclaw.json | head -6

# ACPX — check binary and version
acpx --version

# ACPX — check config
cat ~/.acpx/config.json | head -20

# Test ACP delegation (dry run)
acpx --agent opencode "echo hello" 2>&1 | head -3

# Aider — check config
cat ~/.aider.conf.yml | head -10
aider --dry-run --message "ping" 2>&1 | head -5
```

## Pitfalls

**Hermes configuration safety:** Prefer `hermes config set --force` for targeted provider fields and verify them with `hermes config get`; use `hermes config edit` for complex edits. Never rewrite the file with Python's `yaml.dump()`, which strips comments and can overwrite unrelated settings.
- **omp ≠ npm:** omp's monorepo uses bun. npm will fail with
  `EUNSUPPORTEDPROTOCOL catalog:`. Always use `bun install`.
- **Configs are all different:** Hermes = YAML `providers:` mapping (legacy `custom_providers:` still works) with secrets referenced by `key_env`; omp = YAML modelRoles, OpenCode = .env, OpenClaw = JSON models.providers, ACP = delegation section. There is no universal format.
- **ACP key inheritance:** Subprocess agents spawned via acpx inherit
  environment variables from the parent. If OPENROUTER_API_KEY is set
  in the parent shell, child agents will have access to it.
- **OpenClaw model schema:** Each model entry needs `id`, `name`,
  `contextWindow`, `input`, and `maxTokens`. Missing fields may cause
  the model to not appear in the UI.
- **Path breaks:** The terminal PATH may drop system directories. Use
  full paths (e.g. `~/.npm-global/bin/acpx`) in background scripts.
**acpx config location:** The acpx config at `~/.acpx/config.json` is
read on every invocation. No restart needed — changes apply immediately.
However, `acpx set model <name>` requires an active session first
(`acpx codex sessions new`). For agent-free configuration, edit the
JSON file directly.

Check for bundled acpx versions: projects may bundle acpx in node_modules. Verify which version runs before debugging.
- **Model override precedence:** `--model` flag > per-agent config >
  `defaultModel` > hardcoded default. If an inline override doesn't take
  effect, check `~/.acpx/config.json` agents entry for that agent.
