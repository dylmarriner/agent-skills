---
name: agent-optimizer-wiring
description: "Wire a rewrite/optimizer tool (obelisk, rtk, etc.) into every AI coding agent's pipeline — Hermes, Codex, Claude Code, OpenCode, OpenClaw, Cline. Covers install, hook registration, PATH setup, and multi-machine rollout."
version: 1.0.0
author: Hermes
---

# Agent Optimizer Wiring

Install a tool that hooks into every AI coding agent's tool execution pipeline (a rewrite layer that compresses command output, fetches symbols instead of whole files, etc.). Currently covers Obelisk; the pattern generalizes to any tool that uses agent-specific hooks.

---

## Trigger

Use when the user says:
- "install obelisk for all my agents"
- "wire obelisk to everything"
- "replace rtk with obelisk"
- "install [tool] for codex, claude, hermes, etc."
- "make this work on [another machine] too"
- "rebuild obelisk" / "re-pull obelisk" / "rebuild and reinstall"
- "read the documentation and rebuild and reinstall on both"

## How It Works

Each agent uses a different mechanism for tool hooks:

| Agent | Hook Mechanism | Install Command |
|-------|---------------|----------------|
| Hermes | `pre_tool_call` plugin (`__init__.py` + `plugin.yaml` + `OBELISK.md`) | `obelisk install hermes` |
| Codex CLI | `hooks.json` (PreToolUse) | `obelisk install codex` |
| Claude Code | `settings.json` (PreToolUse) | `obelisk install claude` |
| OpenCode | TypeScript plugin (`plugins/obelisk.ts`) | `obelisk install opencode` |
| OpenClaw | awareness rule (`OBELISK.md` in config dir) | `obelisk install openclaw` |
| Cline | `.clinerules` / `OBELISK.md` | `obelisk install cline` |

## Procedure

### 1. Install the binary

```bash
obelisk doctor
```

If it's not in PATH, ensure `~/.local/bin` is on PATH in your shell profile:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

### 2. Remove the old tool completely (if migrating from RTK)

Rushing this creates confusion. The user expects RTK gone — not symlinked, not
coexisting as a stale hook. Do a thorough sweep.

```bash
# 2a. Remove RTK plugin files from all agent configs
rm -rf ~/.hermes/plugins/rtk-rewrite
rm -f ~/.config/opencode/plugins/rtk.ts

# 2b. Remove the RTK binary everywhere it could live
rm -f ~/.local/bin/rtk
rm -f ~/.cargo/bin/rtk
sudo rm -f /usr/local/bin/rtk 2>/dev/null || true
cargo uninstall rtk 2>/dev/null || true
cargo uninstall rtk-cli 2>/dev/null || true

# 2c. Remove RTK config/data dirs
rm -rf ~/.config/rtk ~/.local/share/rtk

# 2d. Remove RTK hook entries from agent configs
# Claude: rtk and obelisk hooks can coexist as separate PreToolUse blocks.
# Remove the rtk one explicitly — don't just install over it.
# Edit ~/.claude/settings.json to delete the block with "rtk hook claude"
#
# Codex: check hooks.json for any "rtk" reference
grep -n rtk ~/.codex/hooks.json 2>/dev/null && echo "WARNING: Codex hooks still reference rtk" || echo "Codex hooks clean"

# 2e. Remove RTK.md / RTK references from AGENTS.md / CLAUDE.md
rm -f ~/.claude/RTK.md
grep -l "RTK.md\|@RTK" ~/.claude/CLAUDE.md 2>/dev/null && \
  sed -i '/@RTK.md/d' ~/.claude/CLAUDE.md || true
# Codex: check for RTK.md in project roots
find ~/.codex -name "RTK.md" 2>/dev/null -delete
find ~ -maxdepth 3 -name "AGENTS.md" -exec grep -l "rtk\|RTK" {} \; 2>/dev/null | while read f; do
  echo "WARNING: $f still references RTK — edit manually"
done

# 2f. Verify nothing remains
which rtk || echo "✓ rtk binary gone"
obelisk --version 2>/dev/null || echo "✗ obelisk not found!"
```

**Key insight**: Do NOT create a backward-compat `rtk → obelisk` symlink unless
the user explicitly asks for it (e.g. scripts hardcode `rtk`). A symlink keeps
`rtk` resolving and confuses agents into thinking RTK is still installed.
The user's `which rtk` should return nothing.

### 3. Wire the new tool to every agent on the machine

```bash
obelisk install hermes      # installs Hermes plugin + OBELISK.md
obelisk install codex       # installs codex hooks.json entry
obelisk install claude      # installs claude settings.json entry
obelisk install opencode    # installs opencode TypeScript plugin
obelisk install openclaw    # installs awareness rule
obelisk install cline       # installs .clinerules entry
```

### 4. Handle edge cases

**`.clinerules` is a directory** — if `obelisk install cline` fails with "Is a directory (os error 21)", `~/.clinerules` is a directory containing `instructions`, workflow scripts, etc. Don't overwrite it. Create a separate `OBELISK.md` inside:

```bash
cat > ~/.clinerules/OBELISK.md << 'EOF'
# Obelisk — token optimizer

Obelisk is installed. When you see `obelisk run <command>` or `obelisk squeeze`
in tool output, the command was routed through Obelisk for token compression.
The original output is stashed in Obelisk's local ledger and is one
`obelisk restore <handle>` away.
EOF
```

