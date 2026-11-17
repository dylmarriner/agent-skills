# OpenCode OpenRouter Configuration for Hermes Users

When using Hermes with OpenRouter as the primary provider (as configured in `~/.hermes/config.yaml`), you can leverage the same API key for OpenCode:

```json
{
  "model": "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
  "provider": {
    "openrouter": {
      "name": "OpenRouter",
      "options": {
        "api_key": "$OPENROUTER_API_KEY"  // or explicit key from ~/.hermes/.env
      },
      "models": {
        "nvidia/nemotron-3-super-120b-a12b:free": { "name": "Nemotron 3 Super 120B" },
        "google/gemini-3.1-flash-lite": { "name": "Gemini 3.1 Flash Lite" }
      }
    }
  }
}
```

**Important**: OpenCode requires explicit `api_key` in the provider options even when `OPENROUTER_API_KEY` is set in environment variables. Unlike some other tools, it doesn't automatically pick it up from env vars in all contexts. If you see "OpenRouter API key is missing" errors, ensure the api_key field is set in your `opencode.json`.

## LiteLLM Port Note
In this specific setup, the LiteLLM proxy runs on port 4000 (not 8899). If configuring OpenCode to use LiteLLM directly, use `http://localhost:4000/v1` as the baseURL.