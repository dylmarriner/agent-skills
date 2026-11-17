---
name: litellm-vertex-ai
description: Configure LiteLLM proxy for Vertex AI Gemini models — auth, model routing, global vs regional endpoints, and OpenCode integration.
---

# LiteLLM ↔ Vertex AI Proxy

Set up LiteLLM to proxy Vertex AI Gemini models. Covers authentication via service account, model routing with correct endpoint locations, and connecting downstream tools (OpenCode, OpenClaw) to the proxy.

## When to use

- User asks to "set up LiteLLM with Vertex AI"
- User wants to create an OpenAI-compatible proxy for Vertex AI models
- User is getting 404 errors on Vertex AI models and needs endpoint debugging
- User needs to connect OpenCode or other tools to Vertex AI through LiteLLM

## Prerequisites

- Google Cloud project with Vertex AI enabled
- Service account key JSON (GOOGLE_APPLICATION_CREDENTIALS)
- LiteLLM installed (`pip install litellm` or system package)
- `gcloud` CLI authenticated with the service account

## Authentication

LiteLLM authenticates to Vertex AI via `GOOGLE_APPLICATION_CREDENTIALS` environment variable:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

The service account needs the `Vertex AI User` IAM role on the project. Activate the service account for CLI verification:

```bash
gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"
```

## Systemd Service (recommended for production)

Create `/etc/systemd/system/litellm.service`:

```ini
[Unit]
Description=LiteLLM Proxy
After=network.target

[Service]
Type=simple
User=root
Environment="GOOGLE_APPLICATION_CREDENTIALS=/home/user/.config/gcloud/.../adc.json"
ExecStart=/usr/bin/python3 /home/user/.local/bin/litellm --config /home/user/.litellm/config.yaml --port 8899 --num_workers 1
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable litellm
systemctl start litellm
```

## Config Structure (`~/.litellm/config.yaml`)

### Endpoint location: CRITICAL distinction

Models follow this location rule — ignore it and you get 404s:

| Model generation | Vertex AI location |
|---|---|
| **Gemini 2.x** (2.5-flash, 2.5-pro, 2.5-flash-lite) | `us-central1` (regional) |
| **Gemini 3.x** (3.1-flash-lite, 3.1-pro-preview, 3-flash-preview) | `global` (global endpoint) |

Using a regional location like `us-central1` for 3.x models returns:
> `Publisher Model `...` was not found or your project does not have access to it.`

The global endpoint URL is `https://aiplatform.googleapis.com/v1/projects/{project}/locations/global/publishers/google/models/...` — LiteLLM handles URL construction when `vertex_location: global` is set.

### Full example config

```yaml
model_list:
  - model_name: gemini-3.1-pro-preview
    litellm_params:
      model: vertex_ai/gemini-2.5-pro
      vertex_project: my-project
      vertex_location: us-central1
  - model_name: gemini-3.1-flash-lite
    litellm_params:
      model: vertex_ai/gemini-3.1-flash-lite
      vertex_project: my-project
      vertex_location: global         # <-- 3.x model: GLOBAL
  - model_name: gemini-3.1-flash-lite-preview
    litellm_params:
      model: vertex_ai/gemini-3.1-flash-lite-preview
      vertex_project: my-project
      vertex_location: global         # <-- 3.x model: GLOBAL
  - model_name: gemini-2.5-flash-lite
    litellm_params:
      model: vertex_ai/gemini-2.5-flash-lite
      vertex_project: my-project
      vertex_location: us-central1    # <-- 2.x model: regional
  - model_name: gemini-2.5-pro
    litellm_params:
      model: vertex_ai/gemini-2.5-pro
      vertex_project: my-project
      vertex_location: us-central1
  - model_name: gemini-2.5-flash
    litellm_params:
      model: vertex_ai/gemini-2.5-flash
      vertex_project: my-project
      vertex_location: us-central1
  - model_name: gemini-3.1-flash-image-preview
    litellm_params:
      model: vertex_ai/gemini-2.5-flash-image
      vertex_project: my-project
      vertex_location: us-central1

general_settings:
  master_key: sk-litellm-local   # set an API key for downstream tools
  database_url: null
```

### Model naming in LiteLLM

Use the `vertex_ai/` prefix to route through Vertex AI:
- `vertex_ai/gemini-2.5-flash` (regional)
- `vertex_ai/gemini-3.1-flash-lite` (global)
- `vertex_ai/gemini-3.1-flash-lite-preview` (global)

The `model_name` in LiteLLM config is the alias downstream tools use. The `model` value under `litellm_params` with the `vertex_ai/` prefix is the actual Vertex AI endpoint.

## Connecting OpenCode

Add a custom provider in `~/.config/opencode/opencode.json`:

```json
{
  "model": "vertex/gemini-3.1-flash-lite",
  "provider": {
    "vertex": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Vertex AI",
      "options": {
        "baseURL": "http://localhost:8899/v1",
        "apiKey": "sk-litellm-local"
      },
      "models": {
        "gemini-3.1-pro-preview": { "name": "Gemini 3.1 Pro" },
        "gemini-3.1-flash-lite": { "name": "Gemini 3.1 Flash Lite" },
        "gemini-3.1-flash-lite-preview": { "name": "Gemini 3.1 Flash Lite" },
        "gemini-2.5-flash-lite": { "name": "Gemini 2.5 Flash Lite" },
        "gemini-2.5-pro": { "name": "Gemini 2.5 Pro" },
        "gemini-2.5-flash": { "name": "Gemini 2.5 Flash" },
        "gemini-3.1-flash-image-preview": { "name": "Gemini Flash Image" }
      }
    }
  }
}
```

The `model` field sets the default. Downstream tools reference models as `vertex/<model_name>`.

## Verification

```bash
# Check proxy is running
curl -s -H "Authorization: Bearer sk-litellm-local" http://localhost:8899/v1/models

# Test a 2.x model (regional)
curl -s -H "Authorization: Bearer sk-litellm-local" \
  -H "Content-Type: application/json" \
  -d '{"model":"gemini-2.5-flash","messages":[{"role":"user","content":"say ok"}]}' \
  http://localhost:8899/v1/chat/completions

# Test a 3.x model (global)
curl -s -H "Authorization: Bearer sk-litellm-local" \
  -H "Content-Type: application/json" \
  -d '{"model":"gemini-3.1-flash-lite","messages":[{"role":"user","content":"say ok"}]}' \
  http://localhost:8899/v1/chat/completions

# Check OpenCode connectivity
opencode models | grep vertex/
```

## Pitfalls

- **Don't silently map model aliases to different generations.** If the user names a model `gemini-3.1-flash-lite`, it should map to `vertex_ai/gemini-3.1-flash-lite` — not to `gemini-2.5-flash-lite`. Ask the user if unsure.
- **Global vs regional:** 3.x models ONLY work on the `global` location. 2.x models ONLY work on regional locations (`us-central1`, `europe-west4`, etc.). Mixing them up produces silent 404s.
- **Service account permissions:** Must have `Vertex AI User` role. Verify by calling the Vertex AI API directly.
- **Port conflicts:** LiteLLM's systemd Restart=always can fight with a stale process holding the port. Use `fuser -k {port}/tcp` before restarting.
- **Model name versioning:** Google changes model naming frequently. Always verify against available model versions. Use the `gcloud` or direct API to check: direct call to `https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/google/models/{model}:generateContent`.
