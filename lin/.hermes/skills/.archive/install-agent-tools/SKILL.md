---
name: install-agent-tools
description: Install and configure third-party tools, plugins, skills, and extensions on the agent (Hermes/OpenClaw) from GitHub URLs or package managers
---

# Install Agent Tools

When the user sends a GitHub URL (or multiple), they want the tool **installed as a capability of the agent** — not cloned and analyzed. Resist the urge to demonstrate the tool against a repo unless explicitly asked.

## Trigger

User provides any of:
- A GitHub URL (`https://github.com/org/repo`)
- Multiple URLs in a single message
- An instruction like "install this" or "set this up"
- A request to install/setup something on the agent

## Steps

1. **Check what it is.** Browse the repo or check its README. Determine:
   - Is it a Hermes skill/plugin? → symlink into `~/.hermes/skills/`
   - Is it an npm package? → `npm install -g <package>`
   - Is it a standalone binary? → use its documented install method
   - Is it a skill collection? → symlink the `skills/` directory
   - Is it a desktop app / full application? → note it, install if the binary is reasonable size
   - Is it reference material? → just clone it to `~/<repo-name>/`

2. **Install it.** Do the install — don't speculate, don't explain options, don't describe what you're about to do first. Just do it.

3. **Verify.** Quick smoke test (version check, ls the skills dir, etc.).

4. **Report.** One-line table or brief summary of what was installed and where.

## Pitfalls

- **Do NOT run the tool against a repo unless asked.** Cloning for analysis, indexing, or demonstration is off-limits without an explicit request.
- **Do NOT start the tool's pipeline.** Installing Understand-Anything means symlinking its skills — not running `/understand` against a codebase.
- **Do NOT explain what you're about to do.** Just install and report.
- **Do NOT explain what the tool does in detail.** A one-liner is fine; the user already knows what they're sending.
- **Do NOT spin up dashboards, servers, or UIs** unless the user explicitly asks to see it running.
- **Network timeouts**: big repos/binaries (>200MB) may fail on this machine's connection. Report the failure concisely, don't retry indefinitely.
- **Stop retrying failing approaches.** If something fails 2-3 times the same way (e.g. auth flow keeps generating new URLs), switch approaches or stop — don't cycle. The user will tell you when to try again. Never open browser windows without explicit permission.
- **When the user expresses frustration** ("fuck off", "stop doing X", swearing): IMMEDIATELY stop whatever you're doing, state the current state concisely in one sentence, and ask what they want instead. No apologies, no explanations of what went wrong, no "let me try another approach" — just stop and report.

## Bundled / Embedded CLIs

Some CLI tools are distributed inside desktop applications rather than as standalone packages. Detection:

1. Check if the desktop app's extension directory contains a `bin/devin` or similar (e.g. Windsurf at `/usr/share/windsurf/resources/app/extensions/windsurf/devin/bin/devin`)
2. The embedded CLI may be a different version than the standalone one
3. Auth is often shared with the parent desktop app (e.g. Windsurf passes its API key to Devin via ACP authenticate RPC)
4. Credentials format is tool-specific — check the binary's strings for field names (`windsurf_api_key`, etc.)

For bundled CLIs, prefer symlinking the embedded binary to `~/.local/bin/` rather than copying — the app update will keep the CLI current.

## Reference Files

- `references/devin-cli.md` — Devin CLI installation paths, credentials format, auth flow, and ACP mode details

This user wants URLs installed as agent tools, period. When they send `https://github.com/org/repo`, the expected action is:
```
clone → check what it is → symlink into ~/.hermes/skills/ or npm install → verify → report
```
Not:
```
clone → run tool against repo → start analyzing/indexing/understanding
```
