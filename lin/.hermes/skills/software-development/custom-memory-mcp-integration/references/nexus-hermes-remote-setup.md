# Nexus memory setup for remote Hermes hosts

Use this when enabling Nexus memory on a remote Hermes machine (for example `lin` or `rabuntu`) where Hermes should talk to a Nexus server on another host.

## What must be configured

Hermes can expose Nexus through two related surfaces:

- General Hermes plugin: `~/.hermes/plugins/nexus-memory/` with `plugins.enabled: [nexus-memory, ...]`.
- MCP stdio compatibility block: `mcp_servers.nexus-memory` with adapter command/args/env, if the host already uses the `synapse-memory` Nexus adapter.

Do not configure only one surface and assume the other works.

## Remote-host checklist

1. Copy/install plugin directory:

   ```bash
   mkdir -p ~/.hermes/plugins
   # copy nexus-memory into ~/.hermes/plugins/nexus-memory
   chmod -R u+rwX,go-rwx ~/.hermes/plugins/nexus-memory
   ```

2. Update `~/.hermes/config.yaml`:

   - Back it up first.
   - Normalize `plugins.enabled` to a YAML list if it was a JSON string or comma string.
   - Add `nexus-memory`.
   - Ensure `memory.memory_enabled: true` and `memory.user_profile_enabled: true`.
   - Preserve any existing `mcp_servers.nexus-memory` adapter, but refresh its `env` values.

3. Update `~/.hermes/.env` with plugin-required env vars:

   ```bash
   # For stdio adapters and direct REST plugins, prefer the base URL:
   NEXUS_URL=http://<nexus-host>:7777
   NEXUS_SECRET=<current bearer token if server requires auth>
   NEXUS_AGENT=hermes
   NEXUS_AGENT_ID=hermes
   NEXUS_SOURCE=hermes
   NEXUS_DEVICE=<device-name>
   ```

   Hermes plugin `requires_env` checks read `~/.hermes/.env`, so config-only secrets may still leave the plugin looking unconfigured.

4. Verify plugin discovery:

   ```bash
   hermes plugins list --plain --no-bundled | grep nexus-memory
   ```

5. Verify live plugin behavior without printing secrets:

   ```bash
   set -a
   . ~/.hermes/.env
   set +a
   python3 - <<'PY'
   import importlib.util, json, pathlib
   p = pathlib.Path.home() / '.hermes/plugins/nexus-memory/tools.py'
   spec = importlib.util.spec_from_file_location('nexus_tools', p)
   mod = importlib.util.module_from_spec(spec)
   spec.loader.exec_module(mod)
   health = json.loads(mod.nexus_health({}))
   print('health', health.get('healthy'), health.get('components'))
   store = json.loads(mod.nexus_store({
       'content': 'Nexus setup verification marker',
       'tags': ['setup', 'verification'],
       'importance': 0.2,
   }))
   print('store_error', store.get('error'), 'stored', bool(store.get('id')))
   recall = json.loads(mod.nexus_recall({'query': 'Nexus setup verification marker', 'limit': 3}))
   print('recall_error', recall.get('error'), 'results', len(recall.get('results', [])))
   PY
   ```

6. Verify the stdio adapter separately if configured:

   ```bash
   printf '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"nexus_status","arguments":{}}}\n' \
     | timeout 10 python3 ~/.hermes/scripts/adapters/nexus_mcp_stdio.py
   ```

## Interpreting failures

- `401 Missing Bearer token`: the live server requires auth. If the user expected no-auth, treat that as a server-side mismatch, not a client setup failure. Either update clients with the current live secret or change/restart the Nexus server auth policy.
- `HTTP 401: Invalid API key`: the plugin and endpoint are wired, but the bearer token is stale/wrong. Refresh from the authoritative Nexus server/container or ask the user for the current token. Do not keep reworking the plugin path.
- `tools/list` on `/mcp` succeeds but `tools/call` hangs or times out: probe REST directly. A Nexus MCP endpoint may self-dispatch through its own REST API and hang, while direct REST works. Use the stdio adapter or a Hermes plugin that calls `/health`, `/v1/memory/save`, and `/v1/memory/recall` directly.
- `HTTP 422` on recall with `search_modes: null` or `memory_types: null`: omit optional list fields when not set; do not send explicit null.
- `Connection failed`: check Tailscale/DNS, Nexus host reachability, and whether `NEXUS_URL` format matches the transport.
- Plugin not listed: check `~/.hermes/plugins/nexus-memory/plugin.yaml`, config `plugins.enabled`, and whether the right `hermes` binary is being used on that remote host.

## Direct REST plugin pattern

When HTTP MCP self-dispatch hangs, the Hermes plugin `tools.py` can call REST directly:

- `nexus_health` -> `GET /health`
- `nexus_store` -> `POST /v1/memory/save`
- `nexus_recall` -> `POST /v1/memory/recall`
- `nexus_context` -> `GET /v1/agents/{agent_id}/context?tokens=...`
- `nexus_learn` -> `POST /v1/agents/{agent_id}/learn`
- `nexus_reflect` -> `POST /v1/memory/reflect`

Use the base URL in env (`http://host:7777`), strip a trailing `/mcp` defensively in code, and include `Authorization: Bearer ...` only when `NEXUS_SECRET` is non-empty.

## Safety notes

- Do not print secrets into chat/log output.
- Back up `~/.hermes/config.yaml` before mutation.
- If an approval prompt blocks reading a live container secret, stop and ask for approval or the current bearer token; do not retry the same blocked secret-read path.
