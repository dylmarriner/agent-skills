---
name: prototype-to-production-api
description: "Transform AI-generated/prototype code skeletons into production-grade FastAPI applications with proper async patterns, validation, auth, Docker, and comprehensive tests."
version: 1.0.0
---

# Prototype-to-Production API

Turn loose prototype/generated code into a production-grade FastAPI application. Covers the full pipeline: audit → organize → build → deploy → test.

## When to Use

- User hands you a directory of loose generated files (DeepSeek, Claude, GPT artifacts)
- User wants a "working" API from stub/simulation code
- User wants production-grade code with no placeholders, mock data, or TODOs
- Auditing code for placeholder patterns before shipping

## Step 1: Audit the Prototype

Run an audit script to detect placeholder/simulation indicators before touching anything:

```python
# Run this in execute_code to scan all .py files
bad_patterns = {
    'sleep_sim': r'time\.sleep\(',
    'placeholder': r'placeholder|stub|mock|fake|dummy',
    'NotImplementedError': NotImplementedError,
    'todo': r'TODO|FIXME|HACK|XXX',
    'pass_body': r'^\s+pass\s*$',
    'rfc1918': r'(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})',
    'static_return': r"return\s*\{[^}]*'status'[^}]*\}",
}
```

### Common prototype indicators:
- **`time.sleep()`** — simulating work instead of doing it (HIGH severity)
- **Static dict returns** — `return {"status": "compromised"}` with no real logic
- **RFC1918 IPs** — hardcoded 10.x.x.x or 192.168.x.x addresses, never real infrastructure
- **`NotImplementedError`** — unimplemented stubs
- **Print-based progress** — printing step names and sleeping rather than executing operations
- **Comments with "placeholder", "simulate", "demo"**

## Step 2: Reorganize into Project Structure

1. Classify each file by content (classes, imports, purpose)
2. Remove `(1)` duplicate files
3. Create directories: `backend/api/`, `backend/models/`, `backend/schemas/`, `backend/services/`, `backend/auth/`, `config/`, `scripts/`, `tests/`
4. Rename to meaningful names based on class names, not the generated hash names
5. Delete original generated files after copying

## Step 3: Build Production Infrastructure

### Core files to create:

| File | Purpose |
|------|---------|
| `pyproject.toml` | Project metadata, deps, ruff/mypy config |
| `.env` / `.env.example` | pydantic-settings config |
| `backend/config.py` | Pydantic BaseSettings from .env |
| `backend/database.py` | Async SQLAlchemy engine + session factory |
| `backend/models/*.py` | SQLAlchemy 2.0 models (mapped_column style) |
| `backend/schemas/*.py` | Pydantic v2 request/response models |
| `backend/auth/jwt.py` | JWT creation + verification |
| `backend/services/*.py` | Business logic layer (routers never touch ORM) |
| `backend/api/*.py` | FastAPI APIRouter endpoints |
| `backend/main.py` | App entry: lifespan, CORS, middleware, routers |
| `backend/logging_config.py` | structlog configuration |

### Key patterns:
- **Async everywhere**: `async def`, `await db.execute()`, `AsyncSession`
- **Service isolation**: routers never call ORM directly
- **Pydantic validation**: schemas enforce field patterns on input
- **Target existence checks**: validate FK targets exist before creating dependent records (prevents 500s)
- **IntegrityError handler**: catch `sqlalchemy.exc.IntegrityError` → return 409, not 500

## Step 4: Common Fix Patterns (from real testing)

| Issue | Fix |
|-------|-----|
| FK violation → 500 | Add target existence check in router before service call |
| Valid direction rejected | Accept both `inbound|outbound` AND `incoming|outgoing` |
| `start_time` crashes on None | Make it Optional, default to `datetime.utcnow()` |
| Location coords nullable | Make `latitude`/`longitude` required (float, not Optional) |
| Duplicate unique field → 500 | Add `IntegrityError` exception handler → 409 |
| Old DB baked in Docker image | Delete `data/` dir from project root before building |
| Docker DNS broken | Set `{"dns": ["8.8.8.8", "1.1.1.1"]}` in `/etc/docker/daemon.json` |

## Step 5: Docker Deployment

```
docker-compose.yaml → single API service (dev: SQLite, prod: PostgreSQL)
Dockerfile → python:3.12-slim, pip install deps, uvicorn
```

Key compose patterns:
- `dns: [8.8.8.8, 1.1.1.1]` when systemd-resolved blocks container DNS
- `restart: unless-stopped` + `healthcheck` with Python URL check
- Named volume for SQLite persistence
- Delete `data/` dir from project root before `docker compose build` to prevent stale DB baking into image

## Step 6: Comprehensive API Testing

Test EVERY endpoint with a script:
1. **Healthy endpoints** — health check, auth flows
2. **Happy path CRUD** — create, read, update, delete for every resource
3. **Edge cases** — missing required fields → 422, bad UUID → 422/404, non-existent IDs → 404
4. **Business logic** — duplicate unique fields → 409, FK validation → 404, time-range filters
5. **State management** — confirm deletes work (GET after DELETE → 404)
6. **OpenAPI/Swagger** — verify generated docs contain all paths
7. **Metrics** — Prometheus /metrics returns 200
8. **Clean DB verification** — test that `docker compose down -v && up -d` produces empty state

## Verification: Zero Placeholder Check

After building, scan all production files for:
- No `time.sleep()` in service/api code (only in middleware like request logging)
- No `NotImplementedError` or `pass` as function body
- No `return {"status": "..."}` hardcoded dicts
- No `print()` in production code (use structlog instead)
- No `TODO`, `FIXME`, `HACK`, `XXX` comments
- No `# placeholder`, `# stub`, `# simplified`, `# for now` comments
- `return None` is acceptable for "not found" patterns; `return True/False` is acceptable for delete status
