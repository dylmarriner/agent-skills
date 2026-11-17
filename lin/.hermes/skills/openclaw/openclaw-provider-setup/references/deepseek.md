# DeepSeek Provider for OpenClaw

Bundled plugin at `@openclaw/deepseek-provider` (bundled in OpenClaw 2026.5.7).

## Plugin Details

- **pluginId**: `deepseek`
- **Manifest**: `~/.npm-global/lib/node_modules/openclaw/dist/extensions/deepseek/openclaw.plugin.json`
- **Provider ID**: `deepseek`
- **API format**: `openai-completions`
- **Base URL**: `https://api.deepseek.com`

## Available Models (from catalog)

| Model ID | Context | Cost (in/out per 1M) | Reasoning |
|---|---|---|---|
| `deepseek/deepseek-v4-flash` | 1,000,000 | $0.14 / $0.28 | yes |
| `deepseek/deepseek-v4-pro` | 1,000,000 | $1.74 / $3.48 | yes |
| `deepseek/deepseek-chat` | 131,072 | $0.28 / $0.42 | no |
| `deepseek/deepseek-reasoner` | 131,072 | $0.28 / $0.42 | yes |

## Required Env Var

`DEEPSEEK_API_KEY` — reads it from environment at gateway startup.

## Auth Profile

```json
"deepseek:default": {
  "mode": "api_key",
  "provider": "deepseek"
}
```

## Config Snippet

```json
{
  "agents": {
    "defaults": {
      "model": {
        "fallbacks": [
          "deepseek/deepseek-chat"
        ],
        "primary": "deepseek/deepseek-v4-flash"
      },
      "models": {
        "deepseek/deepseek-v4-flash": { "alias": "DeepSeek V4 Flash" },
        "deepseek/deepseek-v4-pro": { "alias": "DeepSeek V4 Pro" }
      }
    }
  }
}
```

## Verification

Gateway log line on successful startup:
```
agent model: deepseek/deepseek-v4-flash (thinking=high, fast=off)
```
