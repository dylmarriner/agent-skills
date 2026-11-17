# Seeding agentmemory via REST API

When you need to bulk-import existing knowledge into agentmemory (migration
from a prior memory store, seeding from session archives, or initializing a
fresh daemon), use the REST API directly rather than `agentmemory import`
(which starts a competing daemon instance).

## Endpoint

```
POST /agentmemory/remember
Content-Type: application/json

{
  "content": "The memory text to store",
  "metadata": {
    "type": "fact|user|project|infra|identity|workflow|preference",
    "source": "hermes-migration|session-import|custom"
  }
}
```

The response returns a 201 with the created memory object including its ID,
strength, title, and timestamp.

```json
{
  "memory": {
    "id": "mem_mqc0lxj0_f883ce380b95",
    "content": "...",
    "title": "...",
    "type": "fact",
    "strength": 7,
    "createdAt": "2026-06-13T07:09:28.187Z",
    "concepts": [],
    "sessionIds": [],
    "sourceObservationIds": []
  }
}
```

## Key Details

- The field is **`content`**, NOT `memory`. Using `memory` returns 400.
- `metadata.type` is optional but useful for later filtering.
- Each call creates one fact memory with `strength: 7` (default).
- Sequential calls have no rate limits — batch 15+ successfully in one go.

## Bulk Seeding Pattern (Node.js)

```javascript
const http = require("http");

function remember(content, type) {
  return new Promise(resolve => {
    const data = JSON.stringify({
      content,
      metadata: { type, source: "hermes-migration" }
    });
    const req = http.request("http://localhost:3111/agentmemory/remember", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(data)
      }
    }, res => {
      let d = "";
      res.on("data", c => d += c);
      res.on("end", () => resolve(res.statusCode));
    });
    req.on("error", e => resolve(-1));
    req.write(data);
    req.end();
  });
}

// Then call sequentially or via Promise.all (safe for 15+ entries)
```

## Verification

After seeding, check the store has the expected count:

```bash
curl -s http://localhost:3111/agentmemory/memories | python3 -c "import sys,json; print(len(json.load(sys.stdin)['memories']), 'memories')"
```

Or search for a known term:

```bash
curl -s -X POST http://localhost:3111/agentmemory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "agentmemory"}' | python3 -c "import sys,json; r=json.load(sys.stdin); print(len(r['results']), 'results')"
```

## Why Not `agentmemory import`

`agentmemory import <file.jsonl>` is the intended CLI for bulk import, but:
- It spawns its own daemon instance (iii-worker) that competes for port 3111
- It cannot import while the main daemon is already running
- It times out if `iii` binary isn't on PATH

Use the REST API directly instead. It's faster, more reliable, and works
while the daemon is live.
