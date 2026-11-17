# Claude Code, AIRIS Gateway, and MindBase

Use this when wiring MCP for Claude Code in real repos.

## Verified patterns from a real session

### 1) Gateway installation is not the whole job
- `superclaude mcp --servers airis-mcp-gateway` installs the gateway bundle and registers `airis-gateway` / `airis-mcp-gateway`.
- That does not automatically install separate Claude Code MCP entries for every underlying server.
- If the user wants the individual servers visible in `claude mcp list`, add them directly with `claude mcp add` too.

### 2) Register individual Claude MCP servers explicitly
Examples that worked:
- `claude mcp add --scope user --transport stdio context7 -- npx -y @upstash/context7-mcp`
- `claude mcp add --scope user --transport stdio sequential-thinking -- npx -y @modelcontextprotocol/server-sequential-thinking`
- `claude mcp add --scope user --transport stdio serena -- uvx --from git+https://github.com/oraios/serena serena start-mcp-server --context ide-assistant`
- `claude mcp add --scope user --transport http tavily https://mcp.tavily.com/mcp/?tavilyApiKey=...`
- `claude mcp add --scope user --transport stdio magic -e API_KEY=... -- npx -y @21st-dev/magic@latest`

Verification:
- `claude mcp list` should show each server as connected.

### 3) MindBase is a separate local stack
MindBase is not just a gateway toggle. It needs its own local runtime:
- PostgreSQL + pgvector
- Ollama embedding model
- MindBase MCP server process

Known-good local wiring:
- DB: `postgresql://mindbase:mindbase_dev@localhost:15434/mindbase_dev`
- Ollama: `http://localhost:11434`
- Embedding model: `bge-m3`
- MCP entrypoint: `corepack pnpm exec tsx apps/mcp-server/index.ts`

Register it in Claude Code as a stdio server and point env vars at the local services.

### 4) Installation sanity checks
- Use `claude mcp list` to confirm the client-side registration.
- Use `docker ps` and health endpoints to confirm the gateway and local backing services are alive.
- If a gateway installer creates the wrong path shape for a config file, replace the stale path with a real file before retrying.

## Why this matters
This avoids a common failure mode: assuming the gateway install implies the client now sees all underlying MCP servers. It doesn’t. If the goal is a richer Claude Code tool list, add the direct servers as well.