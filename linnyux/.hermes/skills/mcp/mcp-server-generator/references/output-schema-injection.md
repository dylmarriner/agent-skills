# Output Schema Injection for Existing MCP Servers

When you need ChatGPT or Codex to understand what fields to expect from an MCP server's tool responses, add `outputSchema` to each tool definition. The LLM discovers this at runtime via `tools/list` and can parse results correctly without guesswork.

## Approach: Enrich at the Handler Level

For a running MCP server with a static `TOOLS` list, do NOT modify every tool entry individually. Instead:

1. Create a mapping dict of `name → outputSchema` for the key tools
2. Write an `_enrich_tools()` function that adds `outputSchema` to each tool before the `tools/list` response
3. Patch the handler to call `_enrich_tools(tools)` before returning

### Python/FastAPI Example

```python
OUTPUT_SCHEMAS = {
    "memory_save": {
        "type": "object",
        "properties": {
            "id": {"type": "string", "description": "Short UUID of saved memory"},
            "type": {"type": "string", "enum": ["observation", "experience", "world", "preference", "lesson"]},
            "extraction_queued": {"type": "boolean"},
        },
    },
    "memory_recall": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "ordinal": {"type": "integer"},
                "type": {"type": "string"},
                "score": {"type": "number", "description": "Relevance score 0-1"},
                "content": {"type": "string"},
            },
        },
    },
}


def _enrich_tools(tools_list):
    enriched = []
    for tool in tools_list:
        t = dict(tool)
        name = t["name"]
        if name in OUTPUT_SCHEMAS:
            t["outputSchema"] = OUTPUT_SCHEMAS[name]
        else:
            t["outputSchema"] = {"type": "object", "properties": {"content": {"type": "array"}}}
        enriched.append(t)
    return enriched
```

Then patch the handler:

```python
# BEFORE
return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}

# AFTER
return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": _enrich_tools(TOOLS)}}
```

## Verification

```bash
curl -s <server_url> -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | \
  python3 -c "import sys,json; d=json.load(sys.stdin); \
  for t in d['result']['tools']: \
    print(f\"{t['name']}: {'has outputSchema' if 'outputSchema' in t else 'MISSING'}\")"
```

## Restart After Modifying

For FastAPI servers with read-only container mounts: modify the file on the host filesystem (the Docker volume source), then `docker compose restart <service>` to pick up changes.
