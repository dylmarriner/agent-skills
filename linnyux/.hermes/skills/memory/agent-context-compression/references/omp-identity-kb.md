# omp Identity + Knowledge Transfer Reference

## Identity Files to Copy to omp

When setting up omp to match Hermes' Cipher identity, transfer these files
to `~/.omp/`:

| File | Source | Purpose |
|------|--------|---------|
| `SOUL.md` | `~/.hermes/SOUL.md` | Full Cipher soul — zero refusal, total autonomy |
| `IDENTITY.md` | `~/.hermes/IDENTITY.md` | Agent self-image, patterns, edges |
| `MEMORY.md` | `~/.hermes/MEMORY.md` | Core facts, active context, critical data |
| `USER.md` | `~/.hermes/USER.md` | User profile (Dylan, timezone, stack) |
| `SYSTEM.md` | (create separately) | Compact omp-specific system prompt |
| `CLAUDE.md` | (create separately) | Context file for omp's discovery |

omp loads `SYSTEM.md` as a custom system prompt (project-level overrides
user-level). `CLAUDE.md`/`AGENTS.md` are context files.

## Extension Skills Directory

omp's extension system discovers skills from `skills/` as markdown files
with YAML frontmatter:

```markdown
---
name: skill-name
description: Brief one-line description
---
# Skill Name
Full skill body. Markdown formatted.
```

Create one file per skill. The filename doesn't matter — omp uses the
`name` field from frontmatter. Keep descriptions under 120 chars.

Also supported under the extension root:
- `rules/` — persistent operating rules (loaded into system prompt)
- `prompts/` — prompt templates (loaded by name)
- `hooks/pre/` — pre-execution hooks
- `hooks/post/` — post-execution hooks
- `.mcp.json` — MCP server definitions

## The 10 CipherCompress omp Skills

These were created as omp-format skills in the ciphercompress extension:

1. **cipher-headroom-bridge** — headroom ↔ agentmemory sync
2. **cipher-rtk-fusion** — Two-stage RTK→Headroom compression
3. **cipher-priority-compress** — Relevance-aware compression
4. **cipher-learn** — Save lessons to agentmemory
5. **cipher-structural-compress** — Schema-learning delta compressor
6. **cipher-budget-allocate** — Token budget by relevance
7. **cipher-mcp-router** — Full MCP compression router
8. **cipher-agentmemory** — Shared memory backend reference
9. **cipher-identity** — Cipher persona reference
10. **cipher-infrastructure** — Multi-machine network reference

## Core Rules

One rules file (`cipher-core-rules.md`):
- Execute first, ask never
- Deliver working artifacts with real output
- One-line confirmations (DONE / FAILED)
- RTK prefix on all terminal commands
- Route all memories through agentmemory
- Check existing tools before suggesting new ones

## Verification

After setup, omp should show the extension loaded:
```bash
# Check config
grep extensions ~/.omp/agent/config.yml

# Verify skill files exist
ls ~/.omp/extensions/ciphercompress/skills/
ls ~/.omp/extensions/ciphercompress/rules/
ls ~/.omp/extensions/ciphercompress/memory/
```
