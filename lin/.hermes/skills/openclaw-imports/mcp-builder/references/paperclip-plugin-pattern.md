# Paperclip Adapter Plugin Pattern

Paperclip plugins are TypeScript workers that run in an isolated worker thread
and communicate with the Paperclip host via RPC. They use the
`@paperclipai/plugin-sdk` package.

This pattern covers creating an adapter plugin that wraps an MCP server
as Paperclip-native tools.

## Package Structure

```
paperclip-synapse/
├── package.json
├── tsconfig.json
├── manifest.json       ← Declares tools, params, descriptions
├── src/
│   └── worker.ts       ← definePlugin entry point
└── dist/               ← Built output (tsc)
```

## package.json

```json
{
  "name": "@synapse/paperclip-adapter",
  "version": "0.1.0",
  "type": "module",
  "main": "./dist/worker.js",
  "dependencies": {
    "@paperclipai/plugin-sdk": "latest"
  },
  "devDependencies": {
    "typescript": "^5.0.0"
  }
}
```

## manifest.json

Declares the plugin's tools with descriptions and parameter schemas. The
Paperclip host uses this to show the tools in its UI and to validate calls:

```json
{
  "id": "synapse-memory",
  "name": "Synapse Memory",
  "version": "0.1.0",
  "description": "Persistent multi-tenant AI memory backbone",
  "tools": [
    {
      "name": "synapse_store",
      "description": "Store a durable memory into persistent AI memory.",
      "params": {
        "content": { "type": "string", "description": "Memory content" },
        "projectKey": { "type": "string", "default": "default" },
        "kind": { "type": "string", "enum": ["working", "episodic", "semantic"], "default": "semantic" },
        "tags": { "type": "array", "items": { "type": "string" } },
        "importance": { "type": "number", "default": 0.5 }
      }
    }
  ]
}
```

## worker.ts — Plugin Entry Point

```typescript
import { definePlugin } from "@paperclipai/plugin-sdk";

const SERVER_URL = process.env.SYNAPSE_SERVER_URL ?? "http://localhost:8765/mcp";
let session: { id: string; expiresAt: number } | null = null;

async function ensureSession(): Promise<string> {
  const now = Date.now();
  if (session && now < session.expiresAt) return session.id;
  const resp = await fetch(SERVER_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0", id: 1, method: "initialize",
      params: { protocolVersion: "2025-03-26", capabilities: {},
               clientInfo: { name: "paperclip-synapse", version: "0.1.0" } },
    }),
  });
  const id = resp.headers.get("mcp-session-id") ?? "";
  if (!id) throw new Error("Failed to get MCP session");
  session = { id, expiresAt: now + 840_000 };
  return id;
}

async function callServer(tool: string, args: Record<string, unknown>) {
  const sessionId = await ensureSession();
  const resp = await fetch(SERVER_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json",
               "Mcp-Session-Id": sessionId },
    body: JSON.stringify({
      jsonrpc: "2.0", id: 1, method: "tools/call",
      params: { name: tool, arguments: args },
    }),
  });
  const data = await resp.json() as any;
  if (data.error) throw new Error(data.error.message);
  const text = data.result?.content?.[0]?.text;
  return text ? JSON.parse(text) : { ok: false, error: "Empty response" };
}

export default definePlugin({
  async setup(ctx) {
    ctx.logger.info("Synapse plugin starting...");

    ctx.tools.register("synapse_store", async (params) => {
      const result = await callServer("store", {
        project_key: params.projectKey ?? "default",
        kind: params.kind ?? "semantic",
        content: params.content,
        tags: params.tags ?? [],
        importance: params.importance ?? 0.5,
      });
      return { content: [{ type: "text", text: JSON.stringify(result) }] };
    });

    // Register more tools similarly...
  },

  async onHealth() {
    try {
      const h = await callServer("health", {});
      return { status: h.ok ? "ok" : "degraded",
               details: { memories: h.memories } };
    } catch {
      return { status: "error", message: "Cannot reach MCP server" };
    }
  },
});
```

## Installation

Add to `~/.paperclip/adapter-plugins.json`:

```json
{
  "@synapse/paperclip-adapter": {
    "path": "/absolute/path/to/paperclip-synapse"
  }
}
```

## Key Differences from Hermes Plugin

| Aspect | Paperclip | Hermes |
|--------|-----------|--------|
| Language | TypeScript | Python |
| SDK | `@paperclipai/plugin-sdk` | Native (no SDK, just schemas.py+tools.py) |
| Entry pattern | `definePlugin({ setup(ctx) { ... } })` | Module-level functions |
| Tool registration | `ctx.tools.register(name, handler)` | Declare in schemas.py + define in tools.py |
| Lifecycle hooks | `ctx.events.on()`, `ctx.jobs.register()` | `provides_hooks` in plugin.yaml |
| Config | `process.env` | `requires_env` in plugin.yaml |
| Install dir | Via `adapter-plugins.json` path | `~/.hermes/plugins/<name>/` |

## Pitfalls

- **Session caching**: MCP sessions expire after ~15 min. Cache across calls with a TTL check.
- **Worker isolation**: Paperclip plugins run in isolated worker threads. Module-level globals persist within the worker lifetime but not across restarts.
- **Error handling**: Return `{ content: [{ type: "text", text: errorMsg }] }` on errors. Don't throw — the host catches but the error message presented to the user may be generic.
- **Build**: Compile with `tsc` before install. The host loads `dist/worker.js` (per `main` in package.json), not the source `.ts` files.
- **Plugin SDK types**: Install `@paperclipai/plugin-sdk` as a dependency. The TypeScript types come from the package; no `@types/*` needed.
