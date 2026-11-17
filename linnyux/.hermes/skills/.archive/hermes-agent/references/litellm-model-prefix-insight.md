# LiteLLM Model Name Prefix — Critical Correction

⚠️ **CORRECTION:** Earlier versions of this file claimed that Hermes with `custom_providers` strips the provider prefix from model names before forwarding to LiteLLM. This is **false**. The behavior depends entirely on `model.provider` type.

## The Two Routing Patterns

### Pattern A: `model.provider: openrouter` (DON'T use with local LiteLLM)

```yaml
model:
  provider: openrouter          # ← WRONG with local proxy
  base_url: http://localhost:4000/v1
```

With `provider: openrouter`, model names with a provider prefix like `gemini/gemini-3.1-flash-lite` are sent **verbatim** to the base_url. LiteLLM receives `model: gemini/gemini-3.1-flash-lite` — which doesn't match its `model_name: gemini-3.1-flash-lite` and fails.

This was the root cause of the user's frustration: Hermes appeared to be "connected by OpenRouter" but actually pointed to the local proxy, and the `gemini/` prefix on model names caused LiteLLM model lookup failures.

### Pattern B: `model.provider: custom:<name>` (CORRECT for local proxy)

```yaml
model:
  provider: custom:litellm        # ← CORRECT
  base_url: http://localhost:4000/v1
  api_key: sk-1234
  default: gemini-2.5-flash

custom_providers:
  litellm:
    base_url: http://localhost:4000/v1
    api_key: sk-1234
```

With `custom:<name>`, model names are sent **as bare names** to the custom provider's base_url. No prefix, no stripping needed. LiteLLM receives `model: gemini-2.5-flash` which matches `model_name: gemini-2.5-flash` perfectly.

### Pattern C: Multiple custom providers with prefix routing

When you define multiple `custom_providers` entries and use provider-prefixed model names like `vertex-ai/gemini-3.1-pro-preview`, Hermes:
1. Matches `vertex-ai/` to the custom provider entry
2. Strips the `vertex-ai/` prefix
3. Sends `gemini-3.1-pro-preview` to that provider's base_url

This is the only case where prefix stripping happens — and only because the `custom_providers` dict defines multiple routing targets.

## The Confusion

The earlier version of this file was written during a session where the user had:
- `model.provider: custom:vertex-ai` (or similar multi-provider setup)
- Model names like `vertex-ai/gemini-3.1-pro-preview`

The prefix stripping observed was correct for the **multi-provider** pattern. But the advice was then incorrectly generalized to single-provider setups, and the file also recommended putting `gemini/` in LiteLLM's `model_name` field — which would never match anything.

## Correct LiteLLM Configuration

```yaml
# ~/litellm-config.yaml
model_list:
  - model_name: gemini-3.1-flash-lite      # bare name, no prefix
    litellm_params:
      model: vertex_ai/gemini-3.1-flash-lite
      vertex_project: YOUR_PROJECT_ID
      vertex_location: global
```

The `model_name` in LiteLLM should **never** have a provider prefix. It's the name clients use to request the model.

## Correct Hermes Configuration (Single Proxy)

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
  model: gemini-3.1-flash-lite    # bare name, no prefix
```

## Quick Rule

| Provider type | Model name format | Example |
|:--------------|:------------------|:--------|
| `openrouter` | `provider/model` | `gemini/gemini-2.5-flash` |
| `custom:<name>` (single) | bare name | `gemini-2.5-flash` |
| `custom:<name>` (multi, via provider prefix) | `provider/model` → stripped | `vertex-ai/gemini-3.1-pro-preview` |
| `anthropic` / `openai` / others | bare name (per-provider format) | `claude-sonnet-4` |