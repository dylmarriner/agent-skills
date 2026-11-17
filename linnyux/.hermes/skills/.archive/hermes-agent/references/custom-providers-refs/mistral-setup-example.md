# Mistral AI Custom Provider — Session Walkthrough

Added 2026-06-04. API key was a free Experiment plan key (phone verified, no CC, 2 RPM / 1B tokens/month).

## Key used: `uTPi1143KPAFtdCt6p5pwCpR3q3q2z2X`

## Models available (59 total, free tier)

| Best picks | Context | Caps |
|---|---|---|
| `mistral-small-latest` (2603) | 262K | vision + reasoning + tools |
| `mistral-medium-3.5` (2604) | 262K | vision + reasoning + tools |
| `mistral-large-latest` (2512) | 262K | vision + tools |
| `codestral-latest` (2508) | 256K | tools (code specialist) |
| `mistral-ocr-latest` (2512) | 16K | vision-based OCR |

Full list at `https://api.mistral.ai/v1/models`.

## Config entry placed in config.yaml

```yaml
custom_providers:
- name: mistral
  api_key: uTPi1143KPAFtdCt6p5pwCpR3q3q2z2X
  base_url: https://api.mistral.ai/v1
  api_mode: chat_completions
  models:
  - codestral-2508
  - codestral-embed
  - codestral-embed-2505
  - codestral-latest
  - devstral-2512
  - devstral-latest
  - devstral-medium-latest
  - labs-leanstral-2603
  - magistral-medium-2509
  - magistral-medium-latest
  - magistral-small-2509
  - magistral-small-latest
  - ministral-14b-2512
  - ministral-14b-latest
  - ministral-3b-2512
  - ministral-3b-latest
  - ministral-8b-2512
  - ministral-8b-latest
  - mistral-code-agent-latest
  - mistral-code-fim-latest
  - mistral-code-latest
  - mistral-embed
  - mistral-embed-2312
  - mistral-large-2512
  - mistral-large-latest
  - mistral-medium
  - mistral-medium-2505
  - mistral-medium-2508
  - mistral-medium-2604
  - mistral-medium-3
  - mistral-medium-3-5
  - mistral-medium-3.5
  - mistral-medium-c21211-r0-75
  - mistral-medium-latest
  - mistral-moderation-2411
  - mistral-moderation-2603
  - mistral-moderation-latest
  - mistral-ocr-2512
  - mistral-ocr-latest
  - mistral-small-2506
  - mistral-small-2603
  - mistral-small-latest
  - mistral-tiny-2407
  - mistral-tiny-latest
  - mistral-vibe-cli-fast
  - mistral-vibe-cli-latest
  - mistral-vibe-cli-with-tools
  - open-mistral-nemo
  - open-mistral-nemo-2407
  - voxtral-mini-2507
  - voxtral-mini-2602
  - voxtral-mini-latest
  - voxtral-mini-realtime-2602
  - voxtral-mini-realtime-latest
  - voxtral-mini-transcribe-realtime-2602
  - voxtral-mini-tts-2603
  - voxtral-mini-tts-latest
  - voxtral-small-2507
  - voxtral-small-latest
```

## Provider alias

```bash
hermes config set model.provider custom:mistral
hermes config set model.default mistral-small-latest
```

Usage: `hermes --provider custom:mistral chat`
