---
name: pi-coding-agent-litellm
description: Configure the `@mariozechner/pi-coding-agent` CLI to use a LiteLLM proxy via OpenAI-compatible environment variables.
metadata:
  category: software-development
---

# Pi Coding Agent + LiteLLM

Use this skill when a user wants Pi (`pi` from `@mariozechner/pi-coding-agent`) to route requests through LiteLLM.

## Key finding

Pi can route through a LiteLLM proxy, but the most reliable path in this environment was not Pi's OpenAI provider. Pi's `--provider openai` path can fail with an `AzureOpenAI`/extension import error or a 401 even when LiteLLM is available. The working path we verified was Pi's `azure-openai` provider against LiteLLM's OpenAI-compatible `/v1` endpoint.

Verified command:

```bash
export AZURE_OPENAI_API_KEY="<litellm-key>"
export AZURE_OPENAI_BASE_URL="http://localhost:45564/v1"
export AZURE_OPENAI_API_VERSION="v1"
pi --provider azure-openai --model gpt-4o -p "Reply with exactly: ping"
```

That produced `pong` in the test environment.

## Setup

1. Make sure LiteLLM is running and reachable.
2. Prefer these environment variables for the working path we verified:

```bash
export AZURE_OPENAI_API_KEY="<litellm-key>"
export AZURE_OPENAI_BASE_URL="http://localhost:45564/v1"
export AZURE_OPENAI_API_VERSION="v1"
```

3. Start Pi with the Azure-compatible provider and a LiteLLM-accepted model ID:

```bash
pi --provider azure-openai --model gpt-4o "hello"
```

If Pi says the model is not found, try the exact model IDs exposed by your proxy or use `pi --list-models` to see what Pi currently knows about.

## Verification

- Run `pi --help` to confirm provider/model flags are supported.
- Run `pi --list-models` to see the models Pi currently accepts.
- If `--provider openai` returns 401 or says the key is invalid even though LiteLLM is reachable, try `--provider azure-openai` instead.
- If Pi errors about `AzureOpenAI` when extensions are enabled, retry with `--no-extensions` to isolate the provider path.
- If the model name is rejected, check the LiteLLM `model_list` mapping and the Pi-discovered model list rather than Pi itself.
- If you see `Resource not found` from the Azure provider path, verify the base URL and the model/provider pairing; some Azure-style routes are stricter than the raw LiteLLM endpoint.

## Notes

- The LiteLLM target is still the OpenAI-compatible endpoint; Pi's provider selection determines which internal client path it uses.
- Keep the LiteLLM key and base URL in a wrapper script if you want a one-command workflow; that is safer than relying on global shell vars alone.
- `pi --list-models` is useful for discovering which provider/model names Pi currently accepts.

## OpenCode note

OpenCode can also be pointed at LiteLLM reliably using a global config file rather than only shell env vars.

Verified setup:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "litellm": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "LiteLLM",
      "options": {
        "baseURL": "http://localhost:45564/v1"
      },
      "models": {
        "gpt-4o": { "name": "GPT-4o" }
      }
    }
  }
}
```

Useful locations:
- Global config: `~/.config/opencode/opencode.json`
- Credentials file: `~/.local/share/opencode/auth.json`

A convenience alias can wrap the LiteLLM env vars for shell use, but the config file is the more durable setup for OpenCode.

