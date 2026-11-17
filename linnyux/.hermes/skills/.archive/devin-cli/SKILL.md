---
name: devin-cli
description: "Discover, authenticate, and use the Devin CLI bundled with Windsurf. Covers finding the binary, auth, ACP mode for Hermes subagent integration, and common commands."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
tags: [devin, windsurf, acp, agent, cli]
---

# Devin CLI

## Overview

Devin CLI is bundled inside the Windsurf IDE installation. It is **not** in PATH by default. It supports ACP (Agent Client Protocol) for agent-to-agent delegation, as well as direct CLI usage.

## Installation

### Standalone Install (CLI-only, no Windsurf required)

```bash
curl -fsSL https://cli.devin.ai/install.sh | bash
```

Installs to `~/.local/bin/devin`. If a previous binary exists and blocks the install:

```bash
rm -f ~/.local/bin/devin && curl -fsSL https://cli.devin.ai/install.sh | bash
```

After install, run `devin login` to authenticate.

### From Windsurf IDE

Devin CLI is bundled **inside the Windsurf IDE** at:

```
/usr/share/windsurf/resources/app/extensions/windsurf/devin/bin/devin
```

Or inside a **standalone Devin Desktop** download (if present) at:

```
~/Downloads/Devin/resources/app/extensions/windsurf/devin/bin/devin
```

Both contain the same Devin CLI binary (versions may differ).

To add to PATH, symlink it:

```bash
ln -sf /usr/share/windsurf/resources/app/extensions/windsurf/devin/bin/devin ~/.local/bin/devin
```

### Devin Desktop App (Separate Install)

If `Devin-linux-x64-<version>.tar.gz` is in Downloads:
```bash
cd ~/Downloads
tar -xzf Devin-linux-x64-<version>.tar.gz
# Extracts to ~/Downloads/Devin/

# Symlink the CLI
ln -sf ~/Downloads/Devin/bin/devin ~/.local/bin/devin-downloads

# Create desktop entry
cat > ~/.local/share/applications/devin-desktop.desktop << 'EOF'
[Desktop Entry]
Name=Devin
Comment=Devin Desktop IDE
Exec=/home/$USER/Downloads/Devin/bin/devin-desktop %F
Icon=devin-desktop
Type=Application
StartupNotify=true
Categories=Development;IDE;
MimeType=text/plain;inode/directory;
EOF
```

## Verification

```bash
# Check version
devin --version
# Expected: "devin 2026.5.26-N (commithash)"

# Check auth status
devin auth status
# Expected: "Logged in" or "Not logged in."
```

## Authentication (PKCE OAuth Flow)

Devin uses a **PKCE OAuth flow**. Each invocation of `devin auth login` generates a UNIQUE state + challenge URL.

### ⚠️ CRITICAL: ONE-SHOT RULE

**Do NOT run `devin auth login` more than once per auth attempt.** Each run generates a new PKCE challenge, invalidating the previous one. The code the user pastes only works with the session that generated the URL. Killing and restarting the process = invalidating the user's code.

### Terminal/SSH Environments

Use `--force-manual-token-flow` for environments without a browser:

```bash
devin auth login --force-manual-token-flow
```

### Correct Flow from Hermes

1. **Start the auth process ONCE in background with PTY:**
```bash
devin auth login --force-manual-token-flow
# background=true, pty=true, timeout=120
```

2. **Capture the URL** from the process output. It looks like:
```
https://app.devin.ai/auth/cli/continue?state=<uuid>&prompt=select_account&code_challenge=<base64>&code_challenge_method=S256
```

3. **Give the URL to the user** — they open it in a browser and authenticate.

4. **WAIT.** Do NOT poll, kill, or restart the process. The user will respond with a code.

5. **Submit the code** via `process(action='submit', data='<code>')`.

6. **Let it complete.** Poll/wait for the process to exit. Credentials saved to:
   `/home/lin/.local/share/devin/credentials.toml`

### If Auth Fails

If the code doesn't work (wrong session):
- Kill the stuck process
- Start a fresh auth session
- Give the user the **new URL** (old code won't work)
- Wait for a **new code**

### Windsurf Integration

When Devin is spawned via ACP from Windsurf, Windsurf passes its API key directly:
```
ACP: authenticate called with method_id: windsurf-api-key
ACP: API key provided directly via authenticate meta
```

When running standalone (not inside Windsurf), it falls back to stored CLI credentials:
```
ACP_BACKEND not set. Will accept host credentials if provided,
otherwise fall back to env vars and stored CLI credentials.
```

Credentials are stored at `~/.local/share/devin/credentials.toml`.

## Common Commands

| Command | Description |
|---------|-------------|
| `devin -- <prompt>` | Start interactive session with prompt |
| `devin -p <prompt>` | Non-interactive mode: run and exit |
| `devin auth status` | Check login status |
| `devin auth login` | Authenticate |
| `devin list` | List sessions in current directory |
| `devin rules` | Manage agent rules (always-on context blobs) |
| `devin skills` | Manage agent skills |
| `devin mcp` | Connect and log in to MCP servers |
| `devin version` | Print version |
| `devin update` | Check for updates |

## Permission Modes

```bash
# Auto-approve read-only tools (default)
devin -p "analyze this code"

# Auto-approve ALL tools (dangerous — use with caution)
DEVIN_PERMISSION_MODE=dangerous devin -p "fix the bugs"
```

## ACP Mode (Agent Client Protocol)

Devin can run as an ACP server over stdio, enabling Hermes to delegate tasks to it as a subagent:

```bash
devin acp
```

The Hermes `delegate_task` tool supports `acp_command` parameter for ACP delegation:

```python
# Within Hermes, delegate a coding task to Devin
delegate_task(
    goal="implement the user authentication module",
    context="SCOS project at /home/lin/Documents/SCOS",
    toolsets=["terminal", "file"],
    acp_command="devin",
    acp_args=["acp"],
)
```

**Important:** Devin ACP mode runs the default agent type. To use a specific agent type (e.g. `summarizer`), pass `--agent-type summarizer`.

## Model Selection

```bash
DEVIN_MODEL=claude-sonnet-4 devin -p "analyze this code"
```

Available models include: `claude-sonnet-4`, `claude-opus-4.6`, `opus`, `codex`.

## Skills Directory

Devin skills (synced from Windsurf) are stored at:

```
~/.config/devin/skills/
```

These are similar to Hermes skills — slash commands and agent-triggered context blobs.

## Pitfalls

- Devin is NOT in PATH after installing Windsurf — you must find the binary or symlink it
- ACP mode requires `devin auth login` first
- Standalone install via `curl -fsSL https://cli.devin.ai/install.sh | bash` — if old binary exists, `rm -f ~/.local/bin/devin` first
- The `devin` binary is the Windsurf-bundled version, not a standalone install
- Auth credentials path: `~/.local/share/devin/credentials.toml`
- Config path: `~/.config/devin/config.json`
- Version checked by: `devin version`
