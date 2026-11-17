---
name: paperclip-plugin-development
description: >-
  Develop, debug, and ship Paperclip plugins — migrations, worker entrypoints,
  manifest validation, plugin lifecycle, and common pitfalls.
---

# Paperclip Plugin Development

Patterns, pitfalls, and workflows for building plugins in the Paperclip monorepo
(`packages/plugins/`). Covers migration validation quirks, worker startup,
dev-mode configuration, and the plugin lifecycle.

## When to Use

Triggers:
- Creating or modifying a Paperclip plugin in `packages/plugins/<name>/`
- Debugging "Activation failed" / "Worker initialize failed" errors
- Authoring plugin SQL migrations
- Troubleshooting plugin manifest validation (capabilities, database namespace)
- Setting up dev-mode config for a new plugin
- Working with `definePlugin`, `runWorker`, or the plugin SDK

## Key Architecture

Each plugin lives in `packages/plugins/<name>/` with:

```
migrations/          # SQL migration files (001_*.sql, 002_*.sql, ...)
src/worker.ts        # Main entrypoint — exports definePlugin + runWorker
src/manifest.ts      # Plugin manifest (capabilities, database, entrypoints, tools)
dist/                # Built output (esbuild)
```

### Worker Entrypoint (Mandatory)

The worker **must** call `runWorker(plugin, import.meta.url)` after `definePlugin()`:

```typescript
import { definePlugin, runWorker } from "@paperclipai/plugin-sdk";

const plugin = definePlugin({
  async setup(ctx) { /* ... */ },
  // ...
});

runWorker(plugin, import.meta.url);
export default plugin;
```

Without `runWorker`, the child process exits immediately with code 0 and the
plugin enters a crash-loop — the error reads "Worker process exited (code=0,
signal=null)" with no useful diagnostic.

⚠ See pitfalls for the exact error signature.

## DB Migrations — Validation Rules

The host validates every migration statement via
`validatePluginMigrationStatement()`. Key rules:

1. **All table/index references must be fully qualified** with the plugin's
   deterministic namespace schema
   (`plugin_<namespaceSlug>_<sha256(pluginId).slice(0,10)>`).

2. **Only DDL and namespaced backfills allowed**. No DROP, TRUNCATE, DELETE,
   GRANT, REVOKE, COPY, CALL, CREATE FUNCTION, or anonymous DO blocks.

3. **`stripSqlForKeywordScan` processes quote removal BEFORE comment removal.**
   Comments containing single quotes (e.g. `-- The host's shared table`)
   cause the `'([^']|'')*'` regex to match from the apostrophe all the way
   to the next string literal in the SQL body, silently destroying the
   CREATE TABLE header and columns.

4. **`CREATE INDEX` table ref must be schema-qualified** — the validator's regex
   expects `schema.table` format after `ON`. `IF NOT EXISTS` is allowed but was
   not the issue — the Phase 3 failure was caused by unqualified table names.

### Validation flow

```
Migration SQL file
  → splitSqlStatements()  (splits on `;`, respects string quoting)
    → validatePluginMigrationStatement() per statement
      → normaliseSql()  (strip quoted strings first, then comments)
        → DDL/backfill check
        → qualified-ref check
        → namespace-scope check
      → execute on DB
```

## Dev Mode Without Secrets

For initial development before GitHub credentials are configured, the worker's
`createAuthProvider` will throw if neither PAT nor App credentials resolve.
Patch the `setup()` to tolerate dev mode:

```typescript
if (config.syncMode !== "dev" || currentSecrets.pat) {
  createAuthProvider(config, currentSecrets, ctx.http.fetch);
} else {
  ctx.logger.warn("Dev mode without PAT: no auth provider created.");
}
```

Set minimal dev config via `plugin_config`:

```json
{"syncMode":"dev","webhookSecretRef":"placeholder-hook","patSecretRef":"placeholder-pat"}
```

## Plugin Lifecycle States

| Status | Meaning |
|--------|---------|
| installed | Record exists, manifest validated, awaiting approval/activation |
| ready | Active — worker running, tools registered, migrations applied |
| error | Activation failed — check `last_error` for the root cause |
| disabled | Manually disabled via board or API |
| uninstalled | Soft-delete |

