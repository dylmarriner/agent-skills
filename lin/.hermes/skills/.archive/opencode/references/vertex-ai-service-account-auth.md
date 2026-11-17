# Vertex AI Service Account Auth for Gemini Models

Captured from testing on 2026-05-10. Project `ai-system-495310`, service account `dkmarriner-534@ai-system-495310.iam.gserviceaccount.com`.

## ⚠️ Critical: Use `global` region, NOT `us-central1`

Vertex AI Gemini models are accessed via the **global** endpoint, not a regional one. Using `us-central1` returns **404** for newer models like gemini-3.1. Always use:

```
https://aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/global/publishers/google/models/{MODEL}:generateContent
```

(note: `aiplatform.googleapis.com` not `us-central1-aiplatform.googleapis.com`)

## Quick Test (Direct API)

```bash
# Generate token
pip3 install --break-system-packages google-auth pyjwt requests
python3 -c "
import google.auth.transport.requests, google.oauth2.service_account, json, requests

creds = google.oauth2.service_account.Credentials.from_service_account_file(
    '/path/to/service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
auth_req = google.auth.transport.requests.Request()
creds.refresh(auth_req)
token = creds.token

url = 'https://aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/global/publishers/google/models/gemini-3.1-pro-preview:generateContent'
payload = {'contents':[{'role':'user','parts':[{'text':'Say hello in 3 words'}]}],'generationConfig':{'maxOutputTokens':50}}
resp = requests.post(url, headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}, json=payload)
print(resp.json()['candidates'][0]['content']['parts'][0]['text'])
"
```

## Models Available via Vertex AI (using global region)

These all WORK via the `global` endpoint:
- `gemini-3.1-pro-preview`
- `gemini-3.1-flash-lite`
- `gemini-2.5-pro`
- `gemini-2.5-flash`

## Scopes

| Scope | Works for Vertex AI? | Works for Gemini API? |
|-------|----------------------|----------------------|
| `cloud-platform` | ✅ Yes | ❌ 403 insufficient scopes |
| `generative-language` | — | ✅ Yes (but credits may be depleted) |

## API Endpoints

**Vertex AI (works with cloud-platform scope):**
```
POST https://{REGION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{REGION}/publishers/google/models/{MODEL}:generateContent
```

**Standard Gemini API (needs generative-language scope):**
```
POST https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent
```

## OpenCode Compatibility

OpenCode's Google provider is **hardcoded to the standard Gemini API endpoint**. It cannot use Vertex AI directly. There is no way to configure a custom base URL for the Google provider in OpenCode.

The stored credentials in `~/.local/share/opencode/auth.json` are bare token strings — OpenCode has no OAuth refresh mechanism. OAuth access tokens expire in ~1 hour.

### WORKAROUND: LiteLLM Proxy (Verified Working)

LiteLLM bridges the gap — it reads the service account JSON key, handles token refresh automatically, and presents an OpenAI-compatible endpoint that OpenCode can use via its custom provider config.

**Step 1: Install LiteLLM**

Check which Python the `litellm` binary uses first:

```bash
which litellm
head -1 $(which litellm)    # reads shebang — this is the Python that matters
/usr/bin/python3 -c "import google.oauth2.service_account; print('ok')"
```

**Critical:** If the shebang points to a different Python than the one you install packages for, the `google-cloud-aiplatform` import will fail even though `pip list` shows it installed. Install `litellm[google]` using the same Python that the shebang uses:

```bash
# If shebang is /usr/bin/python3 (system Python):
/usr/bin/python3 -m pip install --break-system-packages 'litellm[proxy]'

# If shebang is a homebrew/cellar Python:
# Use THAT Python's pip explicitly
/usr/bin/python3 -m pip install --break-system-packages 'litellm[google]'  # installs for system Python 3.12
# NOT: pip3 install (may route to homebrew Python 3.14)
```

To verify after install:
```bash
head -1 $(which litellm) | cut -d! -f2 | xargs -I{} sh -c '{} -c "import google.oauth2.service_account; print(\"ok\")"'
```

On systems with both homebrew and system Python (e.g., homebrew Python 3.14 + system Python 3.12), the `pip3` command may target the wrong one. Always use the shebang path's pip explicitly.

