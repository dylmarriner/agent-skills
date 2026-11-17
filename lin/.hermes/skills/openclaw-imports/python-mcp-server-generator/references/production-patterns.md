# Production Patterns for Python MCP Servers

## Multi-Tenant Schema Design

### Tenants Table

```sql
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    api_key TEXT NOT NULL UNIQUE,
    tier TEXT NOT NULL DEFAULT 'free' CHECK(tier IN ('free','pro','team','enterprise')),
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','suspended','deleting')),
    max_devices INTEGER NOT NULL DEFAULT 2,
    max_memories INTEGER NOT NULL DEFAULT 50000,
    max_storage_mb INTEGER NOT NULL DEFAULT 50,
    e2ee_enabled INTEGER NOT NULL DEFAULT 1,
    audit_retention_days INTEGER NOT NULL DEFAULT 30,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
```

### Data Tables (tenant-scoped)

Every table gets a `tenant_id TEXT NOT NULL` column and a composite index:

```sql
CREATE TABLE IF NOT EXISTS memories (
    memory_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    -- other columns...
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_memories_tenant ON memories(tenant_id);
```

### API Key Auth Middleware Pattern

```python
# In each MCP tool:
def some_tool(api_key: str = "", tenant_id: str = "", ...):
    tid = resolve_tenant(api_key, tenant_id)
    if tid is None:
        return {"ok": False, "error": "Authentication required"}
    # ... proceed with tid scoping all queries

def resolve_tenant(api_key: str, tenant_id: str) -> str | None:
    """Validate key in DB, return tenant_id."""
    if api_key:
        con = get_db()
        row = con.execute(
            "SELECT tenant_id FROM tenants WHERE api_key=? AND status='active'",
            (api_key,),
        ).fetchone()
        if row:
            return row["tenant_id"]
    # Optional: single-tenant fallback
    return None
```

### Audit Log Table (SOC2-ready, append-only)

```sql
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    device_id TEXT,
    operation TEXT NOT NULL,
    memory_id TEXT,
    project_key TEXT,
    tool TEXT,
    metadata TEXT,  -- JSON
    ip_address TEXT,
    user_agent TEXT
);
-- Applications enforce append-only at the application layer
```

## FastMCP Redaction Debugging

When FastMCP returns `***` for a field value, check:

1. Does the field name match `api_key`, `key`, `secret`, `token`, `password`? → Rename the field
2. Does the value start with `sk_`? → Change prefix to `syn_`, `se_`, or just strip the prefix
3. Is it in `content[0].text` or `structuredContent`? → Both are redacted
4. The raw DB always has the real value — verify there before debugging response paths

## DB-Backed MCP Tool Structure

```
┌──────────────────────────────────────────┐
│           MCP Server (FastMCP)           │
│  ┌──────────┐  ┌──────────┐             │
│  │ Schema   │  │ Init     │             │
│  │ (tables) │  │ (WAL,    │             │
│  │          │  │  indexes) │             │
│  ├──────────┤  ├──────────┤             │
│  │ Tool:    │  │ Tool:    │             │
│  │ store    │  │ retrieve │             │
│  ├──────────┤  ├──────────┤             │
│  │ Manually │  │ Hybrid   │             │
│  │ manage   │  │ FTS5 +   │             │
│  │ FTS5     │  │ LIKE +   │             │
│  │ index    │  │ embed    │             │
│  └──────────┘  └──────────┘             │
└──────────────────────────────────────────┘
```

## Deployment Checklist

- [ ] systemd unit with After=network-online.target tailscaled.service
- [ ] WAL mode, busy_timeout=5000, synchronous=NORMAL, cache_size=-64000
- [ ] Environment variables for all config (host, port, data dir, limits)
- [ ] Tailscale auto-detection via `tailscale status --json`
- [ ] Health endpoint returning DB stats, version, Tailscale IP
- [ ] Seed default tenant on first run if multi-tenant disabled
- [ ] Rate limiting via Redis or sliding window (Phase 1+)
- [ ] Graceful shutdown (handle SIGTERM for systemd)

## Common Pitfalls

1. **FTS5 trigger with contentless table**: Triggers do NOT work on FTS5 tables
   created with `content=''`. Manage FTS indexing manually in tool code.
2. **LIKE on exact query string**: `LIKE '%JWT authentication%'` won't match
   "Auth uses JWT..." because the query terms aren't contiguous. Use per-word
   LIKE: `(content_text LIKE '%JWT%' OR content_text LIKE '%authentication%')`.
3. **Session management in streamable HTTP**: Each test needs a fresh
   `initialize` call to get a `Mcp-Session-Id` header. Reuse sessions across
   multiple tool calls from the same client.
4. **Embedding mismatch with pseudo-embeddings**: Hash-based embeddings are
   deterministic per-text but NOT semantically meaningful. Only use for
   development — replace with ONNX BGE-small or similar for production.
5. **API key exposure in logs**: FastMCP's automatic redaction is actually a
   security feature. Work around it for development, but keep it for production
   when using a proper key management flow.
