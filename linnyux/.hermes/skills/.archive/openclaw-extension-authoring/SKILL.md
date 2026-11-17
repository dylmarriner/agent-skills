---
name: openclaw-extension-authoring
description: "Author OpenClaw native extensions (plugins) that wrap external services — manifests, tool registration, SDK patterns, agent guidance, and pitfalls. Covers the full lifecycle from scaffold through build verification."
version: 1.0.0
---

# OpenClaw Extension Authoring

Guide for building native OpenClaw extensions (plugins) that wrap external
services as first-class agent tools.

## When to Use

Use this when you need to:
- Wrap an MCP server, REST API, or external service as a native OpenClaw plugin
- Create a bundled extension under `extensions/<name>/`
- Add tools, config, and agent guidance to OpenClaw
- Migrate from an MCP config to a native plugin

## User Preference

This user prefers **plugins over bare MCP configs**. When an external service
could be either (1) an MCP server config or (2) a native OpenClaw plugin,
always build the plugin. The plugin provides agent guidance, better error
messages, structured tool parameters, lifecycle hooks, and discoverability
via the skill system. MCP configs are for simple pass-through; plugins are
for anything with meaningful integration logic.

## User Preference: Standalone Project Structure (CRITICAL)

**Do NOT build OpenClaw plugins by placing files directly into the
`openclaw/extensions/<name>/` directory during development.** This was a
repeated pattern that the user corrected.

Instead, the OpenClaw plugin lives as a **self-contained, distributable
package** inside YOUR own project, under `plugins/openclaw-<name>/`.
Only at install time do you copy it into the OpenClaw extensions directory.

```
your-project/
├── plugins/
│   └── openclaw-synapse/           ← All plugin files here during dev
│       ├── openclaw.plugin.json
│       ├── package.json
│       ├── src/index.ts
│       └── scripts/install-to-openclaw.mjs
├── openclaw/extensions/synapse/    ← Only populated at install time
```

Use an install script (`scripts/install-to-openclaw.mjs`) that copies the
plugin from your project into the OpenClaw extensions directory. Never
develop directly inside another project's tree.

## Extension Structure

```
extensions/<name>/
  openclaw.plugin.json    # Manifest: contracts, configSchema, uiHints, skills
  package.json            # Package metadata + openclaw build/release config
  index.ts                # Entry point: definePluginEntry({ id, name, configSchema, register })
  api.ts                  # Public exports for the plugin
  tsconfig.json           # Extends ../tsconfig.package-boundary.base.json
  skills/<name>/SKILL.md  # Agent skill documentation
  src/
    plugin.ts             # register function: registerTool(), on("before_prompt_build")
    tool.ts               # Tool factory: creates AnyAgentTool instances
    config.ts             # TypeBox schema for plugin config
    types.ts              # Internal types
    prompt-guidance.ts    # Agent system guidance string
```

## Manifest (openclaw.plugin.json)

```json
{
  "id": "my-plugin",
  "activation": { "onStartup": true },
  "name": "My Plugin",
  "description": "What the plugin does for agents",
  "contracts": {
    "tools": ["tool_name", "other_tool"]
  },
  "toolMetadata": {
    "tool_name": { "optional": false }
  },
  "skills": ["./skills"],
  "configSchema": {
    "type": "object",
    "additionalProperties": false,
    "properties": { ... }
  }
}
```

Key contract rules:
- Tool names in contracts must match the name passed to `api.registerTool()`
- `configSchema` is JSON Schema — must use `additionalProperties: false`
- `skills` points to a directory of SKILL.md files (one per skill)

## Package Config (package.json)

```json
{
  "name": "@openclaw/my-plugin",
  "type": "module",
  "dependencies": { "typebox": "1.1.38" },
  "devDependencies": { "@openclaw/plugin-sdk": "workspace:*" },
  "openclaw": {
    "extensions": ["./index.ts"],
    "install": {
      "localPath": "extensions/my-plugin",
      "minHostVersion": ">=2026.4.30"
    }
  }
}
```

