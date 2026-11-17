# AIRIS / Claude MCP session notes

## What happened

- Installed SuperClaude via `pipx install superclaude` and verified with `superclaude doctor`.
- Attempted `superclaude mcp --servers airis-mcp-gateway --scope user`.
- The gateway quick-install initially failed because the downloaded config path was wrong on this machine; the host path had to be corrected so `mcp-config.json` was a file, not a directory.
- After correcting the file path, the AIRIS gateway came up healthy and Claude Code registered `airis-mcp-gateway` / `airis-gateway` successfully.
- The user then corrected the workflow: the gateway bundle alone was not enough. The direct Claude MCP entries still needed to be added.
- Direct Claude MCP entries were added and verified with `claude mcp list`:
  - context7
  - sequential-thinking
  - serena
  - tavily
  - magic

## Practical lessons

- Gateway install and direct Claude registration are separate steps.
- If the user says "install them all into Claude", verify the Claude-side list explicitly.
- `claude mcp list` is the final truth for Claude Code, not the installer log.
- AIRIS profiles may omit some optional servers; add the missing ones directly when needed.

## Useful commands

```bash
superclaude install
superclaude doctor
claude mcp add --scope user --transport stdio context7 -- npx -y @upstash/context7-mcp
claude mcp add --scope user --transport stdio sequential-thinking -- npx -y @modelcontextprotocol/server-sequential-thinking
claude mcp add --scope user --transport stdio serena -- uvx --from git+https://github.com/oraios/serena serena start-mcp-server --context ide-assistant
claude mcp add --scope user --transport http tavily "https://mcp.tavily.com/mcp/?tavilyApiKey=$TAVILY_API_KEY"
claude mcp add --scope user --transport stdio magic -e API_KEY="$MAGIC_API_KEY" -- npx -y @21st-dev/magic@latest
claude mcp list
```
