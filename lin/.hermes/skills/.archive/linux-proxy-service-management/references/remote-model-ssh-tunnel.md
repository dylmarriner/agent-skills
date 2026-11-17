# Remote Model via SSH Tunnel

When a model endpoint is bound to localhost on a remote Tailscale machine and needs to be available to local consumers (Hermes, OpenClaw, etc.), use an SSH tunnel to forward the port through.

## Architecture

```
Local OpenClaw ──→ localhost:8002 ──SSH tunnel──→ kubuntux:8002 ──→ Ollama/RunPod endpoint
```

The remote machine binds to 127.0.0.1; the tunnel makes it appear as localhost on the requesting machine.

## Step-by-Step

### 1. Find the remote machine on Tailscale

```bash
tailscale status | grep -i <name>
# e.g. 100.93.75.87     kubuntux-to-be-filled-by-o-e-m
```

### 2. Determine SSH access

If Tailscale SSH is enabled, try root first — it often maps the Tailscale identity to root:

```bash
ssh root@<tailscale-ip> "hostname; whoami"
```

Otherwise try common usernames (your remote user, ubuntu, etc.) with your SSH key.

### 3. Check what's listening on the remote port

```bash
ssh root@<tailscale-ip> "ss -tlnp | grep <port>"
# Look for: LISTEN 127.0.0.1:<port>
```

Also verify it's a working OpenAI-compatible endpoint:

```bash
ssh root@<tailscale-ip> "curl -s http://localhost:<port>/v1/models"
```

### 4. Find credentials on the remote machine

If the endpoint is proxied through Hermes, the API keys live in the remote Hermes config:

```bash
grep -A10 'runpod:' /home/<user>/.hermes/config.yaml
```

Look for the `RUNPOD_API_KEY` (or equivalent `env` block) under `mcp_servers.<service>.env`. Also check the `custom_providers` section for the model's `base_url` and model list.

If the service is a plain LiteLLM/Ollama/OpenAI-compatible endpoint with no auth, you may not need a key — try `apiKey: "sk-any"` locally.

### 5. Create the SSH tunnel (background)

```bash
ssh -L <local_port>:localhost:<remote_port> root@<tailscale-ip> -N -f -o ExitOnForwardFailure=yes
```

- `<local_port>`: port on this machine (e.g. 8002)
- `<remote_port>`: port on the remote machine
- `-N`: no remote command (tunnel only)
- `-f`: background
- `-o ExitOnForwardFailure=yes`: fail fast if port can't be bound

### 6. Verify the tunnel

```bash
ss -tlnp | grep <local_port>
# Should show ssh process listening

curl -s http://localhost:<local_port>/v1/models
# Should return the same model list as the remote
```

Test a chat completion:

```bash
curl -s http://localhost:<local_port>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"<model-id>","messages":[{"role":"user","content":"hello"}],"max_tokens":50}'
```

### 7. Wire into OpenClaw

**Add MCP server** (if the remote model has an associated MCP server like RunPod):

Add to `mcp.servers` in `~/.openclaw/openclaw.json`:

```json
"runpod": {
  "command": "npx",
  "args": ["-y", "@runpod/mcp-server@latest"],
  "env": {
    "RUNPOD_API_KEY": "rpa_..."
  }
}
```

**Add model provider** — add to `models.providers` in openclaw.json:

```json
"runpod": {
  "baseUrl": "http://localhost:<local_port>/v1",
  "api": "openai-completions",
  "apiKey": "sk-any",
  "models": [
    {
      "id": "<model-id>",
      "name": "<display-name>",
      "contextWindow": 128000,
      "input": ["text"]
    }
  ]
}
```

**Register in agent defaults** — add to `agents.defaults.models`:

```json
"runpod/<model-id>": {
  "alias": "<display-alias>"
}
```

### 8. Persistence

The SSH tunnel lives as long as the ssh process. To make it survive a reboot, wrap it as a systemd service or an `@reboot` cron entry:

```bash
ssh -L 8002:localhost:8002 root@100.93.75.87 -N -o ExitOnForwardFailure=yes
```

Or use autossh for auto-reconnect on network drops.

## Pitfalls

- **Tunnel drops on network interruption:** Standard SSH has no reconnect logic. Use `autossh` or a monitoring cron job for production use.
- **Port conflicts:** If `<local_port>` is already in use, the `-o ExitOnForwardFailure=yes` flag causes immediate failure instead of silently binding wrong.
- **Remote port bound to different interface:** If the remote service binds to `0.0.0.0` instead of `127.0.0.1`, the tunnel is unnecessary — just use the Tailscale IP directly. Always check with `ss -tlnp` first.
- **MCP server + model provider are separate concerns:** The RunPod MCP server provides tool access (deploy endpoints, manage GPUs). The model provider provides chat completions. You may need both, or just one.
