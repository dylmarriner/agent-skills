# Error transcript: GitHub Sync plugin activation

## Issue 1: Manifest capability validation

**Error:**

```
Activation failed: Invalid plugin manifest: capabilities:
  Capability 'database.namespace.migrate' is required when database migrations are declared;
  Capability 'database.namespace.read' is required when database migrations are declared
```

**Root cause:** Plugin's `src/manifest.ts` was missing `"database.namespace.migrate"` and
`"database.namespace.read"` from the capabilities array. The JSON Schema validator
enforces that if `manifest.database.migrationsDir` is non-null, these two capabilities
must be present.

**Fix:** Add to capabilities:
```typescript
"database.namespace.migrate",
"database.namespace.read",
```

## Issue 2: Migration SQL comment with single quote

**Error:**

```
Plugin migrations may contain DDL or namespace-scoped backfill statements only
```

Affected file: `001_init.sql`, line 143:
```sql
-- The host's shared `plugin_webhook_deliveries` table records every inbound
```

**Root cause:** `stripSqlForKeywordScan()` runs `'([^']|'')*'` (remove quoted strings)
BEFORE `--.*$` (remove line comments). The apostrophe in `host's` is matched as
a SQL string-literal opener, consuming all content up to the next `'` in a
DEFAULT value like `'received'`, which silently deletes the entire CREATE TABLE
and most column definitions.

**Reproduction (standalone):**
```javascript
function stripSqlForKeywordScan(input) {
  return input
    .replace(/'([^']|'')*'/g, "''")     // ← runs first, catastrophically
    .replace(/--.*$/gm, '')              // ← runs second, too late
    .replace(/\/\*[\s\S]*?\*\//g, '');
}
```

**Fix:** Remove apostrophe: `host's` → `host shared`

## Issue 3: Missing runWorker() call

**Error:**

```
Activation failed: Worker initialize failed for "<uuid>": Worker process exited (code=0, signal=null)
```

**Root cause:** `src/worker.ts` only called `definePlugin({...})` and exported it as
default, but never called `runWorker(plugin, import.meta.url)`. The paperclip SDK's
`runWorker` sets up the stdin/stdout JSON-RPC readline loop that keeps the worker
process alive and responsive to host commands. Without it, the module evaluation
completes and the process exits normally (code 0).

**Reference pattern (LLM Wiki plugin):**
```typescript
import { definePlugin, runWorker } from "@paperclipai/plugin-sdk";

runWorker(plugin, import.meta.url);
export {
  worker_default as default
};
```

**Fix:** Add to source:
```typescript
import { definePlugin, runWorker } from "@paperclipai/plugin-sdk";
// ... definePlugin ...
runWorker(plugin, import.meta.url);
export default plugin;
```

## Issue 4: Phase 3 migration — unqualified table names

**Error (same as Issue 2):**

```
Plugin migrations may contain DDL or namespace-scoped backfill statements only
```

**Root cause:** `003_phase3.sql` used unqualified table names:
```sql
CREATE TABLE IF NOT EXISTS gh_issue_ticket_links ( ... )
CREATE INDEX IF NOT EXISTS gh_issue_ticket_links_repo_link_id_idx ON gh_issue_ticket_links(repo_link_id)
```

**Fix:** Use fully qualified schema prefix and remove `IF NOT EXISTS`:
```sql
CREATE TABLE plugin_github_sync_60491d4d6b.gh_issue_ticket_links ( ... )
CREATE INDEX gh_issue_ticket_links_repo_link_id_idx
  ON plugin_github_sync_60491d4d6b.gh_issue_ticket_links(repo_link_id)
```

## Issue 5: Cross-field Zod validation on empty config

**Error:**

```
GitHub Sync plugin config is invalid:
  - patSecretRef: syncMode=dev requires either patSecretRef OR full App credentials
```

Then after adding patSecretRef:
```
Private key is required for GitHub App authentication.
```

**Root cause:** `instanceConfigZodSchema` has a `.superRefine()` rule requiring
PAT secret or App credentials in dev mode. When `ctx.secrets.resolve()` fails
(because the ref points to a non-existent secret), `pat` is undefined, and
`createAuthProvider()` falls through to the App auth path which also fails.

**Fix:** Patch worker to tolerate dev mode without resolved PAT (warn instead of throw).

## DB queries used during debugging

```sql
-- Check plugin status
SELECT plugin_key, status, last_error FROM plugins;

-- Check namespace status
SELECT * FROM plugin_database_namespaces WHERE plugin_key LIKE '%github%';

-- Check migration records
SELECT * FROM plugin_migrations WHERE plugin_key LIKE '%github%';

-- Reset for retry
UPDATE plugins SET status = 'ready', last_error = NULL, updated_at = NOW()
  WHERE plugin_key = 'paperclip-plugin-github-sync';
UPDATE plugin_database_namespaces SET status = 'pending', updated_at = NOW()
  WHERE plugin_key = 'paperclip-plugin-github-sync' AND status = 'migration_failed';
DELETE FROM plugin_migrations WHERE plugin_key = 'paperclip-plugin-github-sync' AND status = 'failed';

-- Set dev config
INSERT INTO plugin_config (plugin_id, config_json) VALUES (
  '<uuid>', '{"syncMode":"dev","webhookSecretRef":"placeholder-hook","patSecretRef":"placeholder-pat"}'
);

-- Check manifest in DB
SELECT jsonb_pretty(manifest_json) FROM plugins WHERE plugin_key LIKE '%github%';

-- Find postgres port
ls /tmp/.s.PGSQL*
