# Connecting Installed Tools to Hermes

When the user sends GitHub URLs and explicitly says "connect them to you so you can use them" (or similar), the default install-and-report is NOT enough. You must also integrate the tool into Hermes' runtime so it's callable in future sessions.

## Integration Patterns Per Tool Type

| Tool type | How to connect to Hermes |
|-----------|--------------------------|
| **Python library** | `pip install -U <pkg>` (or `uv pip install`). Verify with `import <pkg>`. If the library has a skill file (SKILL.md) in its repo, symlink it to `~/.hermes/skills/<name>/`. |
| **CLI tool** (npm/pipx/cargo) | Install globally. Verify with `--version`. If the tool is a framework/agent system (e.g. SuperClaude), it may install to its target platform's config dir (~/.claude/ for Claude Code) — report this rather than hacking a bridge. |
| **MCP server** | Run the built-in installer (e.g. `codegraph install --target=hermes`) or manually add an `mcp_servers:` entry to `~/.hermes/config.yaml` via `hermes config set`. Requires restart. |
| **Hermes skill** (SKILL.md) | Symlink the skill dir or file to `~/.hermes/skills/<name>/`. |
| **Agent rules / custom instructions** (e.g. `.claude/` files) | These are platform-specific (Claude Code, Cursor, Windsurf). Report where they landed, don't rewrite them for Hermes unless the structure is compatible. |

## What to Report

After installing + connecting, give a simple status table:

| Tool | Where | Status |
|------|-------|--------|
| **tool-name** | path + install method | ✅ Library/CLI/Skill ready. What to do next to use it. |

One sentence per tool. No feature descriptions. No step-by-step narration.

## Pitfalls

- **Do NOT default to connecting.** The default is install-and-report. Only connect when the user explicitly says "connect to you" or "set up so you can use it."
- **Do NOT rewrite platform-specific configs.** If a tool installs to `~/.claude/` (Claude Code), don't move it — just report the path.
- **Do NOT run the tool against other projects** as part of installation unless asked. Installing and verifying are separate from exercising.
- **Some MCP gateways fail** (dead download URLs, missing API keys). Report the failure and move on. Don't spend time debugging third-party infrastructure.
