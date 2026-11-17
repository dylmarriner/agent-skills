---
name: unlimited-free-ai-aggregator
description: "Setup and maintenance of the unlimited-free-ai OpenAI-compatible aggregator proxy — multi-provider failover, key rotation, provider fixes, and Hermes integration."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [aggregator, proxy, openai, free-providers, failover, key-rotation]
    related_skills: [ai-platform-provisioning, hermes-agent]
---

# Unlimited Free AI Aggregator

An OpenAI-compatible aggregator proxy (Node.js/Express) that round-robins across multiple free AI providers with automatic failover, rate-limit tracking, and streaming support.

Project root: `/mnt/development1/unlimited-free-ai/`

## Architecture

```
index.js          → Express server, routes /v1/chat/completions
src/providers.js  → ProviderRouter class (failover + round-robin)
src/provider.js   → AIProvider class (per-provider request/response transforms)
src/usage-tracker.js → RPM/RPD tracking
```

**Key flow:** Request arrives → ProviderRouter picks next available provider (random start, round-robin) → checks rate limits → transforms request to provider format → on failure, tries next → returns first success → records usage.

## Verified Free Providers (current models)

| Provider | Model | RPM | RPD | Format |
|----------|-------|-----|-----|--------|
| Groq | `llama-3.3-70b-versatile` | 30 | 14,400 | openai |
| Cerebras | `gemma-4-31b` | 30 | 14,400 | openai |
| Google Gemini | `gemini-2.5-flash` | 10 | 500 | gemini |
| Mistral | `mistral-small-latest` | 60 | ∞ | openai |
| NVIDIA | `meta/llama-3.1-70b-instruct` | 40 | ∞ | openai |
| SambaNova | `Meta-Llama-3.3-70B-Instruct` | 30 | 1,000 | openai |
| Cohere | `command-r-plus-08-2024` | 20 | 1,000 | cohere |
| OpenRouter | `openrouter/auto` | 20 | 50 | openai |
| Kilo AI | `kilo-auto/free` | 20 | 1,000 | openai |
| OpenCode Go | `glm-5.2` | 30 | 500 | openai |
| DeepSeek | `deepseek-chat` ⚠️ (paid, $0.07/M tokens) | 20 | ∞ | openai |

**Current state: 20/20 providers active** across duplicate keys:
- `openrouter` / `openrouter-2` / `openrouter-3` — lin + kubuntux + macuntu keys
- `deepseek` / `deepseek-2` / `deepseek-3` — lin + kubuntux + macuntu keys
- `nvidia` / `nvidia-2` — lin + kubuntux keys
- `kilo` / `kilo-2` — lin + kubuntux keys
- `opencode-go` — OpenCode GO/ZEN key (monthly limit may be hit)

⚠️ **DeepSeek is NOT free** — $0.29 balance, paid per token. Use only as a paid fallback or remove from free tier.

## Provider Patterns

### Adding a provider
```js
new AIProvider('name', process.env.API_KEY_VAR, 'https://api.example.com/v1', [
    { id: 'model-name', rpm: 30, rpd: 1000, name: 'Friendly Name' },
], 'openai')
```

### Key rotation (duplicate providers)
Create multiple provider entries with different env var keys to get N× rate limit:
```js
new AIProvider('openrouter', process.env.OPENROUTER_API_KEY, ...)
new AIProvider('openrouter-2', process.env.OPENROUTER_API_KEY_2, ...)
```

### Format types
- `'openai'` — standard OpenAI-compatible (default)
- `'gemini'` — Google Gemini API (key in URL, v1beta models)
- `'cohere'` — Cohere API (uses `/v1/chat` endpoint, singular `message` field)
- `'cloudflare'` — Cloudflare Workers AI

## Common Fixes

### Model name override bug
The `transformRequest()` default handler must spread `...body` BEFORE setting `model` and `messages`, otherwise the original request body's `model` field overwrites the resolved model ID:
```js
// CORRECT:
return { ...body, model: this.getModelId(body.model), messages };
// WRONG (model gets overwritten):
return { model: this.getModelId(body.model), messages, ...body };
```

