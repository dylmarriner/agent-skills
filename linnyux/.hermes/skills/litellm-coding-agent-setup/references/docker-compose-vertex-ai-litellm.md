# LiteLLM via Docker Compose + Vertex AI ADC

Documents the Docker Compose-based LiteLLM deployment in this environment, which proxies Google Vertex AI Gemini models using Application Default Credentials (ADC) rather than a service account key file.

## When to Use

- You encounter a `model_name` mismatch between client requests and LiteLLM's `model_list`
- Port 8899 is occupied and you need to find which port LiteLLM is actually on
- ADC credentials need refreshing or verifying
- You need to restart LiteLLM after config changes

## Deployment Details

| Aspect | Value |
|--------|-------|
| Project root | `/home/kubuntux/litellm/` |
| Docker Compose | `/home/kubuntux/litellm/docker-compose.yml` |
| Config file | `/home/kubuntux/litellm/config.yaml` (mounted at `/app/config.yaml` in container) |
| Port | **4000** (Docker mapped: `'4000:4000'`) |
| API base URL | `http://localhost:4000/v1` |
| API key | `sk-litellm-local` |
| Auth mechanism | ADC via mounted gcloud config dir (`/root/.config/gcloud` as read-only volume) |
| Workers | 8 (via `--num_workers 8`) |
| Image | `ghcr.io/berriai/litellm:main-latest` |

### docker-compose.yml

```yaml
services:
  litellm:
    image: ghcr.io/berriai/litellm:main-latest
    ports:
      - '4000:4000'
    volumes:
      - ./config.yaml:/app/config.yaml
      - /root/.config/gcloud:/root/.config/gcloud:ro
    environment:
      - LITELLM_MASTER_KEY=sk-litellm-local
      - GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json
    command: [ '--config', '/app/config.yaml', '--port', '4000', '--num_workers', '8' ]
```

## Restart After Config Changes

```bash
cd /home/kubuntux/litellm && docker compose restart
```

Wait 2-3 seconds, then verify:

```bash
curl -s http://localhost:4000/v1/models -H "Authorization: Bearer sk-litellm-local"
```

## OpenCode Config

OpenCode sends model names directly to LiteLLM's `/v1/chat/completions` endpoint. The `model_name` in LiteLLM config must match **exactly** what OpenCode sends.

**OpenCode config** at `~/.config/opencode/opencode.json`:

```json
{
  "model": "vertex/gemini-3.1-flash-lite",
  "provider": {
    "vertex": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Vertex AI",
      "options": {
        "baseURL": "http://localhost:4000/v1",
        "apiKey": "sk-litellm-local"
      },
      "models": {
        "gemini-3.1-pro-preview": { "name": "Gemini 3.1 Pro" },
        "gemini-3.1-flash-lite": { "name": "Gemini 3.1 Flash Lite" },
        "gemini-2.5-pro": { "name": "Gemini 2.5 Pro" },
        "gemini-2.5-flash": { "name": "Gemini 2.5 Flash" }
      }
    }
  }
}
```

**OpenCode env file** at `~/.opencode/.env`:

```
OPENAI_API_KEY=sk-litellm-local
OPENAI_BASE_URL=http://localhost:4000/v1
```

## Current Model List (this environment)

All models use `vertex_location: global` — this environment runs only 3.x Gemini models:

| model_name in LiteLLM | Underlying Vertex AI model | Endpoint |
|---|---|---|
| `gemini-3.1-pro-preview` | `vertex_ai/gemini-3.1-pro-preview` | global |
| `gemini-3.1-flash-lite-preview` | `vertex_ai/gemini-3.1-flash-lite-preview` | global |
| `gemini-3.1-flash-lite` | `vertex_ai/gemini-3.1-flash-lite` | global |
| `gemini-2.5-pro` | `vertex_ai/gemini-2.5-pro` | global |
| `gemini-2.5-flash` | `vertex_ai/gemini-2.5-flash` | global |

## Key Differences From Non-Docker Setup

| Aspect | Docker (this env) | Systemd (reference doc) |
|--------|-------------------|------------------------|
| Port | 4000 | 8899 |
| Auth | ADC (mounted gcloud dir) | Service account key JSON |
| Config path | `./config.yaml` relative to compose file | Full path in systemd ExecStart |
| Restart | `docker compose restart` | `systemctl restart litellm` |
| Model location | All models use `global` | 2.x use `us-central1`, 3.x use `global` |

## Common Pitfalls

- **ADC expiration:** The mounted gcloud credentials expire periodically. If LiteLLM starts returning auth errors, on the host run `gcloud auth application-default login` to refresh, then `docker compose restart`.
- **Port 4000 conflict:** Check `sudo lsof -i :4000` or `ss -tlnp | grep 4000` if LiteLLM won't start.
- **Wrong BASE_URL:** OpenCode's `.env` and `config.json` use `http://localhost:4000/v1` — using port 8899 (the old systemd port) or the wrong path (`/v1` suffix is critical) will fail.
- **Config not reloaded:** Docker Compose does NOT auto-reload config.yaml. After editing, you MUST run `docker compose restart` for changes to take effect.
