---
name: multi-provider-ai-proxy
description: Setup, fix, enhance, and maintain multi-provider AI aggregator proxies that route across free-tier and hosted LLM providers with failover, rate limiting, and format translation.
---

# Multi-Provider AI Proxy

Build and maintain OpenAI-compatible aggregator proxies that distribute requests across multiple free-tier AI providers with automatic failover.

## Trigger

When the user asks to set up, fix, enhance, or debug an AI provider aggregator/proxy — fixing provider integrations, updating model names, adding new providers, fixing API format translations, or debugging failover issues.

## Provider Discovery Pattern

Before fixing a broken provider integration, always verify the current state:

### Step 1: Check API endpoint is alive
```bash
# Test endpoint with auth-free ping if possible
curl -s https://api.provider.com/v1/models
```

### Step 2: Verify auth works
```bash
curl -s https://api.provider.com/v1/models \
  -H "Authorization: Bearer $KEY" | python3 -c "import sys,json; [print(m['id']) for m in json.load(sys.stdin).get('data',[])]"
```

### Step 3: Test actual chat completion
```bash
curl -s https://api.provider.com/v1/chat/completions \
  -X POST \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"MODEL_ID","messages":[{"role":"user","content":"say ok"}],"max_tokens":5}'
```

### Step 4: Check response shape
- OpenAI-format: `response.choices[0].message.content`
- Cohere (v1/chat): `response.text`
- Gemini (v1beta): `response.candidates[0].content.parts[0].text`
- Cloudflare: `response.response`

## Common Provider Fixes

### Model name staleness
Provider model names change frequently. Always query `/v1/models` to verify current names before hardcoding. Use `gemini-2.5-flash` (stable) not `gemini-2.5-flash-exp-*` (experimental/expired). Use `gemma-4-31b` not `llama-3.3-70b` for Cerebras.

### Env var name mismatch
Providers often use different env var names than what the code expects. Check both the code and the .env file. E.g. Cloudflare uses `CLOUDFLARE_API_TOKEN` not `CLOUDFLARE_API_KEY`.

### Cohere special handling
- Endpoint: `/v1/chat` NOT `/v1/chat/completions`
- Request uses singular `message` field (the last user message), not `messages[]`
- Prior conversation goes in `chat_history` array
- Response has `text` field, not `choices[].message.content`
- Response transform: `data.text` or `data.generations?.[0]?.text`

### Gemini special handling
- API key in URL query param (`?key=...`), not header
- Model name in URL path: `/v1beta/models/{MODEL_ID}:generateContent`
- Request format: `contents` array with `role`/`parts[{text}]`
- Response: `candidates[0].content.parts[0].text`
- Available stable models: `gemini-2.5-flash`, `gemini-2.0-flash`, `gemini-3.1-flash-lite-preview`

### Platform-specific pitfalls

**Groq**: `llama-3.3-70b-versatile` is the current best model. 30 RPM, 14,400 RPD free.

**Cerebras**: Models changed from `llama-3.3-70b`/`llama-3.1-8b` to `gemma-4-31b`/`gpt-oss-120b`/`zai-glm-4.7`. The `gpt-oss-120b` is a reasoning model (content in `reasoning` field, `content: null`). Use non-reasoning models for standard chat.

**NVIDIA NIM**: Base URL `https://integrate.api.nvidia.com/v1`. Current working models: `meta/llama-3.1-70b-instruct`, `meta/llama-3.1-8b-instruct`, `mistralai/mistral-small-4-119b-2603`.

**Mistral**: `mistral-small-latest` maps to `mistral-small-2603`. Standard OpenAI format, 60 RPM, unlimited RPD.

**SambaNova**: `Meta-Llama-3.3-70B-Instruct` is the best Llama model. Also has `DeepSeek-V3.1` and `gpt-oss-120b`. Standard OpenAI format.

**Cloudflare**: Needs both `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`. Base URL: `https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/v1`. Response has `data.response` field.

**Together AI**: Free key credits may expire. Check billing if 402/credit errors appear. Standard OpenAI format.

