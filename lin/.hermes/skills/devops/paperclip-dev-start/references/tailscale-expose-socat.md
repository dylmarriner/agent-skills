# Paperclip Tailscale Exposure via socat

Tested on kubuntux (Ubuntu 24.04 x86_64, Paperclip v0.3.1).

## Architecture

```
Tailscale client → 100.93.75.87:3101 → socat (0.0.0.0:3101) → Paperclip (127.0.0.1:3100)
```

## Step-by-Step

### 1. Allow the hostname

Paperclip enforces hostname checks in private mode. Add your Tailscale IP:

```bash
cd ~/paperclip
pnpm paperclipai allowed-hostname <tailscale-ip>
# e.g. pnpm paperclipai allowed-hostname 100.93.75.87
```

Restart Paperclip after this.

### 2. Start Paperclip

```bash
cd ~/paperclip
LD_LIBRARY_PATH=$HOME/.local/lib pnpm dev:once
```

The `LD_LIBRARY_PATH` is needed when embedded Postgres requires `libicui18n.so.60` (see the ICU60 extraction notes in the main skill).

Paperclip starts on `127.0.0.1:3100` — it does NOT bind to `0.0.0.0`. The `PAPERCLIP_BIND_HOST` env var and `--bind-host` flag are used for URL construction, not the actual listen address.

### 3. Start socat proxy

In a separate terminal / screen session / systemd service:

```bash
socat TCP-LISTEN:3101,bind=0.0.0.0,fork,reuseaddr TCP:127.0.0.1:3100
```

Use port 3101 (not 3100) because:
- Paperclip already binds `127.0.0.1:3100`
- Binding `0.0.0.0:3100` would conflict since `0.0.0.0` includes `127.0.0.1`

### 4. Verify

```bash
curl http://<tailscale-ip>:3101/api/health
# Expected: {"status":"ok","version":"0.3.1",...}
```

Works from any machine on the tailnet, including the local one:
```bash
curl http://100.93.75.87:3101/api/health
```

## Making socat Permanent

Create a systemd user service:

```bash
mkdir -p ~/.config/systemd/user/
cat > ~/.config/systemd/user/paperclip-socat.service << 'EOF'
[Unit]
Description=Paperclip socat Tailscale proxy
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/socat TCP-LISTEN:3101,bind=0.0.0.0,fork,reuseaddr TCP:127.0.0.1:3100
Restart=always

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now paperclip-socat.service
```

## Troubleshooting

- **curl returns empty response / connection refused**: Paperclip might have crashed. Check `ss -tlnp | grep 3100`.
- **socat exits immediately**: Port 3100 might not be listening yet (Paperclip still starting). Wait and retry.
- **`{"error":"Hostname 'X' is not allowed..."}`**: Run `pnpm paperclipai allowed-hostname X` and restart Paperclip.
