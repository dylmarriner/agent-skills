---
name: memory-setup
description: Enable and configure persistent memory for any agent platform (Moltbot/Clawdbot or Hermes Agent). Use when setting up memory, fixing goldfish brain, configuring the memory provider, installing agentmemory backend, or setting up cognitive memory structure with reflection and decay.
---

# Memory Setup Skill

Transform your agent from goldfish to elephant. Generic setup steps followed by platform-specific sections.

## Quick Setup

### 1. Enable Memory Search in Config

Add to `~/.clawdbot/clawdbot.json` (or `moltbot.json`):

```json
{
  "memorySearch": {
    "enabled": true,
    "provider": "voyage",
    "sources": ["memory", "sessions"],
    "indexMode": "hot",
    "minScore": 0.3,
    "maxResults": 20
  }
}
```

### 2. Create Memory Structure

In your workspace, create:

```
workspace/
├── MEMORY.md              # Long-term curated memory
└── memory/
    ├── logs/              # Daily logs (YYYY-MM-DD.md)
    ├── projects/          # Project-specific context
    ├── groups/            # Group chat context
    └── system/            # Preferences, setup notes
```

### 3. Initialize MEMORY.md

Create `MEMORY.md` in workspace root:

```markdown
# MEMORY.md — Long-Term Memory

## About [User Name]
- Key facts, preferences, context

## Active Projects
- Project summaries and status

## Decisions & Lessons
- Important choices made
- Lessons learned

## Preferences
- Communication style
- Tools and workflows
```

## Config Options Explained

| Setting | Purpose | Recommended |
|---------|---------|-------------|
| `enabled` | Turn on memory search | `true` |
| `provider` | Embedding provider | `"voyage"` |
| `sources` | What to index | `["memory", "sessions"]` |
| `indexMode` | When to index | `"hot"` (real-time) |
| `minScore` | Relevance threshold | `0.3` (lower = more results) |
| `maxResults` | Max snippets returned | `20` |

### Provider Options
- `voyage` — Voyage AI embeddings (recommended)
- `openai` — OpenAI embeddings
- `local` — Local embeddings (no API needed)

