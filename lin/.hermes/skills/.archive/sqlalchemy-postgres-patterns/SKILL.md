---
name: sqlalchemy-postgres-patterns
description: PostgreSQL + SQLAlchemy non-obvious gotchas — UUID PKs in raw SQL, JSONB parameter encoding, FastAPI body dict for flexible endpoints, Docker volume mounts for live code.
---

# SQLAlchemy + PostgreSQL Patterns

UUID PK defaults, JSONB parameter passing, FastAPI body handling, and Docker live-reload patterns discovered while building Nexus (a FastAPI+PostgreSQL+Redis agent memory server).

## UUID Primary Keys with Raw SQL Text()

SQLAlchemy ORM `default=uuid.uuid4()` is Python-level only. Raw `text()` INSERTs
will NOT auto-generate the id:

```
NOT NULL violation: null value in column "id"
```

**Fix — always use `gen_random_uuid()` in raw SQL:**
```sql
INSERT INTO table (id, col1, col2)
VALUES (gen_random_uuid(), :v1, :v2)
```

Apply to every raw SQL INSERT on tables with UUID PKs (projects, file_index, events, etc.).

## JSONB Parameter Encoding with text()

Python lists/dicts cannot be passed as parameters to JSONB columns via `text()`.
asyncpg raises: `list object has no attribute 'encode'`

**Fix — three-part pattern:**
1. Serialize: `json.dumps(your_list_or_dict)`
2. Cast in SQL: `CAST(:param AS jsonb)` or `:param::jsonb`
3. Pass the resulting string

For complex metadata, pre-build the full dict and pass as a single param.

## FastAPI POST Body: Use Dict Not Individual Params

For flexible endpoints, accept `body: dict` instead of individual params to
avoid FastAPI type-checking conflicts:

```python
@router.post("/{key}/action")
async def handler(key: str, body: dict, db=Depends(get_db)):
    kind = body.get("kind", "default")
```

## Docker Volume Mounts for Live Code

Add to compose to avoid rebuilds on Python changes:
```yaml
services:
  api:
    build: .
    volumes:
      - .:/app:ro
```

Restart container for new imports. Rebuild only for pip packages.