### Cohere API quirks
- Uses `/v1/chat` endpoint, NOT `/v1/chat/completions`
- Uses singular `message` field, NOT `messages` array
- Format: `{ model, message: "text", chat_history?: [{role, message}] }`
- Response has `text` field instead of `choices`

Set via `options.chatPath`:
```js
new AIProvider('cohere', key, 'https://api.cohere.ai', [...], 'cohere',
    { chatPath: '/v1/chat' })
```

### Reasoning model token needs
Kilo AI's free models (`kilo-auto/free`) are reasoning models. With low `max_tokens`, they return `content: null` — only `reasoning` field is populated. Need `max_tokens >= 50` for reasoning to complete and produce output.

### Import gotcha
`index.js` must NOT use destructuring for the ProviderRouter import:
```js
// CORRECT:
const ProviderRouter = require('./src/providers');
// WRONG (ProviderRouter is undefined):
const { ProviderRouter } = require('./src/providers');
```

## Key Aggregation Across Machines

### ⚠️ CIFS/NFS Shared-Mount Pitfall (this session's lesson)

When `/mnt/development1/` is the project directory, **all machines see the same disk:**
- kubuntux exports `/media/kubuntux/DEVELOPMENT1` via Samba
- lin and macuntu mount it as `//100.93.75.87/DEVELOPMENT1`
- A `.env` write on lin appears on kubuntux and macuntu too. Writes clobber each other.

**Fix:** Each machine runs from its OWN local directory with a per-machine `.env`:

| Machine | Aggregator Path | .env Contains |
|---------|----------------|---------------|
| lin | `~/Documents/unlimited-free-ai/` | Built-in free keys + lin's personal keys |
| kubuntux | `/mnt/development1/unlimited-free-ai/` (local disk) | Built-in free keys + kubuntux's keys |
| macuntu | `/home/macuntu/unlimited-free-ai/` | Built-in free keys + macuntu's keys |

**Building per-machine .env:** each needs (1) built-in free provider keys from `.env.example` (same on all machines) + (2) that machine's personal keys (OpenRouter, DeepSeek, Kilo, NVIDIA_2, OpenCode).

On CIFS mounts, shell `tee`/`cat >` may fail. Use `python3 -c "with open(...) as f: f.write(...)"` instead.

After moving copies or changing port, update the Hermes config on each machine to `http://localhost:3099/v1`.

Collect API keys from multiple machines and create duplicate providers:

### Key harvesting pattern
```bash
# From the machine running the aggregator:
grep 'SOME_API_KEY' ~/.hermes/.env                                    # local
ssh kubuntux "grep 'SOME_API_KEY' /home/kubuntux/.hermes/.env"        # remote
ssh macuntu "grep 'SOME_API_KEY' /home/macuntu/.hermes/.env"          # remote
```

### Duplicate provider pattern
Add numbered provider entries, each with its own env var:
```js
// In providers.js:
new AIProvider('openrouter',  process.env.OPENROUTER_API_KEY, ...)    // lin's key
new AIProvider('openrouter-2', process.env.OPENROUTER_API_KEY_2, ...) // kubuntux's key  
new AIProvider('openrouter-3', process.env.OPENROUTER_API_KEY_3, ...) // macuntu's key
```

In `.env`:
```bash
OPENROUTER_API_KEY=sk-or-...     # from lin
OPENROUTER_API_KEY_2=sk-or-...   # from kubuntux
OPENROUTER_API_KEY_3=sk-or-...   # from macuntu
```

This works for any provider: `deepseek`, `nvidia`, `kilocode`, etc.

## Hermes Integration

### Same machine
Add as a custom provider in `~/.hermes/config.yaml`:
```yaml
custom_providers:
  - api_key: ''
    base_url: http://localhost:3099/v1
    models: [unlimited-free-ai]
    name: unlimited-free-ai
fallback_providers:
  - provider: unlimited-free-ai
    model: unlimited-free-ai
```

### Cross-machine (kubuntux, macuntu)
When the aggregator runs on lin (Tailscale IP), other machines connect via Tailscale:
```yaml
# On kubuntux and macuntu — use lin's Tailscale IP as the target
custom_providers:
  - api_key: ''
    base_url: http://100.91.55.113:3099/v1
    models: [unlimited-free-ai]
    name: unlimited-free-ai
fallback_providers:
  - provider: unlimited-free-ai
    model: unlimited-free-ai
```

