# agentmemory v0.9.24 — Wiring Reference

## Install (global)

```
npm install -g @agentmemory/agentmemory
→ added 236 packages
→ agentmemory v0.9.24 at ~/.npm-global/bin/agentmemory
```

## Init

```
agentmemory init
→ Wrote ~/.agentmemory/.env
```

All keys commented out by default. No provider key = noop mode (BM25 +
synthetic compression only).

## Hermes Wiring (manual YAML)

`agentmemory connect hermes` → "YAML merge not implemented — manual install"

Edits to `~/.hermes/config.yaml`:

1. Under `mcp_servers:`, add before first existing entry:
```yaml
  agentmemory:
    command: npx
    args:
    - -y
    - '@agentmemory/mcp'
    enabled: true
```

2. Change `memory.provider:` from `''` to `agentmemory`

## OpenClaw Wiring (auto)

```
agentmemory connect openclaw
→ Backup: ~/.agentmemory/backups/openclaw-YYYY-MM-DD.json
→ Wired into ~/.openclaw/openclaw.json
```

Adds `mcpServers.agentmemory` block:
```json
"mcpServers": {
  "agentmemory": {
    "command": "npx",
    "args": ["-y", "@agentmemory/mcp"],
    "env": {
      "AGENTMEMORY_URL": "${AGENTMEMORY_URL:-http://localhost:3111}",
      "AGENTMEMORY_SECRET": "${AGENTMEMORY_SECRET:-}",
      "AGENTMEMORY_TOOLS": "${AGENTMEMORY_TOOLS:-all}"
    }
  }
}
```

Then: `systemctl --user restart openclaw-gateway`

## Skills

```
npx skills add rohitg00/agentmemory -y
→ 8 skills installed: commit-context, commit-history, forget, handoff,
  recall, recap, remember, session-history
→ Symlinked to Claude Code, OpenClaw, Hermes Agent +12 more agents
```

Overwrites any existing `remember` skill in Hermes Agent.

## Server Start

```
agentmemory                    # Daemon on :3111
agentmemory status
→ Healthy, 0 sessions, 0 observations, 0 memories, viewer :3113
```

## Demo

```
agentmemory demo
→ Seeded 6 observations across 3 sessions
→ "jwt auth middleware" → 3 hits
→ "database performance optimization" → 0 hits (semantic gap)
→ "rate limiting" → 1 hit
```

## Devin CLI Integration

Installed via official script:
```bash
curl -fsSL https://cli.devin.ai/install.sh | bash
# → Devin CLI v2026.5.26-2 at ~/.local/bin/devin
# → Automatically logged in
```

Wire agentmemory MCP:
```bash
devin mcp add agentmemory -- npx -y @agentmemory/mcp
```

Key syntax: `devin mcp add <name> -- <command> [args...]` — the `--` separator is mandatory; `--args` flags are not accepted.

Devin skill paths (checked via `devin skills paths`):
- Global: `~/.config/devin/skills/<name>/SKILL.md` and `~/.agents/skills/<name>/SKILL.md`
- Project: `.devin/skills/<name>/SKILL.md` and `.agents/skills/<name>/SKILL.md`

Since agentmemory's 8 skills land in `~/.agents/skills/`, Devin picks them up automatically. Verified with:
```bash
devin skills list | grep -E "recall|remember|recap|forget|handoff"
# → /recall [user,model] (./.agents/skills/recall)
# → /remember [user,model] (./.agents/skills/remember)
# → /recap [user,model] (./.agents/skills/recap)
# → /forget [user,model] (./.agents/skills/forget)
# → /handoff [user,model] (./.agents/skills/handoff)
# → /commit-context [user,model] (./.agents/skills/commit-context)
# → /commit-history [user,model] (./.agents/skills/commit-history)
# → /session-history [user,model] (./.agents/skills/session-history)
```

## Cross-Machine Install (macuntu via SSH)

Installed on `macuntu@100.75.23.127` (Node v24.15.0, npm 11.12.1):

```bash
ssh macuntu@100.75.23.127 "npm install -g @agentmemory/agentmemory"
# → added 236 packages

ssh macuntu@100.75.23.127 "<full-path>/agentmemory init"
# → Wrote /home/macuntu/.agentmemory/.env
```

**PATH note:** `~/.npm-global/bin` not in SSH non-interactive PATH on macuntu. Use full path `~/.npm-global/bin/agentmemory` or add dir to PATH.

Env config pushed via heredoc:
```bash
ssh macuntu@100.75.23.127 "cat > ~/.agentmemory/.env << 'EOF'
OPENAI_API_KEY=sk-<deepseek-key>
OPENAI_BASE_URL=https://api.deepseek.com/v1
AGENTMEMORY_AUTO_COMPRESS=true
AGENTMEMORY_INJECT_CONTEXT=true
CONSOLIDATION_ENABLED=true
GRAPH_EXTRACTION_ENABLED=true
EOF"
```

