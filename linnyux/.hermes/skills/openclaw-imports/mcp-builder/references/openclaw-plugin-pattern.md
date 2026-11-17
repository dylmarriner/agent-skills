# OpenClaw Plugin Integration Pattern

When you need to expose an MCP server as an OpenClaw native plugin, follow
this architecture. The plugin is a thin TypeScript wrapper — it does NOT
re-implement the MCP server's logic, it just proxies calls via HTTP.

## Architecture

```
OpenClaw Agent Tool Call
    │ api.registerTool(name, { execute: ... })
    ▼
Plugin src/index.ts
    │ fetch(serverUrl + mcp-session-id)
    ▼
MCP Server (Python, port 8765)
    │ SQLite / logic
    ▼
Response → formatted text → agent
```

## Structure (standalone package)

```
plugins/openclaw-<name>/
├── package.json
│   ├── name: "@<org>/openclaw-<name>"
│   ├── devDependencies: { "@openclaw/plugin-sdk": "workspace:*" }
│   └── openclaw: { extensions: ["./src/index.ts"], install: { ... } }
├── openclaw.plugin.json
│   ├── id, name, description, activation.onStartup
│   ├── contracts.tools = ["tool1", "tool2", ...]
│   ├── skills = ["./skills"]
│   ├── configSchema (serverUrl, apiKey, defaults)
│   └── uiHints (labels + help text for each config field)
├── tsconfig.json
├── src/
│   ├── index.ts        ← definePluginEntry + register function
│   └── prompt-guidance.ts
├── skills/<name>/SKILL.md
└── scripts/
    └── install-to-openclaw.mjs
```

## Plugin Entry Pattern (index.ts)

```typescript
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { resolveLivePluginConfigObject } from "openclaw/plugin-sdk/plugin-config-runtime";
import type { OpenClawConfig } from "openclaw/plugin-sdk/config-contracts";
import { type AnyAgentTool, type OpenClawPluginApi } from "openclaw/plugin-sdk/plugin-entry";
import { Static, Type } from "typebox";

// 1. Define config schema
const ConfigSchema = Type.Object({
  serverUrl: Type.Optional(Type.String({ default: "http://localhost:8765/mcp" })),
  apiKey: Type.Optional(Type.String({ default: "" })),
}, { additionalProperties: false });

// 2. MCP session cache (TTL 14 min)
const sessions = new Map<string, { id: string; expiresAt: number }>();

async function ensureSession(serverUrl: string): Promise<string> {
  const now = Date.now();
  const cached = sessions.get(serverUrl);
  if (cached && now < cached.expiresAt) return cached.id;

  const resp = await fetch(serverUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ jsonrpc:"2.0", id:1, method:"initialize", params:{
      protocolVersion:"2025-03-26", capabilities:{},
      clientInfo:{ name:"openclaw-plugin", version:"0.1.0" },
    }}),
  });
  const sessionId = resp.headers.get("mcp-session-id") ?? "";
  if (!sessionId) throw new Error("No MCP session ID returned");
  sessions.set(serverUrl, { id: sessionId, expiresAt: now + 14*60*1000 });
  return sessionId;
}

// 3. Generic MCP call
async function callServer(
  serverUrl: string, tool: string, args: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const sessionId = await ensureSession(serverUrl);
  const resp = await fetch(serverUrl, {
    method: "POST",
    headers: { "Content-Type":"application/json", "Accept":"application/json",
               "Mcp-Session-Id": sessionId },
    body: JSON.stringify({ jsonrpc:"2.0", id:1, method:"tools/call",
      params: { name: tool, arguments: args } }),
  });
  const data = await resp.json() as any;
  if (data.error) throw new Error(data.error.message);
  const text = data.result?.content?.[0]?.text;
  return text ? JSON.parse(text) : { ok: false, error: "Empty response" };
}

// 4. Register plugin
export default definePluginEntry({
  id: "my-plugin",
  name: "My Plugin",
  description: "...",
  configSchema: ConfigSchema,
  register: (api: OpenClawPluginApi) => {
    // 5. Register each tool
    api.registerTool(
      (_ctx) => ({
        name: "my_tool",
        label: "My Tool",
        description: "Description for the agent",
        parameters: { type: "object", properties: { ... }, required: [...] },
        execute: async (_id, rawParams) => {
          const cfg = resolveLivePluginConfig(api);
          try {
            const result = await callServer(cfg.serverUrl, "mcp_tool", rawParams);
            const text = formatResult(result);
            return { content: [{ type: "text", text }], isError: !result.ok };
          } catch (e) {
            return { content: [{ type:"text", text: `Error: ${e.message}` }], isError: true };
          }
        },
      }),
      { name: "my_tool" },
    );

    // 6. Agent guidance
    api.on("before_prompt_build", async () => ({
      prependSystemContext: "## Memory System\nUse my_tool when...",
    }));
  },
});
```

## Config Resolution

```typescript
function resolveLivePluginConfig(api: OpenClawPluginApi): Static<typeof ConfigSchema> {
  return (resolveLivePluginConfigObject(
    api.runtime.config?.current
      ? () => api.runtime.config.current() as OpenClawConfig
      : undefined,
    "synapse",
    api.pluginConfig as Record<string, unknown>,
  ) ?? {}) as Static<typeof ConfigSchema>;
}
```

## Install Script Pattern

```javascript
// scripts/install-to-openclaw.mjs
import fs from "fs";
import path from "path";

const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || "/path/to/openclaw";
const TARGET = path.join(OPENCLAW_ROOT, "extensions", "my-plugin");
const FILES = ["package.json", "openclaw.plugin.json", "tsconfig.json",
               "src/index.ts", "src/prompt-guidance.ts", "skills/my-plugin/SKILL.md"];

for (const file of FILES) {
  const dst = path.join(TARGET, file);
  fs.mkdirSync(path.dirname(dst), { recursive: true });
  fs.copyFileSync(file, dst);
}
// Generate api.ts barrel
fs.writeFileSync(path.join(TARGET, "api.ts"),
  `export { registerPlugin } from "./src/index.js";\n`);
```

## Pitfalls

- **API key redaction**: FastMCP v1.27+ auto-redacts `api_key` fields. Use `key` not `api_key` as the response field name, or prefix keys with `syn_` instead of `sk_`.
- **Session expiry**: MCP sessions last ~15 min on the server. Always handle session re-initialization gracefully.
- **Config scoping**: Plugin config is per-instance, not per-tool-call. Read it fresh each call via `resolveLivePluginConfigObject` so changes apply immediately.
- **No deep imports**: Plugin code must NOT import from `openclaw/src/` — only from `openclaw/plugin-sdk/*` and its own local modules.
