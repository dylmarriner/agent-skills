---
name: linux-proxy-service-management
description: Standardized workflow for deploying and troubleshooting systemd-managed network proxy services (LiteLLM, API gateways, etc.) on Linux infrastructure.
---

# Linux Proxy Service Management

Standardized workflow for deploying and troubleshooting systemd-managed network proxy services (LiteLLM, API gateways, etc.) on Linux infrastructure.

## Service Pattern (Systemd User)
Services must be managed as systemd user units to respect user scope:
- **Location:** `~/.config/systemd/user/<service>.service`
- **Unit Lifecycle:** 
  `systemctl --user daemon-reload`
  `systemctl --user restart <service>`
  `systemctl --user status <service>`
  `journalctl --user -u <service> -n 50`

## Troubleshooting

### Portainer (Docker Web UI) Setup

Portainer 2.39.4+ requires a setup token on first boot. Two ways to skip it:

**Option A (recommended): Pre-set admin password**
```bash
docker run -d --name portainer --restart=always \
  -p 9443:9443 -p 8000:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:latest \
  --admin-password="$(python3 -c "import bcrypt; print(bcrypt.hashpw(b'<password>', bcrypt.gensalt(rounds=10)).decode())")"
```
Then login at `https://<host>:9443` with username `admin` and your chosen password.

**Option B:** `--no-setup-token` — disables the token check entirely (only on trusted networks).

**If you need the token from logs:** `docker logs portainer 2>&1 | grep setup_token` — must catch within 5 minutes of first startup.

