---
name: acpx
description: Deploy, configure, and operate acpx — the headless CLI client for the Agent Client Protocol (ACP). Covers installation, config, model selection, per-agent settings, session management, and integration with Hermes delegation, OpenCode, pi, Claude Code, and 16 other ACP agents.
category: autonomous-ai-agents
emoji: 🔌
requires:
  bins: [node, npm]
trigger: |
  User asks to set up acpx, configure ACP, delegate to coding agents,
  connect Hermes to OpenCode/pi/Claude via ACP, set default ACP models,
  or troubleshoot acpx sessions. Also relevant when user says "use acpx
  to run X agent" or "set up agent delegation".
---

# acpx — Agent Client Protocol Orchestration

acpx is a headless CLI client for the [Agent Client Protocol (ACP)](https://agentclientprotocol.com/).
It lets orchestrators (Hermes, scripts, CI) talk to coding agents over a structured
protocol instead of PTY scraping. One command surface for 16+ agents.

## Quick Install

```bash
npm install -g acpx@latest
# or run without installing:
npx acpx@latest codex "fix the tests"
```

Check version: `acpx --version`

## Configuration

Config file: `~/.acpx/config.json`. Auto-created on first run with defaults.

### Default Model

Set a cheap smart model as the default for all agents:

```json
{
  "defaultModel": "qwen/qwen3.6-plus",
  "defaultAgent": "codex"
}
```

### Per-Agent Models

Override per agent:

```json
{
  "agents": {
    "opencode":  { "model": "qwen/qwen3.6-plus" },
    "codex":     { "model": "qwen/qwen3.6-plus" },
    "pi":        { "model": "qwen/qwen3.6-plus" },
    "claude":    { "model": "anthropic/claude-sonnet-4-6" },
    "openclaw":  { "model": "qwen/qwen3.6-plus" }
  }
}
```

Override inline per call:

```bash
acpx opencode --model anthropic/claude-sonnet-4-6 "hard refactor"
```

### Permission Policy

```json
{
  "defaultPermissions": "approve-all",
  "nonInteractivePermissions": "deny",
  "authPolicy": "skip"
}
```

## Available Agents (16+)

| Agent | Command | Adapter |
|-------|---------|---------|
| pi | `acpx pi` | [pi-acp](https://github.com/svkozak/pi-acp) |
| openclaw | `acpx openclaw` | native (`openclaw acp`) |
| codex | `acpx codex` | [codex-acp](https://github.com/agentclientprotocol/codex-acp) |
| claude | `acpx claude` | [claude-agent-acp](https://github.com/agentclientprotocol/claude-agent-acp) |
| gemini | `acpx gemini` | native (`gemini --acp`) |
| cursor | `acpx cursor` | native (`cursor-agent acp`) |
| copilot | `acpx copilot` | native (`copilot --acp --stdio`) |
| droid | `acpx droid` | native (`droid exec --output-format acp`) |
| opencode | `acpx opencode` | `npx -y opencode-ai acp` |
| qoder | `acpx qoder` | native (`qodercli --acp`) |
| qwen | `acpx qwen` | native (`qwen --acp`) |
| kimi | `acpx kimi` | native (`kimi acp`) |
| kilocode | `acpx kilocode` | `npx -y @kilocode/cli acp` |
| kiro | `acpx kiro` | native (`kiro-cli-chat acp`) |
| iflow | `acpx iflow` | native (`iflow --experimental-acp`) |
| trae | `acpx trae` | native (`traecli acp serve`) |
| fast-agent | `acpx fast-agent` | `uvx fast-agent-mcp acp` |
| mux | `acpx mux` | `npx -y mux@^0.27.0 acp` |

## Sessions

ACP sessions are **persistent and multi-turn**. They survive across invocations.

```bash
# Create a session for current directory
acpx codex sessions new

# Use a named session
acpx codex -s my-feature "implement the feature"

# List sessions
acpx sessions

# Set session config
acpx codex set model 'gpt-5.2[high]'
```

### Session Scope

- Sessions are scoped to the **working directory** (cwd).
- Named sessions (`-s name`) bypass cwd scoping.
- Default TTL: 300 seconds (5 min idle before shutdown).
- Set `--ttl 0` to keep alive forever.

## Common Workflows

### One-Shot Prompt

```bash
acpx exec "summarize this repo"
acpx codex exec "fix the failing tests"
```

### Multi-Turn Task

```bash
acpx codex "find the flaky test and fix it"
# Agent investigates, finds the bug, fixes it, reports back
```

### Hermes Delegation

When Hermes delegates via ACP:

```yaml
# ~/.hermes/config.yaml
delegation:
  acp_command: acpx
  acp_args: ['--agent', 'opencode']
  provider: openrouter
```

Then `delegate_task()` in Hermes spawns `acpx --agent opencode` as a subagent.
The default agent can be changed per-task via the `acp_command` parameter.

### Set Default Agent

```json
{ "defaultAgent": "opencode" }
```

Now `acpx "do something"` routes to OpenCode by default.

## Model Selection

Cheap smart models (OpenRouter pricing):

| Model | $/M in | $/M out | Quality |
|-------|--------|---------|---------|
| `qwen/qwen3.6-plus` | $0.30 | $1.80 | Good for most tasks |
| `deepseek/deepseek-v4-flash` | $0.35 | $1.50 | Fast, good coding |
| `mistral/mistral-small-2603` | $0.50 | $1.50 | Strong reasoning |

Expensive but capable:

| Model | $/M in | $/M out | When to use |
|-------|--------|---------|-------------|
| `anthropic/claude-sonnet-4-6` | $3.00 | $15.00 | Complex refactors |
| `anthropic/claude-opus-4-6` | $5.00 | $25.00 | Architecture/design |

Set via env var: `ACPX_DEFAULT_MODEL=qwen/qwen3.6-plus`

## Troubleshooting

### "No acpx session found"

acpx searches up from the CWD for a session. Either:
1. Create a session: `acpx codex sessions new`
2. Use `-s` for a named session that isn't CWD-scoped

### "Command timed out" on sessions new

The `sessions new` command tries to connect to the agent and may hang if the
agent isn't running or the model isn't available. Use `--timeout <seconds>`:
```bash
acpx codex sessions new --timeout 30
```

### Permission denied / auth errors

Check `authPolicy` in config. Set to `"skip"` to bypass auth for local use:
```json
{ "authPolicy": "skip" }
```

### Agent not found

Ensure the agent CLI is on PATH. For OpenCode: `which opencode` should resolve.
For pi: `which pi` or point to the bun install at `~/.bun/bin/omp`.

### Model not routing through OpenRouter

acpx uses the model name to determine the provider. Models prefixed with
`provider/name` (e.g. `anthropic/claude-sonnet-4-6`) route through OpenRouter
by default. Set `OPENROUTER_API_KEY` in the environment if using OpenRouter
models.

## Upgrade

```bash
npm install -g acpx@latest
```

Check latest version on npm vs installed:
```bash
acpx --version
npm view acpx version
```

## Pitfalls

- **Sessions are CWD-scoped.** Running `acpx codex` from different directories
  creates/uses different sessions. Use `-s <name>` for cross-directory sessions.
- **Default agent is `codex`.** Change via `defaultAgent` or use explicit
  `acpx opencode "..."` per call.
- **First `sessions new` can timeout.** The agent needs to start and load
  the model. Increase `--timeout` or ensure the model is available.
- **Config file is JSON, not YAML.** Don't use `.yaml` extension.
- **No global model config across all agents** (as of v0.10.0). Set per-agent
  or use `defaultModel` + per-agent overrides.
