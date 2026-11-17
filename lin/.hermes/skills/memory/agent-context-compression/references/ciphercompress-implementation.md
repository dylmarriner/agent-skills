# CipherCompress Implementation Reference

The 6 enhancements live in `~/.hermes/plugins/headroom_retrieve/` as three files:

| File | Purpose |
|------|---------|
| `ciphercompress.py` | Engine: all 6 algorithms |
| `tools_ciphercompress.py` | Hermes tool registrations |
| `agentmemory_bridge.py` | Agentmemory push/search bridge |
| `headroom_agentmemory_sync.py` | Cron-ready sync daemon |

## agentmemory REST API Endpoints

Discovered through real interaction with agentmemory v0.9.27:

| Endpoint | Method | Body Key | Purpose |
|----------|--------|----------|---------|
| `/agentmemory/remember` | POST | `content` (NOT `memory`) | Create a fact memory. Returns 201. |
| `/agentmemory/search` | POST | `query` | Hybrid search (BM25 + vector). Returns `results[]`. |
| `/agentmemory/memories` | GET | — | List all memories. Returns `{memories: [...]}`. |
| `/agentmemory/health` | GET | — | Health check. Returns circuit breaker state. |
| `/agentmemory/forget` | POST | `id` | Delete a memory by ID. |

**CRITICAL:** The field is `content`, NOT `memory`. Using `memory` as the key
returns 400 `"content is required"`.

## Response Shapes

### remember (201)
```json
{
  "memory": {
    "id": "mem_mqc0lxj0_f883ce380b95",
    "content": "...",
    "title": "...",
    "type": "fact",
    "strength": 7,
    "concepts": [],
    "sessionIds": [],
    "sourceObservationIds": [],
    "createdAt": "2026-06-13T07:09:28.187Z"
  }
}
```

### search (200)
```json
{
  "format": "full",
  "results": [
    {
      "observation": {
        "id": "mem_...",
        "content": "...",
        "facts": ["..."],
        "narrative": "...",
        "importance": 7,
        "createdAt": "..."
      }
    }
  ]
}
```

## Relevance Scoring Algorithm

Used by `cipher_compress` to decide compression level:

1. Hash content (first 1000 bytes) with MD5 — cache result
2. If cached, return stored score
3. If task_context provided, search agentmemory for it
4. For each result, check word overlap with content
5. Score = min(1.0, 0.3 + (overlap_count / max_results) * 0.7)
6. Default (no context or no results): 0.5

Compression decisions by score:
| Score Range | Compression | Behavior |
|-------------|-------------|----------|
| < 0.2 | Aggressive | First 2 + last 2 lines only |
| 0.2 – 0.5 | Moderate | First 3 + error lines + last 3 |
| 0.5 – 0.8 | Light | Preserve most, add relevance marker |
| > 0.8 | None | Preserve verbatim |

## Structural Compressor Schema Learner

Uses SQLite at `~/.ciphercompress/schemas.db` with two tables:

```sql
CREATE TABLE schemas (
    schema_hash TEXT PRIMARY KEY,
    schema_json TEXT NOT NULL,
    first_seen REAL NOT NULL,
    last_seen REAL NOT NULL,
    hit_count INTEGER DEFAULT 1
);

CREATE TABLE deltas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schema_hash TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    delta_json TEXT NOT NULL,
    seen_at REAL NOT NULL
);
```

Schema extraction detects types: dict, array, int, float, string, bool, text,
null. Arrays are summarized by most common element type with a depth limit
of 50 elements for union computation.

## Tool Schemas (Hermes Plugin Format)

All tools use `ctx.register_tool()` with:
```python
ctx.register_tool(
    name="tool_name",
    toolset="headroom",
    schema={...},         # JSON Schema for parameters
    handler=function,      # Takes (args, **kw) -> str
    emoji="emoji",
)
```

The handler must return a JSON string. Tool errors should be returned as
`json.dumps({"error": "message"})` rather than raising exceptions.

## Known Hermes Plugin API

Two plugin registration patterns exist:

### Pattern 1: `register(ctx)` with hooks
```python
def register(ctx):
    ctx.register_hook("pre_tool_call", handler)
```
Used by rtk-rewrite plugin.

### Pattern 2: `register(ctx)` with tools
```python
def register(ctx):
    ctx.register_tool(name=..., toolset=..., schema=..., handler=..., emoji=...)
```
Used by headroom_retrieve and CipherCompress plugins.

The plugin loader scans for a `register` function in `__init__.py`.
Multiple `register` calls can be chained in the same function to register
multiple tools.
