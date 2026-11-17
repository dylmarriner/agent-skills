---
name: postgres-async-raw-sql
description: asyncpg raw SQL gotchas with SQLAlchemy async — NOT NULL defaults, RETURNING consumption, transaction boundaries, URI normalization, and n-plus-one-commit patterns.
---

# PostgreSQL Async Raw SQL Patterns

Gotchas discovered building Synapse Memory (FastAPI + asyncpg + SQLAlchemy async).
The ORM hides these; raw `text()` INSERTs expose them.

## NOT NULL Columns Must Be Explicit in Raw INSERTs

`mapped_column(Integer, nullable=False, default=0)` creates a **Python-level**
default, NOT a server-side `DEFAULT 0`. The column DDL is `NOT NULL` with no
default. Raw `text()` INSERTs MUST provide every NOT NULL column explicitly:

```sql
-- BROKEN: usage_count omitted, has default=0 in ORM but not in DB
INSERT INTO skills (id, name, content)
VALUES ($1, $2, $3)
-- NotNullViolationError: null value in column "usage_count"

-- FIXED: every NOT NULL column listed with explicit value
INSERT INTO skills (id, name, content, usage_count, is_active, version)
VALUES ($1, $2, $3, 0, true, 1)
```

**Checklist before writing a raw INSERT:**
1. List every `nullable=False` column from the ORM model
2. If the model has `default=X` but no `server_default=text('X')`, you must provide it in the SQL
3. Common culprits: `is_active`, `version`, `usage_count`, `access_count`, `level`

## RETURNING Results Must Be Consumed

`await db.execute(text("INSERT ... RETURNING col"))` returns a `CursorResult`
that **must** be read. Unconsumed RETURNING rows hold the asyncpg cursor open:

```python
# BROKEN — no fetch, corrupts transaction
await db.execute(text("INSERT ... RETURNING id, version"))

# FIXED — consume the result
row = await db.execute(text("INSERT ... RETURNING id, version"))
inserted = row.fetchone()          # single row
version = inserted.version if inserted else 1
```

Patterns:
- `fetchone()` — single-row RETURNING
- `fetchall()` — multi-row RETURNING
- `scalar()` — single value RETURNING
- Never skip the fetch when RETURNING is present

## Don't Commit Inside Shared-Session Helpers

A helper that receives the caller's DB session must NOT call `db.commit()`.
Committing inside a helper commits the **outer** transaction:

```python
# BROKEN — helper commits caller's transaction
async def _upsert(db, ...):
    await db.execute(...)
    await db.commit()       # outer transaction committed!

async def handler(db=Depends(get_db)):
    for item in items:
        await _upsert(db, item)   # 1st call commits, 2nd call crashes
    # "current transaction is aborted, commands ignored"
```

**Rule:** helpers accumulate work silently; the outermost scope commits once:

```python
async def _upsert(db, ...):
    await db.execute(...)          # no commit

async def handler(db=Depends(get_db)):
    saved = []
    for item in items:
        saved.append(await _upsert(db, item))
    if saved:
        await db.commit()          # single commit at caller level
```

**Exception:** use `async with db.begin_nested()` (savepoints) when a helper
genuinely needs to roll back internally without affecting the caller's
transaction. But prefer the defer-commit pattern for simplicity.

## URI normalize() Must Preserve Scheme Separator

`re.sub(r"/+", "/", uri)` collapses `://` to `:/`, destroying URI schemes:

```python
# BROKEN
normalize_uri("synapse://user/default")   # → "synapse:/user/default"

# FIXED — detect scheme boundary first
def normalize_uri(uri: str) -> str:
    scheme_end = uri.find("://")
    if scheme_end >= 0:
        scheme = uri[:scheme_end + 3]
        path = uri[scheme_end + 3:]
        path = re.sub(r"/+", "/", path.rstrip("/"))
        return scheme + path
    return re.sub(r"/+", "/", uri.rstrip("/"))
```

## FastAPI body: Dict vs Body()

`body: dict = None` works for JSON body endpoints but is fragile — FastAPI
infers it only because `dict` is a "complex" type. Explicit is better:

```python
from fastapi import Body, Query

# Works but implicit
async def handler(agent_id: str = Query(...), body: dict = None):
    data = body or {}
    val = data.get("key", "")

# Explicit and clear
async def handler(agent_id: str = Query(...), body: dict | None = Body(None)):
    data = body or {}
```

For endpoints with more than 2-3 body fields, use a Pydantic model.
