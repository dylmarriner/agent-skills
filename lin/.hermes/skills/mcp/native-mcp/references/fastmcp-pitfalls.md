# FastMCP Server Pitfalls for Hermes Clients

When building FastMCP servers that Hermes Agent connects to, be aware of
these gotchas that affect tool discovery and response handling.

## API Key Redaction in Structured Content

FastMCP v1.27+ has automatic credential redaction:

1. **Field name `api_key`** — Any JSON response field named `api_key` is
   replaced with `"***"` in the `structuredContent` output. The raw JSON
   in `content[0].text` also gets truncated (middle replaced with `...`).

2. **Prefix `sk_`** — String values starting with `sk_` trigger the same
   redaction, even under different field names.

**Symptoms**: The server logs show the real API key was stored, but the
client receives a truncated value like `sk_syn...09f8` (13 chars instead
of the original 52).

**Workarounds**:
- Use a field name like `"key"` instead of `"api_key"` in the response
- Use a prefix like `syn_`, `cust_`, or `tenant_` instead of `sk_syn_`
- Include the full key in a plain-text `message` field as well

## Streamable HTTP Session Management

FastMCP servers using `transport="streamable-http"` require explicit
session management:

1. Send an `initialize` request to establish a session
2. Extract the session ID from the `mcp-session-id` response header
3. Include the session ID in all subsequent requests via the `Mcp-Session-Id` header
4. Sessions have a 15-minute TTL — cache with expiry tracking

The initialize request:
```json
{
  "jsonrpc": "2.0", "id": 1, "method": "initialize",
  "params": {
    "protocolVersion": "2025-03-26",
    "capabilities": {},
    "clientInfo": { "name": "client-name", "version": "1.0.0" }
  }
}
```

Without a valid session, all subsequent calls return:
```json
{"error": {"code": -32600, "message": "Bad Request: Missing session ID"}}
```

## FTS5 Contentless Table Setup

When creating an FTS5 virtual table intended for manual index management,
use `content=''` to create a contentless table:

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS my_fts USING fts5(
    id UNINDEXED,
    text_col,
    tokenize='unicode61 remove_diacritics 2',
    content=''
);
```

With a contentless table:
- Use `INSERT INTO my_fts(my_fts, id) VALUES ('delete', ?)` for deletions
- Use `INSERT INTO my_fts(...)` for regular inserts
- Do NOT use SQL triggers on the source table — manage FTS indices
  synchronously in your application code alongside the data operations
