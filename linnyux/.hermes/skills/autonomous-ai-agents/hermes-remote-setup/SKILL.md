---
name: hermes-remote-setup
description: "Provision a remote Hermes agent: deploy plugins, install CLI tools (Obelisk/RTK), enable MCP servers, wire to shared services (Nexus), restart gateway, and verify. Covers SSH-based remote deployment across the fleet."
version: 1.0.0
author: Hermes
metadata:
  hermes:
    tags: [hermes, remote, setup, deployment, ssh, provisioning, nexus, obelisk]
    related_skills: [hermes-agent, tailscale, ai-provider-cross-config]
---

# Hermes Remote Setup

Provision a remote Hermes instance with plugins, CLI tools, MCP servers, and service connections. SSH-based deployment across the fleet (macuntu, lin, etc.).

---

## Trigger

Use when the user says any of:
- "connect <host> to nexus"
- "install obelisk on <host>"
- "add plugin to hermes on <host>"
- "copy config/tool to <host>"
- "setup hermes on <host>"
- "deploy <tool> to <host>"

## Prerequisites

1. **SSH access** must work (`ssh <host>` succeeds without interactive password)
2. **Tailscale** connectivity for remote hosts (`tailscale status` shows the host)
3. **SSH PATH caveat**: non-interactive SSH shells do NOT source `.bashrc` or `.profile`. Always prefix remote commands with `export PATH=$HOME/.local/bin:$PATH && <command>`
4. Verify basics first if unsure:
   ```bash
   ssh <host> "whoami; uname -a; which rustc cargo 2>/dev/null; cat ~/.local/bin/hermes 2>/dev/null && echo 'hermes binary exists' || echo 'no hermes'"
   ```

## Task: Connect Nexus to Remote Hermes

### 1. Create nexus.env

Use SCP (not heredoc/echo) to avoid shell-escaping issues with the secret:

```python
import subprocess, tempfile
content = """NEXUS_URL=http://100.93.75.87:7777/mcp
NEXUS_SECRET=***n
"""
with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
    f.write(content)
    tmp = f.name
subprocess.run(["scp", tmp, f"{host}:/home/{host_user}/.hermes/nexus.env"], ...)
os.unlink(tmp)  # clean up local temp file
```

**Verify** with hexdump to confirm no truncation:
```bash
ssh <host> "xxd ~/.hermes/nexus.env"  # confirms exact bytes
```

### 2. Copy plugin directory

```bash
scp -r ~/.hermes/plugins/nexus-memory <host>:~/.hermes/plugins/nexus-memory
```

Check that both `plugin.yaml` and `tools.py` landed:
```bash
ssh <host> "ls ~/.hermes/plugins/nexus-memory/"
```

### 3. Enable plugin in config.yaml

Find the `plugins.enabled` list and add the plugin:
```bash
ssh <host> "sed -i '/- obelisk-rewrite/a\\    - nexus-memory' ~/.hermes/config.yaml"
```

Or use the more precise `grep -n` approach to find the right line first, then `sed`.

### 4. Restart Hermes gateway

```bash
ssh <host> "export PATH=\$HOME/.local/bin:\$PATH && hermes gateway restart"
```

### 5. Verify Nexus connectivity

```bash
ssh <host> 'curl -s --connect-timeout 5 -X POST http://100.93.75.87:7777/mcp \
  -H "Authorization: Bearer *** \
  -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\",\"params\":{}}" | \
  python3 -m json.tool | head -20'
```

---

## Task: Install Obelisk on Remote Hermes

### 1. Deploy binary

SCP the pre-built binary:
```bash
scp ~/.local/bin/obelisk <host>:~/.local/bin/obelisk
ssh <host> "chmod +x ~/.local/bin/obelisk; ls -la ~/.local/bin/obelisk"
```

### 2. Wire for Hermes and all available agents

```bash
ssh <host> "export PATH=\$HOME/.local/bin:\$PATH && obelisk install hermes && obelisk install codex && obelisk install claude"
```

This installs the `obelisk-rewrite` Hermes plugin (pre_tool_call hook), the Codex hook, and the Claude Code hook.

### 3. Enable the Hermes plugin and verify

```bash
ssh <host> "export PATH=\$HOME/.local/bin:\$PATH && hermes plugins enable obelisk-rewrite"
```

---

## Task: Add MCP Server to Remote Hermes

### Via config.yaml (preferred, avoids CLI gotchas)

Add under `mcp_servers:` in the remote host's `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  nexus-memory:
    command: python3
    args:
      - /path/to/nexus_mcp_stdio.py
    enabled: true
    env:
      NEXUS_SECRET: ***
      NEXUS_URL: http://100.93.75.87:7777
      NEXUS_AGENT_ID: hermes
```

### Via CLI (when config.yaml approach isn't possible)

```bash
echo 'y' | hermes mcp add <name> --command <cmd> --args <arg1> <arg2>
```

**Pitfall**: `--args` values that look like flags (e.g. `-y`) get eaten by the Hermes CLI parser. Use config.yaml instead.

---

## Common Pitfalls

| Issue | Fix |
|-------|-----|
| `obelisk: command not found` via SSH | SSH doesn't source .bashrc. Use `export PATH=$HOME/.local/bin:$PATH &&` prefix |
| Plugin not showing tools after restart | Check `plugins.enabled` list for obelisk-rewrite (not rtk-rewrite); verify plugin.yaml names match |
| Remote clone takes long | Cargo downloads all deps from scratch on first build. Use `scp` of pre-built binary for faster deployment |
| Gateway restart kills active agents | Warn user; command requires approval when agents are running |

## Verification

Run a comprehensive check script (see `scripts/verify.sh`) or check each layer manually:

```bash
# 1. Nexus env
ssh <host> "cat ~/.hermes/nexus.env"

# 2. Plugin files
ssh <host> "ls ~/.hermes/plugins/nexus-memory/"

# 3. Config
ssh <host> "grep -E '^\s+-\s+nexus-memory' ~/.hermes/config.yaml"

# 4. Nexus endpoint
ssh <host> '<curl check>'

# 5. Obelisk
ssh <host> "export PATH=\$HOME/.local/bin:\$PATH && obelisk --version && obelisk doctor"

# 6. Gateway status
ssh <host> "export PATH=\$HOME/.local/bin:\$PATH && hermes status | head -5"
```
