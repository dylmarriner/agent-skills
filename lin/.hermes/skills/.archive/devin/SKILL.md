---
name: devin
description: "Delegate coding to Devin CLI (bundled with Windsurf/Devin Desktop)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Coding-Agent, Devin, Windsurf, Exafunction, ACP, Autonomous]
    related_skills: [claude-code, codex, opencode, hermes-agent]
---

# Devin CLI — Hermes Orchestration Guide

Delegate coding tasks to [Devin CLI](https://app.devin.ai) (Exafunction's autonomous coding agent). Devin CLI is bundled inside Windsurf and Devin Desktop.

## Devin CLI Locations

Devin CLI ships as a component of Windsurf/Devin Desktop. Two sources:

### Source 1: Standard Windsurf Installation

Windsurf (v1.110.x) bundles Devin CLI at:

```
/usr/share/windsurf/resources/app/extensions/windsurf/devin/bin/devin
```

Version: `2026.5.26-0` (varies by Windsurf version)

Symlink this to PATH:

```bash
ln -sf /usr/share/windsurf/resources/app/extensions/windsurf/devin/bin/devin ~/.local/bin/devin
which devin  # verify
devin --version
```

### Source 2: Standalone Devin Desktop Tarball

The Devin Desktop download (`Devin-linux-x64-<version>.tar.gz`) is a rebranded Windsurf (same Electron IDE, same extension set, same bundled CLI). Extract and set up:

```bash
cd ~/Downloads
tar -xzf Devin-linux-x64-3.0.12.tar.gz
# Extracts to: ./Devin/  (the IDE)
# CLI lives at: ./Devin/resources/app/extensions/windsurf/devin/bin/devin

# Create a CLI wrapper in Devin's own bin/
cat > ~/Downloads/Devin/bin/devin << 'EOF'
#!/usr/bin/env bash
DIR="$(cd "$(dirname "$0")/.." && pwd)"
exec "$DIR/resources/app/extensions/windsurf/devin/bin/devin" "$@"
EOF
chmod +x ~/Downloads/Devin/bin/devin

# Create desktop entry for the IDE
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/devin-desktop.desktop << 'EOF'
[Desktop Entry]
Name=Devin
Comment=Devin Desktop IDE
Exec=/home/user/Downloads/Devin/bin/devin-desktop %F
Icon=devin-desktop
Type=Application
StartupNotify=true
Categories=Development;IDE;
MimeType=text/plain;inode/directory;
EOF

# Symlink CLI from Downloads version
ln -sf ~/Downloads/Devin/bin/devin ~/.local/bin/devin-downloads

# Clean up duplicate tarballs
rm -f ~/Downloads/Devin-linux-x64-*.tar.gz
rm -f ~/Downloads/Devin-linux-x64-*\(1\)*.tar.gz
```

The CLI inside the standalone tarball may be slightly newer than the Windsurf-bundled one (e.g., `2026.5.26-2` vs `2026.5.26-0`).

## Authentication

Devin CLI has two auth paths:

### Path 1: ACP Mode (via Windsurf API Key)

When spawned via ACP (`devin acp`), Windsurf authenticates Devin by passing a `windsurf-api-key` during the ACP `authenticate` handshake. In this mode, the CLI output shows:

```
ACP: authenticate called with method_id: windsurf-api-key
ACP: API key provided directly via authenticate meta
Authenticated bundled agent with Windsurf API key
```

This happens automatically when Windsurf starts Devin in ACP mode.

### Path 2: Standalone OAuth (Browser Flow)

When running standalone, Devin CLI requires browser-based OAuth:

```bash
devin auth login                  # Opens browser for OAuth
devin auth login --force-manual-token-flow  # Prints URL, wait for code paste
```

The manual token flow prints a URL like:
```
Visit https://app.devin.ai/auth/cli/continue?state=...&prompt=select_account&...
```

User opens URL in browser → signs in → copies code → pastes back.

**Not authenticated** = commands fail with:
```
Welcome to Devin CLI!
Error: Login canceled
```

### Environment Variables

`ACP_BACKEND` — when set, ACP mode waits for host-provided credentials. When unset (default), ACP mode falls back to env vars and stored CLI credentials if no host credentials arrive.

## ACP Integration with Hermes

Devin supports the Agent Client Protocol (ACP) for agent-to-agent communication. Hermes can delegate tasks to Devin via ACP.

### Start ACP Server

```bash
echo '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"hermes","version":"1.0"}}}' | devin acp
```

Response includes:
```json
{
  "agentCapabilities": {
    "loadSession": true,
    "promptCapabilities": {"image": true, "audio": false},
    "sessionCapabilities": {"list": {}, "additionalDirectories": {}},
    "mcpCapabilities": {"http": false, "sse": false}
  },
  "authMethods": [{"id": "windsurf-api-key", "name": "API Key", "description": "Authenticate with your API key"}],
  "agentInfo": {"name": "affogato", "title": "Affogato Agent", "version": "0.0.0-dev"}
}
```

### From Hermes delegate_task

The Hermes `delegate_task` tool supports `acp_command` and `acp_args` parameters for spawning ACP subprocesses:

```python
delegate_task(
    goal="Implement feature X",
    context="Project at /path/to/repo",
    acp_command="devin",
    acp_args=["acp"],
)
```

**Auth for ACP mode:** When spawned from Windsurf, the Windsurf application acts as ACP host and provides the API key via the `authenticate` handshake. When spawned standalone (outside Windsurf), the CLI says:

```
ACP server credential policy: ACP_BACKEND not set. Will accept host credentials if provided, otherwise fall back to env vars and stored CLI credentials.
```

### ACP Capabilities

From Devin's ACP initialization response:
- `terminal=false` — Devin ACP does not provide terminal access to the host
- `fs.read=true, fs.write=true` — can read and write files
- `subagents=true` — can spawn its own subagents
- `elicitation=true` — can ask follow-up questions
- `partial_content=true, multi_root=true` — partial content streaming, multi-root workspaces
- `windsurf_config=true` — WindSurf config access
- `message_grouping=true` — message grouping
- `mcp=true` — MCP server support

## Direct CLI Mode

For simple one-shot tasks without ACP:

```bash
devin -p "task description" --model claude-sonnet-4
devin --prompt-file /path/to/prompt.txt
devin -- task description  # interactive session
```

### Flags Reference

| Flag | Purpose |
|------|---------|
| `--prompt-file <FILE>` | Load initial prompt from a file |
| `--config <PATH>` | Override config path |
| `--permission-mode <MODE>` | `auto` (default, read-only auto-approve), `dangerous` (approve all) |
| `--sandbox` | Linux bwrap+seccomp sandbox for exec tool |
| `--model <MODEL>` | Override model |
| `-p, --print [PROMPT]` | Print mode — non-interactive, exits after response |
| `--` | Separator for prompt argument to start interactive session |

### Subcommands

| Command | Purpose |
|---------|---------|
| `auth login` | OAuth login |
| `auth status` | Check auth status |
| `mcp` | Manage MCP servers |
| `rules` | Manage agent rules (always-on context) |
| `skills` | Manage agent skills |
| `cloud` | Manage Devin Cloud resources |
| `list` / `ls` | List sessions |
| `acp` | Start ACP server over stdio |
| `update` | Check for updates |
| `version` | Print version |
| `setup` | Interactive setup wizard |
| `uninstall` | Uninstall |

### Auth Subcommands

| Command | Purpose |
|---------|---------|
| `auth login` | Login (add `--force-manual-token-flow` for headless/SSH) |
| `auth logout` | Logout |
| `auth status` | Check login status |

### Cloud Subcommands

| Command | Purpose |
|---------|---------|
| `cloud drs run` | Run a Devin Cloud session (remote sandbox) |
| `cloud drs build` | Build a Devin Cloud session |
| `cloud drs build-logs` | View build logs |
| `cloud drs build-start` | Start a build |
| `cloud drs build-wait` | Wait for build to complete |
| `cloud drs blueprint create` | Create execution blueprint |
| `cloud drs blueprint list` | List blueprints |
| `cloud drs blueprint write` | Write blueprint |
| `cloud drs sandbox create` | Create sandbox |
| `cloud drs secret create` | Create cloud secrets |
| `cloud drs whoami` | Check cloud identity |

## MCP Integration

Devin can connect to MCP servers:

```bash
devin mcp add <name> -- <command>  # Add MCP server
devin mcp list                     # List MCP servers
devin mcp remove <name>           # Remove MCP server
devin mcp get <name>              # Get MCP server details
devin mcp enable <name>          # Enable MCP server
devin mcp disable <name>         # Disable MCP server
devin mcp login <name>           # Log in to MCP server
devin mcp logout <name>          # Log out of MCP server
```

## Skills & Rules

Devin uses the same skills directory as Windsurf:

```
~/.config/devin/skills/    # Skills (context blobs)
~/.config/devin/rules/     # Rules (always-on context)
```

## Relationships

- **Windsurf → Devin CLI:** Windsurf v1.110.x bundles Devin CLI v2026.5.x. The CLI is at `extensions/windsurf/devin/bin/devin` inside the Windsurf installation.
- **Devin Desktop → Windsurf:** Devin Desktop is a rebranded Windsurf (same Electron app, same product.json, same extensions). The `product.json` shows: `nameShort: "Devin"`, `oldNameShort: "Windsurf"`, `dataFolderName: ".devin"`, `oldDataFolderName: ".windsurf"`.
- **ACP auth:** When spawned by Windsurf/Devin Desktop, Devin CLI authenticates via the Windsurf API key passed through the ACP authenticate handshake. It does NOT need separate OAuth in this mode.

## Devin Desktop (Electron IDE) — Linux GPU Crash

The Devin Desktop app (rebranded Windsurf, Electron 39+) often crashes on Linux with:

```
GPU process launch failed: error_code=1002
FATAL:gpu_data_manager_impl_private.cc:415] GPU process isn't usable. Goodbye.
```

This happens when the system lacks a GPU context the Electron version demands. Fix:

### 1. chrome-sandbox SUID Permission

First-time launch fails with the SUID sandbox error. Fix:

```bash
sudo chown root:root ~/Downloads/Devin/chrome-sandbox
sudo chmod 4755 ~/Downloads/Devin/chrome-sandbox
```

### 2. Launch with GPU Disabled

Create a launcher wrapper to pass required flags:

```bash
cat > ~/.local/bin/devin << 'SCRIPT'
#!/bin/bash
# Devin launcher – passes required GPU flags for this system
exec ~/Downloads/Devin/devin-desktop --disable-gpu --no-sandbox "$@"
SCRIPT
chmod +x ~/.local/bin/devin
```

Now `devin` from the terminal opens the Desktop app. The `--no-sandbox` flag requires the chrome-sandbox SUID fix above be done first (otherwise it still works but with reduced security).

## Pitfalls

- Devin CLI is NOT in PATH by default — you must symlink it from the Windsurf installation
- **Windsurf removed the bundled Devin CLI** in newer versions — the path `/usr/share/windsurf/resources/app/extensions/windsurf/devin/bin/devin` may no longer exist. Fall back to the standalone Devin Desktop tarball CLI
- Standalone Devin CLI requires OAuth — `devin -p` fails with "Login canceled" if not authenticated
- ACP mode works without auth when run by Windsurf (gets API key from host), but requires auth when run standalone
- The standalone Devin Desktop tarball (`Devin-linux-x64-*.tar.gz`) is 280MB compressed, ~945MB extracted — it's a full Electron IDE, not just a CLI
- There are often duplicate tarballs (`file.tar.gz` and `file (1).tar.gz`) — remove the duplicate after extraction
- The Devin CLI version inside the tarball may differ from the Windsurf-bundled one (check with `devin --version`)
- **Devin Desktop Electron crash on headless/GPU-less Linux**: the app hard-crashes with error_code=1002 unless `--disable-gpu --no-sandbox` is passed. Always create a launcher wrapper rather than running the binary directly
