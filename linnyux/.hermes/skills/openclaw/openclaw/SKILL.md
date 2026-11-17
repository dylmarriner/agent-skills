---
name: openclaw
description: "Install, diagnose, update, and maintain OpenClaw — the full-agent messaging gateway. Covers CLI repair, doctor, gateway lifecycle, and plugin dependency issues. For provider-specific setup use the companion openclaw-provider-setup skill."
emoji: 🦞
requires:
  bins: [node]
trigger: Set up OpenClaw from scratch, diagnose a broken CLI, update the gateway, fix plugin loading errors, or perform general maintenance.
related_skills: [openclaw-provider-setup]
---

# OpenClaw — General Setup & Maintenance

## Quick Diagnosis

**First command for any OpenClaw issue:**
```bash
openclaw doctor --fix
```

This checks config validity, plugin state, service health, channel status, permissions, and applies auto-fixable changes (Ollama params, directory permissions, WhatsApp group allowlist migration, etc.).

## CLI Binary Issues

### Symptom: `openclaw` says "command not found" or a 9-byte stub containing "Not Found"

OpenClaw is installed at:
- `~/.npm-global/bin/openclaw` → `../lib/node_modules/openclaw/openclaw.mjs`
- `/usr/local/bin/openclaw` → `../lib/node_modules/openclaw/openclaw.mjs`

If `~/.local/bin/openclaw` exists and is a small file (e.g. 9 bytes containing "Not Found"), it shadows the real binary on PATH. Remove it:

```bash
rm ~/.local/bin/openclaw && hash -r
which openclaw && openclaw --version
```

Expected: `OpenClaw <version> (<hash>)`

### Verify the real binary

```bash
ls -la ~/.npm-global/bin/openclaw
# Expected: -> ../lib/node_modules/openclaw/openclaw.mjs
```

If the symlink is pointing at a nonexistent target, reinstall:

```bash
npm install -g openclaw
```

## Updating

```bash
openclaw update
```

This stops the gateway, updates the global npm package, re-runs doctor, and restarts the gateway. Check version after:

```bash
openclaw --version
```

## Gateway Management

### Check status
```bash
systemctl --user is-active openclaw-gateway
openclaw status
```

### Start/stop/restart
```bash
systemctl --user start openclaw-gateway
systemctl --user stop openclaw-gateway
systemctl --user restart openclaw-gateway
```

### View logs
```bash
journalctl --user -u openclaw-gateway -n 50 --no-hostname -o cat
openclaw logs --follow
```

### Common gateway startup messages
- `agent model: <provider>/<model>` — confirms the primary model loaded
- `http server listening` — gateway is ready
- `tailscale serve failed: Access denied` — run `sudo tailscale set --operator=$USER` once to fix

## Plugin Diagnostics

### Check loaded plugins
```bash
openclaw plugins list
openclaw plugins list --all
```

### Plugin dependency issues

**Synapse plugin: `Cannot find module 'typebox'`**

The synapse plugin lists `typebox` as a dependency but its devDependencies use pnpm workspace protocol (`workspace:*`), which breaks `npm install`. Fix by linking from global installs:

```bash
mkdir -p /home/kubuntux/.openclaw/extensions/synapse/node_modules/@sinclair
ln -sf /home/kubuntux/.npm-global/lib/node_modules/@sinclair/typebox \
  /home/kubuntux/.openclaw/extensions/synapse/node_modules/@sinclair/typebox
```

Or install typebox globally if not present:
```bash
npm install -g @sinclair/typebox
```

**openclaw-web-search: "requires compiled runtime output for TypeScript entry"**

This is a publisher packaging issue (TypeScript source fallback unsupported in bundled plugins). Non-blocking — the gateway warns at startup but continues. Fix requires the publisher to ship compiled JS in `dist/`.

### Disable a problematic plugin
```bash
openclaw plugins disable <plugin-name>
```

If the plugin doesn't appear in the installed list, remove its directory:
```bash
rm -rf /home/kubuntux/.openclaw/extensions/<plugin-name>
```

## Config Issues

### JSON duplicate keys in openclaw.json

If a key (e.g. `deepseek`) appears twice in `plugins.entries`, Python's `json.load()` takes the last value. This is harmless but can be cleaned up by running `openclaw doctor --fix` or manually editing the file.

### Secrets in plaintext

Gateway auth token, Telegram bot token, Ollama API key are stored in openclaw.json. To migrate to SecretRefs:

```bash
openclaw secrets configure
openclaw secrets apply
openclaw secrets audit --check
```

## Pitfalls

- `~/.local/bin` on PATH before `~/.npm-global/bin` can shadow the real binary with stale stubs.
- The gateway uses its own Node binary from `/usr/local/bin/node`, which may differ from the Node version in your shell. OpenClaw update handles this correctly.
- `openclaw doctor --fix` backs up config to `~/.openclaw/openclaw.json.bak` before applying changes.
- After `openclaw update`, the gateway is stopped. Restart it with `systemctl --user start openclaw-gateway`.
- The `openclaw-web-search` plugin warning in gateway logs is non-blocking — it does not affect model inference or channel routing.
- Version check uses `--version` flag (not `version` subcommand).