Push config via SSH:
```bash
ssh kubuntux "python3 -c '
import yaml
with open(\"/home/kubuntux/.hermes/config.yaml\") as f: data = yaml.safe_load(f)
existing = json.loads(data.get(\"custom_providers\", \"[]\"))
existing.append({\"name\": \"unlimited-free-ai\", \"base_url\": \"http://100.91.55.113:3099/v1\", \"api_key\": \"\", \"models\": [\"unlimited-free-ai\"]})
data[\"custom_providers\"] = existing
fbs = data.get(\"fallback_providers\", [])
fbs.append({\"provider\": \"unlimited-free-ai\", \"model\": \"unlimited-free-ai\"})
data[\"fallback_providers\"] = fbs
with open(\"/home/kubuntux/.hermes/config.yaml\", \"w\") as f: yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
'"
```

Use via: `hermes --provider unlimited-free-ai --model unlimited-free-ai`
Or set as default: update `model.provider` in config.

## Migrating aggregator providers INTO OmniRoute (single central router)

OmniRoute (npm -g omniroute, `omniroute serve` on :20128) can absorb all the free-tier providers from the aggregator .env as native provider connections. Bulk-add via `omniroute providers add <catalog-id> --name <conn> --credential-env OMNI_CRED --yes` (pass key via env, never argv).

**CRITICAL provider-id mapping (OmniRoute catalog names differ from aggregator names):**
- CLOUDFLARE_API_TOKEN -> provider id **`cloudflare-ai`** (NOT `cloudflare` — that's invalid)
- KILOCODE JWT keys -> provider id **`kilo-gateway`** (NOT `kilocode` — that's OAuth/copilot-only, rejects raw keys)
- OPENCODE_API_KEY -> provider id **`opencode-go`** (NOT `opencode` — that's a noauth web provider; adding there stores no useful cred)
- GROQ/CEREBRAS/MISTRAL/SAMBANOVA/TOGETHER/COHERE/GOOGLE(gemini) keys -> same-named catalog ids (`cerebras`,`groq`,`mistral`,`sambanova`,`together`,`cohere`,`gemini`)
- GitHub Models PAT (GITHUB_MODELS_TOKEN, models.inference.ai.azure.com) has **NO** api-key catalog slot — catalog `github` is OAuth-only. Skip it or route via a separate OpenAI-compatible proxy.

**Pitfalls:**
- Run the omniroute CLI from a NEUTRAL cwd (~ or ~/.omniroute). If cwd is the aggregator project dir, omniroute auto-loads that ./.env (PORT=3099 etc.) and every `providers add` fails rc=1. Same for remove.
- `--dry-run` lies: it returns rc=0 for invalid catalog ids that fail on the real add with `✖ Invalid provider`. Always run the real add to confirm.
- Dead keys are common (aggregator DeepSeek keys returned `Invalid API key` against api.deepseek.com — paid tier, revoked). `omniroute providers test-all` flags them; remove dead ones so auto-fallback doesn't burn a hop.
- Verify with `omniroute providers test-all` (real upstream calls, not config validation).
- Model routing needs a `provider/model` prefix AND the model in the provider's active live catalog: `omniroute chat -m 'samba/MiniMax-M2.7'` works; `groq/Llama 3.3 70B` can 400 "not in active live catalog" even though the key is fine and the model shows in `omniroute models`.
- Startup banner: dashboard login password stored bcrypt in key_value table (settings|password); check against INITIAL_PASSWORD env (default `CHANGEME`).

## Port conflict
Default port 3000 conflicts with Grafana. Changed to **3099**.
Set via `PORT=3099` in `.env`.
After changing port, update Hermes config on all machines to point at the new port.

## Verification
Run `cd /mnt/development1/unlimited-free-ai && node test.js` — tests module load, health, and live inference.

### test.js pitfalls
When aggregator has reasoning-model providers (Kilo AI, etc.):
- Low `max_tokens` returns `content: null` because reasoning doesn't finish
- Bump `max_tokens` to `50` in the test to account for reasoning models in the rotation
- The test's inference test routes to the first available provider — if that's a reasoning model, it needs enough tokens
