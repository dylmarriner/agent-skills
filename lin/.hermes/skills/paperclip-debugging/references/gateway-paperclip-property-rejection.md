# Gateway "unexpected property 'paperclip'" Error

## Error Signature

```
invalid agent params: at root: unexpected property 'paperclip'
(openclaw_gateway_request_failed)
Exit code 1
```

Full error in adapter result JSON:
```json
{"stopReason":"adapter_failed","timeoutFired":false}
```

## Root Cause

The `openclaw_gateway` adapter sends agent params to the remote OpenClaw gateway over WebSocket. The gateway validates agent params against a schema and **rejects unknown top-level properties**. The `paperclip` context object was being set as a top-level `agentParams.paperclip` property.

## Fix

**File:** `packages/adapters/openclaw-gateway/src/server/execute.ts`

Move the paperclip context JSON into the `message` text field:

```typescript
// BEFORE (broken):
agentParams.paperclip = paperclipPayload;

// AFTER (fixed):
const paperclipJson = stringifyPaperclipWakePayload(paperclipPayload);
const messageWithPaperclip = paperclipJson
  ? `${message}\n\nStandard paperclip context JSON:\n\`\`\`json\n${paperclipJson}\n\`\`\``
  : message;
// Remove agentParams.paperclip entirely
```

## Verification

- Adapter typecheck: `pnpm --filter @paperclipai/adapter-openclaw-gateway typecheck`
- Build: `pnpm --filter @paperclipai/adapter-openclaw-gateway build`
- Restart Paperclip server and retry the agent run

## Prevention

Gateway adapters MUST NOT send unknown top-level properties in agent params. The gateway's schema only accepts: `message`, `sessionKey`, `idempotencyKey`, `agentId`, `timeout`, and any properties from the agent's configured `payloadTemplate`.

Any context data that the remote agent needs (workspace info, wake context, run metadata) must be embedded in the `message` text, not as separate top-level keys.
