---
name: memory-system-integration
description: "Merge one memory/backend system's feature set into another (e.g. Synapse → Nexus). Covers schema compat, REST route building, MCP tools, Docker/Postgres debugging."
version: 1.0.0
author: agent
---

# Memory System Integration

Pattern for taking all features from one memory/backend system and integrating them into another Postgres-based system.

## Trigger Conditions

Use when the user asks to:
- "integrate X's features into Y"
- "merge all of X's tools into Y"
- "make Y have everything X had"

## Workflow

### 1. Audit Source Features

List ALL source tools and tables. The user means **everything** — not just memories.

Source tables to look for:
```
projects     — project/workspace registry
memories     — memory store (kind, title, content, tags, importance)
files        — indexed file metadata (sha256, symbols, language)
events       — audit log (actor, action, detail)
tenants      — multi-tenancy
devices      — device registry
sync_events  — multi-node sync
```

### 2. Create Compat Tables in Target

For each source table not in the target:
- Add SQLAlchemy model to schema.py
- Add migration SQL to main.py's `_run_migrations()`
- **CRITICAL**: Use `gen_random_uuid()` in raw SQL INSERTs (NOT Python-level `default=uuid.uuid4` which doesn't apply at the DB level)

```sql
INSERT INTO projects (id, key, name, created_at, updated_at)
VALUES (gen_random_uuid(), :key, :name, :now, :now)
```

### 3. Build REST Routes

Create a `routers/synapse.py` (or compat named) file with FastAPI routes for each compat tool.

**FastAPI body parsing pitfall**: When a route has multiple simple-type parameters AND a `Depends(get_db)`, FastAPI requires the body to be a single `dict` parameter:

```python
# WRONG — FastAPI can't parse this
@router.post("/remember")
async def remember(project_key: str, kind: str = "note", content: str = "", db=Depends(get_db)):

# RIGHT — single body dict
@router.post("/remember")
async def remember(project_key: str, body: dict, db=Depends(get_db)):
    kind = body.get("kind", "note")
    content = body.get("content", "")
```

### 4. Add MCP Tools

Register new tools in the TOOLS list and add dispatch handlers in mcp.py.

### 5. Docker Volume Mounts

If the target uses `build: .` (baked image), add a volume mount for live code reload:

```yaml
volumes:
  - .:/app:ro
```

This avoids needing to rebuild the image every time.

### 6. PostgreSQL Type Handling

When passing Python lists/json to PostgreSQL via SQLAlchemy text():

```python
# WRONG — can't determine type
jsonb_build_object('tags', :tags, ...)

# RIGHT — pre-serialize + CAST
metadata_val = json.dumps({"tags": tag_list, ...})
CAST(:metadata AS jsonb)
```

### 7. Synapse Memory "Adopted Patterns" Integration

When merging features **into** Synapse Memory (rather than from it), use the **adopted patterns** convention in `app/adopted/`. This is how Synapse Memory absorbs external ideas — cleanly, without touching existing code.

#### Architecture

Every adopted module lives in `app/adopted/<module_name>.py` and follows these rules:
- **Self-contained**. Each module is independently importable, no cross-deps between adopted modules.
- **Additive**. Patterns extend existing Nexus code via hooks/overrides — they never modify existing code.
- **No branding**. The source project's name, copyright, and branding are never recorded in the code. Docstrings describe the pattern, not where it came from.
- **Safe-by-default**. Anything that changes recall, extraction, or persistence is gated behind an import-or-fail pattern.

#### Registration

In `app/adopted/__init__.py`:

```python
# 1. Import the module
from app.adopted import (
    existing_module,
    your_new_module,
)

# 2. Add a REGISTRY entry
REGISTRY: List[AdoptedModule] = [
    # ... existing entries ...
    AdoptedModule(
        name="your_pattern_name",
        what="One-sentence description of what it does.",
        module="app.adopted.your_new_module",
        feature_flag="ADOPTED_YOUR_FEATURE_ENABLED",
    ),
]

# 3. Add to __all__
__all__ = [
    # ... existing exports ...
    "your_new_module",
]
```

#### REST Endpoints

Add routes to `app/routers/adopted.py` (the existing adopted router already has prefix `/v1/adopted`):

```python
class YourRequest(BaseModel):
    query: str
    param1: str = "default"


@router.post("/your-endpoint", response_model=YourResponse)
async def your_handler(body: YourRequest):
    from app.adopted.your_new_module import some_function
    result = await some_function(body.query, body.param1)
    return YourResponse(answer=result)
```

#### MCP Tool Registration

In `app/mcp.py`:

1. **Add tool schema** to the `TOOLS` list (before the closing `]`):
```python
{
    "name": "adopted_your_tool",
    "description": "What the tool does.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Description"},
        },
        "required": ["query"],
    },
},
```

2. **Add dispatch handler** in `_dispatch()` before the `else:` raise:
```python
elif tool == "adopted_your_tool":
    r = await client.post(f"{base}/v1/adopted/your-endpoint", json={
        "query": args.get("query", ""),
        "param1": args.get("param1", "default"),
    }, headers=headers, timeout=120)
    r.raise_for_status()
    d = r.json()
    return d.get("answer", "")
```

**Timeout note**: Agentic reasoning tools (dialectic, reflection) need longer timeouts (120s+). Simple lookups need 30-60s.

#### Background Tasks

If the module has a background/service loop, wire it into `main.py`'s `lifespan` function:

```python
# Startup (add after existing task starts)
try:
    from app.adopted.your_module import start_service
    start_service()
    log.info("Your service started")
except Exception as e:
    log.warning("Your service not started: %s", e)

# Shutdown (add to the cleanup block, after yield)
try:
    from app.adopted.your_module import stop_service
    await stop_service()
except Exception:
    pass
```

The module itself exposes `start_service()` / `stop_service()` using asyncio patterns:
```python
import asyncio

_task: asyncio.Task | None = None

def start_service():
    global _task
    if _task is not None and not _task.done():
        return
    _task = asyncio.create_task(_loop())

async def stop_service():
    global _task
    if _task and not _task.done():
        _task.cancel()
        try: await _task
        except asyncio.CancelledError: pass
        _task = None
```

### 8. Inline HTML Dashboard Extension

Synapse Memory serves its dashboard from an inline `_DASHBOARD_HTML` string in `app/main.py`. To add new tabs/views:

1. **CSS** — Add new classes to the `<style>` block. Keep selectors compact (no newlines inside braces since the whole style block is one HTML attribute).
2. **Nav** — Add nav buttons as `<button data-tab="yourtag">` in the same line as existing nav buttons.
3. **Tab sections** — Add `<section id="tab-yourtag" class="tabs ...">` before the closing `</main>`.
4. **JS tabNames** — Add your tag to the `tabNames` dict.
5. **JS switchTab** — Add `if(tab==='yourtag')loadYourTab();` in the switchTab function.
6. **JS functions** — Add async fetch functions that call Synapse's REST API at `/v1/*`.

Hindsight's control-plane (at `/tmp/hindsight/hindsight-control-plane/src/components/`) is a solid reference for component patterns — think-view, data-view, memory-detail-modal, entities-view for UX patterns.

### 9. Verify All Endpoints

Test every endpoint — health, register, CRUD, search, context, events. The user runs `curl` commands to verify.

## Files to Modify

| File | What |
|------|------|
| `app/models/schema.py` | Add ORM models for new tables |
| `app/main.py` | Add import + `include_router`, add migration SQL |
| `app/routers/` | Create compat router file |
| `app/mcp.py` | Add tool schemas + dispatch handlers |
| `app/adopted/<name>.py` | New self-contained module (adopted patterns only) |
| `app/adopted/__init__.py` | Import + REGISTRY + __all__ (adopted patterns only) |
| `app/routers/adopted.py` | REST endpoints (adopted patterns only) |
| `docker-compose.yml` | Add volume mounts for live code |

## Reference Files

- `references/honcho-hindsight-merge.md` — Exact details of the Honcho dialectic/dreamer and Hindsight dashboard UI merges into Synapse Memory.

## Pitfalls

- **UUID defaults**: Python `default=uuid.uuid4` doesn't apply at DB level. Use `gen_random_uuid()` in raw SQL. This applies to ALL tables with UUID IDs — not just the one you're thinking about right now. Check every INSERT.
- **JSONB params**: Pre-serialize to JSON string in Python, use `CAST(:param AS jsonb)` in SQL. The ON CONFLICT UPDATE params need the SAME json.dumps() treatment — it's easy to fix the INSERT value but miss the UPDATE clause value (e.g. `symbols2` param in file_index upsert).
- **FastAPI body**: Multiple positional params + Depends = FastAPI chokes. Use a single `dict` body param. After refactoring signatures, find ALL internal callers of that function — they now pass positional args that the new dict body won't accept.
- **Docker build**: `build: .` bakes code into image. Add `volumes: - .:/app:ro` for live reload. But volume mounts don't trigger uvicorn hot-reload — you must `docker restart nexus-nexus-api-1` to clear Python's in-memory cached modules.
- **PyCache**: After code changes in volume mounts, `docker exec nexus-nexus-api-1 find /app -name __pycache__ -type d -exec rm -rf {} +` clears bytecode cache. Then restart.
- **PyCache at import time**: Even with volume mounts, the container caches compiled .pyc from the BUILD time. A `docker restart` after file edits is required to pick up changes — `docker compose up -d` alone may not recreate the container.
- **ORMs vs raw SQL**: Raw SQL INSERTs must include ALL non-null columns (including `id`). The ORM model may have `default=uuid.uuid4` at the Python level, but the DB table has a NOT NULL constraint and no DEFAULT.
- **events table inserts**: The events table also needs `gen_random_uuid()` in the INSERT. It's easy to fix the projects table and forget that events has the same UUID id column.
- **file_index symbols**: When inserting into file_index, the `symbols` field is a Python list. Pass it as `json.dumps(symbols)` in BOTH the INSERT values AND the ON CONFLICT UPDATE clause (`symbols2`).
- **Error reading**: When debugging 500 errors from FastAPI+asyncpg, `docker logs nexus-nexus-api-1 | grep -A5 'Error\|error\|violates\|Indeterminate\|type of parameter'` shows the actual SQL and the parameter that broke.

## User Preference

This user (Dylan) operates by: NO narration of what you're about to do. NO verbose step-by-step explanations. Deliver the result, the command, or the fix. If something fails, state the next actionable step concisely. If it works, say what worked. No apologies, no course-correction narration, no "first I will" / "now let's" / "as we discussed".
