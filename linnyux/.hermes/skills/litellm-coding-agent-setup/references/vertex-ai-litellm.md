# LiteLLM + Vertex AI Setup

Configure LiteLLM to proxy requests to Google Vertex AI (Gemini models). Uses a GCP service account for authentication.

## When to Use

- Configuring LiteLLM to serve Gemini models via Vertex AI
- opencode CLI or other agents need to call Gemini through a local proxy
- Application Default Credentials (ADC) are expired and you need a fallback
- Gemini 3.x models return 404 from Vertex AI — likely needs the global endpoint

## Prerequisites

- GCP project with Vertex AI API enabled
- Service account with `roles/aiplatform.user` (or equivalent)
- Service account key JSON file (`.json`)

## LiteLLM Config

### Model Mappings (Gemini 2.x — regional endpoint)

Place these in `~/.litellm/config.yaml`. Gemini 2.x models use the **regional** endpoint (e.g., `us-central1`). The `model_name` is what clients (opencode, curl) use. The `litellm_params.model` is the actual Vertex AI model ID:

```yaml
model_list:
  - model_name: gemini-2.5-pro
    litellm_params:
      model: vertex_ai/gemini-2.5-pro
      vertex_project: your-project-id
      vertex_location: us-central1       # regional — for Gemini 2.x
  - model_name: gemini-2.5-flash
    litellm_params:
      model: vertex_ai/gemini-2.5-flash
      vertex_project: your-project-id
      vertex_location: us-central1
  - model_name: gemini-2.5-flash-lite
    litellm_params:
      model: vertex_ai/gemini-2.5-flash-lite
      vertex_project: your-project-id
      vertex_location: us-central1
```

### Model Mappings (Gemini 3.x — global endpoint only)

Gemini 3.x models (3.1 Flash Lite, 3.1 Pro Preview, 3 Flash, 3 Pro) are **only available on the global endpoint**. They **must** use `vertex_location: global` — us-central1 or any other regional location will return 404.

```yaml
model_list:
  - model_name: gemini-3.1-flash-lite
    litellm_params:
      model: vertex_ai/gemini-3.1-flash-lite
      vertex_project: your-project-id
      vertex_location: global           # required — Gemini 3.x only on global
  - model_name: gemini-3.1-flash-lite-preview
    litellm_params:
      model: vertex_ai/gemini-3.1-flash-lite-preview
      vertex_project: your-project-id
      vertex_location: global
```
**Do not mix:** Gemini 2.x models fail on `global`, Gemini 3.x models fail on regional endpoints.

The `vertex_project` field must match the GCP project ID that has Vertex AI enabled and the service account in.

### Auth: Two Options

**Option A — ADC (default, expires):**
```bash
gcloud auth application-default login
```
Credentials expire and need periodic refresh.

**Option B — Service Account Key (preferred for persistent setups):**
```yaml
# In config.yaml (per model):
litellm_params:
  model: vertex_ai/gemini-2.5-pro
  vertex_project: your-project-id
  vertex_location: us-central1
  vertex_credentials: /path/to/service-account-key.json
```

OR via environment variable (works per-process):
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
litellm --config ~/.litellm/config.yaml --port 8899 --num_workers 1
```

## Systemd Service (persistent across reboot)

```ini
[Unit]
Description=LiteLLM Proxy for Vertex AI
After=network.target

[Service]
Type=simple
User=kubuntux
Environment="GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json"
ExecStart=/home/kubuntux/.local/bin/litellm --config /home/kubuntux/.litellm/config.yaml --port 8899 --num_workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Install:
```bash
sudo systemctl daemon-reload
sudo systemctl enable litellm.service
sudo systemctl start litellm.service
```

## Verification

### 1. Check models are served
```bash
curl -s http://localhost:8899/v1/models \
  -H "Authorization: Bearer sk-litellm-local"
```

### 2. Test a completion
```bash
curl -s http://localhost:8899/v1/chat/completions \
  -H "Authorization: Bearer sk-litellm-local" \
  -H "Content-Type: application/json" \
  -d '{"model":"gemini-2.5-flash","messages":[{"role":"user","content":"Say hello"}]}'
```

### 3. Check systemd status
```bash
systemctl status litellm.service --no-pager
```

## opencode Config

The opencode config at `~/.config/opencode/opencode.json` needs to point at the LiteLLM proxy:

```json
{
  "provider": {
    "vertex": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Vertex AI",
      "options": {
        "baseURL": "http://localhost:8899/v1",
        "apiKey": "sk-litellm-local"
      },
      "models": {
        "gemini-2.5-pro": { "name": "Gemini 2.5 Pro" },
        "gemini-2.5-flash": { "name": "Gemini 2.5 Flash" }
      }
    }
  }
}
```

The `baseURL` must point to the LiteLLM port (8899 in this example), not to the actual Vertex AI endpoint. opencode talks to LiteLLM as a drop-in OpenAI-compatible API.

## Available Vertex AI Gemini Models (as of May 2026)

### Gemini 2.x — Regional (e.g., us-central1)

| Alias | Vertex AI model ID | Location | Notes |
|-------|-------------------|----------|-------|
| Gemini 2.5 Pro | `gemini-2.5-pro` | `us-central1` | Best reasoning, coding |
| Gemini 2.5 Flash | `gemini-2.5-flash` | `us-central1` | Balanced speed/quality |
| Gemini 2.5 Flash Lite | `gemini-2.5-flash-lite` | `us-central1` | Fastest, cheapest |
| Gemini 2.5 Flash Image | `gemini-2.5-flash-image` | `us-central1` | Vision/multimodal |

### Gemini 3.x — Global Endpoint Only

| Alias | Vertex AI model ID | Location | Notes |
|-------|-------------------|----------|-------|
| Gemini 3.1 Flash Lite | `gemini-3.1-flash-lite` | `global` | Most cost-efficient 3.x |
| Gemini 3.1 Flash Lite Preview | `gemini-3.1-flash-lite-preview` | `global` | Preview version |
| Gemini 3.1 Pro Preview | `gemini-3.1-pro-preview` | `global` | Preview — best reasoning |
| Gemini 3.1 Flash Image Preview | `gemini-3.1-flash-image-preview` | `global` | Preview — image gen |
| Gemini 3 Flash Preview | `gemini-3-flash-preview` | `global` | |
| Gemini 3 Pro Preview | `gemini-3-pro-preview` | `global` | |

3.x models do NOT exist on regional endpoints — `us-central1` returns 404. Use `vertex_location: global`.

For the latest full model list, check: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions

## Common Pitfalls

- **ADC expired:** `gcloud auth application-default print-access-token` returns `invalid_grant`. Fix by using service account key directly via `GOOGLE_APPLICATION_CREDENTIALS`.
- **Gemini 3.x on wrong endpoint:** A 3.x model like `gemini-3.1-flash-lite-preview` returns 404 from Vertex AI because it's configured with a regional location (e.g., `us-central1`). Fix: use `vertex_location: global` — see the Gemini 3.x section above. (Do NOT assume the model doesn't exist; it just needs the global endpoint.)
- **Port conflict:** If something else is on port 8899, LiteLLM fails to bind. Check with `ss -tlnp | grep 8899`.
- **Wrong endpoint:** The opencode `baseURL` should be `http://localhost:8899/v1` (LiteLLM proxy), NOT the actual Vertex AI endpoint URL.
- **Missing Vertex API enablement:** If you get 403/PERMISSION_DENIED, ensure `gcloud services enable aiplatform.googleapis.com` was run on the project.
