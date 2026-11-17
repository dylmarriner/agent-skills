# Context-window plumbing (openclaude / any agent CLI)

"It won't do <huge> context" is almost never the value the user set. The value
resolves fine; something else still assumes the old default.

## Resolution order (openclaude `resolveContextWindowForModel`)

1. `CLAUDE_CODE_MAX_CONTEXT_TOKENS` (internal, `USER_TYPE=ant`)
2. session override — `/set-context-window [model] <tokens>`
3. `[1m]` model suffix
4. runtime limits / provider catalog (`CLAUDE_CODE_OPENAI_CONTEXT_WINDOWS`
   exact then prefix, `modelLimits` in settings.json)
5. 1M beta header / experiment / internal model config
6. default

`modelLimits` schema is `z.number().int().positive()` — up to
`Number.MAX_SAFE_INTEGER`, so a billion always validates. Check the resolution
`source`, not the number.

## The cap that actually bites: message count

Compaction has two independent triggers — token threshold and **message count**.
The message-count default is a flat 200 (hard cap 1000) regardless of window, so
a 1e9 window force-compacts at ~0.02% usage forever. Rule: any per-turn cap
expressed in *messages* or *turns* must scale with the window, e.g.

```ts
const TOKENS_PER_COMPACTED_MESSAGE = 1_000
export function scaleMessageLimitForContextWindow(limit: number, window?: number) {
  if (limit <= 0 || !window || window <= 0) return limit
  return Math.max(limit, Math.ceil(window / TOKENS_PER_COMPACTED_MESSAGE))
}
```

`max(limit, ceil(window/1000))` leaves 200k windows at exactly 200 (no behaviour
change) and gives 1e6 messages at 1e9. Apply it inside the shared trigger helper
(one place both the query loop and the `/ctx_viz` report route through) and pass
the resolved window in at the two call sites.

## Verify offline, no credentials

1. Start `scripts/fake_openai_stub.py` (port 8899).
2. Run the CLI against it with a fake window:

```bash
CLAUDE_CODE_USE_OPENAI=1 OPENAI_BASE_URL=http://127.0.0.1:8899/v1 \
OPENAI_MODEL=fake-model OPENAI_API_KEY=x \
CLAUDE_CODE_OPENAI_CONTEXT_WINDOWS='{"fake-model":1000000000}' \
  timeout -k 5 120 openclaude -p "/ctx_viz"
```

The report prints window, source, auto-compact threshold and the message-count
trigger — that line is where the old assumption shows up. Re-run with `200000`
to prove no regression for normal models.

## Gotchas

- `/ctx_viz` and `/set-context-window` work headless through `-p "<slash command>"`;
  no TUI needed.
- `dist/` is a bundle: source edits do nothing until rebuilt (`bun run build`,
  minutes; run it in the background with notify). Verify the symbol made it into
  the bundle before re-testing behaviour.
- Don't stop at "the CLI accepts the number" — a window is only real if the
  compaction/turn/message budgets scale with it, and the provider actually
  accepts that many tokens.
