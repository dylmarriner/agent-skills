# Verified Provider API Details

Current as of July 2026. Model names and endpoints fetched live from each provider's `/v1/models` endpoint.

## Groq
- **Endpoint:** `https://api.groq.com/openai/v1`
- **Format:** openai
- **Verified models:** `llama-3.3-70b-versatile`, `llama-3.1-70b-versatile`, `llama-3.1-8b-instant`, `mixtral-8x7b-32768`
- **Limits:** 30 RPM, 14,400 RPD per model
- **Key prefix:** `gsk_`

## Cerebras
- **Endpoint:** `https://api.cerebras.ai/v1`
- **Format:** openai
- **Verified models:** `gemma-4-31b` ✓ (content output), `gpt-oss-120b` (reasoning model, `content: null`), `zai-glm-4.7`
- **Limits:** 30 RPM, 14,400 RPD
- **Key prefix:** `csk-`

## Google Gemini
- **Endpoint:** `https://generativelanguage.googleapis.com`
- **Format:** gemini (key in URL query param `?key=`)
- **Path:** `/v1beta/models/{model}:generateContent`
- **Available models:** `gemini-2.5-flash`, `gemini-2.0-flash`, `gemini-3.1-flash-lite-preview`
- **Expired:** `gemini-2.5-flash-exp-05-20` (returns "model not found")
- **Limits:** 10 RPM, 500 RPD (2.5 Flash)
- **Key prefix:** `AIzaSy`

## Mistral
- **Endpoint:** `https://api.mistral.ai/v1`
- **Format:** openai
- **Verified models:** `mistral-small-latest` ✓, `open-mistral-nemo-2407`, `ministral-8b-latest`
- **Limits:** 60 RPM, ∞ RPD
- **Key prefix:** variable

## NVIDIA NIM
- **Endpoint:** `https://integrate.api.nvidia.com/v1`
- **Format:** openai
- **Verified models:** `meta/llama-3.1-70b-instruct` ✓, `meta/llama-3.1-8b-instruct`, `mistralai/mistral-small-4-119b-2603`
- **NOT `nvidia/llama-3.3-70b-instruct`** — that model is gone
- **Limits:** 40 RPM, ∞ RPD
- **Key prefix:** `nvapi-`

## SambaNova
- **Endpoint:** `https://api.sambanova.ai/v1`
- **Format:** openai
- **Verified models:** `Meta-Llama-3.3-70B-Instruct` ✓, `DeepSeek-V3.1`, `gpt-oss-120b`
- **Limits:** 30 RPM, 1,000 RPD
- **Key format:** UUID

## Cohere
- **Endpoint:** `https://api.cohere.ai` + `/v1/chat` (NOT `/v1/chat/completions`)
- **Format:** cohere (special — uses `message` singular, `/v1/chat`)
- **Verified models:** `command-r-plus-08-2024` ✓, `command-r-08-2024`
- **Request format:** `{ model, message, chat_history?, max_tokens, temperature }`
- **Response format:** `{ text, ... }` — transform to OpenAI `choices[0].message.content`
- **Limits:** 20 RPM, 1,000 RPD

## OpenRouter
- **Endpoint:** `https://openrouter.ai/api/v1`
- **Format:** openai
- **Free models:** `openrouter/auto`, `openrouter/free`, `qwen/qwen3-coder:free`, `openai/gpt-oss-120b:free`, `meta-llama/llama-3.3-70b-instruct:free`
- **Limits:** 20 RPM, 50 RPD (free tier)
- **Key prefix:** `sk-or-v1-`

## Kilo AI (Kilocode)
- **Endpoint:** `https://api.kilo.ai/api/gateway/v1`
- **Format:** openai
- **Free model:** `kilo-auto/free` (routes to e.g. `tencent/hy3-20260706:free`)
- **Key:** JWT format (starts with `kc_`)
- **⚠️ All free models are reasoning models** — need `max_tokens >= 50` for `content` to populate. With low tokens, `content: null` and response lives in `reasoning` field only.
- **⚠️ test.js inference test needs max_tokens >= 50** when Kilo is in the rotation
- **Key has negative balance for paid models** — only free models work
- **Key rotation:** `KILOCODE_API_KEY` (lin), `KILOCODE_API_KEY_2` (kubuntux)

## OpenCode Go
- **Endpoint:** `https://opencode.ai/zen/go/v1`
- **Format:** openai
- **Models:** `glm-5.2`, `glm-5.1`, `kimi-k2.7-code`, `kimi-k2.6`, `qwen3.7-max`, `qwen3.7-plus`, `deepseek-v4-pro`, `deepseek-v4-flash`, `mimo-v2.5-pro`, `minimax-m3`
- **Paid subscription** ($10/mo, $5 first month). Monthly limit may be hit.
- **Same key** used for both OpenCode GO and ZEN
- **Key format:** `sk-...`

## Cloudflare Workers AI
- **Endpoint:** `https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/v1`
- **Format:** cloudflare
- **Env var:** `CLOUDFLARE_API_TOKEN` (NOT `CLOUDFLARE_API_KEY`)
- **Requires:** `CLOUDFLARE_ACCOUNT_ID` set
- **Models:** `@cf/meta/llama-3.1-70b-instruct`
- **Limits:** 10k neurons/day

## GitHub Models
- **Endpoint:** `https://models.inference.ai.azure.com`
- **Format:** openai
- **Models:** `gpt-4o-mini`, `Meta-Llama-3.1-8B-Instruct`
- **Requires:** PAT token with `models` permission scope — standard `github_pat_` tokens may lack this scope
