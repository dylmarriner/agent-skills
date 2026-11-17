---
name: synapse-memory-integration
description: "Connect Hermes agents to Synapse Memory — a shared agent-memory backend with semantic, lexical, graph, and temporal recall. Covers configuration, sync scripts, MCP bridge, API access, and multi-machine deployment."
version: 1.0.0
author: Hermes
---

# Synapse Memory Integration

Connect Hermes agents to Synapse Memory for cross-session, cross-machine memory persistence.

## Architecture

Synapse Memory runs at `http://100.93.75.87:7777` — a FastAPI+PostgreSQL+Redis backend with:
- **Semantic search** (vector embeddings via pgvector, HNSW index)
- **Lexical search** (FTS via GIN index on `to_tsvector`)
- **Agent profiles** per `agent_id` with typed memories (observation, preference, world, experience, lesson)
- **Admin dashboard** (React+Vite) at `:7778`
- **MCP SSE endpoint** at `/mcp/sse`

```
Hermes agent ──► memory tool ──► local MEMORY.md/USER.md
                                      │
                                      ▼ (every 5m via no-agent cron)
                  sync-memory-to-nexus.py ──► REST API :7777 ──► PostgreSQL
                                      │
                                      ▼ (prefetched per turn)
                  Nexus memory provider injects context
```

Two sync mechanisms work together:
1. **Cron-based diff-sync** (every 5m) — catches everything, zero LLM tokens
2. **Agent double-write** (via this skill) — instant persistence for important entries

## Quick Start

### On a new machine

```bash
# 1. Deploy the sync script
scp sync-memory-to-nexus.py <host>:~/.hermes/scripts/

# 2. Create the cron job
hermes cron create "every 5m" --name sync-memory-to-nexus \
  --script sync-memory-to-nexus.py --no-agent

# 3. Initial backfill
python3 ~/.hermes/scripts/sync-memory-to-nexus.py

# 4. Ensure gateway is running
hermes gateway status
```

### On this machine (lin)

Already deployed. The cron job fires every 5 minutes. The sync script is at `~/.hermes/scripts/sync-memory-to-nexus.py`.

## Machine Inventory

See `references/deployment-guide.md` for the full machine inventory and per-machine SSH commands.

## Hermes Memory Provider Architecture

Synapse Memory integrates with Hermes at two levels:

### 1. Config-level (`memory.provider: nexus`)

Edit `~/.hermes/config.yaml`:
```yaml
memory:
  memory_enabled: true
  user_profile_enabled: true
  provider: nexus
  write_approval: false

nexus:
  agent_id: hermes
  auto_save: true
  prefetch_limit: 20
  secret: nexus-memory-shared-key-2026
  url: http://100.93.75.87:7777
```

This provider handles:
- **Prefetching** relevant context before each LLM turn
- **Session extraction** at end of session (auto_save)
- **Context injection** into the system prompt

### 2. MemoryProvider plugin interface (`on_memory_write`)

Hermes ships a `MemoryProvider` ABC in `agent/memory_provider.py` with an `on_memory_write()` hook that fires on every `memory` tool call. Memory provider plugins (Honcho, RetainDB, Supermemory, etc.) implement this to mirror built-in writes to their backend.

Key methods on the MemoryProvider interface:
- `initialize(session_id, **kwargs)` — called at agent startup
- `system_prompt_block()` — static text for system prompt
- `prefetch(query, session_id)` — recall context before each turn
- `sync_turn(user_content, assistant_content)` — persist each turn
- `get_tool_schemas()` — expose tools to the LLM
- `handle_tool_call(tool_name, args)` — dispatch tool calls
- `on_memory_write(action, target, content, metadata)` — mirror built-in memory writes
- `on_session_end(messages)` — end-of-session extraction
- `shutdown()` — clean exit

**Important:** Only ONE external memory provider can run at a time (the config enforces this). The cron-based sync approach avoids this limitation.

### 3. MCP tools

The MCP endpoint at `/mcp` exposes 50+ tools. Key categories:

**Memory tools** — `memory_save`, `memory_recall`, `memory_reflect`, `memory_profile`, `memory_confirm`, `memory_contradict`, `memory_save_lesson`, `memory_save_global`, `memory_note_to_agent`, `memory_forget_by_query`, `memory_extract_session`

**Agent tools** — `agent_context`, `agent_learn`, `agent_represent`

