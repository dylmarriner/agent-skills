# Vertex AI maxOutputTokens Limits

When using Vertex AI Gemini models through a LiteLLM proxy, the `max_tokens` parameter in the LiteLLM config maps to Vertex AI's `maxOutputTokens`. Each Gemini model has a hard cap that cannot be exceeded.

## Verified Limits (May 2026)

| Model | maxOutputTokens (inclusive max) | Notes |
|-------|-------------------------------|-------|
| gemini-2.5-flash | 65536 | Error: "range is from 1 to 65537 (exclusive)" — max = 65536 |
| gemini-2.5-pro | 65536 | Same limit as 2.5 Flash based on Vertex API |
| gemini-3.1-flash-lite | 8192 | Standard GenerationConfig default |
| gemini-3.1-pro-preview | 8192 | Standard GenerationConfig default |

## Error Pattern

Setting `max_tokens` above the per-model cap in `litellm-config.yaml` produces:

```
Vertex_ai_betaException: maxOutputTokens value of NNNNNNN but the supported range 
is from 1 (inclusive) to MMMMM (exclusive)
```

The error surfaces as HTTP 400 from LiteLLM with a nested Vertex AI exception body.

## Fix

Set per-model `max_tokens` in `litellm-config.yaml` to the model's verified max. The global `litellm_settings.max_tokens` is also sent to the API — if it's higher than the model cap, it will be overridden by the per-model value. Best practice: keep per-model `max_tokens` within limits and remove the global setting or set it to a safe max.
