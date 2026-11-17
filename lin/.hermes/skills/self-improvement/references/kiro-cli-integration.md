# Kiro CLI Integration

Setup guide for integrating self-improvement + skill-creation capabilities with Kiro CLI.

## Overview

Kiro CLI is a Go-based AI coding agent CLI. Unlike OpenClaw (workspace-injected prompts) or Claude Code (hook scripts), Kiro uses **JSON agent configs** with a built-in `prompt` field and event-driven hooks. This reference covers how to add self-improving behavior as a Kiro agent config.

## Agent Config Format

Kiro agent configs are JSON files stored at:

- **Global**: `~/.kiro/agents/<name>.json`
- **Workspace**: `<project>/.kiro/agents/<name>.json`

### Full Schema

```json
{
  "name": "agent-name",
  "description": "Short description shown in agent list",
  "prompt": "# Agent Prompt\n\nInstructions here...",
  "tools": ["*"],
  "mcpServers": {},
  "hooks": {},
  "model": null
}
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Lowercase-hyphenated name, matches filename without `.json` |
| `description` | Yes | Shown in `kiro-cli agent list` |
| `prompt` | No | System prompt / instructions for the agent |
| `tools` | No | Tool allowlist: `["*"]` for all, or specific tools |
| `mcpServers` | No | MCP server configurations (keyed by server name) |
| `hooks` | No | Event-driven hooks (see below) |
| `model` | No | Model override (null = use default) |

## Available Tools

Set `"tools": ["*"]` to grant all tools, or restrict to specific ones:

```
read          - Read files
write         - Write/edit files
shell         - Run shell commands
grep          - Search file contents
glob          - Pattern file search
knowledge     - Knowledge base queries
thinking      - Chain-of-thought reasoning
todo          - Task checklist management
delegate      - Sub-agent delegation
aws           - AWS operations
report        - Generate reports
introspect    - Self-analysis
@server/tool  - MCP server tools (prefixed with @)
```

## Event Hooks

Hooks fire on lifecycle events. Each hook is a command string executed when the event triggers.

### Available Events

| Event | When It Fires |
|-------|---------------|
| `agentSpawn` | Agent session starts |
| `userPromptSubmit` | User sends a prompt |
| `preToolUse` | Before a tool executes |
| `postToolUse` | After a tool executes |
| `stop` | Session ends |

### Hook Config Format

```json
"hooks": {
  "agentSpawn": [
    {
      "command": "'/path/to/script.sh' 'arg1' 'arg2'"
    }
  ]
}
```

Commands use single-quote-wrapped arguments to avoid shell escaping issues.

## Setup: Self-Improving Agent

### 1. Create the Config

```bash
kiro-cli agent create self-improving
```

This creates `~/.kiro/agents/self-improving.json`. Edit it to add the prompt and hooks.

### 2. Add the Prompt

The `prompt` field should instruct the agent to:
- Log learnings to `.learnings/LEARNINGS.md` when corrected or discovering better approaches
- Log errors to `.learnings/ERRORS.md` on command failures
- Log feature requests when user asks for missing capabilities
- Create new agent configs from recurring patterns

See [Self-Improvement Agent Template](#self-improvement-agent-template) below.

### 3. Add Bootstrap Hook

```json
"hooks": {
  "agentSpawn": [
    {
      "command": "'/path/to/init-learnings.sh'"
    }
  ]
}
```

This auto-creates `.learnings/` in the workspace on agent start.

### 4. Set as Default

```bash
kiro-cli agent set-default self-improving
```

### 5. Validate

```bash
kiro-cli agent validate --path ~/.kiro/agents/self-improving.json
kiro-cli agent list
```

The starred entry shows the default agent.

## Self-Improvement Agent Template

Below is the essential prompt content for a self-improving Kiro agent. It combines two capabilities:

### Capability 1: Learning & Error Capture

Log to `.learnings/` whenever:

| Trigger | File | ID Prefix |
|---------|------|-----------|
| User corrects you | `LEARNINGS.md` | `LRN-` |
| Command/operation fails | `ERRORS.md` | `ERR-` |
| Better approach discovered | `LEARNINGS.md` | `LRN-` |
| User requests missing capability | `FEATURE_REQUESTS.md` | `FEAT-` |
| Knowledge was outdated | `LEARNINGS.md` | `LRN-` |

Log format:

```
## [LRN-YYYYMMDD-XXX] brief_title

