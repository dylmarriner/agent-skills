# Hindsight + OpenCode Setup Session (2026-04-30)

## Scenario

Setting up Hindsight CLI + MCP integration for OpenCode on a dev machine running Linux x64.

## Error Encountered

Paperclip reported:
```
Error: `opencode models` failed: Configuration is invalid at /tmp/paperclip-opencode-config-XXXXXX/opencode/opencode.json
↳ Unrecognized key: mcpServers
stopReason: adapter_failed
```

### Root Cause

OpenCode 1.14.30 validates against `https://opencode.ai/config.json` which uses `mcp` (singular) for MCP server definitions. The config had a legacy `mcpServers` key left over from an older schema. Paperclip copies `~/.config/opencode/` to a temp directory and runs `opencode models` as a preflight check — the validation failure cascaded to `adapter_failed`.

### Fix Steps

1. Identify the stale key:
   ```bash
   opencode models 2>&1
   # → "Unrecognized key: mcpServers"
   ```

2. Review the config:
   ```bash
   cat ~/.config/opencode/opencode.json
   ```

3. Move all entries from `mcpServers` into `mcp`, converting their format:
   - Old `mcpServers` format:
     ```json
     { "command": "http", "args": ["http://localhost:8888/mcp"], "env": {}, "disabled": false, "autoApprove": [] }
     ```
   - New `mcp` format (remote/HTTP):
     ```json
     { "type": "remote", "url": "http://localhost:8888/mcp", "enabled": true }
     ```
   - New `mcp` format (local/stdio):
     ```json
     { "type": "local", "command": ["binary-name"], "args": [] }
     ```

4. For Hindsight cloud API, add Bearer auth in headers:
   ```json
   { "type": "remote", "url": "https://api.hindsight.vectorize.io/mcp", "enabled": true, "headers": { "Authorization": "Bearer hsk_..." } }
   ```

5. Validate:
   ```bash
   opencode models
   # Should list 200+ models without error
   ```

## Final Config

File: `~/.config/opencode/opencode.json`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "openrouter": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "OpenRouter",
      "options": {
        "baseURL": "https://openrouter.ai/api/v1",
        "headers": {
          "HTTP-Referer": "https://paperclip.local",
          "X-Title": "Paperclip-Atlas"
        }
      },
      "models": {
        "openai/gpt-oss-120b": { "name": "GPT-OSS 120B" },
        "meta-llama/llama-3.3-70b-instruct:free": { "name": "Llama 70B Free" },
        "qwen/qwen-3.5-flash": { "name": "Qwen 3.5 Flash" }
      }
    }
  },
  "model": "openrouter/openai/gpt-oss-120b",
  "mcp": {
    "cocoindex": {
      "type": "local",
      "command": ["cocoindex-code"]
    },
    "hindsight": {
      "type": "remote",
      "url": "https://api.hindsight.vectorize.io/mcp",
      "enabled": true,
      "headers": {
        "Authorization": "Bearer hsk_5b8816e021e870f680fc3a3417b311b4_73e15d0268a6d8f3"
      }
    }
  }
}
```

## Paperclip Integration Gap

Paperclip repo (HenkDz fork) has zero Hindsight references — no adapter, no plugin, no memory integration. Hindsight is only wired into OpenCode at the MCP level. Paperclip's own memory/context system is independent.
