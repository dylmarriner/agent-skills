# Multi-Client MCP Registration (Claude Code / Codex / Hermes)

Verified recipe for registering the same MCP server set across all three agents.
Confirmed working 2026-07-12 on kubuntux (bun / pnpm / npx / uvx all available).

## The standard 6-server set used this session
- **context7** — library/docs fetch (stdio `npx @upstash/context7-mcp`)
- **sequential-thinking** — reasoning (stdio `npx @modelcontextprotocol/server-sequential-thinking`)
- **serena** — semantic code intel (uvx serena, needs a Python venv)
- **tavily** — web search (HTTP, api key in query string)
- **magic** — 21st.dev UI components (stdio npx, `API_KEY` env)
- **mindbase** — local RAG (stdio: local Postgres + Ollama + tsx server)

## Claude Code  (`claude mcp add`)
```bash
claude mcp add --scope user --transport stdio context7 -- npx -y @upstash/context7-mcp
claude mcp add --scope user --transport stdio sequential-thinking -- npx -y @modelcontextprotocol/server-sequential-thinking
claude mcp add --scope user --transport stdio serena -- uvx --from git+https://github.com/oraios/serena serena start-mcp-server --context ide-assistant
claude mcp add --scope user --transport http tavily -- 'https://mcp.tavily.com/mcp/?tavilyApiKey=KEY'
claude mcp add --scope user --transport stdio magic -- npx -y @21st-dev/magic@latest
claude mcp add --scope user --transport stdio mindbase -- bash -lc 'cd /tmp/mindbase && DATABASE_URL="postgresql://mindbase:mindbase_dev@localhost:15434/mindbase_dev" OLLAMA_URL="http://localhost:11434" EMBEDDING_MODEL="bge-m3" corepack pnpm exec tsx apps/mcp-server/index.ts'
claude mcp list      # verify (shows ✔ Connected)
```
Notes:
- `--scope user` = global; omit for project-local (`.mcp.json`).
- `claude mcp remove <NAME>` first for idempotency.

## Codex  (`codex mcp add`)
```bash
codex mcp add context7 -- npx -y @upstash/context7-mcp
codex mcp add sequential-thinking -- npx -y @modelcontextprotocol/server-sequential-thinking
codex mcp add serena -- uvx --from git+https://github.com/oraios/serena serena start-mcp-server --context ide-assistant
codex mcp add tavily --url "https://mcp.tavily.com/mcp/?tavilyApiKey=KEY"
codex mcp add magic --env API_KEY=xxx -- npx -y @21st-dev/magic@latest
codex mcp add mindbase -- bash -lc 'cd /tmp/mindbase && DATABASE_URL="postgresql://mindbase:mindbase_dev@localhost:15434/mindbase_dev" OLLAMA_URL="http://localhost:11434" EMBEDDING_MODEL="bge-m3" corepack pnpm exec tsx apps/mcp-server/index.ts'
codex mcp list
codex mcp get <NAME>
```
PITFALL — **OAuth trap (headless):** `codex mcp add <NAME> --url https://mcp.context7.com/mcp` launches an interactive browser OAuth flow that TIMES OUT in a PTY-less context (`Error: timed out waiting for OAuth callback`). Use the stdio package instead. `tavily`'s `--url ?tavilyApiKey=` completed OAuth via stdout — server-dependent. If it hangs on a browser URL, switch to stdio.
PITFALL — `--env` is stdio-only; for HTTP put the key in the URL query string.

## Hermes  (`hermes mcp add` — agent-safe)
```bash
hermes mcp add context7 --command npx --args -y @upstash/context7-mcp --connect-timeout 60
hermes mcp add sequential-thinking --command npx --args -y @modelcontextprotocol/server-sequential-thinking --connect-timeout 60
hermes mcp add serena --command uvx --args --from git+https://github.com/oraios/serena serena start-mcp-server --context ide-assistant --connect-timeout 90
hermes mcp add tavily --url "https://mcp.tavily.com/mcp/?tavilyApiKey=KEY" --connect-timeout 60
hermes mcp add magic --command npx --args -y @21st-dev/magic@latest --env API_KEY=xxx --connect-timeout 60
hermes mcp add mindbase --command bash --args -lc "cd /tmp/mindbase && DATABASE_URL=\"postgresql://mindbase:mindbase_dev@localhost:15434/mindbase_dev\" OLLAMA_URL=\"http://localhost:11434\" EMBEDDING_MODEL=\"bge-m3\" corepack pnpm exec tsx apps/mcp-server/index.ts" --connect-timeout 90
hermes mcp list
```
PITFALL — The agent CANNOT edit `~/.hermes/config.yaml` directly (refused with `Refusing to write to Hermes config file`). `hermes mcp add` writes the same `mcp_servers` block safely.
PITFALL — Hermes discovers MCP at startup; the current session won't see new tools until the agent restarts.

## MindBase local stack (all three clients point at it)
- Postgres: `docker compose up -d postgres` in `/tmp/mindbase` → container `mindbase-postgres-canon`, host port `15434`. DB `postgresql://mindbase:mindbase_dev@localhost:15434/mindbase_dev`.
- Ollama embedding model: `ollama pull bge-m3`.
- Server: `corepack pnpm exec tsx apps/mcp-server/index.ts` from `/tmp/mindbase` (run `corepack pnpm install` first).
- Env: `DATABASE_URL`, `OLLAMA_URL`, `EMBEDDING_MODEL=bge-m3`.

## Pitfall: broken Claude Code PreToolUse hook (`obelisk hook claude`)
A `PreToolUse` Bash hook running `obelisk hook claude` fails with `Failed PreToolUse: Bash hook error` (fires per Bash call) when the `obelisk` on PATH lacks a `hook` subcommand. Diagnose by running the exact hook command:

```bash
obelisk hook claude <<<'{"tool_name":"Bash","tool_input":{"command":"ls"}}'; echo "EXIT=$?"
# correct token-engine build (v1.0.0): returns valid JSON + exit 0
#   {"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow",...}}
# wrong/agent-fork build (v0.0.0-dev): prints help text + exit 1 -> no JSON -> hook failure
```

Root cause seen this session: `~/.local/bin/obelisk` was shadowed by the agent-fork binary instead of the token-engine (Rust `obelisk 1.0.0`) that installs the hook. The hook requires the token-engine's `hook` subcommand which emits `{"hookSpecificOutput":...}`.

Fix options:
1. **Pin the hook to the absolute token-engine path** in `~/.claude/settings.json` (safest — leaves the agent fork as bare `obelisk`): change `command` from `obelisk hook claude` to `/home/kubuntux/obelisk-fresh/target/release/obelisk hook claude`.
2. **Restore the token-engine binary** to `~/.local/bin/obelisk` (matches intended state; breaks anything invoking the agent fork by bare name).
3. **Remove the hook** entirely if token-compression is not wanted.

Verify any fix by re-running the hook command above — it must emit valid JSON with exit 0.