## Entry Point (index.ts)

```typescript
import { definePluginEntry } from "./api.js";
import { myConfigSchema } from "./src/config.js";
import { registerMyPlugin } from "./src/plugin.js";

export default definePluginEntry({
  id: "my-plugin",
  name: "My Plugin",
  description: "...",
  configSchema: myConfigSchema,
  register: registerMyPlugin,
});
```

## Registering Tools (src/plugin.ts)

The pattern for wrapping an external MCP service as native tools:

```typescript
export function registerMyPlugin(api: OpenClawPluginApi): void {
  const resolveConfig = () => resolveLivePluginConfig(api, "my-plugin", ...);

  // Register each tool
  api.registerTool(
    (ctx) => ({
      name: "my_tool",
      description: "...",
      parameters: Type.Object({ ... }),
      execute: async (_toolCallId, rawParams) => {
        const cfg = resolveConfig();
        // Call external MCP server
        const result = await callMcpServer(cfg.serverUrl, "external_tool", {
          api_key: cfg.apiKey ?? "",
          ...rawParams,
        });
        return { content: [{ type: "text", text: JSON.stringify(result) }] };
      },
    }),
    { name: "my_tool" },
  );

  // Add agent guidance
  api.on("before_prompt_build", async () => ({
    prependSystemContext: AGENT_GUIDANCE,
  }));
}
```

## Agent Guidance (src/prompt-guidance.ts)

Write clear, actionable guidance that tells the agent WHEN and HOW to use
the plugin's tools. Include specific examples for each tool.

## MCP Session Management for HTTP Transport

When wrapping a StreamableHTTP MCP server:

```typescript
async function ensureSession(serverUrl: string): Promise<string> {
  // 1. Initialize session
  const resp = await fetch(serverUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0", id: 1, method: "initialize",
      params: { protocolVersion: "2025-03-26", capabilities: {},
               clientInfo: { name: "openclaw-<plugin>", version: "1.0.0" } },
    }),
  });

  // 2. Extract session ID from response header
  const sessionId = resp.headers.get("mcp-session-id") ?? "";
  if (!sessionId) throw new Error("No session ID returned");

  // 3. Use in subsequent calls via Mcp-Session-Id header
  return sessionId;
}
```

Session IDs have a 15-minute TTL. Cache them with expiry tracking.

## Pitfalls

### FastMCP API Key Redaction

FastMCP v1.27+ automatically redacts:
- Response fields named `api_key` in structured content
- String values starting with `sk_` patterns (replaces middle with `...`)

**Workarounds**:
- Return the key in a field named `key` instead of `api_key`
- Use a prefix like `syn_` or `cust_` instead of `sk_`
- Include the full key in the response `message` text as well

### Tool Name Collisions

When wrapping MCP tools, you control the OpenClaw-side tool name.
Prefix tools with your plugin namespace (e.g., `synapse_store` not `store`)
to avoid collisions with other plugins or built-in tools.

### Response Formatting

Return `{ content: [{ type: "text", text: ... }], isError: false }` for success
and `isError: true` for failures. The `isError` flag is critical — without it
the agent may misinterpret error responses as successful tool results.

### Config Resolution

Use `resolveLivePluginConfigObject()` from `openclaw/plugin-sdk/plugin-config-runtime`
to get current config at call time. Cache the resolver function, not the config
value — config can change at runtime.

## Verification Checklist

- [ ] `openclaw.plugin.json` has correct tool names in contracts
- [ ] All tools handle errors and return `isError: true`
- [ ] Session caching respects TTL (refresh before expiry)
- [ ] Agent guidance covers WHEN and HOW to use each tool
- [ ] Config defaults work without user configuration
- [ ] Plugin is auto-discovered from `extensions/` directory
