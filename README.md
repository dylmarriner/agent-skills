# agent-skills

Snapshot of every skill installed for the agents on both of my machines (`lin`, `linnyux`), taken 2026-11-17. Public so the library is inspectable and portable; nothing here is application code.

## Layout

`<host>/<agent>/…` — agent names are the tool's own directory, not a person.

Every `~/.*/skills` directory on both hosts, plus the system-level `antigravity`/`windsurf` skill dirs. Agent names are the tool's own dot-directory, not a person.

`lin/`: `.hermes`, `.claude`, `.codex`, `.agents`, `.openclaude`, `.cc-switch`, `.orchestra`, `.ecc-antigravity`, `.kimi-code`, `.kiro`, `.continue`, `.cline`, `.codebuddy`, `.copilot`, `.cursor`, `.qwen`, `.trae`, `.zcode`, `.kilo`, `.kilocode`, `.gemini`, `.grok`, `.factory`, `.augment`, `.bob`, `.codeium`, `.openclaw`, `.opencode`, `.openhoof`, `.openhuman`, `.openjarvis`, `.openrig`, `.vibe`, `.moltbot`, `.understand-anything-plugin`, `openclaw/extensions/*/skills`, `devin/`, `etc-antigravity-skills/`
`linnyux/`: `.hermes`, `.claude`, `.codex`, `.agents`, `.clawdbot`, `.cline`, `openclaw/skills`, `etc-antigravity-skills/`, `etc-windsurf-skills/`

Each skill is a directory with a `SKILL.md` (YAML frontmatter: `name`, `description`) plus optional `references/`, `scripts/`, `templates/`, `assets/`.

## What is not here

- `node_modules/`, Next.js `.next/` build output, `.git/`, curator backup tarballs (`.curator_backups/`), the local hub index cache (`.hub/`).
- Repo-scoped skill folders inside individual projects (only agent-level homes are mirrored).
- Dead symlinks: 155, inherited from the source homes and left in place so their original paths are recorded — 108 `gstack*` skills point into `/media/kubuntux/DEVELOPMENT1/gstack/…` (external disk unmounted at snapshot time) and 47 point at pruned targets (an `_npx` cache and `.agents/skills` entries already deleted on the host). Their content is absent from the repo until those sources are restored and re-mirrored.

## Credentials

Every file was scanned for API-token shapes and private keys before publishing — 192 files were rewritten with the literal replaced:

| shape | replaced with |
| --- | --- |
| `sk-…`, `ghp_…`/`gho_…`, `github_pat_…`, `glpat-…` | `sk-REDACTED`, `gh_REDACTED`, `github_pat_REDACTED`, `glpat-REDACTED` |
| `AKIA…`, `AIza…`, `xox?-…` | `AKIA_REDACTED`, `AIza-REDACTED`, `xox-REDACTED` |
| JWT (`eyJ….….…`) | `JWT_REDACTED` |
| PEM private key bodies | `REDACTED` between the BEGIN/END lines |

So a skill that expects a real key needs it supplied again. Identifiers that merely start with `sk-` (CSS vars, memory keys) are untouched.

## Refreshing

```sh
rsync -a --exclude node_modules/ --exclude .next/ --exclude .curator_backups/ --exclude .hub/ --exclude .git/ \
  ~/.hermes/skills/ ./lin/.hermes/skills/
# …repeat per source, then re-run the redaction pass before committing
```
