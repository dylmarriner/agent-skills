# LiteLLM Systemd User Service Setup for Vertex AI (Gemini)

This guide details the exact steps to configure LiteLLM as a systemd user service for automatic startup and reliable operation with Gemini models via Vertex AI.

## 1. Prepare Vertex AI Credentials
Ensure your GCP service account key is available at:
`~/.config/gcloud/service-account-key.json`
Test with: `gcloud auth application-default print-access-token`

## 2. Create LiteLLM Configuration File
Create `~/litellm-config.yaml` with the following content:

```yaml
model_list:
  - model_name: gemini-3.1-pro-preview
    litellm_params:
      model: vertex_ai/gemini-3.1-pro-preview
      vertex_project: ai-system-495310
      vertex_location: global
      vertex_credentials: /home/lin/.config/gcloud/service-account-key.json
      max_tokens: 1048576
  - model_name: gemini-3.1-flash-lite
    litellm_params:
      model: vertex_ai/gemini-3.1-flash-lite
      vertex_project: ai-system-495310
      vertex_location: global
      vertex_credentials: /home/lin/.config/gcloud/service-account-key.json
      max_tokens: 1048576
  - model_name: gemini-2.5-pro
    litellm_params:
      model: vertex_ai/gemini-2.5-pro
      vertex_project: ai-system-495310
      vertex_location: global
      vertex_credentials: /home/lin/.config/gcloud/service-account-key.json
      max_tokens: 1048576
  - model_name: gemini-2.5-flash
    litellm_params:
      model: vertex_ai/gemini-2.5-flash
      vertex_project: ai-system-495310
      vertex_location: global
      vertex_credentials: /home/lin/.config/gcloud/service-account-key.json
      max_tokens: 1048576

litellm_settings:
  drop_params: true
  set_verbose: false
  max_tokens: 1048576

general_settings:
  master_key: sk-123...cdef  # Replace with your actual key or set to None for no auth
```

> **Note**: Replace `ai-system-495310` with your actual Vertex AI project ID. The `master_key` is used for proxy authentication; clients must send `Authorization: Bearer <master_key>`.

## 3. Install Systemd User Service
Create `~/.config/systemd/user/litellm-vertex.service`:

```ini
[Unit]
Description=LiteLLM Vertex AI Proxy
After=network.target

[Service]
Type=simple
Environment=GOOGLE_APPLICATION_CREDENTIALS=/home/lin/.config/gcloud/service-account-key.json
Environment=PYTHONIOENCODING=utf-8
ExecStart=/home/lin/.local/bin/litellm --config /home/lin/litellm-config.yaml --port 4000 --num_workers 1
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

> **Important**: Use absolute paths obtained via:
> - `which litellm` (usually `/home/lin/.local/bin/litellm`)
> - Absolute path to your config file (`/home/lin/litellm-config.yaml`)

## 4. Enable and Start the Service
```bash
# Reload systemd manager configuration
systemctl --user daemon-reload

# Enable the service to start on user login
systemctl --user enable litellm-vertex.service

# Start the service immediately
systemctl --user start litellm-vertex.service
```

## 5. Verify Operation
Check service status:
```bash
systemctl --user status litellm-vertex.service
```
Look for `Active: active (running)` and the main PID.

View logs for startup confirmation:
```bash
journalctl --user -u litellm-vertex.service -n 30 --no-pager
```
You should see "Application startup complete" and "Uvicorn running on http://0.0.0.0:4000".

Test the model list endpoint (requires auth if master_key set):
```bash
curl -s -H "Authorization: Bearer sk-123...cdef" http://localhost:4000/v1/models
```
Expected output: JSON array containing `gemini-3.1-pro-preview`, `gemini-3.1-flash-lite`, `gemini-2.5-pro`, `gemini-2.5-flash`.

Test a chat completion:
```bash
curl -s -H "Authorization: Bearer sk-123...cdef" \
     -H "Content-Type: application/json" \
     -d '{"model":"gemini-2.5-flash","messages":[{"role":"user","content":"Hello in Persian"}],"max_tokens":20}' \
     http://localhost:4000/v1/chat/completions
```
Should return a valid completion.

## 6. Troubleshooting Tips

### Service Fails to Start
- Check logs: `journalctl --user -u litellm-vertex.service -n 100`
- Common issues:
  - Invalid YAML in config file (use a yamllint tool)
  - Wrong path to litellm binary or config file
  - Missing or invalid Vertex AI credentials
  - Port 4000 already in use (`ss -tulpn | grep :4000`)

### Authentication Errors (401)
- Ensure you're sending the correct `Authorization: Bearer <master-key>` header
- Verify `master_key` in `litellm-config.yaml` matches the token you're sending
- To disable auth, set `master_key: None` in config and omit the header

### "No connected db" Error (400)
- This occurs if `general_settings.master_key` is not set but the proxy expects key management
- Fix: Set `master_key` to any non-empty string (even a dummy value) in the config

### Connection Refused (curl error 7)
- Confirm service is `active (running)`
- Check what port it's bound to: `ss -tulpn | grep litellm`
- Ensure `ExecStart` includes `--port 4000` (or your desired port)
- LiteLLM binds to `0.0.0.0` by default; accessible via localhost and Tailscale

## 7. Maintenance
- After changing `litellm-config.yaml`: `systemctl --user restart litellm-vertex.service`
- To check version: `curl -s http://localhost:4000/version` (if enabled) or check logs on startup
- Monitor resource usage: `systemctl --user status litellm-vertex.service`

## 8. Hermes Integration
Hermes can be configured to use this LiteLLM endpoint by setting in `~/.hermes/config.yaml`:
```yaml
model:
  provider: openrouter
  base_url: http://localhost:4000/v1
  api_key: sk-123...cdef  # Must match master_key in litellm-config.yaml
  default: gemini-2.5-flash
```
Note: Despite the `openrouter` provider name, Hermes will communicate with the local LiteLLM proxy at the given base_url.