**VFS filesystem tools** — `fs_ls` (browse synapse:// hierarchy), `fs_tree` (tree view), `fs_mkdir` (create directory)

**Schema tools** — `schema_register` (YAML memory type schema), `schema_list`

**Skill tools** — `skills_extract` (from conversation), `skills_list`, `skills_use`

**Context tools** — `context_build` (tiered L0/L1/L2 pack), `dir_search` (directory-scoped search)

**System tools** — `nexus_status`, `sys_core_*`, `synapse_compat_*`

---

## OpenViking-Inspired Features (v2)

Synapse Memory now includes a **filesystem paradigm** ported from OpenViking:

### Virtual Filesystem (VFS)

Memories are organized under `synapse://` URIs instead of flat storage:

```
synapse://
  user/{agent_name}/
    memories/
      preferences/    — user preferences by topic
      entities/       — people, projects, concepts
      events/         — important occurrences
      patterns/       — reusable methods and workflows
      cases/          — specific problems and resolutions
      tools/          — tool usage experience
      skills/         — skill execution experience
      trajectories/   — end-to-end task traces
      experiences/    — distilled from trajectories
      lessons/        — lessons learned (auto-type)
      observations/   — observations (auto-type)
    resources/        — user-owned knowledge
    skills/           — callable skill definitions
    peers/{peer}/     — memories about interaction peers
    sessions/         — conversation records
    privacy/          — sensitive configuration snapshots
  resources/          — global shared resources
  agent/skills/       — shared agent skills
```

Every memory saved via `POST /v1/memory/save` now auto-generates a URI like `synapse://user/{agent}/memories/{type}/{content-hash}` with:
- **L0 (abstract)** — first sentence extracted on save
- **L1 (overview)** — paragraph summary (populated by extraction)
- **L2 (content)** — full content

### Tiered Context Building

Build context packs within a token budget using `GET /v1/search/context`:
- Loads L0 abstracts from all memory types (cheap scan)
- Loads L1 overviews of highest-importance types
- Loads L2 full content of top entries within budget

```bash
curl -s "http://100.93.75.87:7777/v1/search/context?agent_id=default&token_budget=2000"
```

Also level-specific: `GET /v1/search/levels?agent_id=X&level=0&memory_type=preferences`

### YAML Memory Type Schemas

Define custom memory types as YAML — auto-generates extraction prompts:

```yaml
name: bug_report
description: "Bug reports from sessions"
stage: user
fields:
  - name: title
    type: string
    required: true
  - name: severity
    type: string
    enum: [critical, high, medium, low]
    required: true
  - name: component
    type: string
extraction_prompt: Extract bug details from the conversation.
```

```bash
# Register
curl -X POST "http://100.93.75.87:7777/v1/schemas?agent_id=default" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"schema_yaml": "name: bug_report\n..."}'

# List
curl "http://100.93.75.87:7777/v1/schemas?agent_id=default"
```

### Skill Extraction

Extract reusable skills from conversation text — stored with trigger conditions, steps, and tags:

```bash
# Extract from conversation
curl -X POST "http://100.93.75.87:7777/v1/skills/extract?agent_id=default" \
  -d '{"conversation": "..."}'

# List skills
curl "http://100.93.75.87:7777/v1/skills"

# Record usage
curl -X POST "http://100.93.75.87:7777/v1/skills/{name}/use?agent_id=default"
```

### Directory-Scoped Search

Search within a specific `synapse://` directory:

```bash
curl -X POST "http://100.93.75.87:7777/v1/search/dir?query=connection+pool&directory_uri=synapse://user/default/memories/lessons&limit=10"
```

## API Endpoints

Base: `http://100.93.75.87:7777`

### Memory & Search
| Endpoint | Method | Purpose |
|---|---|---|
| `POST /v1/memory/save` | POST | Save a memory (auto-generates URI + L0 abstract) |
| `POST /v1/memory/batch` | POST | Batch save |
| `POST /v1/memory/recall` | POST | 4-way recall (vector, lexical, graph, temporal) |
| `GET /v1/memory/profile/{agent_id}` | GET | Full agent profile |
| `POST /v1/memory/{id}/confirm` | POST | Confirm a memory |
| `POST /v1/memory/{id}/contradict` | POST | Contradict a memory |
| `POST /v1/search/dir` | POST | Directory-scoped search |

### Virtual Filesystem
| Endpoint | Method | Purpose |
|---|---|---|
| `GET /v1/fs/ls?uri=synapse://...` | GET | List directory contents |
| `GET /v1/fs/tree?uri=synapse://...&depth=3` | GET | Show directory tree |
| `POST /v1/fs/mkdir?uri=synapse://...` | POST | Create directory node |
| `DELETE /v1/fs/rm?uri=...&recursive=true` | DELETE | Remove entry |
| `GET /v1/fs/stat?uri=synapse://...` | GET | Get URI metadata |
| `GET /v1/search/context?agent_id=X&token_budget=N` | GET | Build tiered context pack |
| `GET /v1/search/levels?agent_id=X&level=N` | GET | Level-specific retrieval |

### Schemas & Skills
| Endpoint | Method | Purpose |
|---|---|---|
| `POST /v1/schemas?agent_id=X` | POST | Register YAML memory schema |
| `GET /v1/schemas` | GET | List registered schemas |
| `GET /v1/schemas/{memory_type}` | GET | Get schema details |
| `DELETE /v1/schemas/{memory_type}` | DELETE | Remove schema |
| `POST /v1/skills/extract` | POST | Extract skills from conversation |
| `GET /v1/skills` | GET | List extracted skills |
| `GET /v1/skills/{name}` | GET | Get skill details |
| `POST /v1/skills/{name}/use` | POST | Record skill usage |
| `DELETE /v1/skills/{name}` | DELETE | Soft-delete a skill |

### Admin & Dashboard
| Endpoint | Method | Purpose |
|---|---|---|
| `GET /v1/health` | GET | Health check (all components) |
| `GET /v1/admin/metrics` | GET | Admin stats |
| `POST /v1/admin/consolidate` | POST | Trigger consolidation |
| `GET /v1/browse/memories` | GET | Browse memories |
| `GET /v1/browse/agents` | GET | Browse agents |
| `GET /v1/synapse/projects` | GET | List projects |

## Synapse Memory Source

The source lives on kubuntux:
- **Docker mount:** `/home/kubuntux/synapse-memory/` → `/app` in container
- **Service name:** `nexus-nexus-api-1` (Docker Compose)
- **Restart:** `docker restart nexus-nexus-api-1` (after edits)
- **GitHub:** `dylanmarriner/synapse-memory`

The `main.py` FastAPI app is at `/home/kubuntux/synapse-memory/app/main.py`.

### Killing Swagger UI

Swagger UI and ReDoc auto-serve on FastAPI by default. To disable:
```python
app = FastAPI(
    ...,
    docs_url=None,
    redoc_url=None,
)
```
Then restart the container: `docker restart nexus-nexus-api-1`

## Dashboard UI

The React+Vite dashboard runs at `:7778` as a separate Node.js process:
```
node /home/kubuntux/synapse-memory/dashboard/node_modules/.bin/vite --host 0.0.0.0 --port 7778
```

To build for production and serve from FastAPI instead:
```bash
cd /home/kubuntux/synapse-memory/dashboard
npm run build
# Then mount dist/ as static files in FastAPI
```

## Sync Script

See `scripts/sync-memory-to-nexus.py` — the no-agent cron script that diffs local memory files against Nexus and pushes new entries.

## Pitfalls

- **Docker volume path**: The actual source mount is `/home/kubuntux/synapse-memory/`, NOT `/media/kubuntux/DEVELOPMENT1/shared-memory/nexus/` or other stale backup paths. Always check with `docker inspect` to find the real mount.
- **Gateway Dependency**: Cron jobs are dispatched by the Hermes gateway. Without it (`hermes gateway status`), cron won't fire. On fresh installs, the gateway must be started first.
- **Content dedup is exact string match**: Slight differences in phrasing between machines = duplicates in Nexus.
- **Additive-only sync**: Removing local memory entries does NOT remove them from Nexus. The script is additive-only by design.
- **One provider limit**: Hermes allows only one external memory provider. The cron bypasses this but doesn't replace provider-level features like prefetching.
- **Swagger is not a dashboard**: FastAPI's auto-generated Swagger/ReDoc docs are API documentation, not a custom dashboard. They can be killed with `docs_url=None` if you run a separate dashboard.
- **Never declare tools broken as a lesson**: Check admin metrics and direct API first. If the MCP tools seem wrong, verify via REST API before concluding.
- **Old memories lack URIs**: Pre-existing memories have `uri=NULL`. They still work for search and recall but won't appear in VFS directory listings. Backfill by re-ingesting or leaving them as flat records.
- **normalize_uri preserves `://`**: The `normalize_uri()` function must NOT collapse `://` to `:/`. The implementation splits on `://` and only collapses path segments after it, else all `synapse://` URIs become `synapse:/`.
- **is_active column needs explicit TRUE**: The `is_active` column in `memory_schemas` and `skills` tables has a Python-level default but no server-side DEFAULT. Always INSERT `is_active = TRUE` explicitly, or use `ALTER TABLE ... ALTER COLUMN is_active SET DEFAULT true`.
- **Body params vs query params on POST endpoints**: Endpoints like `POST /v1/schemas` and `POST /v1/skills/extract` take `agent_id` as a query parameter and data fields (`schema_yaml`, `conversation`) from the request body. Don't pass large strings as query params — they truncate silently.
- **URI routing with curl**: Use `-G --data-urlencode "uri=..."` when passing synapse:// URIs as query params to curl, otherwise `://` can confuse URL parsing.
