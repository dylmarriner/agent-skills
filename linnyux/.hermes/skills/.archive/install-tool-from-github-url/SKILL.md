---
name: install-tool-from-github-url
description: Install and setup tools, skills, and applications from GitHub repository URLs. Clone, install deps, configure for the platform, and report — no over-extension.
argument-hint: "[GitHub URL]"
---

# Install a Tool from a GitHub URL

Install and setup a tool from a GitHub URL. **Do not run the tool against other repos, do not analyze the tool's own repo with third-party tools, do not over-extend.** The user wants the tool installed and ready to use — not exercised.

## Workflow

### 0. Pre-check: repo may already exist

Before cloning, check if the repo is already present anywhere on this machine.
The user may be asking "is this already installed?" not "install this." Search
common project directories: `~/Documents/<repo-name>/`, `~/CascadeProjects/<repo-name>/`,
`/mnt/development1/<repo-name>/`. If found at any path, report the location and
skip cloning.

### 0b. Process multiple URLs in batch

If the user sends multiple URLs (in a single message or across consecutive messages), process ALL of them in the same response. Clone them in parallel where possible, report in a single summary table. Do not do one at a time and wait.

### 1. Identify the tool — skim, don't read

Open the GitHub page (browser_navigate) and **skim** the README to determine:

- **What kind of thing is it?** Hermes skill? CLI tool? pnpm/npm monorepo? Desktop app? Reference material?
- **How does it install?** npm/pip/cargo/brew/binary download? Symlink to skills dir? MCP config? `pnpm install`?
- **What platform(s) does it support?** Hermes listed?

Do NOT narrate the tool's feature list. Do NOT explain what the tool does unless asked. Just identify the install method and execute.

### 2. Clone to Documents

```bash
cd ~/Documents && git clone --depth 1 <url>
```

If shallow clone times out, try a tarball download from the main branch. If that also times out, ask the user for an upload or skip — do not waste time retrying 3+ times.

### 3. Install / setup for the platform

Match the install method to the tool type:

| Tool type | How to install |
|---|---|
| **SKILL.md repo** (single skill) | Symlink the repo dir to `~/.hermes/skills/<name>/` |
| **Multi-skill repo** (e.g. `skills/` dir) | Symlink the `skills/` dir to `~/.hermes/skills/<name>/` |
| **CLI tool** | Install via npm/pip/cargo/brew as documented. Verify with `--version` |
| **MCP server** | Install via npm, then `codegraph install --target=hermes --yes --location=global` or manually add `mcp_servers:` entry to `~/.hermes/config.yaml` |
| **Desktop app** (Electron/Tauri) | Download binary/release artifact, or if source is provided: `cd repo && pnpm install`. Note: large binaries may fail on slow connections — offer to download on another machine |
| **pnpm monorepo** (multiple apps/packages) | Run `pnpm install` — it will execute postinstall scripts (build packages, native deps). This can take 4-5 minutes. Verify with `ls node_modules` or postinstall output |
| **Reference/notebooks repo** | Just clone. No symlink or deps needed |

### 4. Verify

- For skills: check the symlink exists and SKILL.md is readable
- For CLI tools: run `<tool> --version` or `--help`
- For MCP servers: check the config.yaml entry
- For apps: confirm `pnpm install` completed (check exit code and output)

### 5. Report

One-line bullet list per URL: ✓ or ✗, where it landed, and what's next (e.g. "ready to `pnpm dev`"). No tables, no feature descriptions, no "what is X" explanation.

## Pitfalls

- **Do NOT run the installed tool as part of the install process.** If the user sends `github.com/colbymchenry/codegraph`, install codegraph — do NOT run `codegraph init -i` on some other repo unless asked.
- **Do NOT run third-party analysis tools on the cloned repo.** If the user sends a URL, the repo IS the tool being installed — not a target for analysis. Don't run `understand-anything` or `codegraph init` on the repo that was just cloned as part of installation.
- **Do NOT clone to the home directory.** Always use `~/Documents/<repo-name>/`.
- **Do NOT over-extend.** If the user sends a URL, your job is: identify → clone → install → verify → report. Not analyze, index, or exercise the tool.
- **Network timeouts on large repos.** Use `--depth 1` for the clone. For repos with many commits that still time out, try downloading from the releases page (binaries) or ask the user for a zip upload.
- **Desktop apps (Electron/Tauri) are not Hermes skills.** Don't symlink them. Just clone the repo or download the binary.
- **Verify before reporting.** A symlink that points to a non-existent path is not "installed".

## User preferences (this user)

- All repos go to `~/Documents/`. Never clone to `~/` or home directory root.
- Just install and setup. Do not use the tool against other repos unless asked explicitly.
