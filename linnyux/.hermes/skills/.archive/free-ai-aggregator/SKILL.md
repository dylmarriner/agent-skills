---
name: free-ai-aggregator
description: Build and maintain a free AI provider aggregator proxy — Node.js Express proxy that round-robins across multiple free-tier AI APIs behind a single OpenAI-compatible endpoint.
trigger: When the user says build/maintain/fix/test an AI provider aggregator, free-tier AI proxy, multi-provider failover, or unlimited-free-ai.
---

# Free AI Provider Aggregator

Class of work: maintaining a Node.js Express proxy that aggregates multiple free-tier AI providers behind one OpenAI-compatible `/v1/chat/completions` endpoint with round-robin failover and rate-limit tracking.

## Architecture

```
Express server → ProviderRouter → AIProvider[0..N] → external API
                 UsageTracker (RPM/RPD counters)
                 failover on 429/500/timeout
```

**Key file structure:**
```
index.js            — Express server (health, models, chat completions)
src/provider.js     — AIProvider class (format transforms, URL building)
src/providers.js    — ProviderRouter class (provider list, failover logic)
src/usage-tracker.js — RPM/RPD rate-limit counters
```

## Provider Integration Process

### 1. Find the endpoint
- Check the provider's docs for an OpenAI-compatible `/v1/chat/completions` endpoint
- If the provider uses a custom format (Gemini, Cohere), note the differences
- Verify with `curl -s <base_url>/v1/models`

### 2. Verify with a real request
```bash
curl -s "<base_url>/v1/chat/completions" \
  -H "Authorization: Bearer <key>" \
  -H "Content-Type: application/json" \
  -d '{"model":"<model-id>","messages":[{"role":"user","content":"say ok"}],"max_tokens":10}'
```

### 3. Handle non-OpenAI formats
Add a `format` type to AIProvider and implement `transform*Request` / `transform*Response`.

| Format | API Endpoint | Body Format | Response |
|--------|-------------|-------------|----------|
| `openai` | `/v1/chat/completions` | `{model, messages}` | `choices[0].message.content` |
| `kilo` | `https://api.kilo.ai/api/gateway/v1` | OpenAI-compatible | same (but reasoning models return `content: null` with low `max_tokens`) |
| `gemini` | `/v1beta/models/{model}:generateContent` | `{contents, generationConfig}` | `candidates[0].content.parts[0].text` |
| `cohere` | `/v1/chat` | `{message, chat_history}` | `text` field |
| `cloudflare` | `/ai/v1/chat/completions` | OpenAI-compatible | `response` field |

### 4. Set up options for path overrides (e.g., Cohere)
```js
new AIProvider(..., 'cohere', { chatPath: '/v1/chat' })
```

## Common Bugs & Fixes

### `...body` spread overwrites model name
```js
// ❌ WRONG: ...body overwrites model back to 'unlimited-free-ai'
return { model: getModelId(body.model), messages, ...body };

// ✅ CORRECT: ...body first, then override
return { ...body, model: getModelId(body.model), messages };
```

### Destructuring import mismatch
```js
// If module exports: module.exports = ProviderRouter;
// ❌ WRONG: const { ProviderRouter } = require('./path');
// ✅ CORRECT: const ProviderRouter = require('./path');
```

### Reasoning models return content=null
Some free models (Tencent HY3, Nemotron variants) are reasoning models — with low `max_tokens` the model never finishes thinking and `content` stays null. Solution: set `max_tokens >= 100` or pick non-reasoning models.

### Port conflict: Grafana uses 3000
If Grafana is installed, it owns port 3000 by default. Move the aggregator:
```bash
# In .env
PORT=3099
```
Also update any test.js that hardcodes `'http://localhost:3000'` to `'http://localhost:3099'`.

### Multi-machine deployment: shared NFS/CIFS mount gotcha
If machines share an NFS/CIFS mount (e.g. `/mnt/development1/` is the same share on all machines), keeping the aggregator there means they share ONE `.env`. This breaks when each machine has different API keys.

**Fix:** copy the repo to each machine's **local** disk and give each its own `.env`:
- lin: `~/Documents/unlimited-free-ai/`
- kubuntux: local disk aggregator dir  
- macuntu: `~/unlimited-free-ai/`

### Fast failover: lower timeout from 30s to 10s
In `src/providers.js`, both request and streaming timeouts default to 30000ms. For free-tier providers that frequently timeout, lower to 10000ms:
```js
timeout: 10000,  // instead of 30000
```
This makes the round-robin skip dead providers 3x faster.

### Stale model names change frequently
Free-tier providers rotate model names often. Verify current models via:
```bash
curl -s <provider_url>/v1/models -H "Authorization: Bearer <key>"
```

### Kilo AI free models need enough max_tokens
Kilo (`https://api.kilo.ai/api/gateway/v1`) routes to reasoning models that need `max_tokens >= 100` to finish chain-of-thought and emit `content`. With low `max_tokens`, `content` is null and only `reasoning` is populated.

### OpenCode Go endpoint
OpenCode Go and Zen share the same base URL and API key:
- Base URL: `https://opencode.ai/zen/go/v1`
- API key from env: `OPENCODE_API_KEY`
- Monthly subscription ($10/mo), not truly free — rate-limit resets monthly

## Multi-Machine Deployment

When deploying across machines that share an NFS/CIFS mount — each gets a local copy with its own `.env`. See `references/multi-machine-deployment.md` for exact steps, key lists, and verification commands for a 3-machine fleet (lin, kubuntux, macuntu).

## Hermes Integration

To connect the aggregator as a Hermes custom provider on any machine:

```yaml
# In ~/.hermes/config.yaml
custom_providers:
  - api_key: ''
    base_url: http://localhost:3099/v1
    models:
      - unlimited-free-ai
    name: unlimited-free-ai
fallback_providers:
  - provider: unlimited-free-ai
    model: unlimited-free-ai
```

For multi-machine setups, each machine must run its own aggregator instance pointing at localhost. Do NOT share one aggregator across machines via CIFS/NFS — latency adds 200-500ms per request.

## Environment Setup
Add duplicate provider entries for the same service with different API keys to multiply rate-limit capacity:
```js
new AIProvider('groq', process.env.GROQ_API_KEY_1, ...),
new AIProvider('groq-2', process.env.GROQ_API_KEY_2, ...),
```
Each key gets independent RPM/RPD tracking.

## Environment Setup
- `.env` with `API_KEY=VALUE` per provider
- `dotenv` loads in `index.js`
- Keep `.env.example` for reference, never check `.env` into git

## Testing
```bash
# Health check
curl localhost:3000/health | jq '.[] | {name, configured, available}'

# Chat completion
curl localhost:3000/v1/chat/completions -X POST \
  -H "Content-Type: application/json" \
  -d '{"model":"unlimited-free-ai","messages":[{"role":"user","content":"hi"}]}'

# Streaming
curl localhost:3000/v1/chat/completions -X POST \
  -H "Content-Type: application/json" \
  -d '{"model":"unlimited-free-ai","messages":[{"role":"user","content":"hi"}],"stream":true}'
```

## Daily Capacity Math
Sum RPM × 60 (minutes) of all configured providers, accounting for per-provider RPM cap. Typical free-tier: ~170K–300K req/day.