The plugin-loader reads `ready` plugins at startup. Dev-watcher hot-reloads
when the `dist/worker.js` file changes.

## Pitfalls

### 1. Silent worker exit with code 0

**Symptom:** `Worker initialize failed ... Worker process exited (code=0, signal=null)`
with no stderr.

**Root cause:** Missing `runWorker(plugin, import.meta.url)` call in worker.ts.
The module defines the plugin object but never enters the RPC event loop.

**Fix:** Add the import and call as shown in the Worker Entrypoint section above,
then rebuild: `pnpm --filter @paperclipai/plugin-<name> build`.

### 2. Comments with single quotes break migration validation

**Symptom:** `Plugin migrations may contain DDL or namespace-scoped backfill statements only`
even though every CREATE TABLE looks correct.

**Root cause:** `-- The host's shared table` — the apostrophe in `host's` is
matched as a SQL string-literal opener by `'([^']|'')*'`, which then consumes
all content up to the next `'` in the SQL body, deleting the CREATE TABLE header.

**Fix:** Remove apostrophes from comments. Write `the host shared` instead of
`the host's shared`.

### 3. Unqualified table/index names in migrations

**Symptom:** `Plugin migration objects must use fully qualified schema names`

**Fix:** Prefix every table and index reference with the deterministic namespace
(`plugin_<slug>_<hash>`). Use the same namespace value that the plugin's
`constants.ts` exports as `PLUGIN_DB_NAMESPACE`.

### 4. Config validation blocks worker startup

**Symptom:** Worker fails with Zod validation errors referencing missing fields.

**Fix:** Insert a minimal dev config into `plugin_config` (see Dev Mode section).
For a new install with no config, the worker's `ctx.config.get()` returns null
and `parseConfigOrThrow` throws.

## Testing Paperclip Plugins

Each plugin should have a corresponding `tests/` directory with vitest tests.
Key patterns (see `references/plugin-testing-patterns.md` for full details):

- **Pure functions** (compress, token estimation, config validation) — test
  boundary values, defaults, error cases. No mocking needed.
- **Tool handlers** — export `makeHandler()` and call with mock params.
  Validate `data` and `error` fields on the `ToolResult`.
- **Cache/state operations** — mock `ctx.state.get/set` with a plain object
  store. Compute cache keys by replicating `cacheKey()` logic to avoid
  fragile `expect.any(String)` patterns.
- **Config validation** — test `parseConfigOrThrow` with empty, partial,
  boundary, and invalid inputs. Verify defaults fall through correctly.

Common pitfalls:
- **State key mismatches**: don't use `expect.any(String)` as a stored cache
  key — it becomes the literal string `"expect.any(String)"` in the store.
  Compute the key explicitly.
- **Handler type casts**: tool handlers cast `params as SomeInterface`. If the
  manifest schema and worker schema disagree, the cast silently produces
  `undefined` fields. Test the handler directly to catch this.
- **Error paths**: handler validation errors return `{ error: string }`, not
  throws. Test both the `error` and `data` response branches.

Run tests from the plugin directory:

```sh
cd packages/plugins/plugin-<name>
pnpm test:run
```

## Code Review / Audit Checklist

Before merging plugin changes, run through the patterns in
`references/plugin-audit-checklist.md`. Key checks:

- Worker tool schemas match manifest tool schemas (same field names, types)
- All plugin logging uses `ctx.logger.*` (not `console.*`)
- `database` field uses consistent format with sibling plugins
- Webhook signature verification accepts raw bytes, not re-encoded strings
- No dangling or implicit globals (`crypto`, `globalThis.*`)
- Tests cover config validation, tool handlers, and error paths (see Testing section)

## Verification

After changes, verify:

```sh
pnpm --filter @paperclipai/plugin-<name> typecheck
pnpm --filter @paperclipai/plugin-<name> build
pnpm --filter @paperclipai/plugin-<name> test:run
```

Check server log for `loadAll complete ... succeeded=N` where N includes
your plugin. Check `last_error` in the DB:

```sql
SELECT plugin_key, status, substring(last_error, 1, 300) FROM plugins;
```