### Source Options
- `memory` — MEMORY.md + memory/*.md files
- `sessions` — Past conversation transcripts
- `both` — Full context (recommended)

## Daily Log Format

Create `memory/logs/YYYY-MM-DD.md` daily:

```markdown
# YYYY-MM-DD — Daily Log

## [Time] — [Event/Task]
- What happened
- Decisions made
- Follow-ups needed

## [Time] — [Another Event]
- Details
```

## Agent Instructions (AGENTS.md)

Add to your AGENTS.md for agent behavior:

```markdown
## Memory Recall
Before answering questions about prior work, decisions, dates, people, preferences, or todos:
1. Run memory_search with relevant query
2. Use memory_get to pull specific lines if needed
3. If low confidence after search, say you checked
```

## Troubleshooting

### Memory search not working?
1. Check `memorySearch.enabled: true` in config
2. Verify MEMORY.md exists in workspace root
3. Restart gateway: `clawdbot gateway restart`

### Results not relevant?
- Lower `minScore` to `0.2` for more results
- Increase `maxResults` to `30`
- Check that memory files have meaningful content

### Provider errors?
- Voyage: Set `VOYAGE_API_KEY` in environment
- OpenAI: Set `OPENAI_API_KEY` in environment
- Use `local` provider if no API keys available

## Verification

Test memory is working:

```
User: "What do you remember about [past topic]?"
Agent: [Should search memory and return relevant context]
```

If agent has no memory, config isn't applied. Restart gateway.

## Full Config Example

```json
{
  "memorySearch": {
    "enabled": true,
    "provider": "voyage",
    "sources": ["memory", "sessions"],
    "indexMode": "hot",
    "minScore": 0.3,
    "maxResults": 20
  },
  "workspace": "/path/to/your/workspace"
}
```

---

## Hermes Agent Adaptation

Hermes uses its own memory system — Moltbot/Clawdbot config doesn't apply directly. Here's the mapping:

### Concept Mapping

| Moltbot/Clawdbot | Hermes Agent |
|---|---|
| `memorySearch` in `clawdbot.json` | `memory` section in `~/.hermes/config.yaml` |
| `voyage` embeddings provider | Built-in memory tool (no embedding key needed) |
| Vector search + MEMORY.md files | `memory` tool entries injected every turn |
| `clawdbot gateway restart` | Restart Hermes session (config loaded per-session) |
| File-based MEMORY.md | `memory` tool actions: add / replace / remove |

### Level 1: Built-in Memory (zero config)

Hermes memory is enabled by default. In `~/.hermes/config.yaml`:

```yaml
memory:
  memory_enabled: true
  user_profile_enabled: true
  memory_char_limit: 2200
  user_char_limit: 1375
```

Use the `memory` tool to store facts:
- `memory(action='add', target='memory', content='...')` — personal notes
- `memory(action='add', target='user', content='...')` — user profile
- `memory(action='replace', ...)` — update existing

Memory entries are automatically injected into every session turn.

### Level 2: agentmemory Backend (vector search + knowledge graph)

For hybrid search (BM25 + vector + knowledge graph), install the agentmemory backend:

```bash
npm install -g @agentmemory/agentmemory
agentmemory init     # Creates ~/.agentmemory/.env
```

Configure `.env` with an OpenAI-compatible provider (DeepSeek, Venice, or any API key):

```ini
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.venice.ai/api/v1
EMBEDDING_PROVIDER=local
AGENTMEMORY_AUTO_COMPRESS=true
AGENTMEMORY_INJECT_CONTEXT=true
CONSOLIDATION_ENABLED=true
GRAPH_EXTRACTION_ENABLED=true
```

Start the daemon:

```bash
cd ~/.agentmemory && set -a && source .env && set +a && exec ~/.npm-global/bin/agentmemory
```

Wire into Hermes `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  agentmemory:
    command: npx
    args: ['-y', '@agentmemory/mcp']
    enabled: true

memory:
  provider: agentmemory
  agentmemory_url: http://127.0.0.1:3111
```

Install companion skills:

```bash
npx skills add rohitg00/agentmemory -y
```

Verify:

```bash
agentmemory status    # Should show ✓ healthy + LLM + embeddings
agentmemory doctor    # 8/10+ passing
```

### Level 3: Cognitive Memory Structure (file-based)

For the full reflection/decay/graph/audit system, run the init script:

```bash
bash ~/.hermes/skills/cognitive-memory-1.0.8/scripts/init_memory.sh ~/.hermes
```

Creates:
```
~/.hermes/
├── MEMORY.md           # Core memory (~3K tokens, always in context)
├── IDENTITY.md         # Facts + self-image + self-awareness
├── SOUL.md             # Values, principles, boundaries
└── memory/
    ├── episodes/       # Daily logs: YYYY-MM-DD.md
    ├── graph/          # Knowledge graph (entities + relations)
    ├── procedures/     # Learned workflows
    ├── vault/          # Pinned memories (no decay)
    └── meta/           # Decay scores, reflection log, audit
```

### Verifying Hermes Memory

```yaml
User: "Remember that I prefer dark mode."
Agent: [Use memory(action='add', target='memory') to store]

User: "What do you remember about my preferences?"
Agent: [Should find the stored memory in injected context]
```

---

### Level 4: Nexus Memory Backend (shared multi-agent memory)

Links Hermes to a self-hosted Nexus memory server (semantic + lexical + graph + temporal search).

#### Prerequisites

- Nexus server running (Docker Compose at `synapse-memory/docker-compose.yml`)
- `NEXUS_SECRET` from the server's `.env` file

#### Install

```bash
# 1. Copy plugin from Nexus repo to user plugins
cp -r /path/to/synapse-memory/integrations/plugins/hermes-nexus ~/.hermes/plugins/nexus-memory

# 2. Write env — URL must end with /mcp, not base
NEXUS_URL=http://<host>:7777/mcp
NEXUS_SECRET=<your-secret>
NEXUS_AGENT_ID=hermes

# 3. Enable
hermes plugins enable nexus-memory

# 4. Verify
hermes plugins list | grep nexus-memory  # "enabled"
```

Plugin provides 6 tools (nexus_health, nexus_store, nexus_recall, nexus_context, nexus_learn, nexus_reflect) backed by Nexus MCP's 69 tools behind the scenes.

#### Pitfalls

- **Secret corruption**: `write_file` and heredocs can truncate the secret. Read it from source `.env` with Python — never paste or echo it.
- **URL**: Must end with `/mcp` (MCP POST endpoint), not the base URL.
- **Plugin dir**: `~/.hermes/plugins/nexus-memory/`, NOT `~/.hermes/hermes-agent/plugins/memory/nexus/` (dev tree).
- **Session restart**: Plugin tools appear only after `/new` or gateway restart.
- **Installer bug**: `scripts/nexus-install` may put files in the wrong directory. Manual copy is safer.

#### Debug: VRAM crash from multiple LLM processes

When GPU crashes, check these in order:

```bash
# 1. GPU ring timeout = VRAM contention
sudo dmesg -T | grep -i amdgpu

# 2. How many llama-servers are fighting for GPU?
ps aux | grep llama-server | grep -v grep
docker ps --format '{{.Names}} {{.Image}}' | grep llama

# 3. RAM pressure
free -h

# 4. Disk health (pending sectors = hangs)
sudo smartctl -a /dev/sdX | grep -E 'pending|reallocated'
```

Crash chain: multiple llama-server processes load same model → VRAM overcommit → GPU page faults → ring timeout → driver reset → display server dies. Fix: one server only, drop context size, kill duplicates.

## Why This Matters

Without memory:
- Agent forgets everything between sessions
- Repeats questions, loses context
- No continuity on projects

With memory:
- Recalls past conversations
- Knows your preferences
- Tracks project history
- Builds relationship over time

Goldfish → Elephant. 🐘
