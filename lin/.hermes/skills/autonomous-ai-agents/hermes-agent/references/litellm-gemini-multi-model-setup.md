# LiteLLM Multi-Model Gemini Setup for Hermes Agent

⚠️ **CORRECTED:** Earlier versions of this document recommended model names with `gemini/` prefix in Hermes config. This only works with `model.provider: openrouter` (which routes to OpenRouter, not a local LiteLLM proxy). For a local LiteLLM proxy at localhost:4000, use bare model names and `model.provider: custom:litellm`.

## Architecture

```
Hermes → custom:litellm provider → LiteLLM (localhost:4000) → Vertex AI Gemini models
```

## Correct Configuration (Single LiteLLM Proxy)

### Hermes Config (`~/.hermes/config.yaml`)

```yaml
model:
  provider: custom:litellm
  base_url: http://localhost:4000/v1
  api_key: sk-1234
  default: gemini-2.5-flash

custom_providers:
  litellm:
    base_url: http://localhost:4000/v1
    api_key: sk-1234

agent:
  model: gemini-3.1-flash-lite      # bare name, NO provider prefix
```

### LiteLLM Config (`~/litellm-config.yaml`)

```yaml
model_list:
  - model_name: gemini-3.1-pro-preview     # bare name, no prefix
    litellm_params:
      model: vertex_ai/gemini-3.1-pro-preview
      vertex_project: YOUR_PROJECT_ID
      vertex_location: global
      vertex_credentials: /path/to/key.json
  - model_name: gemini-3.1-flash-lite
    litellm_params:
      model: vertex_ai/gemini-3.1-flash-lite
      vertex_project: YOUR_PROJECT_ID
      vertex_location: global
      vertex_credentials: /path/to/key.json
  - model_name: gemini-2.5-pro
    litellm_params:
      model: vertex_ai/gemini-2.5-pro
      vertex_project: YOUR_PROJECT_ID
      vertex_location: global
      vertex_credentials: /path/to/key.json
  - model_name: gemini-2.5-flash
    litellm_params:
      model: vertex_ai/gemini-2.5-flash
      vertex_project: YOUR_PROJECT_ID
      vertex_location: global
      vertex_credentials: /path/to/key.json
```

## Why Provider Prefixes Don't Belong Here

With `model.provider: custom:litellm`, Hermes sends model names verbatim to the custom provider's base_url. If you set `agent.model: gemini/gemini-3.1-flash-lite`, LiteLLM receives `model: gemini/gemini-3.1-flash-lite` — which doesn't match `model_name: gemini-3.1-flash-lite` and returns a 400 error.

The `gemini/` prefix only belongs with `provider: openrouter` (which routes to OpenRouter's API where `gemini/gemini-3.1-flash-lite` is a valid model ID).

## Common Mistake: Using `provider: openrouter` with a local base_url

This is the most common misconfiguration:

```yaml
# ❌ WRONG — this uses OpenRouter naming but routes to local LiteLLM
model:
  provider: openrouter
  base_url: http://localhost:4000/v1
  default: gemini-2.5-flash
```

The default model `gemini-2.5-flash` (no prefix) might work, but the agent model `gemini/gemini-3.1-flash-lite` (with prefix) fails because `openrouter` sends names verbatim.

## Verification

```bash
# Check LiteLLM has the models
curl -s http://localhost:4000/v1/models | jq '.data[].id'

# Test direct completion
curl -s http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-1234" \
  -H "Content-Type: application/json" \
  -d '{"model":"gemini-2.5-flash","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'

# Test via Hermes
hermes chat -q "hi"
```

## Available Models (using correct bare names)

- `gemini-3.1-pro-preview`
- `gemini-3.1-flash-lite`
- `gemini-2.5-pro`
- `gemini-2.5-flash`

## Notes

- `vertex_location: global` is critical for Vertex AI Gemini models
- LiteLLM handles token refresh automatically from the service account
- The proxy runs at `localhost:4000`
- Auth uses `master_key` from `general_settings` in litellm-config.yaml