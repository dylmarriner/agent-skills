# Verified Provider Configurations (July 2026)

Current working endpoints, model names, and rate limits for free-tier AI providers.
Verified via live API calls — do not assume model names are stable.

## Groq (openai format)
- **Base URL**: `https://api.groq.com/openai/v1`
- **Verified models**: `llama-3.3-70b-versatile`, `llama-3.1-70b-versatile`, `llama-3.1-8b-instant`, `mixtral-8x7b-32768`
- **Limits**: 30 RPM, 14,400 RPD per model

## Cerebras (openai format)
- **Base URL**: `https://api.cerebras.ai/v1`
- **Verified models**: `gemma-4-31b` (non-reasoning), `gpt-oss-120b` (reasoning — content in `reasoning` field), `zai-glm-4.7`
- **Limits**: 30 RPM, 14,400 RPD
- **Note**: Old model names `llama-3.3-70b` and `llama-3.1-8b` no longer exist.

## Google Gemini (gemini format)
- **Base URL**: `https://generativelanguage.googleapis.com`
- **API endpoint**: `/v1beta/models/{MODEL_ID}:generateContent?key={API_KEY}`
- **Verified models**: `gemini-2.5-flash` (10 RPM, 500 RPD), `gemini-2.0-flash` (15 RPM, 1,000 RPD), `gemini-3.1-flash-lite-preview` (20 RPM, 1,500 RPD)
- **Note**: Experimental models like `gemini-2.5-flash-exp-05-20` expire. Use stable names.

## Mistral (openai format)
- **Base URL**: `https://api.mistral.ai/v1`
- **Verified models**: `mistral-small-latest` (→ `mistral-small-2603`), `open-mistral-nemo-2407`, `ministral-8b-latest`
- **Limits**: 60 RPM, ~100,000 RPD

## NVIDIA NIM (openai format)
- **Base URL**: `https://integrate.api.nvidia.com/v1`
- **Verified models**: `meta/llama-3.1-70b-instruct`, `meta/llama-3.1-8b-instruct`, `mistralai/mistral-small-4-119b-2603`
- **Limits**: 40 RPM, ~100,000 RPD
- **Note**: `nvidia/llama-3.3-nemotron-super-49b-v1.5` is a reasoning model (content in `reasoning` field). Use non-reasoning models for standard chat.

## SambaNova (openai format)
- **Base URL**: `https://api.sambanova.ai/v1`
- **Verified models**: `Meta-Llama-3.3-70B-Instruct`, `DeepSeek-V3.1`, `gpt-oss-120b`
- **Limits**: 30 RPM, 1,000 RPD

## Cohere (cohere format — custom)
- **Base URL**: `https://api.cohere.ai`
- **Chat endpoint**: `/v1/chat` (NOT `/v1/chat/completions`)
- **Verified models**: `command-r-plus-08-2024`, `command-r-08-2024`
- **Limits**: 20 RPM, 1,000 RPD
- **Request format**: `message` (singular string, last user message), `chat_history` array for prior messages
- **Response format**: `data.text` (not `choices[].message.content`)

## Cloudflare Workers AI (cloudflare format)
- **Base URL**: `https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/v1`
- **Env vars**: `CLOUDFLARE_API_TOKEN` (NOT `CLOUDFLARE_API_KEY`), `CLOUDFLARE_ACCOUNT_ID`
- **Verified models**: `@cf/meta/llama-3.1-70b-instruct`, `@cf/meta/llama-3.2-11b-vision-instruct`
- **Limits**: 60 RPM, 10,000 RPD
- **Response format**: `data.response`

## Together AI (openai format)
- **Base URL**: `https://api.together.xyz/v1`
- **Limits**: 30 RPM, 1,000 RPD
- **Note**: Free key credits may expire. 402/credit errors = add credits at billing portal.

## OpenRouter (openai format)
- **Base URL**: `https://openrouter.ai/api/v1`
- **Limits**: 20 RPM, 50 RPD (free tier)
- **Note**: Requires key — no free tier without signup.

## GitHub Models (openai format)
- **Base URL**: `https://models.inference.ai.azure.com`
- **Auth**: GitHub PAT with `models` permission scope
- **Limits**: 15 RPM, 150 RPD
- **Note**: The `models` scope must be enabled in the PAT token settings.

## Kilo AI (openai format)
- **Base URL**: `https://api.kilo.ai/api/gateway/v1`
- **Auth**: JWT token, env var `KILOCODE_API_KEY`
- **Free models**: `kilo-auto/free`, `stepfun/step-3.7-flash:free`, `poolside/laguna-xs-2.1:free`, `cohere/north-mini-code:free`, `nvidia/nemotron-3-ultra-550b-a55b:free`
- **Pitfall**: All free models are reasoning-type — return `content: null` with low max_tokens (< 20). Need `max_tokens >= 50` for visible output.

## OpenCode Go/Zen (openai format)
- **Base URL**: `https://opencode.ai/zen/go/v1`
- **Auth**: API key, env var `OPENCODE_API_KEY`
- **Note**: Paid service ($10/mo Go, $20 pay-as-you-go Zen). Monthly request limit applies. Not a free provider.
