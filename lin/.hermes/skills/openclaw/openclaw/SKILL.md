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

Start with read-only checks on the machine that actually owns the gateway; do not assume a remote host from unrelated machine notes.

```bash
hostname
systemctl --user status openclaw-gateway --no-pager -l
openclaw gateway status
openclaw status --deep
journalctl --user -u openclaw-gateway -n 100 --no-pager -o cat
```

Read the first startup/reload error and follow that failure before changing config. Do not lead with `openclaw doctor --fix` while the gateway is unhealthy: it may mutate config or block on the same lifecycle lease. Run read-only doctor checks after collecting logs; use `--fix` only for a diagnosed auto-fixable issue.

Before reinstalling, compare the shell CLI with the service's actual `ExecStart` Node and OpenClaw paths. Run the service-managed entry point directly for `--version` and status; a stale shell CLI can reject newer config/state schemas even while a compatible service installation is present. Keep CLI and gateway versions aligned, and check the target release's Node engine before installing. Preserve the existing `~/.openclaw` state; never treat a schema-version error as a reason to reset or downgrade it.

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

### Stuck reloads, lifecycle leases, and crash-loop recovery

1. Search recent logs for `restart preflight failed`, `Waiting for plugin lifecycle lease`, plugin resource-cleanup timeouts, and the first `Gateway failed to start` line. A hanging restart may be caused by a plugin operation that never drained, not by systemd itself.
2. When a lifecycle lease is named, read its owner PID and heartbeat from `~/.openclaw/state/openclaw.sqlite`, then compare the PID with the live gateway. A lease owned by the current gateway is not stale just because the gateway is unhealthy; do not delete lease rows or edit the state database by hand.
3. If the gateway is still healthy, let admitted work settle and address the named plugin/config reload failure first. If its listener is down and the gateway is demonstrably stuck holding its own lease, force-kill only the service main process as a last resort; this interrupts in-flight work and relies on systemd's restart policy:
   ```bash
   systemctl --user kill --kill-whom=main --signal=SIGKILL openclaw-gateway
   ```
4. After restart, inspect the new startup log before repeating the restart. Fix the exact configuration validation error; do not invent credentials when an enabled integration requires a token. Check config backups/secret references first, and coordinate a new token with its callers if rotation is truly required.
5. OpenClaw may suppress channel/provider auto-start after repeated unclean boots. Once the gateway is healthy, start each required channel explicitly, for example:
   ```bash
   openclaw gateway call channels.start --params '{"channel":"telegram"}'
   openclaw channels status --channel telegram --probe
   ```
6. Verify the gateway version and WebSocket health with `openclaw gateway status`, then verify channel runtime/connectivity with `openclaw status --deep`. Confirm the systemd MainPID and restart count stay unchanged across a brief observation window.

### Common gateway startup messages
- `agent model: <provider>/<model>` — confirms the primary model loaded
- `http server listening` — gateway is ready
- `tailscale serve failed: Access denied` — run `sudo tailscale set --operator=$USER` once to fix

## Plugin Installation

1. Resolve the registry before installing. Use `openclaw plugins search <name> --json` for ClawHub and `npm view <name> ...` for npm; a bare name may resolve to npm, so use `clawhub:<name>` when ClawHub is the intended source. An npm 404 says nothing about whether a ClawHub package exists.
2. Review the upstream repo and package metadata before accepting capabilities: confirm publisher/source link, version, entrypoint, declared tools/capabilities, and required helper binaries. Install helper binaries somewhere visible to the Gateway service PATH, or set the plugin's explicit binary path.
3. Install from the intended source, then verify the installed version and runtime. Example: `openclaw plugins install clawhub:<name> --accept-capabilities`. Use `--accept-capabilities` only after reviewing what the plugin registers; use `--force` only to confirm a non-ClawHub/local source or overwrite an existing plugin.
4. If installation fails because a TypeScript entry has no compiled runtime output, do not bypass the loader or disable validation. Pin/record the upstream commit, build the documented output, and check the entry points to the generated runtime file. For plugins that call `registerTool`, ensure `openclaw.plugin.json` declares every tool name in `contracts.tools`; OpenClaw rejects undeclared agent tools.
5. A local-path install can require exclusive offline state ownership. Stop the Gateway through its service manager, install the verified local build, and always start the service again even if installation fails; local installs interrupt active work. Use a trap so a failed install does not strand the Gateway stopped:
   ```bash
   set -e
   repo=/path/to/verified-plugin
   trap 'systemctl --user start openclaw-gateway' EXIT
   systemctl --user stop openclaw-gateway
   openclaw plugins install "$repo" --force --accept-capabilities
   systemctl --user start openclaw-gateway
   trap - EXIT
   ```
   Keep any packaging fix minimal, applied to the reviewed source before installing, not as an untracked edit to the live copy.
6. Verify `openclaw plugins info <id>`, `openclaw plugins list`, target-specific entries from `openclaw plugins doctor --json`, and the Gateway startup log (`http server listening` with the plugin ID). Test the helper binary and use a brief agent/tool smoke test when practical. Global plugin diagnostics may contain unrelated failures; judge the target plugin's own errors separately.
7. If the plugin adds a model provider, do not equate “enabled” with “connected”; follow `openclaw-provider-setup` to complete its auth/discovery flow before claiming its models are usable.

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
- The gateway service may use a private Node/OpenClaw installation that differs from the shell's PATH-selected CLI. Inspect `systemctl --user cat openclaw-gateway`; check the service-managed CLI first and align the shell install only after confirming Node engine compatibility. Installing the matching release under an older shell Node can fail its preinstall engine check.
- `openclaw doctor --fix` backs up config to `~/.openclaw/openclaw.json.bak` before applying changes, but it is not a safe first probe during a stuck gateway reload; collect status and logs first.
- After `openclaw update`, the gateway is stopped. Restart it with `systemctl --user start openclaw-gateway`.
- The `openclaw-web-search` plugin warning in gateway logs is non-blocking — it does not affect model inference or channel routing.
- Version check uses `--version` flag (not `version` subcommand).
