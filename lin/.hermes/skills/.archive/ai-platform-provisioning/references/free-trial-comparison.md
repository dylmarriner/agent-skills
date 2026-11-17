# AI Model API — Free Trial Credit Comparison

| Platform | Free Credits | Card Required | Models Available | Signup Method | Notes |
|----------|-------------|---------------|-----------------|---------------|-------|
| **Google Cloud (Vertex AI)** | $300 | Yes | Claude, Gemini, Llama, Mistral, open models | Google Console | Billing account can be `open: false` (closed) while still linked to project. Needs user to add card in Console. |
| **Together AI** | $100 | Yes | Llama, Mistral, DeepSeek, Qwen, Gemma | Google OAuth | Fast inference. Google OAuth blocks automated browser. |
| **DeepInfra** | $100 | Yes | Claude, Gemini, Llama, Qwen, open models | Email/password or GitHub OAuth | Auto-creates account on first login. reCAPTCHA blocks headless browsers. Also serves Anthropic Claude models. |
| **Fireworks AI** | $100 | Yes | Llama, Mistral, DeepSeek, Qwen | Google OAuth | Fast inference-optimized platform. |
| **Groq** | Free tier (no card) | No | Llama, Mistral, Gemma, DeepSeek | Google OAuth | Truly free, no card required. LPU-powered, very fast. No Claude/GPT. Best for open-model inference without spending. |
| **Azure (Azure OpenAI)** | $200 | Yes | GPT-4, GPT-4o, o1, o3 | Microsoft/Entra | Azure OpenAI Service. Also serves Meta Llama via Azure AI Studio. |
| **AWS Bedrock** | Varies (some $300) | Yes | Claude, Llama, Mistral, Titan | AWS Console | Pay-as-you-go with free tier for some models. |
| **Nebius AI Studio** | $100 | Yes | Open models (Llama, Qwen, etc.) | Email/password | Formerly Nebius Cloud GPU. $100 credit on signup. |
| **OpenRouter** | Pay-as-you-go | Yes* | ALL major models (gateway) | Google or GitHub OAuth | Single API gateway for every provider. Some models have free tiers. Credit from referrals. |
| **Hugging Face Inference** | Limited free rate-limited | Optional | Thousands of open models | Email or OAuth | Free rate-limited tier for community models. Pro for higher limits. |
| **Replicate** | Free tier (rate-limited) | Optional | Open models, image gen | GitHub OAuth | Pay-as-you-go beyond free tier. Good for image/audio models too. |

## Quick Decision Guide

| You want... | Best Pick | Why |
|-------------|-----------|-----|
| No card, no commitment | **Groq** | Only major platform with genuinely free no-card tier |
| $100+ credits, open models | **Together AI / DeepInfra** | $100 each, good model selection |
| Claude models via API | **DeepInfra** or **GCP Vertex AI** | Both serve Anthropic Claude |
| One API key for everything | **OpenRouter** | Gateway to all providers, single billing |
| NVIDIA GPUs for training | **Nebius / Together** | Both offer GPU compute, not just inference |

## Free Credits Expiry

Most platforms expire free credits within 90 days of signup. Some (like Groq's free tier) have daily rate limits instead of a fixed expiry.
