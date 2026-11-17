# Importing Skills from a Remote OpenClaw Instance into Hermes

When an OpenClaw instance runs on a remote machine (e.g. a Raspberry Pi on the local network) with a full skill library, you can bulk-import those skills into Hermes via SSH/rsync.

## Workflow

### 1. Discover the remote skill layout

SSH in and locate skills:

```bash
ssh user@remote-host
ls ~/.openclaw/workspace/skills/        # OpenClaw user skills
ls ~/.openclaw/extensions/              # OpenClaw plugin extensions
ls ~/.openclaw/skills/                  # Additional skill dir
```

OpenClaw skills are `SKILL.md` files (YAML frontmatter + markdown) — same format as Hermes skills. They are compatible as-is.

Extensions are Node.js runtime plugins (`openclaw.plugin.json` + `dist/*.js`). These are **not** Hermes-compatible — they load into the OpenClaw gateway process. However, some extensions do include nested `SKILL.md` files (e.g. `zerogpu/skills/zerogpu/SKILL.md`) that are usable in Hermes.

### 2. Copy skills via rsync

```bash
# Create the target category directory
mkdir -p ~/.hermes/skills/<category-name>/

# Rsync from remote, excluding runtime artifacts
rsync -avh user@remote-host:/home/user/.openclaw/workspace/skills/ \
  ~/.hermes/skills/<category-name>/ \
  --exclude='node_modules' --exclude='.git' \
  --exclude='*.jpg' --exclude='*.png' --exclude='*.pdf'
```

### 3. Copy extensions (with SKILL.md scanning)

```bash
mkdir -p ~/.hermes/skills/<extensions-category>/
rsync -avh user@remote-host:/home/user/.openclaw/extensions/ \
  ~/.hermes/skills/<extensions-category>/ \
  --exclude='node_modules'

# Find which extensions have Hermes-compatible SKILL.md files
find ~/.hermes/skills/<extensions-category>/ -name "SKILL.md"
```

### 4. Copy config and workspace context

```bash
mkdir -p ~/.hermes/<project-dir>/
scp user@remote-host:/home/user/.openclaw/openclaw.json ~/.hermes/<project-dir>/
scp user@remote-host:/home/user/.openclaw/workspace/MEMORY.md ~/.hermes/<project-dir>/
scp user@remote-host:/home/user/.openclaw/workspace/AGENTS.md ~/.hermes/<project-dir>/
scp user@remote-host:/home/user/.openclawbrain/ ~/.hermes/<project-dir>/brain/
```

### 5. Verify registration

Skills in `~/.hermes/skills/<category>/` are auto-detected on Hermes startup or after `/reload-skills`. Verify with:

```bash
# In terminal
hermes skills list

# Or in-session
/skills
```

### 6. Clone clawgig agent source (if present)

```bash
ssh user@remote-host "cd ~/clawgig-agent && tar czf - src/ package.json config.json" \
  | tar xzf - -C ~/.hermes/<project-dir>/clawgig/
```

## Pitfalls

- **OpenClaw plugin SKILL.md files reference OpenClaw-specific tools** (`self_evaluate`, `sessions_spawn`, etc.). They won't work in Hermes without adaptation. Read the SKILL.md before registering — if it references tools that don't exist in Hermes, skip it or rewrite the skill.
- **OpenClaw skill SKILL.md files** use a slightly different frontmatter format with `metadata: { "openclaw": { ... } }` block. Hermes ignores unrecognized frontmatter keys, so these skills work fine.
- **Hardcoded paths** in some OpenClaw skills reference the original user's home directory (e.g. `/home/lidor_shim/...`). These will break in Hermes. Patch before using.
- **Check for OpenClaw gateway running** — `ssh user@remote-host 'ps aux | grep openclaw'`. If the gateway isn't running, there are no MCP servers or runtime services to connect to.
- **OpenClaw bundled plugins** (under `/usr/lib/node_modules/openclaw/dist/extensions/`) are part of OpenClaw itself, not user-installed. They are provider auth plugins (anthropic, openai, deepseek, etc.), platform plugins (telegram, signal, etc.), and media plugins (elevenlabs, comfy, etc.). These cannot be transferred to Hermes — Hermes has its own equivalent systems.
