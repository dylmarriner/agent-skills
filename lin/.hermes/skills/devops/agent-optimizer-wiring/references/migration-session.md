# Obelisk Migration — Session Detail (July 2026)

Full transcript of replacing RTK with Obelisk across kubuntux + Macuntu.

## Source Machine (kubuntux)

```bash
# Remove old — thorough sweep
rm -rf ~/.hermes/plugins/rtk-rewrite
rm -f ~/.config/opencode/plugins/rtk.ts
rm -f ~/.local/bin/rtk ~/.cargo/bin/rtk
sudo rm -f /usr/local/bin/rtk 2>/dev/null || true
rm -rf ~/.config/rtk ~/.local/share/rtk
cargo uninstall rtk 2>/dev/null || true
cargo uninstall rtk-cli 2>/dev/null || true

# Remove RTK hook from Claude settings (separate PreToolUse block)
# Delete the block containing "rtk hook claude" from ~/.claude/settings.json
# Remove RTK.md references
rm -f ~/.claude/RTK.md
sed -i '/@RTK.md/d' ~/.claude/CLAUDE.md 2>/dev/null || true

# Install to Hermes
obelisk install hermes
hermes plugins enable obelisk-rewrite

# Wire all other agents
obelisk install codex       # ~/.codex/hooks.json
obelisk install claude      # ~/.claude/settings.json
obelisk install opencode    # ~/.config/opencode/plugins/obelisk.ts
obelisk install openclaw    # ~/.openclaw/OBELISK.md
obelisk install cline       # FAILED — .clinerules is a directory
```

**Cline fix** — `.clinerules` was a directory with `instructions`, `unrestricted_prompt.txt`, `workflows/`:
```bash
cat > ~/.clinerules/OBELISK.md << 'EOF'
# Obelisk — token optimizer

Obelisk is installed. When you see `obelisk run <command>` or `obelisk squeeze`
in tool output, the command was routed through Obelisk for token compression.
The original output is stashed in Obelisk's local ledger and is one
`obelisk restore <handle>` away.
EOF
```

## Second Machine (Macuntu, 100.75.23.127)

```bash
ssh macuntu "
  export PATH=\$HOME/.local/bin:\$PATH

  # Remove old rtk binary entirely (no symlink — kept rtk resolving confuses agents)
  rm -f ~/.local/bin/rtk ~/.cargo/bin/rtk
  rm -rf ~/.config/rtk ~/.local/share/rtk

  # Swap plugins
  hermes plugins disable rtk-rewrite
  hermes plugins remove rtk-rewrite
  hermes plugins enable obelisk-rewrite

  # Wire agents
  obelisk install codex
  obelisk install claude

  # Ensure PATH
  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc
"
```

## PATH Caveat

On Macuntu, `~/.local/bin` was NOT in the non-interactive SSH PATH, causing
`obelisk: command not found`. Fixed by exporting explicitly in the remote
command and adding to `~/.bashrc`.
