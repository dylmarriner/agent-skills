---
name: docker-fastapi-patterns
description: Patterns for developing FastAPI apps deployed via Docker Compose — volume mounts, SQLAlchemy raw SQL pitfalls, template handling, and MCP router integration.
---

# Docker FastAPI Development Patterns

## Volume Mounting for Live Dev

When the Dockerfile does `COPY . .` to bake source into the image, host filesystem edits have NO effect on the running container. Fix by adding a volume mount:

```yaml
services:
  api:
    build: .
    volumes:
      - .:/app:ro    # Host source overrides baked-in copy
    ports:
      - "7777:7777"
```

After adding the mount, `docker compose up -d` to recreate. No rebuild needed for subsequent edits.

### Trap: `:ro` mount blocks live code fixes

If a volume is `:ro` (read-only), host source changes are NOT visible inside the container even after `docker restart`. The container reads the stale baked-in image copy.

**Hotfix (without rebuild):** temporarily switch to `:rw`, restart, apply fix, verify, then revert to `:ro`:

```bash
sed -i 's|.:/app:ro|.:/app:rw|' docker-compose.yml
docker compose up -d <service>
# verify fix took effect
docker exec <container> grep 'pattern' /app/path/to/file.py
# restore read-only mount
sed -i 's|.:/app:rw|.:/app:ro|' docker-compose.yml
```

**Permanent fix:** rebuild the image instead — `docker compose up -d --build <service>`.

Keep `:ro` for production — it catches accidental in-container writes.

## SQLAlchemy ORM vs Raw SQL UUID

ORM models use `default=uuid.uuid4` (Python-level), NOT a database default. When writing raw `text()` SQL INSERTs to ORM-managed tables, you MUST include `gen_random_uuid()` for the `id` column:

```python
# WRONG — fails with NotNullViolation
await db.execute(text("INSERT INTO projects (key, name) VALUES (:key, :name)"))

# CORRECT
await db.execute(text("INSERT INTO projects (id, key, name) VALUES (gen_random_uuid(), :key, :name)"))
```

This applies to ALL tables created by `Base.metadata.create_all()` with UUID PKs. Search every raw SQL INSERT in the codebase for this when adding raw SQL to an ORM app.

## JSONB Parameter Typing with asyncpg

asyncpg can't infer the type of `list` or `dict` parameters for JSONB columns. Pass them as pre-serialized JSON strings:

```python
# WRONG — asyncpg.DataError: list has no attribute 'encode'
tags = ["gotcha", "synapse-project:key"]
await db.execute(text("...jsonb_build_object('tags', :tags, ...)"), {"tags": tags})

# CORRECT
await db.execute(text("...CAST(:metadata AS jsonb)..."), {"metadata": json.dumps({"tags": tags, ...})})
```

Always `json.dumps()` any list/dict before passing to a JSONB parameter. Use `CAST(:param AS jsonb)` in the SQL.

## HTML Templates: Files Not Embedded Strings

Embedding 20KB+ HTML in Python triple-quoted strings causes escaping nightmares with nested quotes and `"""` in the content. Always use template files:

```python
# main.py
import pathlib
_TEMPLATE = pathlib.Path(__file__).parent / "templates"
_dashboard_html = (_TEMPLATE / "dashboard.html").read_text()

@app.get("/")
async def dashboard():
    html = _dashboard_html.replace("__TOKEN__", generate_token())
    return HTMLResponse(content=html)
```

Create `app/templates/` directory and copy the HTML there.

## Adding FastAPI Routers to Docker Apps

1. Create `app/routers/new_router.py` with `router = APIRouter()`
2. Add `from app.routers.new_router import router as new_router` in main.py imports
3. Add `app.include_router(new_router, prefix="/v1/new", ...)` 
4. If using volume mounts: restart container (`docker restart`)
5. If not using volume mounts: rebuild Docker image

### Sync Check
After adding a router, verify it appears in the OpenAPI:
```bash
curl http://host:port/openapi.json | jq '.paths | keys'
```

## MCP Tool Plugin Pattern

Adding tools to the MCP server (mcp.py):
1. Add tool schemas to the `TOOLS` list with full inputSchema
2. Add dispatch handlers in `_dispatch()` using `elif tool == "name":`
3. Ensure the final `raise HTTPException` is inside the function (correct indentation)
4. Tools proxy to REST routes via `client.post(f"{base}/v1/...", ...)`
5. After edits, check with `curl -X POST /mcp -d '{"jsonrpc":"2.0","id":"1","method":"tools/list","params":{}}'`

### Pitfall: Internal routing in Docker — don't use `request.base_url`

When `_dispatch` builds the base URL from the incoming request, it resolves to the caller's external IP (e.g. a Tailscale IP). From inside Docker, that IP is NOT routable — the container can't reach back through the host's port mapping to itself.

**Wrong — times out when called from outside the container:**
```python
base = str(request.base_url).rstrip("/")
async with httpx.AsyncClient(timeout=30.0) as client:
    r = await client.get(f"{base}/health")
```

**Correct — hardcode the loopback address:**
```python
base = "http://localhost:7777"
async with httpx.AsyncClient(timeout=30.0) as client:
    r = await client.get(f"{base}/health")
```

Alternative: use the Docker Compose service name (`http://nexus-api:7777`) if on the same Docker network.

### Pitfall: `.env` vs running container env

`docker exec <container> env | grep KEY` reveals the actual env — which may differ from the `.env` file (stale file, explicit overrides at `docker run`). Always verify from inside the container.

### Debugging MCP tool call timeouts

When `tools/list` works but `tools/call` times out:
1. Test the tool from **inside** the container first — if it works there, it's a routing issue.
2. Check `docker logs <container> | grep ERROR` for the root cause.
3. Verify the internal REST route independently before blaming the MCP dispatch.

## Dashboard Auth Pattern

For dashboards that need browser access without Bearer tokens:
- Remove `_verify_key()` from the dashboard GET route
- Generate a scoped HMAC token on page load
- Embed the token in the HTML: `const TOKEN = "__NEXUS_TOKEN__";`
- JavaScript uses the embedded token for API calls
- The HMAC token validates against `_verify_dashboard_token()` with time-windowed keys