Started as background SSH process:
```bash
ssh macuntu@100.75.23.127 \
  "env OPENAI_API_KEY=sk-... OPENAI_BASE_URL=https://api.deepseek.com/v1 \
   AGENTMEMORY_AUTO_COMPRESS=true AGENTMEMORY_INJECT_CONTEXT=true \
   CONSOLIDATION_ENABLED=true GRAPH_EXTRACTION_ENABLED=true \
   ~/.npm-global/bin/agentmemory" &
```

Wired into macuntu's agents:
- **OpenClaw**: `~/.npm-global/bin/agentmemory connect openclaw`
- **Hermes**: manual YAML edit — added `mcp_servers.agentmemory` + set `memory.provider: agentmemory` (was `honcho`)

8 skills installed on macuntu via `npx skills add rohitg00/agentmemory -y`.

## Tailscale / socat Exposure

agentmemory's iii-engine binds to `localhost:3111` by default. For lin (SSH blocked by Tailscale policy), exposed via socat on the tailnet:

```bash
TAILSCALE_IP=$(tailscale ip -4)  # 100.93.75.87 for this machine
socat TCP-LISTEN:3111,bind=$TAILSCALE_IP,reuseaddr,fork TCP:127.0.0.1:3111 &
```

Verified reachable from another tailnet node:
```bash
curl -s http://100.93.75.87:3111/agentmemory/health
# → 200 OK
```

This lets lin's agents use `AGENTMEMORY_URL=http://100.93.75.87:3111` for shared memory.

## DeepSeek as LLM Provider

DeepSeek is OpenAI-compatible. Uncomment/add in `.env`:

```
OPENAI_API_KEY=sk-<deepseek-key>
OPENAI_BASE_URL=https://api.deepseek.com/v1
```

**dotenv override trap:** If `OPENAI_API_KEY` is already set in the parent
shell (e.g., `sk-anything` from LiteLLM), the `.env` value is silently
ignored. Start with explicit env vars or use a wrapper:

```
env OPENAI_API_KEY=sk-... OPENAI_BASE_URL=https://api.deepseek.com/v1 agentmemory
```

Create `~/.local/bin/agentmemory-start`:
```bash
#!/bin/bash
cd ~/.agentmemory
set -a; source .env; set +a
exec agentmemory "$@"
```

Then enable all 4 LLM-backed flags in `.env`:

```ini
AGENTMEMORY_AUTO_COMPRESS=true
AGENTMEMORY_INJECT_CONTEXT=true
CONSOLIDATION_ENABLED=true
GRAPH_EXTRACTION_ENABLED=true
```

Restart with the wrapper:

```
agentmemory stop --force
~/.local/bin/agentmemory-start
```

## Health Checks

### No LLM key (noop mode)

```
agentmemory status
→ Provider: ✓ llm (auto-detected from LiteLLM placeholder key)
→ Embeddings: ✓ embeddings (local BM25)
→ Consolidation: ✓
→ Graph extraction: ✗ (off)
→ Auto-compress: ✗ (off)
→ Context injection: ✗ (off)
```

### DeepSeek configured, all flags enabled

```
agentmemory status
→ Provider: ✓ llm (DeepSeek via OpenAI-compatible API)
→ Embeddings: ✓ embeddings
→ Flags:
    ✓ GRAPH_EXTRACTION_ENABLED
    ✓ CONSOLIDATION_ENABLED
    ✓ AGENTMEMORY_AUTO_COMPRESS
    ✓ AGENTMEMORY_INJECT_CONTEXT
→ Token savings: ~252 tokens saved (53% reduction)
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `agentmemory connect hermes` fails | Hermes uses YAML — must edit `~/.hermes/config.yaml` manually |
| OpenClaw CLI says "Not Found" | 9-byte stale stub at `~/.local/bin/openclaw`. Remove it, real binary is at `~/.npm-global/bin/openclaw` |
| `.env` values ignored | dotenv doesn't override existing env vars. Use `env KEY=val agentmemory` or the wrapper script |
| Gateway shows model but agent can't connect | Restart: `systemctl --user restart openclaw-gateway` |
| `openclaw-web-search` warnings | Harmless TypeScript packaging bug. Disable: `openclaw plugins disable openclaw-web-search` |

```
agentmemory status
→ Provider: ✓ llm (auto-detected from OPENAI_API_KEY env)
→ Embeddings: ✓ embeddings (auto-detected)
→ Consolidation: ✓ (on by default)
→ Graph extraction: ✗ (off — needs GRAPH_EXTRACTION_ENABLED=true)
→ Auto-compress: ✗ (needs AGENTMEMORY_AUTO_COMPRESS=true)
→ Context injection: ✗ (needs AGENTMEMORY_INJECT_CONTEXT=true)
```
