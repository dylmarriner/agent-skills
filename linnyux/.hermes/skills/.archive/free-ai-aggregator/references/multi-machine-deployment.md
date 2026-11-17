# Multi-Machine Aggregator Deployment

## The Problem

All machines (lin, kubuntux, macuntu) share `/mnt/development1/` via NFS/CIFS. If the aggregator lives there, they all share ONE `.env`, which breaks when each machine has different API keys. Also, CIFS latency adds 200-500ms per request.

## The Fix: Local Copies

Each machine gets its own copy on local disk with its own `.env`:

| Machine | Path | Keys |
|---------|------|------|
| lin | `~/Documents/unlimited-free-ai/` | Built-in free providers + lin's OpenRouter/DeepSeek/Kilo/NVIDIA |
| kubuntux | `/mnt/development1/unlimited-free-ai/` | Built-in free providers + kubuntux's OpenRouter/DeepSeek/Kilo/NVIDIA/OpenCode |
| macuntu | `/home/macuntu/unlimited-free-ai/` | Built-in free providers + macuntu's OpenRouter/DeepSeek/Kilo/OpenCode |

## Deployment Steps

```bash
# 1. Copy repo (exclude .env to avoid leaking keys between machines)
rsync -avz --exclude='.git' --exclude='node_modules' --exclude='.env' \
  ~/Documents/unlimited-free-ai/ macuntu:/home/macuntu/unlimited-free-ai/

# 2. Install deps on target
ssh macuntu "cd /home/macuntu/unlimited-free-ai && npm install --silent"

# 3. Write per-machine .env
# lin's .env has built-in free providers + lin's keys
# kubuntux's .env has built-in free providers + kubuntux's keys
# macuntu's .env has built-in free providers + macuntu's keys

# 4. Start aggregator
cd ~/Documents/unlimited-free-ai && node index.js &
```

## Built-in Free Provider Keys

These are shared across all machines (same keys work for all):

```
GROQ_API_KEY=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
CEREBRAS_API_KEY=csk-REDACTED
GOOGLE_API_KEY=AIza-REDACTED
MISTRAL_API_KEY=p2VyuqSNMvdoexWu8171JKPI2c08QGfb
NVIDIA_API_KEY=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
COHERE_API_KEY=SFcyaogY55il8wsB2jY9RJECe9Qanhumk9YmPFPu
CLOUDFLARE_API_TOKEN=cfat_ngD4DpmfjDYpHzWqF9OHA7TCQWKmLBrjYUz1omVl56871de8
TOGETHER_API_KEY=tgp_v1_i9sKr8EGdX8ZdcCWhTxfiJazS8nv2Pf-U3taLtm0-v8
SAMBANOVA_API_KEY=84c6c8e6-752a-4cf9-8ab7-41df02f4fd27
GITHUB_MODELS_TOKEN=github_pat_REDACTED
```

## Per-Machine Keys

### Lin
```
OPENROUTER_API_KEY=sk-REDACTED
DEEPSEEK_API_KEY=sk-REDACTED
KILOCODE_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbnYiOiJwcm9kdWN0aW9uIiwia2lsb1VzZXJJZCI6... (lin's key)
NVIDIA_API_KEY_2=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
OPENCODE_API_KEY=sk-REDACTED
```

### Kubuntux
```
OPENROUTER_API_KEY=sk-REDACTED
DEEPSEEK_API_KEY=sk-REDACTED
KILOCODE_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbnYiOiJwcm9kdWN0aW9uIiwia2lsb1VzZXJJZCI6... (kubuntux's key)
NVIDIA_API_KEY_2=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
```

### Macuntu
```
OPENROUTER_API_KEY=sk-REDACTED
DEEPSEEK_API_KEY=sk-REDACTED
KILOCODE_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbnYiOiJwcm9kdWN0aW9uIiwia2lsb1VzZXJJZCI6... (same Kilo key shared)
```

## Maximum Provider Coverage

Add duplicate entries with different keys to multiply rate-limit capacity:

```
OPENROUTER_API_KEY_2, OPENROUTER_API_KEY_3 — same key repeated for extra capacity
DEEPSEEK_API_KEY_2, DEEPSEEK_API_KEY_3
KILOCODE_API_KEY_2
```

## Hermes Integration on Each Machine

Each machine's `~/.hermes/config.yaml` must point at localhost:

```yaml
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

## Verification

```bash
# Health check
curl -s http://localhost:3099/health

# Live inference
curl -s http://localhost:3099/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"unlimited-free-ai","messages":[{"role":"user","content":"say ok"}],"max_tokens":10}'
```