## Fixing the `...body` Override Bug

When transforming requests for the default (OpenAI) format, the processed model name must NOT be overwritten:

```js
// WRONG — ...body spread AFTER model/messages overrides them
return { model: resolvedId, messages, ...body };

// RIGHT — ...body spread BEFORE so model/messages win
return { ...body, model: resolvedId, messages };
```

Same principle applies to any request transformation: set overrides AFTER the spread.

## Architecture Pattern

```
Client → Local Proxy (Express) → Provider Router → Provider 1 (success?)
                                                    → Provider 2 (failover)
                                                    → Provider 3 (failover)
                         ↓
                   Rate Limiter (RPM/RPD tracking)
                   Cooldown Manager (429 backoff)
                   Format Translator (per provider)
```

Key components:
- **ProviderRouter**: Round-robin selection, failover loop, rate limit checks
- **AIProvider**: Per-provider config, URL building, request/response transforms
- **UsageTracker**: RPM counters (reset every 60s) + RPD counters per model

## Pitfalls

- `validateStatus: () => true` in axios is critical — without it, axios throws on non-2xx and you can't detect 429/500 for failover
- RPM resets happen every 60 seconds via `setInterval` — don't miss this or all providers permanently hit their limits
- When adding a new provider, register it in `initializeProviders` AND call `usageTracker.initializeProvider(provider)` — missing either breaks tracking
- For streaming, Cohere uses SSE events with `event_type` and `text` fields, not the standard `data: {...}` format — may need special SSE parsing
- Node.js require cache can cause "stale module" errors after edits — always kill and restart the process
- **Timeout tuning**: Default axios timeout is 30s. Reduce to 10s for free-tier providers (they fail fast or tokens are wasted). Two locations in providers.js need patching — the regular request and the streaming request.
- **Kilo AI reasoning models**: Free Kilo models (e.g. `kilo-auto/free`, `tencent/hy3:free`) are reasoning models. They return `content: null` and `reasoning` with low max_tokens (< 20). Always set `max_tokens >= 50` for good output. Base URL: `https://api.kilo.ai/api/gateway/v1`. API key is a JWT token, env var `KILOCODE_API_KEY`.
- **OpenCode Go/Zen**: OpenAI-compatible endpoint at `https://opencode.ai/zen/go/v1`. Same key for Go (subscription, $10/mo) and Zen (pay-as-you-go). Monthly limits apply. Env var: `OPENCODE_API_KEY`.
- **DeepSeek is NOT free**: DeepSeek charges $0.07/M input tokens. Requires topped-up balance. Only include if key has credits.
- **PORT conflict**: Grafana defaults to 3000. Move AI aggregator to 3099 to avoid collision.
- **Shared NFS/CIFS pitfall**: With a shared mount like `/mnt/development1/` across machines, ONE `.env` file serves ALL. Writing from one host clobbers another. Solution: each machine gets its own LOCAL aggregator directory.
- **Per-machine .env strategy**: Create separate `.env` per machine with that machine's API keys + shared built-in free provider keys (Groq, Cerebras, Google, Mistral, NVIDIA, Cohere, Cloudflare, Together, SambaNova, GitHub Models are same across machines).
- **Kilo env var naming**: Uses `KILOCODE_API_KEY` and `KILOCODE_API_KEY_2`. The `_2` variant is for redundancy — same JWT key works for both.
- **Hermes custom_providers config**: Add to `custom_providers` section with `name`, `base_url`, `api_key`, `models`. Add to `fallback_providers` for auto-failover. Test with `hermes --provider unlimited-free-ai --model unlimited-free-ai`.
- **Grafana port check**: Always `ss -tlnp | grep 3000` before binding — Grafana may claim it even when inactive.

## Reference Files

- `references/verified-provider-configs.md` — current working model names, endpoints, and rate limits per provider (verified via live API calls)
- `references/hermes-integration.md` — wiring the aggregator into Hermes as a custom provider + fallback, per-machine .env strategy, config repair, and CIFS mount tuning
