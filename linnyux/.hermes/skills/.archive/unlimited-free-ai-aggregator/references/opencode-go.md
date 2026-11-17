# OpenCode GO / ZEN Provider

**Base URL:** `https://opencode.ai/zen/go/v1`
**Format:** openai (standard)
**Key:** Same key works for both Go and ZEN

## Models (as of Jul 2026)

```
minimax-m3, minimax-m2.7, minimax-m2.5
kimi-k2.7-code, kimi-k2.6, kimi-k2.5
glm-5.2, glm-5.1, glm-5
deepseek-v4-pro, deepseek-v4-flash
qwen3.7-max, qwen3.7-plus, qwen3.6-plus, qwen3.5-plus
mimo-v2-pro, mimo-v2-omni, mimo-v2.5-pro, mimo-v2.5
hy3-preview
```

## Rate Limits
- **Paid subscription:** $10/month ($5 first month)
- **Monthly usage cap** — once hit, returns `GoUsageLimitError` with message "Monthly usage limit reached. Resets in N days."
- **~500 RPD** per model (estimated)

## Key Info
- Key format: `sk-...` (visible via `opencode.ai/zen` web interface)
- The key is shared between OpenCode ZEN (web IDE) and OpenCode GO (API subscription)
- Monthly limit resets ~26th of each month
- `hermes config check` recognizes env vars: `OPENCODE_ZEN_API_KEY`, `OPENCODE_GO_API_KEY`

## Commercial Usage
OpenCode GO is a paid service. Not "free unlimited" — but cheap enough ($10/mo) to function as a reliable paid fallback provider alongside truly free ones.
