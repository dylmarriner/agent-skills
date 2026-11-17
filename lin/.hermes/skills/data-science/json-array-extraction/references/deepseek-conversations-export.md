# Session-specific example: DeepSeek conversations.json export

Extracted from `conversations.json` (DeepSeek web export, 43MB, 219 conversations).

## File structure

Each conversation object had:
- `id` — UUID
- `title` — user-facing title (or empty string)
- `inserted_at` / `updated_at` — ISO timestamps
- `mapping` — message tree with parent-children links

## Message tree walk (BFS for chronological order)

```python
def flatten_mapping(mapping: dict) -> list[dict]:
    """Walk the mapping tree BFS to get messages in chronological order."""
    if "root" not in mapping:
        return []

    messages = []
    stack = list(mapping["root"].get("children", []))
    seen = set()

    while stack:
        node_id = stack.pop(0)
        if node_id in seen:
            continue
        seen.add(node_id)
        node = mapping.get(node_id)
        if not node:
            continue
        msg = node.get("message")
        if msg:
            role = "REQUEST" if any(f.get("type") == "REQUEST" for f in msg.get("fragments", [])) else "RESPONSE"
            content_parts = [
                f.get("content", "")
                for f in msg.get("fragments", [])
                if f.get("type") in ("REQUEST", "RESPONSE", "CONTEXT")
            ]
            content = "\n".join(content_parts).strip()
            if content:
                messages.append({
                    "role": role,
                    "model": msg.get("model", "unknown"),
                    "timestamp": msg.get("inserted_at", ""),
                    "content": content,
                })
        # BFS: prepend children to maintain chronological order
        stack = list(node.get("children", [])) + stack

    return messages
```

## Output

- 219 conversations → 438 files (219 `.json` + 219 `.md`)
- Filename format: `{title-slug}__{uuid[:8]}.{ext}`
- 80MB total output
