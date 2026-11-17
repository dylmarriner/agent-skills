# Hermes API Server Remote / Mobile Access

## Overview

Enable the built-in API server adapter, expose it via Tailscale Serve, and connect from
any OpenAI-compatible client (Open WebUI, LobeChat, custom Android/iOS app, PWA, curl).

## Prerequisites

- Hermes Agent installed and configured
- Tailscale installed and logged in on the Hermes host
- The phone/client must also be on the same Tailscale tailnet (install Tailscale + log in)

## Step-by-Step

### 1. Enable the API Server Channel

```bash
hermes config set channels.api_server.enabled true
```

Optional config overrides (edit `~/.hermes/config.yaml`):

```yaml
channels:
  api_server:
    enabled: true
    host: 127.0.0.1      # keep loopback — Tailscale handles external access
    port: 8642            # default, change if port conflict
```

### 2. Start the Gateway

```bash
hermes gateway run
```

Verify the API server is up:

```bash
curl -s http://127.0.0.1:8642/health
# → {"status":"ok","service":"hermes-agent"}
```

### 3. Expose via Tailscale Serve

```bash
sudo tailscale serve --bg --https=443 8642
```

Check it worked:

```bash
tailscale serve status
# → https://<hostname>.tail<XXXX>.ts.net/  →  http://127.0.0.1:8642
```

### 4. Test Remote Connectivity

From the phone or any Tailscale-connected device:

```bash
curl https://<hostname>.tail<XXXX>.ts.net/v1/models
# → {"object":"list","data":[{"id":"hermes-agent","object":"model",...}]}
```

### 5. Send a Chat Request

```bash
curl -X POST https://<hostname>.tail<XXXX>.ts.net/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hermes-agent",
    "messages": [{"role": "user", "content": "Hi, who are you?"}]
  }'
```

### 6. Connect from Open WebUI or Similar

In any OpenAI-compatible frontend:

| Setting | Value |
|---------|-------|
| OpenAI API URL | `https://<hostname>.tail<XXXX>.ts.net/v1` |
| Model | `hermes-agent` |
| API Key | (leave blank unless gateway auth requires it) |

## Mobile WebView App (Minimal)

1. Create a simple Android app with a single WebView
2. Point it at the Open WebUI instance or at `https://<hostname>.tail<XXXX>.ts.net/`
3. Use Tailscale's VPN to route

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `curl: connection refused` on localhost | API server not enabled or gateway not started | `hermes config set channels.api_server.enabled true && hermes gateway run` |
| `curl: connection refused` via Tailscale URL | Tailscale serve not set up | `sudo tailscale serve --bg --https=443 8642 && tailscale serve status` |
| `401 Unauthorized` | Gateway auth requires token | Check `hermes config get gateway.auth`; pass token in `Authorization: Bearer <token>` header |
| `404 Not Found` on `/v1/...` | Wrong port or URL path | Verify port: `ss -tnlp \| grep 8642`; Tailscale serves at root `/` → proxies to `/` on 8642 |
| Stream not working in WebView | CORS or SSE handling | Ensure WebView has JavaScript enabled; test with `curl -N` for SSE first |
| `model not found: hermes-agent` | Wrong model name in client | Use exactly `hermes-agent` as the model string |
| Tailscale Serve config lost after reboot | `resetOnExit: true` in Hermes config | Run `sudo tailscale serve --bg --https=443 8642` after restart, or remove `resetOnExit` |

## Persistent Setup (Survives Reboot)

```bash
# Enable Tailscale Serve permanently (no resetOnExit)
sudo tailscale serve --bg --https=443 8642

# Enable Hermes gateway as a user service
hermes gateway install

# Enable lingering so gateway survives SSH logout
sudo loginctl enable-linger $USER
```

## Security Notes

- Tailscale uses WireGuard — traffic is encrypted end-to-end, no open ports on the internet
- The `token` auth mode adds a second layer even within your tailnet
- Tailscale Funnel (public internet) is NOT needed; standard Serve keeps it tailnet-only
- For IoT/guest devices not on your tailnet, use `tailscale funnel --bg --https=443 8642` (risk: exposes to public internet)
