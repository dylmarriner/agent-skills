# OpenClaw Plugin Entry Structure

## Files

```
plugins/openclaw-synapse/
├── openclaw.plugin.json      # Manifest: id, contracts, configSchema, uiHints
├── package.json              # npm package with openclaw block
├── src/index.ts              # Plugin entry using definePluginEntry + register
├── skills/<name>/SKILL.md    # Agent guidance
├── tsconfig.json
└── scripts/install-to-openclaw.mjs  # Install script
```

## Manifest (`openclaw.plugin.json`)

```json
{
  "id": "my-plugin",
  "activation": { "onStartup": true },
  "contracts": { "tools": ["tool1", "tool2"] },
  "toolMetadata": { "tool1": { "optional": false } },
  "skills": ["./skills"],
  "configSchema": { "type": "object", "properties": { ... } }
}
```

The `contracts.tools` list declares which tools the plugin registers.
The `configSchema` defines user-configurable settings via TypeBox.

## Plugin Entry (`src/index.ts`)

Uses `definePluginEntry` from `openclaw/plugin-sdk/plugin-entry`:

```typescript
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { registerMyPlugin } from "./plugin.js";

export default definePluginEntry({
  id: "my-plugin",
  name: "My Plugin",
  description: "...",
  configSchema: myConfigSchema,
  register: registerMyPlugin,
});
```

## Tool Registration (`registerMyPlugin`)

Tools register via `api.registerTool(factory, { name })`:

```typescript
api.registerTool(
  (ctx) => ({
    name: "my_tool",
    label: "My Tool",
    description: "...",
    parameters: paramsSchema,
    execute: async (_toolCallId, rawParams) => {
      const result = await callMCPTool(params);
      if (result.error) {
        return { content: [{ type: "text", text: "Error" }], isError: true };
      }
      return { content: [{ type: "text", text: formatResult(result) }], isError: false };
    },
  }),
  { name: "my_tool" },
);
```

Key points:
- `execute` receives raw params, must return `{ content, isError }`
- Use `api.on("before_prompt_build", ...)` to inject agent guidance
- Config is resolved via `resolveLivePluginConfigObject()` at call time
- MCP sessions managed with fetch() + header-based session IDs

## Config Resolution

```typescript
const cfg = resolveLivePluginConfigObject(
  api.runtime.config?.current ? () => api.runtime.config.current() as OpenClawConfig : undefined,
  "plugin-id",
  api.pluginConfig as Record<string, unknown>,
) ?? {};
```

## Agent Guidance

```typescript
api.on("before_prompt_build", async () => ({
  prependSystemContext: AGENT_GUIDANCE_TEXT,
}));
```

## Install Script

The plugin is a standalone npm package. Install it into OpenClaw by
copying the directory to `extensions/synapse/` (for bundled) or
using the `openclaw.install` block in `package.json`.

## Build

```bash
cd extensions/synapse
pnpm install
# OpenClaw auto-discovers from extensions/
```
