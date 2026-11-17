---
name: paperclip-adapter-development
description: 'Extend Paperclip adapters: add new capabilities like skill sync, model discovery, session codecs, and config schemas following established patterns in the codebase.'
---

# Paperclip Adapter Development

Patterns and recipes for extending Paperclip agent adapters with new capabilities.

## When to Use

Triggers:
- Adding skill sync (`listSkills` / `syncSkills`) to a Paperclip adapter
- Adding model discovery (`listModels` / `refreshModels`) to an adapter
- Adding session management or session codecs to an adapter
- Adding config schemas (`getConfigSchema`) to an adapter
- Adding quota windows, instructions bundle support, or other capability flags
- Working in `packages/adapters/` or `server/src/adapters/registry.ts`

## Architecture

Paperclip adapters live in `packages/adapters/<name>/` and export from two layers:

- **Root** (`src/index.ts`): metadata — `type`, `label`, `models`, `agentConfigurationDoc`
- **Server** (`src/server/index.ts`): runtime — `execute`, `testEnvironment`, `listSkills`, `syncSkills`, `sessionCodec`, `listModels`, `getConfigSchema`, etc.

Both are re-exported via the adapter's `package.json` `exports` field. The server-side `registry.ts` imports them and constructs a `ServerAdapterModule` object.

## Step-by-Step: Adding Skill Sync to an Adapter

See: `references/adding-skill-sync.md`

## Step-by-Step: Adding Model Discovery

1. Create `src/server/models.ts` in the adapter
2. Export `listModels` / `listXxxModels` and optionally `refreshModels` / `resetModelsCacheForTests`
3. Export from `src/server/index.ts`
4. Import and add to the adapter object in `server/src/adapters/registry.ts`

## Step-by-Step: Registering an Adapter in the Server

1. Import runtime exports from `@paperclipai/adapter-<name>/server`
2. Import metadata from `@paperclipai/adapter-<name>`
3. Create a `ServerAdapterModule` object in `server/src/adapters/registry.ts`
4. Add it to the `allAdapters` array at the bottom of the file

## Gateway Adapter Wake Payload (OpenClaw Gateway)

Gateway adapters (like `openclaw_gateway`) send agent params to a remote gateway over WebSocket. The gateway's agent params schema may reject unrecognized top-level properties.

### The Problem

The `openclaw_gateway` adapter previously sent the Paperclip context as a top-level `agentParams.paperclip` property:

```typescript
agentParams.paperclip = paperclipPayload;
```

The remote gateway rejects this with: `invalid agent params: at root: unexpected property 'paperclip'`

### The Fix

Embed the serialized paperclip JSON into the `message` text instead of as a separate top-level property:

```typescript
const paperclipJson = stringifyPaperclipWakePayload(paperclipPayload);
const messageWithPaperclip = paperclipJson
  ? `${message}\n\nStandard paperclip context JSON:\n\`\`\`json\n${paperclipJson}\n\`\`\``
  : message;

const agentParams = {
  ...payloadTemplate,
  message: messageWithPaperclip,
  sessionKey,
  idempotencyKey: ctx.runId,
};
// Do NOT set agentParams.paperclip — gateways reject unknown top-level keys
```

This way the gateway agent receives the full context in the wake message text where it can parse it, but the top-level params stay within the gateway's recognized schema (`message`, `sessionKey`, `idempotencyKey`, `agentId`, `timeout`).

### When to Apply

Always for gateway-type adapters (`openclaw_gateway`, any future ws-based remote adapter). Local adapters that spawn a local process (claude_local, opencode_local, pi_local, gemini_local) do not have this restriction — they can pass arbitrary env/params to the spawned process.

## Pitfalls

- The `ServerAdapterModule` type requires all fields. If an adapter doesn't support a feature, set `listSkills: undefined` explicitly or omit it — check the type definition for optional fields.
- `__moduleDir` resolution using `fileURLToPath(import.meta.url)` is critical for `readPaperclipRuntimeSkillEntries` which uses it to find the Paperclip runtime skills directory relative to the adapter package.
- The adapter's `package.json` `exports` field must list both `"."` (root) and `"./server"` exports, otherwise the server can't import them.
- Always run typecheck in the adapter package before testing: `pnpm --filter @paperclipai/adapter-<name> typecheck`
- The server package's moduleResolution has pre-existing issues (many `TS2307` errors) — these are NOT caused by your changes. Only worry about errors in files you modified.
- Gateway adapters: top-level agent params are validated against the gateway's schema. Unknown keys get rejected. Embed context data in the `message` text instead.