**Backward-compat symlink (only if user asks)** — if the user explicitly wants
scripts that hardcode `rtk` to keep working:

```bash
rm -f ~/.local/bin/rtk
ln -s obelisk ~/.local/bin/rtk
```

Otherwise do NOT create this symlink. It keeps `which rtk` resolving, confuses
agents (Codex's session history shows `rtk run ...` commands), and wastes the
migration. When you're done, `which rtk` should return nothing.

### 5. Verify

```bash
# Hermes plugin
ls ~/.hermes/plugins/obelisk-rewrite/

# Codex hook
grep -c obelisk ~/.codex/hooks.json
# Also check no rtk references linger
grep -n rtk ~/.codex/hooks.json && echo "WARNING: codex still has rtk hook" || echo "✓ clean"

# Claude hook — also check for DUPLICATE hooks
grep -n rtk ~/.claude/settings.json && echo "WARNING: claude still has rtk hook" || echo "✓ no rtk"
# Count obelisk entries — should be exactly 1
grep -c "obelisk" ~/.claude/settings.json

# OpenCode plugin
ls ~/.config/opencode/plugins/obelisk.ts

# OpenClaw awareness
ls ~/.openclaw/OBELISK.md

# Cline awareness
ls ~/.clinerules/OBELISK.md

# Binary + ledger
obelisk doctor

# RTK totally gone
which rtk || echo "✓ rtk binary removed"
```

### 6. Restart each agent

Hooks are cached at agent startup. Without a restart the old hooks remain in
memory. Restart in this order: Claude Code, Codex CLI, Hermes, OpenCode,
then run a shell command in each to verify the hook fires:

## Rebuilding from Source (Obelisk)

After pulling obelisk source updates (`git pull`), rebuild, reinstall, and re-wire hooks on the machine:

```bash
# 1. Read new docs to check for changes
ls docs/

# 2. Stash local changes before pulling (avoids merge conflicts, esp. src/hook.rs)
git stash
git pull
git stash pop

# 3. Format, test, build
cd /path/to/obelisk
cargo fmt
cargo test
cargo build --release

# 4. Install the fresh binary
install -m755 target/release/obelisk ~/.local/bin/obelisk

# 4. Re-wire all agent hooks (refreshes hook configs with the new binary path)
obelisk install hermes
obelisk install codex
obelisk install claude
obelisk install opencode
obelisk install openclaw
obelisk install cline

# 5. Verify
obelisk doctor
```

For a **remote machine that doesn't have the source repo**, clone first:

```bash
ssh <host> "git clone https://github.com/dylmarriner/obelisk ~/obelisk-fresh"
ssh <host> "cd ~/obelisk-fresh && cargo fmt && cargo test && cargo build --release"
ssh <host> "install -m755 ~/obelisk-fresh/target/release/obelisk ~/.local/bin/obelisk"
ssh <host> "export PATH=\$HOME/.local/bin:\$PATH && obelisk install hermes && obelisk install codex && obelisk install claude"
```

**Pitfall**: SSH non-interactive shells don't source `.bashrc`. Always export PATH explicitly:
```bash
ssh <host> "export PATH=\$HOME/.local/bin:\$PATH && <command>"
```

## Multi-Machine Rollout

For a second machine (e.g. Macuntu → kubuntux):

1. SSH in, ensure the binary exists:
   ```bash
   ssh <host> "ls ~/.local/bin/obelisk"
   ```

2. Run install for all agents remotely:
   ```bash
   ssh <host> "export PATH=\$HOME/.local/bin:\$PATH; \
     hermes plugins disable rtk-rewrite; \
     hermes plugins remove rtk-rewrite; \
     obelisk install hermes; \
     obelisk install codex; \
     obelisk install claude"
   ```

3. Handle PATH (if `~/.local/bin` isn't in the non-interactive SSH PATH):
   ```bash
   ssh <host> "echo 'export PATH=\\"\\$HOME/.local/bin:\\$PATH\\"' >> ~/.bashrc"
   ```

4. Enable the Hermes plugin:
   ```bash
   ssh <host> "hermes plugins enable obelisk-rewrite"
   ```

5. Verify:
   ```bash
   ssh <host> "export PATH=\\$HOME/.local/bin:\\$PATH && which obelisk && obelisk doctor"
   ```

**Note**: Do NOT create a backward-compat `rtk → obelisk` symlink unless the user
explicitly asks for it. The symlink was previously standard practice but it
keeps `rtk` resolving and confuses agents. When migration is complete,
`which rtk` should return nothing.

## Pitfalls

| Issue | Fix |
|-------|-----|
| `obelisk install cline`: "Is a directory" | `.clinerules` is a directory, not a file. Create `OBELISK.md` inside it manually |
| `obelisk: command not found` after SSH | `~/.local/bin` not in non-interactive PATH. Export it explicitly or add to `~/.bashrc` |
| `hermes plugins enable` doesn't find plugin | The obelisk-rewrite plugin requires `obelisk install hermes` first (that actually copies the plugin files) |
| Old rtk binary still in PATH alongside obelisk | Remove the old binary and all config references: `rm -f ~/.local/bin/rtk ~/.cargo/bin/rtk; rm -rf ~/.config/rtk ~/.local/share/rtk`. Do NOT create a backward-compat symlink unless the user explicitly asks for it |
| Agents don't pick up the hook immediately | Restart each agent for the hooks to take effect |
