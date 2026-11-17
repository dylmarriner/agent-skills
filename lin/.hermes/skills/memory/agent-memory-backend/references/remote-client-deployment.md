# Remote Client Node Deployment via SSH

Step-by-step to wire a second machine's Hermes as a client-only agentmemory
node (no local daemon — connects to an existing agentmemory over Tailscale).

## Prerequisites

- SSH access to the remote machine
- The remote has `node` + `npx` + `python3` installed
- agentmemory daemon already running on the host machine, exposed via Tailscale

## Steps

### 1. Check remote Hermes config

```bash
ssh macuntu@<remote-ip> "cat ~/.hermes/config.yaml"
# Note: home directory may differ from local user — check with:
ssh macuntu@<remote-ip> "echo HOME=\$HOME"
```

### 2. Add mcp_servers + memory sections via Python YAML

Construct a Python script and pipe it via heredoc to avoid shell quoting issues:

```bash
cat > /tmp/fix_config.py << 'PYEOF'
import yaml

path = '/home/<remote-user>/.hermes/config.yaml'
with open(path, 'r') as f:
    config = yaml.safe_load(f)

config['mcp_servers'] = {
    'agentmemory': {
        'command': 'npx',
        'args': ['-y', '@agentmemory/mcp'],
        'enabled': True,
        'env': {'AGENTMEMORY_URL': 'http://<host-tailscale-ip>:3111'}
    }
}

config['memory'] = {
    'memory_enabled': True,
    'user_profile_enabled': True,
    'write_approval': False,
    'memory_char_limit': 2200,
    'user_char_limit': 1375,
    'provider': 'agentmemory',
    'agentmemory_url': 'http://<host-tailscale-ip>:3111'
}

with open(path, 'w') as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

print('Config updated. Sections:', list(config.keys()))
PYEOF
python3 /tmp/fix_config.py
```

**Pitfall — PyYAML not installed:** If `python3 -c "import yaml"` fails on
the remote, install it: `pip3 install pyyaml` or use `sed` to insert lines
instead.

### 3. Install companion skills

```bash
ssh <user>@<remote-ip> "npx skills add rohitg00/agentmemory -y 2>&1 | tail -10"
```

This installs recall, remember, forget, handoff, session-history, etc. into
`~/.agents/skills/` with Hermes symlinks.

### 4. Create cognitive memory structure

If the cognitive-memory skill's init script hangs on `git init` (large dir),
create the structure manually:

```bash
ssh <user>@<remote-ip> "mkdir -p ~/.hermes/memory/{episodes,graph/entities,procedures,vault,meta/reflections/dialogues,meta/rewards}"

# Write meta template files
ssh <user>@<remote-ip> 'cat > ~/.hermes/memory/meta/decay-scores.json <<'EOF'
{"version": 1, "last_updated": null, "entries": {}}
EOF
# ... repeat for reflection-log.md, audit.log, evolution.md, pending-*.md
# See agent-memory-backend cognitive-memory init script for full template list
```

### 5. Copy persona files

SOUL.md, IDENTITY.md, MEMORY.md, USER.md should be written per-machine.
The SOUL.md (personality/voice) should be identical across all machines
to maintain consistent agent identity. MEMORY.md and IDENTITY.md are
machine-specific (different active context, local paths).

```bash
# Copy SOUL.md from host to maintain consistent persona
cat ~/.hermes/SOUL.md | ssh <user>@<remote-ip> "cat > ~/.hermes/SOUL.md"

# MEMORY.md and IDENTITY.md should be written fresh per-machine
```

### 6. Verify

```bash
# Remote can reach host agentmemory
ssh <user>@<remote-ip> "curl -s http://<host-ip>:3111/agentmemory/health"

# Remote config has provider
ssh <user>@<remote-ip> "grep 'provider: agentmemory' ~/.hermes/config.yaml"

# Cognitive files exist
ssh <user>@<remote-ip> "ls ~/.hermes/MEMORY.md ~/.hermes/SOUL.md ~/.hermes/IDENTITY.md"

# Companion skills installed
ssh <user>@<remote-ip> "ls ~/.agents/skills/recall ~/.agents/skills/remember"
```

## Common Pitfalls

| Issue | Fix |
|-------|-----|
| `ssh: Permission denied` | Try different usernames: `dylan`, `kubuntux`, root, ubuntu, the machine's hostname |
| `python3: command not found` | Remote doesn't have Python 3. Install it or use `sed` for config edits |
| `ModuleNotFoundError: No module named 'yaml'` | `pip3 install pyyaml` on remote |
| path `/home/kubuntux/.hermes/` wrong for remote | Remote home is `/home/<remote-username>/` — must match. Check with `echo $HOME` via SSH |
| `npx: command not found` | Node not installed. Install via nvm or distro packages first |
| `agentmemory import` hangs | Cannot run `agentmemory import` while the daemon is already running. Import is not needed on client-only nodes — memories accumulate naturally |