**Step 2: Create LiteLLM config** (`~/litellm-config.yaml`)

```yaml
model_list:
  - model_name: gemini-3.1-pro-preview
    litellm_params:
      model: vertex_ai/gemini-3.1-pro-preview
      vertex_project: PROJECT_ID
      vertex_location: global
      vertex_credentials: /path/to/service-account-key.json
  - model_name: gemini-3.1-flash-lite
    litellm_params:
      model: vertex_ai/gemini-3.1-flash-lite
      vertex_project: PROJECT_ID
      vertex_location: global
      vertex_credentials: /path/to/service-account-key.json

litellm_settings:
  drop_params: true

general_settings:
  master_key: sk-litellm-local
```

**Step 3: Start proxy**

```bash
litellm --config ~/litellm-config.yaml --port 4000 --num_workers 1
```

Or as a systemd user service for auto-start:

```bash
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/litellm-vertex.service << 'EOF'
[Unit]
Description=LiteLLM Proxy for Vertex AI
After=network.target

[Service]
Type=simple
ExecStart=/home/USER/.local/bin/litellm --config /home/USER/litellm-config.yaml --port 4000 --num_workers 1
Restart=always
RestartSec=5
Environment=PATH=/home/USER/.local/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable litellm-vertex.service
systemctl --user start litellm-vertex.service
```

**Step 4: Configure OpenCode** (`~/.config/opencode/opencode.json`)

```json
{
  "provider": {
    "vertex": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Vertex AI",
      "options": {
        "baseURL": "http://localhost:4000/v1",
        "apiKey": "sk-litellm-local"
      },
      "models": {
        "gemini-3.1-pro-preview": {"name": "Gemini 3.1 Pro Preview"},
        "gemini-3.1-flash-lite": {"name": "Gemini 3.1 Flash-Lite"},
        "gemini-2.5-pro": {"name": "Gemini 2.5 Pro"},
        "gemini-2.5-flash": {"name": "Gemini 2.5 Flash"}
      }
    }
  },
  "model": "vertex/gemini-3.1-pro-preview"
}
```

**Step 5: Use in OpenCode**

```bash
opencode run 'your prompt' --model vertex/gemini-3.1-pro-preview
opencode run 'your prompt' --model vertex/gemini-3.1-flash-lite
```

The models list as `vertex/gemini-3.1-pro-preview` etc. in `opencode models`.

### Key Points About the Workaround

- **Token refresh is automatic.** LiteLLM reads the service account JSON and refreshes OAuth tokens before they expire. No cron job needed.
- **OpenCode's provider config** uses `"npm": "@ai-sdk/openai-compatible"` — this is the same npm package the `openrouter` provider uses internally.
- **The `vertex/` prefix** in the model name comes from the provider key name in `opencode.json`. If you name the provider key `google-vai` instead, the model would be `google-vai/gemini-3.1-pro-preview`.
- **All OpenAI-compatible tools** can use the LiteLLM proxy, not just OpenCode. Set `OPENAI_BASE_URL=http://localhost:4000/v1` and `OPENAI_API_KEY=sk-litellm-local`.
- **LiteLLM proxy forwards all model list requests** — `GET /v1/models` returns the models configured in the YAML.

## Full Test Script

```python
import google.auth.transport.requests
import google.oauth2.service_account
import json, requests

creds = google.oauth2.service_account.Credentials.from_service_account_file(
    "/home/kubuntux/gcp-service-account-key.json",
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)
auth_req = google.auth.transport.requests.Request()
creds.refresh(auth_req)
token = creds.token

models = ["gemini-3.1-pro-preview", "gemini-3.1-flash-lite", "gemini-2.5-pro", "gemini-2.5-flash"]
for model in models:
    url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/ai-system-495310/locations/us-central1/publishers/google/models/{model}:generateContent"
    payload = {"contents":[{"role":"user","parts":[{"text":"Say hello in 3 words"}]}],"generationConfig":{"maxOutputTokens":50}}
    resp = requests.post(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=payload, timeout=15)
    if "candidates" in resp.json():
        print(f"[OK] {model}")
    else:
        print(f"[FAIL] {model}: {resp.json().get('error',{}).get('message','')[:100]}")
```
