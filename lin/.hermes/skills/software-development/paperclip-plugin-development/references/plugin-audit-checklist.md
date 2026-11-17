# Plugin Audit Checklist

Common issues found when auditing Paperclip plugins. Use this as a code-review
checklist before merging plugin changes.

## Manifest / Worker Schema Mismatch

The tool schemas declared in `src/manifest.ts` and those registered in
`src/worker.ts` MUST match. A mismatch means the tool works differently
depending on whether the caller reads the manifest schema or the agent uses
the worker schema.

### Historical example (now fixed)

**Github Sync plugin** (Commit C) originally had mismatched schemas for
`connectRepository` and `disconnectRepository`:

| Source | Tool | Pre-fix Schema | Post-fix Schema |
|--------|------|----------------|-----------------|
| `manifest.ts` | `connectRepository` | `{projectId, owner, repo}` | `{repoOwner, repoName}` |
| `worker.ts` | `connectRepository` | `{repoOwner, repoName}` | `{repoOwner, repoName}` |
| `manifest.ts` | `disconnectRepository` | `{repoLinkId}` | `{repoOwner, repoName}` |
| `worker.ts` | `disconnectRepository` | `{repoOwner, repoName}` | `{repoOwner, repoName}` |

Fix applied: patched `src/manifest.ts` to change the parameter schemas to
match the worker/handler interfaces. Now both sources agree on
`{repoOwner, repoName}`.

### Verification

After making schema changes, verify no mismatches remain:

```bash
# Extract manifest tool schemas
grep -A5 '"name":' packages/plugins/plugin-*/src/manifest.ts | grep -E '"(name|required)"' | paste - - -

# Compare with worker registrations
grep -B1 'ctx.tools.register' packages/plugins/plugin-*/src/worker.ts | grep 'register('
```

### Prevention

Define parameter schemas once and import them in both places, or add a
validation step that compares `manifest.tools` schemas against worker
registrations at build time.

## Structured Logger vs console

The worker receives a `ctx.logger` with `.info()`, `.warn()`, `.error()`
methods that route through the plugin host's structured logging pipeline.
Using `console.warn()` / `console.log()` instead:

- Bypasses structured log formatting (JSON fields, timestamps, plugin IDs)
- Cannot be filtered or routed by log level by the host
- Writes to stdout/stderr which may be lost in the child process

**Found in:** `plugin-github-sync/src/sync/rate-limit.ts` line 71:
```typescript
console.warn(`GitHub API rate limit warning: ...`);
// Should be: this.logger?.warn("GitHub API rate limit warning", ...)
```

## Manifest `database` Format

Two format variants exist across plugins:

```typescript
// Variant A (token-optimizer, github-sync)
database: {
  namespaceSlug: "token_optimizer",
  migrationsDir: "./migrations",
}

// Variant B (agent-memory)
database: {
  namespace: "plugin_agent_memory",
  migrations: ["./migrations/001_init.sql"],
}
```

Variant A uses `namespaceSlug` + `migrationsDir` (SDK auto-computes the
full namespace). Variant B uses `namespace` + `migrations` array (explicit).
Using both in the same monorepo is fine provided the host SDK supports both,
but it's inconsistent — pick one format per project.

## Webhook Signature: Payload Encoding

The `verifyWebhookSignature(secret, payload, signature)` function in
`plugin-github-sync/src/webhooks/signature.ts` accepts payload as a
`string` (UTF-8). GitHub delivers raw bytes with `Content-Type:
application/json`. If the raw body is first decoded as UTF-8 then
re-encoded for HMAC, byte sequences that aren't valid UTF-8 will produce a
mismatched signature.

### Fix

Accept `Buffer | string` for `payload`, and pass the raw buffer to
`crypto.createHmac().update()` without an encoding parameter:

```typescript
export function verifyWebhookSignature(
  secret: string,
  payload: Buffer | string,
  signature: string,
): boolean {
  // ...
  const expectedBuf = crypto
    .createHmac("sha256", secret)
    .update(payload)  // Buffer or string — no encoding param
    .digest();
  // ...
}
```

## Outbound Write Audit: crypto Import

The `generateAuditId()` function in `outbound-writes.ts` calls
`crypto.randomUUID()` without importing `crypto`. In Node.js 19+,
`globalThis.crypto` (Web Crypto) is available and provides `randomUUID()`,
so this works at runtime. But it's implicit — add an explicit import for
clarity:

```typescript
import crypto from "node:crypto";
// or use globalThis.crypto.randomUUID() explicitly
```