**Logged**: ISO-8601 timestamp
**Priority**: low | medium | high | critical
**Status**: pending
**Area**: frontend | backend | infra | tests | docs | config

### Summary
One-line summary

### Details
Full context

### Suggested Action
Specific fix or improvement
---
```

Priority guidelines:
- **critical**: Blocks core functionality, data loss, security
- **high**: Significant impact, common workflows
- **medium**: Workaround exists
- **low**: Minor inconvenience

### Capability 2: Skill Creation (Agent Configs from Learnings)

When a learning is valuable and recurring, promote it to a new Kiro agent config:

**Extraction criteria** (any one triggers creation):
- Recurring issue (linked 2+ similar entries)
- Verified working solution
- Non-trivial debugging required to discover
- Broadly applicable (not project-specific)
- User says "save this as a skill"

**Extraction workflow**:
1. Distill the learning into clear instructions
2. Create `~/.kiro/agents/<skill-name>.json`
3. Update original learning entry status to `promoted`

**Skill config template**:
```json
{
  "name": "skill-name",
  "description": "Clear trigger description",
  "prompt": "# Skill Title\n\nInstructions...\n\n## When to Use\n- Condition 1\n- Condition 2\n\n## Steps\n1. Step one\n2. Step two\n\n## Pitfalls\n- Watch out for X\n\n## Key Rules\n- ALWAYS do this\n- NEVER do that",
  "tools": ["*"],
  "mcpServers": {}
}
```

### Location Priority

Check for existing `.learnings/` in order:
1. Current project workspace (`<project>/.learnings/`)
2. Home directory (`~/.learnings/`)

### Fallback

If no `.learnings/` exists, use global `~/.learnings/`. The `init-learnings.sh` script auto-creates these when the agent starts.

## CLI Reference

```bash
# Create an agent config
kiro-cli agent create <name>

# List all agents (* = default)
kiro-cli agent list

# Validate a config file
kiro-cli agent validate --path ~/.kiro/agents/<name>.json

# Set default agent
kiro-cli agent set-default <name>

# Edit an existing config
kiro-cli agent edit <name>

# Launch chat with specific agent
kiro-cli chat --agent <name>

# MCP server management
kiro-cli mcp add <name> -- <args>
kiro-cli mcp list
kiro-cli mcp remove <name>

# Settings
kiro-cli settings list              # View all settings
kiro-cli settings open              # Open settings file
kiro-cli settings <key> <value>     # Set value
```

## Settings

Kiro stores settings at `~/.kiro/settings/cli.json` (global) or `<project>/.kiro/settings/cli.json` (workspace):

```json
{
  "chat.enableKnowledge": true,
  "chat.enableThinking": true,
  "chat.enableTodoList": true,
  "chat.enableCheckpoint": true,
  "chat.enableDelegate": true,
  "chat.defaultAgent": "self-improving"
}
```

## Knowledge Bases

Kiro knowledge base data lives at `~/.local/share/kiro-cli/knowledge_bases/kiro_default/`. The `chat.enableKnowledge` settings flag must be true (default) for the `knowledge` tool to function.

## Directory Structure

```
~/.kiro/
├── agents/
│   ├── agent_config.json.example   # Example with all fields documented
│   ├── self-improving.json         # Custom agent config
│   └── <other-agents>.json
├── settings/
│   └── cli.json                    # CLI settings
├── sessions/
│   └── cli/
│       ├── <uuid>.jsonl            # Session transcripts
│       ├── <uuid>.json             # Session metadata
│       └── <uuid>/tasks/           # Session tasks (numbered .json)
├── .cli_bash_history               # CLI bash history
~/.local/share/kiro-cli/
├── bun                            # Bundled Bun runtime
├── tui.js                         # TUI JavaScript bundle
├── data.sqlite3                   # SQLite database
└── knowledge_bases/
    └── kiro_default/
        └── models/
~/.learnings/                       # Global learnings directory
├── LEARNINGS.md
├── ERRORS.md
└── FEATURE_REQUESTS.md
```

## Pitfalls

- Agent config JSON must be valid JSON — trailing commas break it
- The `name` field must match the filename (`self-improving.json` → `"name": "self-improving"`)
- Hook commands use single-quoted arguments: `'command' 'arg'` not `command arg`
- Agent changes take effect on NEXT session start, not immediately
- `kiro-cli agent validate` uses `--path` flag, not positional arg
- The `prompt` field is optional; without it the agent behaves as the built-in default
- `"tools": ["*"]` grants all tools — omit or list specific tools to restrict
