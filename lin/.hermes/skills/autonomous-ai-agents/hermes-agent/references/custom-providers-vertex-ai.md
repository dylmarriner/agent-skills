# Hermes Custom Providers — Vertex AI via LiteLLM

Tested 2026-05-10 on lin (Ubuntu 24.04, Hermes with DeepSeek provider).

## Architecture

```
Hermes → custom_providers.vertex-ai → LiteLLM (port 4000) → Vertex AI (aiplatform.googleapis.com)
```

LiteLLM reads a GCP service account key and auto-refreshes OAuth tokens. Hermes sees it as an OpenAI-compatible endpoint.

## Hermes Config

Add to `~/.hermes/config.yaml` under `custom_providers`:

```yaml
custom_providers:
- name: vertex-ai
  base_url: http://localhost:4000/v1
  api_key: sk-litellm-local
  api_mode: chat_completions
  models:
  - gemini-3.1-pro-preview
  - gemini-3.1-flash-lite
  - gemini-2.5-pro
  - gemini-2.5-flash
```

Then use as: `hermes chat -m vertex-ai/gemini-3.1-pro-preview`

## LiteLLM Setup

### Install

```bash
# Must match the Python that runs litellm:
pip3 install --break-system-packages 'litellm[proxy]'
# If using homebrew/system Python mismatch, install for the correct one:
/usr/bin/python3 -m pip install --break-system-packages 'litellm[proxy]'
```

### Config (`~/litellm-config.yaml`)

```yaml
model_list:
  - model_name: gemini-3.1-pro-preview
    litellm_params:
      model: vertex_ai/gemini-3.1-pro-preview
      vertex_project: YOUR_PROJECT_ID
      vertex_location: global       # CRITICAL: use 'global', not a region
      vertex_credentials: /path/to/service-account-key.json
  - model_name: gemini-3.1-flash-lite
    litellm_params:
      model: vertex_ai/gemini-3.1-flash-lite
      vertex_project: YOUR_PROJECT_ID
      vertex_location: global
      vertex_credentials: /path/to/service-account-key.json

litellm_settings:
  drop_params: true

general_settings:
  master_key: sk-litellm-local
```

### Start

```bash
/path/to/litellm --config ~/litellm-config.yaml --port 4000 --num_workers 1
```

The binary's shebang determines which Python runs it. If deps are installed for a different Python, use `python3 -m litellm ...` with the correct python3.

### Verify

```bash
curl http://localhost:4000/v1/chat/completions \
  -H 'Authorization: Bearer sk-litellm-local' \
  -H 'Content-Type: application/json' \
  -d '{"model":"gemini-3.1-pro-preview","messages":[{"role":"user","content":"hi"}],"max_tokens":20}'
```

## Critical: region must be `global`

Vertex AI Gemini models use the **global** endpoint. Using `us-central1` returns 404 for most Gemini 3.x models.

Good: `vertex_location: global`
Bad: `vertex_location: us-central1`

## Hardware / Python Version Pitfalls

- **Homebrew vs system Python mismatch:** If `which litellm` shows a shebang for one Python but `google-cloud-aiplatform` is installed under another, the proxy fails with `Google Cloud SDK not found`. Fix: install `google-cloud-aiplatform` (or `litellm[google]`) for the Python that the litellm binary actually uses, then restart.
- **libicui18n.so.60:** Only relevant for Paperclip embedded postgres, not for LiteLLM. LiteLLM doesn't need ICU libraries.
- **Token refresh:** LiteLLM handles this automatically from the service account JSON key. No cron job needed.