### Common Pitfalls & Fixes
- **Configuration Parsing Errors:** YAML formatting errors in config files (e.g., mismatched indentation, invalid alias usage) will cause the service to fail silently or log exit-code 1. Always validate YAML before restart.
- **Port Conflicts:** Ensure proxy ports (e.g., 4000) aren't taken. Use `ss -tulpn | grep <port>` to check.
- **Credential Pathing:** Hardcoding paths in systemd `Environment=` fields is brittle. Use absolute paths to service account keys. If using placeholders (e.g., `/home/...json`), replace them with absolute paths immediately upon discovery.
- **Service Identity:** LiteLLM and similar proxy services require an explicit API key (in config or passed as env). When using `Bearer` auth, ensure `general_settings.master_key` is set to match the auth string.
- **Connection Refused:** If `localhost:port` is refused despite service being 'active', check if the service is binding to `127.0.0.1` vs `0.0.0.0`. Binding to `0.0.0.0` is generally preferred for internal accessibility across network interfaces (like Tailscale).
- **Application Logic Errors:** Do not rely on 'active' systemd status for application health. Even if the service is running, it may be logging critical errors (e.g., \"Secret not bound\", \"Model unavailable\") due to misconfiguration or missing environment bindings. Always tail the service log (`journalctl --user -u <service> -n 100`) after restarts to confirm the application successfully initialized.
- **Linuxbrew PATH Conflict:** If `brew shellenv` is called in `.bashrc`, it prepends `/home/linuxbrew/.linuxbrew/bin` to PATH. If this comes AFTER `~/.local/bin` has already been added, the linuxbrew litellm (uses Python 3.14, may be missing proxy deps) shadows the pip-installed version (Python 3.12, correct). Fix: ensure `export PATH=\"$HOME/.local/bin:$PATH\"` is placed at the VERY END of `.bashrc` PATH setup, after all `brew shellenv` calls. Verify with `which litellm` and `litellm --version` after sourcing.
- **OpenCode `run` subcommand requires `--print-logs`:** In OpenCode v1.4.3, `opencode run <message> --model <provider/model>` shows the help text instead of running unless `--print-logs 2>/dev/null` is passed. The stderr goes to logs while stdout gets the model response. Without `--print-logs`, the command parser misroutes and dumps help. This is an OpenCode bug that makes non-interactive `run` unusable without this flag.
- **"No connected db." = API key mismatch:** LiteLLM returns HTTP 400 with `{'error': {'message': 'No connected db.', ...}}` when the API key doesn't match `master_key`. Counterintuitive — looks like a database issue but is actually auth failure. If ALL proxy requests fail with this, check the api_key value, not the database.

## Bifrost — the current lin AI gateway (replaced LiteLLM 2026-09-02)

lin's OpenAI-compatible gateway is a self-hosted **Bifrost** (maximhq/bifrost v2), running as a Docker container — NOT a systemd unit. LiteLLM (`litellm-vertex.service`) was stopped + disabled 2026-09-02.

- **Container:** `docker name=bifrost`, image `maximhq/bifrost`, `--network host`, port **8080**, `--restart unless-stopped`. Health: `docker inspect bifrost --format '{{.State.Health.Status}}'`.
- **Config:** `~/bifrost/data/config.json` (mounted at `/app/data`). JSON schema at `https://www.getbifrost.ai/schema` — pull it to get exact field shapes before writing config (providers are open-ended `additionalProperties`, so validate against the schema's `$defs`).
- **Two config modes:** (1) `config.json` alone = file-only (restart to apply); (2) `config_store.enabled: true` (sqlite `./config.db`) = DB-backed, UI edits survive restarts. Default config.json seeds the DB on first load; if you edit config.json later its content-hash changes and the file version wins.
- **CRITICAL — base_url must NOT end in `/v1`:** Bifrost appends `/v1` to the provider `network_config.base_url` itself. Setting `http://localhost:18080/v1` yields `/v1/v1/models` → 404 "File Not Found". Use the bare host: `http://localhost:18080`.
- **CRITICAL — needs `--network host`:** Bifrost serves models bound to host-localhost (e.g. an SSH tunnel to a remote GPU at `localhost:18080`). Without host networking the container can't reach them. Also gives direct access to ports already on the host.
- **Serving a self-hosted OpenAI-compatible model:** register an `openai` provider whose key value = the upstream `--api-key`, with `network_config: { base_url: <tunnel-host-no-v1>, allow_private_network: true, default_request_timeout_in_seconds: 300 }`. Model then exposes as `openai/<alias>` and also resolves as bare `<alias>`.
- **Auth for localhost use:** `auth_config: { master_key: "sk-local", auth_enabled: false }` lets consumers hit it with no key (or any key). Fine on a single-user box; enable auth if it's reachable beyond localhost/tailnet.
- **Consumers repointed at Bifrost:** Hermes `custom_providers` `base_url` → `http://localhost:8080/v1`; Paperclip `.env.litellm.paperclip` `LITELLM_BASE_URL` → `http://host.docker.internal:8080/v1`. Both files hand-edited (they are NOT protected config.yaml — plain text edits OK).
- **Cross-machine consumers (opencode + pi on kubuntux):** Bifrost binds `0.0.0.0` and is reachable tailnet-wide at lin's IP `http://100.91.55.113:8080/v1`. OpenCode (config `~/.config/opencode/opencode.json`) and pi (`~/.pi/agent/models.json` + `settings.json`) each get a `bifrost` provider pointing at that tailnet URL — same provider shape as on lin, just the reachable host. Adding a provider is additive; set it as default/active model (`opencode model` → `bifrost/qwen3.8-27b-aggressive`; pi `settings.json` `defaultProvider: bifrost`, `defaultModel: qwen3.8-27b-aggressive`). See `references/bifrost-gateway.md` and the `ai-provider-cross-config` skill for per-tool provider shapes.
- **Verify clients really hit the gateway:** don't trust client-side self-reports. `docker logs bifrost | grep '"http.target":"/v1/chat/completions"'` and confirm `http.remote_addr` shows the remote tailnet IP (e.g. `100.93.75.87`) for kubuntux clients and `127.0.0.1` for lin, all `http.status_code: 200`.
- Full deploy walkthrough + config.json template: `references/bifrost-gateway.md`.

### Deciding gateway choice
- **Bifrost** = the current lin default. Very fast, richer governance/UI. Custom OpenAI-compatible endpoints are easy (openai provider + custom base_url).
- **LiteLLM** = the previously-used gateway; supports arbitrary provider prefixes (`openai/...`, `vertex_ai/...`). Only reach for it if you specifically need a LiteLLM feature (it's no longer running on lin).
- **Don't migrate dead providers.** If upstream models were failing (e.g. Vertex/Gemini on a billing-disabled GCP project → 403 "requires billing"), they are corpses — don't carry them into the new gateway. Check a live call before migrating a provider set.

## OmniRoute — separate self-hosted AI router (dashboard/playground + /v1 plane)

A distinct npm-installed Node binary (`omniroute`, v3.8.50) on lin — NOT the default gateway and does NOT replace Bifrost. Run it when Dylan asks to start/use OmniRoute; it is its own server with its own dashboard.

- **Start:** `omniroute serve --daemon --no-open` (binds `0.0.0.0`, port 20128; already-global install — do not reinstall unless asked). Verify with `curl -s http://100.91.55.113:20128/api/health` → `{"status":"ok"}`. Dashboard `http://100.91.55.113:20128`, API base `http://100.91.55.113:20128/v1` (Tailscale reachable at lin's IP).
- **Config/state split:** `~/.omniroute/.env` holds user overrides (first-loaded env wins — an `STORAGE_ENCRYPTION_KEY` in the install `.env` is silently ignored if `~/.omniroute/.env` set it first). All auth/state lives in `~/.omniroute/storage.sqlite`. Install-time defaults sit in `<node_modules>/omniroute/.env` (`INITIAL_PASSWORD`, `JWT_SECRET`, `REQUIRE_API_KEY`).
- **Dashboard password:** default login is `admin` / the `INITIAL_PASSWORD` value from the install `.env` (bootstrap = `CHANGEME`). It is stored as a bcrypt hash in `storage.sqlite` under `key_value` row `settings|password`. Recover/verify the current password by bcrypt-comparing candidates against that hash with the tool's own bundled bcryptjs (do NOT rely on reading a plaintext): `NODE_PATH=<node_modules>/omniroute/node_modules node -e '...bcrypt.compareSync(cand, hash)...'`. If none of the env default candidates match, the password was changed and is unrecoverable — reset it instead. `settings|setupComplete=true` means first-run setup already ran.
- **SECURITY DEFAULT (change on a tailnet-facing host):** starts with `REQUIRE_API_KEY=false` and the `CHANGEME` password bound to `0.0.0.0`, so the `/v1` inference plane and dashboard are open to anything that can route to the host. Lock it with `REQUIRE_API_KEY=true` and a real password after first boot. Full operating reference: `references/omniroute-router.md`.

## Multi-Consumer Wiring
A single Litellm proxy on port 4000 can feed multiple downstream systems. Each needs its own model catalog registration:
- **OpenCode:** Provider config at `~/.config/opencode/opencode.json` — set `baseURL: http://localhost:4000/v1`, list model IDs matching Litellm's `model_name` entries.
- **Hermes:** `custom_providers` section in `~/.hermes/config.yaml` — point at `http://localhost:4000/v1`, list models. Use as `provider-name/model-name` (e.g. `vertex-ai/gemini-2.5-flash`).
- **OpenClaw:** Provider entries in `openclaw.json` under `models.providers.<name>.baseUrl` — set to `http://localhost:4000/v1`, add models to the array. Also register in `agents.defaults.models` and `agents/main/agent/models.json`.

See `references/multi-consumer-proxy-wiring.md` for full config examples.

## Remote Models via SSH Tunnel
When a model endpoint is bound to localhost on a remote Tailscale machine, tunnel it: `ssh -L <local_port>:localhost:<remote_port> root@<tailscale-ip> -N -f -o ExitOnForwardFailure=yes` then wire into OpenClaw (MCP server + model provider).

See `references/remote-model-ssh-tunnel.md` for the full step-by-step.

## Verification Workflow
1. **Status:** `systemctl --user status <service>`
2. **Logs:** `journalctl --user -u <service> -n 50`
3. **Connectivity:** `curl -v -H "Authorization: Bearer <key>" http://localhost:<port>/chat/completions ...`
4. **CLI check:** `litellm --version` — confirms the correct Python installation is in PATH (should NOT hit linuxbrew Python with missing deps)
5. **Downstream client test:** Test the proxy through an actual consumer (OpenCode, Hermes, OpenClaw, etc.) — not just curl.
   - **OpenCode:** `opencode run "Reply only: OK" --model vertex/gemini-2.5-flash --print-logs 2>/dev/null`
   - **Hermes:** `hermes chat -q "Reply only: OK" -m vertex-ai/gemini-2.5-flash`
   - **OpenClaw:** `openclaw chat -q "Reply only: OK" -m microsoft-foundry/gemini-2.5-flash`
6. **Validation:** If connectivity fails despite 'active' status, verify that the application is binding to the expected interface (0.0.0.0 is preferred). Check if the application crashed immediately after startup due to invalid configuration (parsing errors in YAML, missing environment files). Do not rely solely on systemd's 'active' status.
