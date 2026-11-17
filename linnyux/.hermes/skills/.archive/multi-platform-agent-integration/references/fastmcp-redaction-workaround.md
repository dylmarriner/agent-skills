# FastMCP API Key Redaction Workaround

## The Problem

FastMCP v1.27.1 automatically redacts sensitive-looking fields when
serializing tool return values. It detects:
- Field names: `api_key`, `secret`, `password`, `token`, `key`
- Value patterns: anything matching `sk_...`, `syn_...`, etc.

This means when `register_tenant` returns the API key, both
`structuredContent` and `content[0].text` show truncated values like
`"api_key": "sk_syn...a1b2"` — the middle gets replaced with `...`.

## The Workaround

Two changes are BOTH required:

### 1. Change the field name

Use `"key"` instead of `"api_key"` in the return dict. This avoids
structuredContent redaction (which matches on field names).

```python
return {
    "ok": True,
    "tenant_id": tenant_id,
    "key": api_key,           # NOT "api_key"
    "message": f"Store this API key: {api_key}",
}
```

### 2. Change the API key prefix

FastMCP's JSON serialization redaction pattern-matches on the value.
A prefix like `sk_syn_` triggers this because it looks like an API key.
Change to something that doesn't match:

```python
def generate_api_key(prefix: str = "syn_") -> str:  # NOT "sk_syn_"
    return prefix + secrets.token_hex(24)
```

The resulting key `syn_a1b2c3...` doesn't trigger the redaction pattern.

### Testing

After both changes, the key should appear in full in the response:
```json
"key": "syn_a1b2c3d4e5f6...",
```

If it's still truncated, the redaction pattern is matching on the value.
Try a different prefix: `se_`, `wa_`, or just generate a raw hex string
with no prefix at all.

## Root Cause

FastMCP's `structuredContent` feature scans return values for patterns
that look like secrets and replaces them with masked versions. This
happens at two levels:
1. The `structuredContent` field in the MCP response (field-name based)
2. The `content[0].text` JSON serialization (value-pattern based)

Both must be bypassed for the API key to reach the client.
