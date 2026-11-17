---
name: fastapi-mcp-server-extension
description: "Add new tools, REST routes, and database tables to a FastAPI-based MCP memory server (like Nexus)."
version: 1.0.0
author: agent
created_by: agent
---

# FastAPI MCP Server Extension

Pattern for extending a FastAPI MCP memory server (Nexus, Synapse, etc.) with
new tools, REST routes, and database tables.

## When to Load

- User asks you to add new features/tools to an existing MCP memory server.
- User asks to port functionality from one memory system into another.
- User asks to add new REST API endpoints or database tables to a FastAPI MCP service.

## Architecture

A FastAPI MCP server has four layers you touch:

```
MCP Client → MCP Tool Schema (TOOLS list in mcp.py)
                ↓
           MCP Dispatch (_dispatch() in mcp.py) — proxies to REST routes
                ↓
           FastAPI Router (routers/*.py) — business logic + DB access
                ↓
           SQLAlchemy Models (models/schema.py) + Migration (main.py startup)
```

## Step-by-Step

### 1. Add database models

Add new SQLAlchemy models to `app/models/schema.py`. Keep them simple:

```python
class Project(Base):
    __tablename__ = "projects"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    # ... other columns
```

### 2. Add migration SQL

The MCP server runs migrations on startup in `main.py` → `_run_migrations()`.
Add `CREATE TABLE IF NOT EXISTS` blocks there so new tables are created on next
container start. Also add indexes.

### 3. Create FastAPI router

Create `app/routers/<name>.py` with:

```python
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db

router = APIRouter()

@router.post("/resource")
async def my_endpoint(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(text("SELECT ..."), params)
    await db.commit()
    return {...}
```

### 4. Register the router

In `app/main.py`:

```python
from app.routers.<name> import router as <name>_router

# In the app setup section:
app.include_router(<name>_router, prefix="/v1/<name>", tags=["<name>"], dependencies=[Depends(_verify_key)])
```

### 5. Add MCP tool schemas

In `app/mcp.py`, add tool definitions to the `TOOLS` list:

```python
{
    "name": "my_tool",
    "description": "What it does. Keep this short but descriptive — agents rely on it.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "param": {"type": "string"},
        },
        "required": ["param"],
    },
},
```

Tools are dispatched by name — an `elif` branch in `_dispatch()`.

### 6. Add MCP dispatch handler

In `_dispatch()` in `app/mcp.py`, add an `elif` block before the final
`raise HTTPException`:

```python
elif tool == "my_tool":
    r = await client.post(f"{base}/v1/<prefix>/endpoint", json={...}, headers=headers)
    r.raise_for_status()
    return json.dumps(r.json(), indent=2)
```

The `_dispatch` function receives:
- `tool` — the tool name string
- `args` — the input arguments dict
- `request` — the FastAPI request object (use to get base_url + auth)

Always forward the `Authorization` header from the incoming request to REST
endpoints inside the same server:

```python
headers = {"Content-Type": "application/json"}
if auth := request.headers.get("Authorization"):
    headers["Authorization"] = auth
```

### 7. Restart (Docker)

**CRITICAL**: if the Dockerfile uses `COPY . .` (source baked into image),
a simple container restart is NOT enough — you must rebuild:

```bash
docker compose build <service-name>
docker compose up -d <service-name>
```

Verify with health check before testing: `curl <server>/health`.

To avoid this in development, add a volume mount to docker-compose.yml:
```yaml
services:
  my-api:
    volumes:
      - .:/app:ro
```

### 8. Test

Test via REST first (debugs faster), then MCP:

```bash
# REST test
curl -s http://<server>:<port>/v1/<prefix>/endpoint \
  -H "Authorization: Bearer $SECRET" \
  -H "Content-Type: application/json" \
  -d '{"param":"value"}' | python3 -m json.tool

# MCP test
hermes mcp test <server-name>
```

## Pitfalls

- **Restart ≠ rebuild**: `docker compose restart` reuses the old image. Always `build && up -d` after code changes when the Dockerfile uses `COPY . .`.
- **MCP dispatch exceptions**: The `_dispatch()` async function catches `Exception` and returns MCP error codes. Log `e` to see what failed: `log.error("Tool %s failed: %s", tool, e)`.
- **DB session lifecycle**: Each async route needs `Depends(get_db)` for a fresh session. Batch operations should commit in batches, not per-row.
- **401 on MCP after restart**: MCP client sessions may cache auth. Reload `/reload-mcp` in Hermes or restart the agent session.
- **Don't break prompt caching**: The MCP tool list is part of the LLM prompt. Adding tools is safe (new items appended), but changing existing tool names/schemas invalidates cached prompts.

## Signals That Trigger This Skill

- "add this feature to the MCP server"
- "port X from system Y into nexus/synapse"
- "integrate X's tools into the memory server"
- "add a route for /v1/..."
- "need a new tool that does X"
