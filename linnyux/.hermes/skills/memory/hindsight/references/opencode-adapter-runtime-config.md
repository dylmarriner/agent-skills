# OpenCode Adapter Runtime Config — Hindsight Injection

The Paperclip OpenCode adapter (`packages/adapters/opencode-local/src/server/runtime-config.ts`) copies the user's `~/.config/opencode/` to a temp directory and injects runtime overrides. The Hindsight MCP server can be auto-injected via env vars.

## How the adapter constructs the runtime config

1. Copies `~/.config/opencode/` → temp dir via `fs.cp()`
2. Reads the copied `opencode.json`
3. Injects `permission.external_directory = "allow"` to suppress headless approval prompts
4. Checks `HINDSIGHT_API_URL` in both `input.env` and `process.env` — if set, adds a `hindsight-memory` entry under the `mcp` key
5. Strips any legacy `mcpServers` key (OpenCode >=1.14 rejects it)
6. Writes the merged config back to the temp dir
7. Sets `XDG_CONFIG_HOME` to the temp dir so OpenCode uses the temp config

## Key design decisions

### Env var reading — both input.env AND process.env

```ts
const apiUrl = env.HINDSIGHT_API_URL?.trim() || process.env.HINDSIGHT_API_URL?.trim();
```

The `env` parameter passed by Paperclip (`buildPaperclipEnv()`) only contains Paperclip-internal vars like `PAPERCLIP_*`. System env vars are NOT included. Always add a `process.env` fallback.

### Skip if already configured

If the user's `opencode.json` already has a `hindsight-memory` entry under `mcp`, injection is skipped. This lets users pin a specific config.

### mcpServers strip

```ts
delete (nextConfig as Record<string, unknown>).mcpServers;
```

OpenCode 1.14+ rejects `mcpServers` with "Unrecognized key". Some processes or plugins write the old key back to the config file. The adapter strips it unconditionally on every run.

## pnpm env var workaround

pnpm strips environment variables from spawned processes for reproducibility. `export` before `pnpm paperclipai run` is ineffective. Two reliable approaches:

### Inline prefix
```bash
HINDSIGHT_API_URL="https://api.hindsight.vectorize.io" HINDSIGHT_API_KEY="hsk_..." pnpm paperclipai run
```

### exec wrapper
```bash
#!/bin/bash
export HINDSIGHT_API_URL="https://api.hindsight.vectorize.io"
export HINDSIGHT_API_KEY="hsk_..."
exec node cli/node_modules/tsx/dist/cli.mjs cli/src/index.ts run
```

### Verification
```bash
cat /proc/$PID/environ | tr '\\0' '\\n' | grep HINDSIGHT
```
