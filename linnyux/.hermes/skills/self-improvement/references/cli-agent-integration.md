# Integrating Self-Improvement into External CLI Coding Agents

When the user has multiple CLI coding agents installed (common pattern with kiro-cli and Kilo Code), self-improvement should be available in each one. This reference covers the integration patterns.

## Target CLIs and Their Config Locations

| CLI | Config Location | Agent File Format | Hook Support |
|-----|-----------------|-------------------|--------------|
| **kiro-cli** | `~/.kiro/agents/<name>.json` | JSON with `name`, `prompt`, `tools`, `hooks`, `mcpServers` | Yes — agentSpawn, userPromptSubmit, preToolUse, postToolUse, stop |
| **Kilo Code** | `~/.config/kilo/kilo.json` | JSON embedded in `"agent"` section with `prompt`, `description`, `mode`, `permission` | No hooks — relies on agent prompt |

## Distinguishing kiro-cli vs Kilo

Beware: These are different tools with similar names.

| Feature | kiro-cli | Kilo Code |
|---------|----------|-----------|
| Binary | `~/.local/bin/kiro-cli` (Go binary, ~113M) | `~/.npm-global/bin/kilo` (npm, links to `@kilocode/cli`) |
| Config dir | `~/.kiro/` | `~/.config/kilo/` |
| Agent storage | Separate JSON files in `~/.kiro/agents/` | Inline in `~/.config/kilo/kilo.json` `"agent"` object |
| Agent selection | `kiro-cli chat --agent <name>` or set default with `kiro-cli agent set-default <name>` | `kilo --agent <name>` |
| Default agent | Set via `chat.defaultAgent` in `~/.kiro/settings/cli.json` | No explicit default — "ask" agent is built-in |
| Hook events | agentSpawn, userPromptSubmit, preToolUse, postToolUse, stop | None |
| MCP servers | Managed via `kiro-cli mcp add/remove/list` | Managed via `"mcp"` section in `~/.config/kilo/kilo.json` |
| Build time | ~570M for binaries (kiro-cli + kiro-cli-chat + kiro-cli-term + bundled bun) | npm package |

## Integration: kiro-cli

### Agent Config Structure

File: `~/.kiro/agents/<name>.json`

```json
{
  "name": "self-improving",
  "description": "Self-improving agent that logs learnings, captures errors, and creates reusable skills/agent configs from recurring patterns.",
  "prompt": "# Self-Improving Agent\n\n...instructions...",
  "tools": ["*"],
  "mcpServers": {},
  "hooks": {
    "agentSpawn": [
      {
        "command": "'/home/kubuntux/.local/bin/init-learnings.sh'"
      }
    ]
  },
  "model": null
}
```

### Hooks for Self-Improvement

| Hook Event | Purpose | Example Command |
|------------|---------|-----------------|
| `agentSpawn` | Initialize `.learnings/` directory | `init-learnings.sh` |
| `postToolUse` | Auto-log tool failures | Custom error-detector script |
| `stop` | Prompt review of learnings | Summary script |

### Setting as Default

```bash
kiro-cli agent set-default self-improving
```

### Init Script

Place at `~/.local/bin/init-learnings.sh`:

```bash
#!/bin/bash
TARGET="${1:-.}"
TARGET_DIR="$(cd "$TARGET" 2>/dev/null && pwd)"
[ ! -d "$TARGET_DIR" ] && echo "Error" && exit 1

LEARNINGS_DIR="$TARGET_DIR/.learnings"
[ -d "$LEARNINGS_DIR" ] && exit 0

mkdir -p "$LEARNINGS_DIR"
for f in LEARNINGS.md ERRORS.md FEATURE_REQUESTS.md; do
  [ ! -f "$LEARNINGS_DIR/$f" ] && echo "# $f" > "$LEARNINGS_DIR/$f"
done
```

## Integration: Kilo Code

### Agent Config Structure

Add to `"agent"` section of `~/.config/kilo/kilo.json`:

```json
{
  "agent": {
    "existing-agent": { ... },
    "self-improving": {
      "prompt": "# Self-Improving Agent\n\n...instructions...",
      "description": "Self-Improving Agent",
      "mode": "primary",
      "permission": {
        "read": "allow",
        "bash": "allow",
        "edit": "allow",
        "mcp": "allow"
      }
    }
  }
}
```

### Usage

```bash
kilo --agent self-improving
kilo --agent self-improving "log this learning"
```

### Permission Notes

Kilo's permission system uses `"allow"` / `"deny"` / `"ask"` for each permission type:

| Permission | Purpose for Self-Improvement |
|------------|------------------------------|
| `read` | Read existing `.learnings/` files and codebase context |
| `bash` | Run shell commands, check disk state, execute verifications |
| `edit` | Write to `.learnings/` files, create new agent config entries |
| `mcp` | Access MCP servers for tool integration |

For the self-improving agent, all four should be `"allow"` so it can autonomously log learnings and create skills.

## Pitfalls

- **Don't confuse the tools** — "kiro" and "kilo" sound similar. When the user says "kilo", verify by checking `~/.config/kilo/kilo.json` exists vs `~/.kiro/agents/`. Check `which kiro-cli` vs `which kilo` if uncertain.
- **kiro-cli agent configs are separate files** — create at `~/.kiro/agents/<name>.json`, NOT inside another config file.
- **Kilo agent configs are embedded** — add inside the `"agent"` object of `~/.config/kilo/kilo.json`, keeping valid JSON structure.
- **kiro-cli validates agents** — use `kiro-cli agent validate --path <file>` to check for errors.
- **Kilo JSON is extensive** — `~/.config/kilo/kilo.json` is large (many permission rules). Use `python3 -c "import json; json.load(open('...'))"` to verify JSON validity after edits.
- **Init script needs executable bit** — `chmod +x ~/.local/bin/init-learnings.sh`.
- **Only kiro-cli has hook support** — Kilo relies entirely on the agent prompt for self-improvement behavior. Make the prompt comprehensive.
