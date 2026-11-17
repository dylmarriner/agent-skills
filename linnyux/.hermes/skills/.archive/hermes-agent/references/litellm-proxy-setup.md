# LiteLLM Proxy Setup for Hermes

This guide details how to configure Hermes to work with a local LiteLLM proxy serving Vertex AI models.

## Prerequisites
- LiteLLM installed in a virtualenv (default: `~/.local/share/litellm-venv`)
- A `litellm-config.yaml` file with your Vertex AI model definitions
- A valid Google Cloud service account key for Vertex AI access

## Step-by-Step Setup

### 1. Stop Existing LiteLLM Service
```bash
systemctl --user stop litellm
pkill -f litellm   # Ensure no stray processes remain
```

### 2. Ensure Prisma Schema Uses SQLite
Both schema files must show `provider = "sqlite"`:
```bash
grep -n 'provider =' \
  $HOME/.local/share/litellm-venv/lib/python3.12/site-packages/litellm/proxy/schema.prisma \
  $HOME/.local/share/litellm-venv/lib/python3.12/site-packages/litellm_proxy_extras/schema.prisma
```
If they show `postgresql`, replace with `sqlite`:
```bash
sed -i 's/provider = "postgresql"/provider = "sqlite"/g' \
  $HOME/.local/share/litellm-venv/lib/python3.12/site-packages/litellm/proxy/schema.prisma \
  $HOME/.local/share/litellm-venv/lib/python3.12/site-packages/litellm_proxy_extras/schema.prisma
```

### 3. Create Systemd Service with SQLite and Schema Update Disabled
```bash
mkdir -p $HOME/.config/systemd/user
cat > $HOME/.config/systemd/user/litellm.service <<'EOF'
[Unit]
Description=LiteLLM Proxy for Vertex AI
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=$HOME/.local/share/litellm-venv/bin/litellm \
  --config $HOME/litellm-config.yaml \
  --port 4000 \
  --num_workers 1
Environment=PATH=$HOME/.local/share/litellm-venv/bin:/usr/bin:/bin
Environment=DATABASE_URL=sqlite:////home/kubuntux/litellm.db
Environment=LITELLM_DISABLE_SCHEMA_UPDATE=true
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user start litellm
systemctl --user status litellm   # Should show active (running)
```

### 4. Verify Proxy Responds
```bash
curl -s http://localhost:4000/v1/models | jq .
```
You should see a JSON list of models from your `litellm-config.yaml`.

### 5. Configure Hermes to Use LiteLLM Proxy
```bash
hermes config set model.provider openai
hermes config set model.base_url http://localhost:4000/v1
hermes config set model.api_key sk-123456   # Any non-empty string works for LiteLLM
hermes config set model.default gemini-3.1-pro-preview   # Or your preferred model
```

### 6. Test a Query
```bash
hermes chat -q "Say hello in one word."
```

## Troubleshooting

- **Proxy not starting**: Check logs with `journalctl --user -u litellm.service -n 20 --no-pager`
- **401/403 errors**: Ensure `model.api_key` is set and `base_url` ends with `/v1`
- **Model not found**: Verify model name matches exactly what's in `litellm-config.yaml`
- **Port conflict**: Change `--port` in the service file and update `model.base_url` accordingly

## Notes
- The `LITELLM_DISABLE_SCHEMA_UPDATE=true` environment variable prevents LiteLLM from attempting Prisma migrations on startup, which can fail if the database schema is not properly initialized.
- Using SQLite (`sqlite:////home/kubuntux/litellm.db`) provides a lightweight, file-based database suitable for single-user proxy instances.
- For multi-user or production setups, consider using PostgreSQL with proper credentials and migration procedures.