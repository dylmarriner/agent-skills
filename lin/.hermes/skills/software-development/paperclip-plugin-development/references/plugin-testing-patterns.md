# Plugin Testing Patterns

Patterns and lessons from testing Paperclip plugins (Token Optimizer, Agent Memory, GitHub Sync).

## 1. Config Validation Tests

Test `parseConfigOrThrow()` with these cases:

```typescript
// Empty config → returns defaults
const cfg = parseConfigOrThrow({});
expect(cfg.briefMaxTokens).toBe(8000);

// Explicit override
const cfg = parseConfigOrThrow({ briefMaxTokens: 16000 });
expect(cfg.briefMaxTokens).toBe(16000);

// Boundary minimum
expect(() => parseConfigOrThrow({ briefMaxTokens: 500 })).toThrow("briefMaxTokens");

// Boundary maximum
expect(() => parseConfigOrThrow({ briefMaxTokens: 99999 })).toThrow("briefMaxTokens");

// Partial model tiers (only override one, others default)
const cfg = parseConfigOrThrow({ modelTiers: { fast: "custom" } });
expect(cfg.modelTiers.fast).toBe("custom");
expect(cfg.modelTiers.standard).toBe("claude-sonnet-4-5");  // default

// Extra fields are silently ignored
const cfg = parseConfigOrThrow({ unknownField: "ignored" } as any);
expect(cfg).toBeDefined();
```

## 2. Tool Handler Tests

Tool handlers are factories — call `makeHandler()` once, then call the returned function with params.

```typescript
const handler = makeHandler();

// Success path (data branch)
const result = await handler({ text: "hello", targetTokens: 1000 }, {});
expect(result.data?.pruned).toBe("hello");
expect(result.data?.savedTokens).toBe(0);

// Error path (error branch — validation failure)
const result = await handler({ text: "", targetTokens: 100 }, {});
expect(result.error).toBe("text must be a non-empty string");

// Strategy variants
const result = await handler({ text: longText, targetTokens: 100, strategy: "head" }, {});
expect(result.data?.strategy).toBe("head");
```

**Important:** The handler's second arg `_runCtx` is optional. Pass `{}` or
`undefined` for unit tests that don't need run context.

## 3. Cache / State Mocking

Use a plain-object store to mock `ctx.state.get/set`. **Never use
`expect.any(String)` as a stored key** — that string literal becomes the
actual key in the store and will never match the real computed key.

```typescript
import { vi } from "vitest";

function mockCtx(stateStore: Record<string, unknown> = {}) {
  const store = { ...stateStore };
  return {
    state: {
      get: vi.fn(async ({ stateKey }) => store[stateKey] ?? null),
      set: vi.fn(async ({ stateKey }, value) => { store[stateKey] = value; }),
    },
    logger: { warn: vi.fn(), debug: vi.fn() },
  } as unknown as PluginContext;
}
```

For cache tests, compute the key the same way the production code does:

```typescript
// Don't do this — fragile, wrong:
const ctx = mockCtx();
await ctx.state.set({ stateKey: expect.any(String) } as any, entry);

// Do this — match the internal cacheKey() logic:
const now = new Date();
const slot = Math.floor(now.getTime() / (ttlHours * 3_600_000));
const ctx = mockCtx({ [`issueId:${slot}`]: entry });
const result = await readBriefCache(ctx, "c1", "i1", now.toISOString(), ttlHours);
```

## 4. Test Organization

Per-plugin test file naming convention:

```
tests/
  config.spec.ts           # parseConfigOrThrow validation
  cache.spec.ts            # Cache/state operations
  compress.spec.ts         # Compression algorithms (pure functions)
  tokenEstimator.spec.ts   # Token estimation (pure functions)
  pruneContext.spec.ts     # Tool: pruneContext handler
  estimateTokensTool.spec.ts  # Tool: estimateTokens handler
  <tool-name>.spec.ts      # Other tool handlers
```

## 5. Running Tests

```bash
# From the plugin directory
cd packages/plugins/plugin-<name>
pnpm test:run         # vitest run — CI mode
pnpm test             # vitest — watch mode
```

Vitest config is per-plugin (`vitest.config.ts`) inheriting from the root
workspace config. The `pnpm test:run` alias runs `vitest run`.

## 6. Common Issues Found via Tests

| Issue | How Test Catches It |
|-------|---------------------|
| Manifest/worker schema mismatch | Handler returns `undefined` for fields that have different names |
| Config boundary violations | `parseConfigOrThrow` throws on out-of-range values |
| Cache key mismatch | Mock store lookup returns null despite pre-seeded entry |
| Missing error handling | Handler returns `{ data }` instead of `{ error }` for invalid input |
| Strategy not propagated | Strategy field in result doesn't match strategy parameter |
