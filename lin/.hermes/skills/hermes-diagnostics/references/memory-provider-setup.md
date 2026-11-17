# Memory Provider Architecture

## Built-in Memory (agentmemory)

agentmemory is the **built-in** memory backend. It is NOT an external plugin.

- Runs as an MCP server under `mcp_servers.agentmemory` in config.yaml
- Uses `@agentmemory/mcp` via npx
- Provides `mcp_agentmemory_memory_*` tools in the agent's toolset
- Always active (no need to "set up" through any wizard)
- Set as active provider: `hermes config set memory.provider agentmemory`
- Default (empty `provider: ''`) still uses built-in memory

## External Memory Plugins

External plugins live at `~/.hermes/hermes-agent/plugins/memory/`.

**Available plugins** (as of v0.15.1):
- honcho
- openviking
- mem0
- hindsight
- holographic
- retaindb
- byterover

### Managing Plugins

| Command | What it does |
|---------|-------------|
| `hermes memory setup` | Interactive wizard to select & configure a provider plugin |
| `hermes memory status` | Show current external provider config |
| `hermes memory off` | Disable external provider (built-in memory only) |
| `hermes memory reset` | Erase all built-in memory (MEMORY.md / USER.md) |

### Common Pitfall

`hermes setup memory` is NOT a valid command — the correct invocation is `hermes memory setup` (subcommand `memory` under `hermes`, not subcommand `setup`).

## How They Stack

Built-in agentmemory + one external plugin can run simultaneously. The external plugin layers additional persistence/retrieval on top of the always-active built-in.
