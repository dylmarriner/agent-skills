---
name: api-proxy-aggregator-patterns
description: Build multi-provider API aggregators with failover, request transformation, rate-limit tracking, and streaming proxy support. Use when creating OpenAI-compatible proxies, API gateways, provider rotators, or any service that aggregates upstream APIs behind a single endpoint.
---

# API Proxy / Aggregator Patterns

Patterns for building multi-provider API aggregators that combine several upstream API providers behind a single OpenAI-compatible (or other) interface with automatic failover, rate-limit tracking, and streaming support.

## When to Use This Skill

- Building an OpenAI-compatible proxy with multiple backend providers
- Creating an API gateway with failover and round-robin
- Aggregating free-tier API providers behind a single endpoint
- Building request transformation pipelines (provider-specific format translation)
- Implementing rate-limit aware routing across multiple upstream services

## Architecture Overview

```
Client ──► Aggregator (localhost:3000) ──► Provider 1 (fail?) ──► Provider 2 ──► ...
                      │
                      ├── Rate-limit tracker (RPM/RPD)
                      ├── Round-robin selector
                      └── Cooldown manager (429 backoff)
```

## Request Transformation — Spread Order Pitfall

**Common bug**: when wrapping API requests, the `...body` spread can silently override properties you think you set.

```js
// ❌ WRONG — ...body comes last, overwrites model/messages
function transformRequest(body) {
    return { model: resolveModel(body.model), messages, ...body };
    // ^ body.model from the original request stomps your resolved model
}

// ✅ CORRECT — explicit overrides come AFTER the spread
function transformRequest(body) {
    return { ...body, model: resolveModel(body.model), messages };
}
```

**Why**: The spread operator copies all enumerable own properties. When `...body` is last, any field in `body` (including `model`, `messages`, `stream`) overwrites the values you set before it.

**Hit hardest in**:
- OpenAI-compatible proxy (user passes `model: "my-virtual-name"` which overwrites the resolved provider model ID)
- Request sanitization pipelines
- Multi-tenant request normalization layers

## Failover Chain Pattern

### Provider Selection (Round-Robin)
```js
getNextProvider(excludeProviders) {
    const all = getAllProviders();
    const start = Math.floor(Math.random() * all.length);
    for (let i = 0; i < all.length; i++) {
        const p = all[(start + i) % all.length];
        if (excludeProviders.includes(p.name)) continue;
        if (!p.isConfigured()) continue;
        if (p.isInCooldown()) continue;
        if (hasAvailableRateLimit(p)) return p;
    }
    return null; // all exhausted
}
```

### Retry Loop
```js
async chatCompletion(body) {
    const tried = [];
    while (true) {
        const p = getNextProvider(tried);
        if (!p) throw { message: 'All providers unavailable', status: 429 };
        tried.push(p.name);
        try {
            return await callProvider(p, body);
        } catch (err) {
            if (err.response?.status === 429) p.setCooldown(60);
            if (tried.length >= allProviders.length) throw err;
            // continue to next provider
        }
    }
}
```

### Key Checks (in order)
1. **Configured**: API key set and valid
2. **Cooldown**: not in backoff from recent 429
3. **Rate limits**: RPM or RPD not exhausted for at least one model
4. **Not already tried**: skip providers that already failed

## Rate-Limit Tracking

```js
class UsageTracker {
    constructor() {
        this.usage = {}; // { providerName: { rpm: {modelId: count}, rpd: {...}, lastReset } }
    }

    canMakeRequest(provider, modelId) {
        const rpmUsed = this.usage[provider.name].rpm[modelId] || 0;
        const rpdUsed = this.usage[provider.name].rpd[modelId] || 0;
        const limits = provider.models.find(m => m.id === modelId);
        return rpmUsed < limits.rpm && rpdUsed < limits.rpd;
    }

    resetRpmCounters() {
        // Called every 60s via setInterval
    }
}
```

- Reset RPM counters every 60s via `setInterval`
- Never reset RPD counters (they roll over naturally after 24h of inactivity, or use a cron job)
- After a 429 response, set provider cooldown for 60s

## Streaming Proxy

```js
res.setHeader('Content-Type', 'text/event-stream');
res.setHeader('Cache-Control', 'no-cache');
res.setHeader('Connection', 'keep-alive');
res.setHeader('X-Accel-Buffering', 'no');

const response = await axios({
    method: 'post',
    url,
    headers,
    data: { ...body, stream: true },
    responseType: 'stream'  // critical — avoids buffering
});

response.data.on('data', chunk => res.write(chunk));
response.data.on('end', () => res.end());
response.data.on('error', () => {
    res.write('data: [DONE]\n\n');
    res.end();
});
```

### SSE Headers Checklist
- `Content-Type: text/event-stream`
- `Cache-Control: no-cache`
- `Connection: keep-alive`
- `X-Accel-Buffering: no` (nginx compatibility)
- Forward `X-Provider` header to identify which upstream served

## Provider-Specific Format Translation

Maintain a `format` field per provider (`'openai'`, `'gemini'`, `'cohere'`, `'cloudflare'`).

```js
transformRequest(body) {
    switch (this.format) {
        case 'gemini':
            return { contents: mapMessages(body.messages), generationConfig: {...} };
        case 'cohere':
            return { model: this.modelId, messages: mapRoles(body.messages), ... };
        default: // openai
            return { ...body, model: this.getModelId(body.model), messages };
    }
}
```

### Response Normalization
Each non-OpenAI provider response must be mapped back to OpenAI format:
```js
{
    id: 'chatcmpl-...',
    object: 'chat.completion',
    created: timestamp,
    model: '...',
    choices: [{ index: 0, message: { role: 'assistant', content: '...' }, finish_reason: 'stop' }],
    usage: { prompt_tokens: N, completion_tokens: N, total_tokens: N }
}
```

### Gemini Specifics
- API key goes in URL query param: `?key=${apiKey}`, not in Authorization header
- URL format: `{baseUrl}/v1beta/models/{modelId}:generateContent`
- Roles: `user` stays, `assistant` becomes `model`
- Content wraps in `parts: [{ text: content }]`

## Health / Status Endpoint

Expose a `/health` or `/status` endpoint returning per-provider:
```json
{
    "status": "ok",
    "activeProviders": 9,
    "totalProviders": 22,
    "providers": [
        { "name": "groq", "configured": true, "available": true, "inCooldown": false, "cooldownRemaining": 0, "availableModels": 4, "totalModels": 4 }
    ]
}
```

## Pitfalls

- **Spread override**: Always put `...body` first when building transformed request objects, then layer overrides on top
- **Gemini model IDs change frequently**: experimental model names (like `gemini-2.5-flash-exp-05-20`) expire. Use stable model names or check the API's `/models` endpoint
- **`.env` vs `.env.example`**: A `.env.example` with pre-filled keys is useful for development; a real `.env` is needed at runtime. Don't forget to `cp .env.example .env`
- **Stream error handling**: A failed upstream stream should send `data: [DONE]\n\n` to the client before closing, not just `res.end()` — otherwise the client hangs waiting for the stream to terminate
- **Rate-limit ordering**: Check rate limits BEFORE sending requests. A rejected request costs the same as a successful one on most free tiers
