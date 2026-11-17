# DeepSeek Provider for OpenCode via LiteLLM

When Vertex AI billing is disabled or you prefer DeepSeek as your provider, add it to OpenCode via the existing LiteLLM proxy — same pattern as the Vertex AI provider.

## Step 1: Add DeepSeek to LiteLLM config

Edit `~/litellm-config.yaml` to add a DeepSeek model entry:

```yaml
model_list:
  # ... existing entries (vertex_ai/ models) ...
  - model_name: deepseek-v4-flash
    litellm_params:
      model: openai/deepseek-chat        # or 'deepseek/deepseek-chat'
      api_key: "${DEEPSEEK_API_KEY}"
      api_base: https://api.deepseek.com/v1
  - model_name: deepseek-v4-reasoner
    litellm_params:
      model: openai/deepseek-reasoner
      api_key: "${DEEPSEEK_API_KEY}"
      api_base: https://api.deepseek.com/v1
```

Or inline the key directly (less secure):
```yaml
      api_key: "sk-REDACTED"
```

Then restart LiteLLM:
```bash
systemctl --user restart litellm-vertex.service
```

## Step 2: Add a DeepSeek provider to OpenCode

Edit `~/.config/opencode/opencode.json`:

```json
{
  "provider": {
    "vertex": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Vertex AI via LiteLLM",
      "options": {
        "baseURL": "http://localhost:4000/v1",
        "apiKey": "sk-..."
      },
      "models": {
        "gemini-2.5-flash": {"name": "Gemini 2.5 Flash"},
        "gemini-2.5-pro": {"name": "Gemini 2.5 Pro"},
        "gemini-3.1-flash-lite": {"name": "Gemini 3.1 Flash Lite"},
        "gemini-3.1-pro-preview": {"name": "Gemini 3.1 Pro Preview"}
      }
    },
    "deepseek": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "DeepSeek via LiteLLM",
      "options": {
        "baseURL": "http://localhost:4000/v1",
        "apiKey": "sk-..."
      },
      "models": {
        "deepseek-v4-flash": {"name": "DeepSeek V4 Flash"},
        "deepseek-v4-reasoner": {"name": "DeepSeek V4 Reasoner"}
      }
    }
  },
  "model": "vertex/gemini-2.5-flash"
}
```

The `apiKey` in the provider options doesn't need to match DeepSeek's key — the LiteLLM proxy handles auth. Use the LiteLLM proxy's `master_key` value.

## Step 3: Use it

```bash
opencode run 'your prompt' --model deepseek/deepseek-v4-flash --print-logs 2>/dev/null
opencode run 'your prompt' --model deepseek/deepseek-v4-reasoner --print-logs 2>/dev/null
```

The model names listed via `opencode models` will show as `deepseek/deepseek-v4-flash` etc.

## Switching Default Model

```bash
opencode config set default_model deepseek/deepseek-v4-flash
# Or edit opencode.json's "model" field
```

## Alternative: Direct DeepSeek Provider (Without LiteLLM)

If you don't have/want LiteLLM, configure DeepSeek as a direct OpenAI-compatible provider in `opencode.json`:

```json
{
  "deepseek": {
    "npm": "@ai-sdk/openai-compatible",
    "name": "DeepSeek",
    "options": {
      "baseURL": "https://api.deepseek.com/v1",
      "apiKey": "sk-REDACTED"
    },
    "models": {
      "deepseek-chat": {"name": "DeepSeek V3"},
      "deepseek-reasoner": {"name": "DeepSeek R1"},
      "deepseek-v4-flash": {"name": "DeepSeek V4 Flash"}
    }
  }
}
```

## Pitfall: Hermes Credential Pool Corrupts API Keys

When using the **direct** DeepSeek provider (without LiteLLM), **do NOT source the API key from Hermes' credential pool or masked `.env` file.** The Hermes credential pool system replaces the middle of stored API keys with `...` to mask them at rest, which corrupts the key for external use.

Example of a masked key (unusable directly):
```
DEEPSEEK_API_KEY=sk-251...a4c7    # Hermes corrupted the middle with ...
```

The actual key would be longer (~51 chars), but the masked version (~35 chars) will fail with `401 Authentication Fails` from the DeepSeek API.

Solutions:
1. **Use LiteLLM proxy** (recommended) — the proxy handles auth internally; OpenCode only needs the LiteLLM master key
2. **Paste a fresh key** into `opencode.json` directly — don't try to extract it from Hermes' `.env` or credential pool
3. Keep the key plain in a shell config file (`~/.bashrc`, `~/.profile`) that OpenCode inherits at runtime, not in `~/.hermes/.env`

## Notes

- Both Vertex AI and DeepSeek providers share the same LiteLLM proxy — no need to run separate proxies
- If LiteLLM is already running, just edit the config and restart; the proxy stays on port 4000
- The `@ai-sdk/openai-compatible` npm package is already installed from the Vertex AI setup
- DeepSeek's API key goes in the LiteLLM config (or as `DEEPSEEK_API_KEY` env var), not in OpenCode's config
