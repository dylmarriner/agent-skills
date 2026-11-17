# Multi-Consumer Proxy Wiring

A single LiteLLM proxy on port 4000 can feed OpenCode, Hermes, and OpenClaw simultaneously. Each needs its own model catalog registration so it knows which models are available through the proxy.

## Architecture

```
OpenCode ─┐
Hermes  ──┤→ LiteLLM (port 4000) → Vertex AI / DeepSeek / etc.
OpenClaw ─┘
```

All three route through the same proxy endpoint. The proxy's `model_name` values in `litellm-config.yaml` are the canonical model IDs that every consumer must reference.

## OpenCode (`~/.config/opencode/opencode.json`)

```json
{
  "provider": {
    "vertex": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Vertex AI via LiteLLM",
      "options": {
        "baseURL": "http://localhost:4000/v1",
        "apiKey": "sk-123...cdef"
      },
      "models": {
        "gemini-2.5-flash": { "name": "Gemini 2.5 Flash" }
      }
    }
  },
  "model": "vertex/gemini-2.5-flash"
}
```

Usage: `opencode run "message" --model vertex/gemini-2.5-flash --print-logs 2>/dev/null`

**Important:** OpenCode v1.4.3 requires `--print-logs 2>/dev/null` for the `run` subcommand — without it the help text is shown instead of running.

## Hermes (`~/.hermes/config.yaml`)

```yaml
custom_providers:
- name: vertex-ai
  base_url: http://localhost:4000/v1
  api_key: sk-123...cdef
  api_mode: chat_completions
  models:
  - gemini-3.1-pro-preview
  - gemini-3.1-flash-lite
  - gemini-2.5-pro
  - gemini-2.5-flash
```

Usage: `hermes chat -q "message" -m vertex-ai/gemini-2.5-flash`

**Important:** Hermes has TWO config files — `~/.hermes/config.yaml` (main, 400+ lines) and `~/.config/hermes/config.yaml` (small, CLI-related). The auto_jailbreak function from the godmode skill writes to `~/.hermes/config.yaml`. Always confirm which file you're editing.

## OpenClaw (`~/.openclaw/openclaw.json`)

Add models to the provider that already routes through the proxy (e.g. `microsoft-foundry`):

```json
{
  "models": {
    "providers": {
      "microsoft-foundry": {
        "baseUrl": "http://localhost:4000/v1",
        "models": [
          {
            "id": "gemini-2.5-flash",
            "name": "Gemini 2.5 Flash",
            "contextWindow": 1048576,
            "api": "openai-completions",
            "reasoning": true
          }
        ]
      }
    }
  },
  "agents": {
    "defaults": {
      "models": {
        "microsoft-foundry/gemini-2.5-flash": {}
      }
    }
  }
}
```

Also mirror the model in `~/.openclaw/agents/main/agent/models.json` under the same provider.

## Litellm Config

The `model_name` in `litellm-config.yaml` is what every consumer sends:

```yaml
model_list:
  - model_name: gemini-2.5-flash
    litellm_params:
      model: vertex_ai/gemini-2.5-flash
      vertex_project: PROJECT_ID
      vertex_location: global
      vertex_credentials: /path/to/key.json
general_settings:
  master_key: sk-123...cdef
```

The `model_name` is the consumer-facing ID; the `model` under `litellm_params` is the actual provider model string.
