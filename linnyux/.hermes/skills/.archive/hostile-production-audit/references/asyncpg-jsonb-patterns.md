# asyncpg / SQLAlchemy JSONB Serialization Patterns

## The Problem

When using raw SQL (via `text()`) with asyncpg driver in SQLAlchemy,
Python `list`/`dict` values passed to JSONB columns cause cryptic errors:

```
IndeterminateDatatypeError: could not determine data type of parameter $N
DataError: invalid input for query argument $N ('list' object has no attribute 'encode')
```

## Root Cause

SQLAlchemy's asyncpg driver cannot infer the Postgres type for a Python
`list` or `dict` when used with `jsonb_build_object()` or a bare JSONB
column INSERT. The driver expects a `str` that can be CAST to JSONB.

## The Fix

**Before (BROKEN):**
```python
await db.execute(
    text("""
        INSERT INTO memories (id, metadata)
        VALUES (gen_random_uuid(), jsonb_build_object('tags', :tags, 'source', :source))
    """),
    {"tags": ["gotcha", "project:test"], "source": "agent"},
)
```

**After (WORKING):**
```python
import json
metadata_val = json.dumps({
    "tags": ["gotcha", "project:test"],
    "source": "agent",
})
await db.execute(
    text("""
        INSERT INTO memories (id, metadata)
        VALUES (gen_random_uuid(), CAST(:metadata AS jsonb))
    """),
    {"metadata": metadata_val},
)
```

## Key Rules

1. **Always `json.dumps()`** Python lists/dicts before passing as JSONB params
2. **Always `CAST(:param AS jsonb)`** in the SQL template — `:param::jsonb` syntax is not supported by asyncpg parameterized queries
3. **Never use `jsonb_build_object()`** with parameterized placeholders when using asyncpg — it produces `IndeterminateDatatypeError`. Build the full JSON in Python instead
4. **UUID primary keys** with `default=uuid.uuid4` in SQLAlchemy ORM models do NOT create a database-level default. Raw INSERTs without `id` + `gen_random_uuid()` will get `NotNullViolationError`

## Affected Patterns

- `INSERT INTO ... VALUES (CAST(:param AS jsonb))`
- `UPDATE ... SET col = CAST(:param AS jsonb)`
- `jsonb_build_object('key', :val)` — DO NOT USE with asyncpg
- `ON CONFLICT ... DO UPDATE SET col = CAST(:param AS jsonb)`

## Tested With

- asyncpg 0.29+
- SQLAlchemy 2.0+
- PostgreSQL 15/16/17 with pgvector
- FastAPI + uvicorn
