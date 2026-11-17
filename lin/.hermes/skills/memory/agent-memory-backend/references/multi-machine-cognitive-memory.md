# Multi-Machine Cognitive Memory Architecture

## Stack Overview

When running Hermes on multiple machines (e.g. `kubuntux` and `macuntu`),
memory is a **dual-layer** system:

```
┌─────────────────────────────────────────────────────────────┐
│                    SHARED LAYER (agentmemory)                │
│  Vector embeddings + BM25 hybrid search + knowledge graph    │
│  Runs on ONE machine, exposed over Tailscale via socat       │
│  All machines READ and WRITE to the same agentmemory store   │
└─────────────────────────────────────────────────────────────┘
                            ↑
                    Tailscale :3111
                            ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  kubuntux    │  │  macuntu     │  │  any other   │
│  Hermes      │  │  Hermes      │  │  Hermes      │
├──────────────┤  ├──────────────┤  ├──────────────┤
│ LOCAL LAYER  │  │ LOCAL LAYER  │  │ LOCAL LAYER  │
│ MEMORY.md    │  │ MEMORY.md    │  │ MEMORY.md    │
│ IDENTITY.md  │  │ IDENTITY.md  │  │ IDENTITY.md  │
│ SOUL.md      │  │ SOUL.md      │  │ SOUL.md      │
│ memory/epis/ │  │ memory/epis/ │  │ memory/epis/ │
│ memory/meta/ │  │ memory/meta/ │  │ memory/meta/ │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Why Dual Layer

| Layer | What | Why Per-Machine |
|-------|------|-----------------|
| **agentmemory** | Vector search, graph, observations, memories | Shared — so machine A's learnings are recallable from machine B |
| **Cognitive files** | MEMORY.md, IDENTITY.md, SOUL.md, daily logs, reflection logs | Per-machine — each node has different active context, projects, local filesystem paths |
| **SOUL.md** | Personality, boundaries, operating mode | Per-machine — can differ (e.g. macuntu may have a different persona than kubuntux) |

## Setup Per Machine

### Machine A (hosts agentmemory)

1. Install + start agentmemory daemon (see agent-memory-backend skill)
2. Expose port via socat on Tailscale IP
3. Keep alive with cron job every 5m
4. Hermes config: `memory.provider: agentmemory` pointing to localhost
5. Cognitive memory files: MEMORY.md, IDENTITY.md, memory/* structure

### Machine B (client only)

1. **No agentmemory daemon needed** — connects remotely
2. Hermes MCP server config with `env.AGENTMEMORY_URL` pointing to Machine A
3. Hermes `memory.agentmemory_url` pointing to Machine A
4. Install companion skills: `npx skills add rohitg00/agentmemory -y`
5. Cognitive memory files: MEMORY.md, IDENTITY.md, SOUL.md, memory/* — **all local**
   - These are the machine's local context (active projects, local paths, working state)
   - Sobelowding agentmemory as the long-term vector/graph store

## Hermes Config for a Client Node

```yaml
mcp_servers:
  agentmemory:
    command: npx
    args: [-y, '@agentmemory/mcp']
    enabled: true
    env:
      AGENTMEMORY_URL: http://100.93.75.87:3111    # Machine A's Tailscale IP

memory:
  memory_enabled: true
  user_profile_enabled: true
  provider: agentmemory
  agentmemory_url: http://100.93.75.87:3111         # Same remote address
```

## Cognitive File Management

- Each machine maintains its own `~/.hermes/MEMORY.md` with machine-specific
  active context (local paths, projects, running services).
- `~/.hermes/IDENTITY.md` per-machine with the machine's role in the network.
- `~/.hermes/SOUL.md` per-machine — defines the local agent's persona.
- Daily episode logs (`memory/episodes/YYYY-MM-DD.md`) stay local.
- agentmemory stores the shared long-term knowledge graph and vector index.

## Pitfalls

- **Port conflicts**: If two machines on the tailnet both bind :3111 via socat,
  Tailscale picks the closest one non-deterministically. Only expose the port
  from ONE machine (the host running agentmemory).
- **Network split**: If the tailnet drops, client machines lose memory write
  access. agentmemory clients will fail gracefully (MCP server unreachable),
  but the Hermes session won't crash — it falls back to no agentmemory.
- **Cron job spacing**: 5m is frequent enough to catch a downed socat within
  one work cycle but sparse enough to avoid tight-loop restarts on a flaky link.
