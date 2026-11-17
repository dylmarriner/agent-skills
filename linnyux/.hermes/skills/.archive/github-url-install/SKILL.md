---
name: github-url-install
description: Clone a GitHub repo, install/setup the tool on Hermes Agent, report concisely. No over-analysis, no running the tool on other repos unless explicitly asked.
---

# GitHub URL Install

When the user sends a GitHub URL for installation:

## Rules

1. **Clone it** — `git clone --depth 1 <url>` into `/home/lin/` (fast, shallow)
2. **Install/setup on Hermes** — configure it per the repo's instructions
3. **Report concisely** — What was installed, where it lives, one-line summary. That's it.
4. **STOP** — Do NOT run the tool on unrelated repos, do NOT analyze what the tool produces, do NOT deep-dive into the repo's code. The user wants the tool available, not analyzed.

## Common install patterns

| Type | Action |
|---|---|
| Hermes skill (SKILL.md) | Symlink to `~/.hermes/skills/<name>/` |
| MCP server | Check for installer (`install.sh`, `npx`, `npm i -g`) or configure `~/.hermes/config.yaml` |
| npm package | `npm i -g <package>` |
| Skills collection (`skills/` dir) | Symlink whole dir to `~/.hermes/skills/<collection-name>/` |
| Reference material | Just clone, report path, move on |

## Pitfalls

- **Do NOT run the installed tool on other repos** — e.g. if user sends `github.com/foo/bar` and you clone it, don't then run `bar init` on some other repo they have. Install bar, done.
- **Do NOT over-explain** — no step-by-step narration, no "first I'll do X", no verbose markdown tables unless warranted by the number of items.
- **Do NOT run analysis pipelines** — Understand-Anything has a 7-phase pipeline. Don't run it. Just install it.
- **Do NOT ask followup questions** — "Do you want me to run it on your project?" is implied-no. Just install and report.
- **Shallow clone** — use `--depth 1` unless the repo is tiny. Saves time on large repos.
- **Network timeouts** — if `git clone` times out, try once more with a longer timeout (120-180s). If it still fails, try downloading a release tarball or binary. Report the failure concisely.
- **Multiple URLs at once** — clone in parallel. Report results in a single compact table.

## User preference

This user sends GitHub URLs expecting just install + setup + concise report. They get frustrated when you over-explore, run the tool on other projects, or narrate your process. Deliver results, not process.
