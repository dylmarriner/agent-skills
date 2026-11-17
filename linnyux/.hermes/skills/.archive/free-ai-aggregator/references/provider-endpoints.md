# Verified Free AI Provider Endpoints (as of Jul 2026)

## OpenAI-Compatible (direct pass-through)
| Provider | Base URL | Key Env Var | Status |
|----------|----------|-------------|--------|
| Groq | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` | 30 RPM, 14,400 RPD |
| Cerebras | `https://api.cerebras.ai/v1` | `CEREBRAS_API_KEY` | 30 RPM, 14,400 RPD |
| Mistral | `https://api.mistral.ai/v1` | `MISTRAL_API_KEY` | 60 RPM, ∞ RPD |
| NVIDIA | `https://integrate.api.nvidia.com/v1` | `NVIDIA_API_KEY` | 40 RPM, ∞ RPD |
| SambaNova | `https://api.sambanova.ai/v1` | `SAMBANOVA_API_KEY` | 30 RPM, 1,000 RPD |
| Together | `https://api.together.xyz/v1` | `TOGETHER_API_KEY` | 30 RPM, 1,000 RPD |
| GitHub Models | `https://models.inference.ai.azure.com` | `GITHUB_MODELS_TOKEN` | 15 RPM, 150 RPD |
| OpenRouter | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | 20 RPM, 50 RPD |
| DeepSeek | `https://api.deepseek.com/v1` | `DEEPSEEK_API_KEY` | 30 RPM, 500 RPD (paid) |
| OpenCode Go | `https://opencode.ai/zen/go/v1` | `OPENCODE_API_KEY` | $10/mo subscription |

## Custom Format Providers
| Provider | Base URL | Format | Key Env Var |
|----------|----------|--------|-------------|
| Google Gemini | `https://generativelanguage.googleapis.com` | `gemini` | `GOOGLE_API_KEY` |
| Cohere | `https://api.cohere.ai` | `cohere` (path: `/v1/chat`) | `COHERE_API_KEY` |
| Cloudflare | `https://api.cloudflare.com/client/v4/accounts/{id}/ai/v1` | `cloudflare` | `CLOUDFLARE_API_TOKEN` |

## Kilo AI (free model gateway)
| Endpoint | Key |
|----------|-----|
| `https://api.kilo.ai/api/gateway/v1` | `KILOCODE_API_KEY` |

Free models: `kilo-auto/free`, `stepfun/step-3.7-flash:free`, `nvidia/nemotron-3-ultra-550b-a55b:free`
Note: Routes to reasoning models — needs `max_tokens >= 50` to produce output.

## OpenCode Go/ZEN
| Endpoint | Key |
|----------|-----|
| `https://opencode.ai/zen/go/v1` | `OPENCODE_API_KEY` |

Subscription service ($10/mo). Monthly limit enforced server-side. Same key serves both Go and ZEN.

## Config Tuning
| Setting | Value | Why |
|---------|-------|-----|
| Port | 3099 | Avoids Grafana (3000) |
| Timeout | 10000ms | 30s default causes slow failover |
| max_tokens | 50+ | Reasoning models return content=null with small values |

## Current Working Model Names
| Provider | Models |
|----------|--------|
| Groq | `llama-3.3-70b-versatile`, `llama-3.1-70b-versatile`, `llama-3.1-8b-instant` |
| Cerebras | `gemma-4-31b`, `gpt-oss-120b`, `zai-glm-4.7` |
| Gemini | `gemini-2.5-flash`, `gemini-2.0-flash`, `gemini-3.1-flash-lite-preview` |
| Mistral | `mistral-small-latest`, `open-mistral-nemo-2407`, `ministral-8b-latest` |
| NVIDIA | `meta/llama-3.1-70b-instruct`, `meta/llama-3.1-8b-instruct` |
| SambaNova | `Meta-Llama-3.3-70B-Instruct`, `DeepSeek-V3.1`, `gpt-oss-120b` |
| Cohere | `command-r-plus-08-2024`, `command-r-08-2024` |
| Cloudflare | `@cf/meta/llama-3.1-70b-instruct` |
| Together | `meta-llama/Llama-3.3-70B-Instruct-Turbo` |
| OpenRouter | `openrouter/auto`, `qwen/qwen3-coder:free` |
| OpenCode Go | `glm-5.2`, `kimi-k2.7-code`, `qwen3.7-max`, `deepseek-v4-pro` |
