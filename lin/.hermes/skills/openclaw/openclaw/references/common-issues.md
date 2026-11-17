# Common OpenClaw Issues — Real Diagnoses

## Stale CLI Binary Stub

**Symptom:** Running `openclaw` prints "Not Found" or exits with code 127.

**Root cause:** `~/.local/bin/openclaw` was a 9-byte ASCII text file containing just "Not Found\n". OpenClaw is actually installed as a global npm package at `~/.npm-global/lib/node_modules/openclaw/` with symlinks at `~/.npm-global/bin/openclaw` and `/usr/local/bin/openclaw`, both pointing to `openclaw.mjs`.

**Why it happened:** The stub was likely left over from an earlier AUR package, a failed install script, or a Flatpak/npx-based wrapper that wrote "Not Found" instead of the actual binary path. The PATH had `~/.local/bin` before `~/.npm-global/bin` so the stub was resolved first.

**Fix:**
```bash
rm ~/.local/bin/openclaw
hash -r  # clear shell cache
openclaw --version  # should now resolve to ~/.npm-global/bin/openclaw
```

## Synapse Plugin Missing typebox

**Symptom:** `openclaw` CLI or gateway logs show:
```
[plugins] synapse failed to load from .../synapse/src/index.ts: Error: Cannot find module 'typebox'
```

**Root cause:** The synapse plugin's `package.json` lists `typebox: "^1.1.38"` as a dependency, but its devDependencies use pnpm workspace protocol (`"@openclaw/plugin-sdk": "workspace:*"`). Running `npm install` inside the extension directory fails with `Unsupported URL Type "workspace:"`.

**Fix:** Link typebox from the global npm install:
```bash
npm install -g @sinclair/typebox
mkdir -p /home/kubuntux/.openclaw/extensions/synapse/node_modules/@sinclair
ln -sf /home/kubuntux/.npm-global/lib/node_modules/@sinclair/typebox \
  /home/kubuntux/.openclaw/extensions/synapse/node_modules/@sinclair/typebox
```

**Verification:** The gateway log should no longer show the typebox error on restart.

## openclaw-web-search TypeScript Entry

**Symptom:** Gateway logs warn:
```
plugin openclaw-web-search: installed plugin package requires compiled runtime output
for TypeScript entry index.ts: expected ./dist/index.js, ./dist/index.mjs, ...
```

**Root cause:** The plugin publisher shipped TypeScript source as the entry point instead of compiled JavaScript. OpenClaw's plugin loader only supports TS fallback for source checkouts and local development paths — bundled plugins must provide compiled output.

**Impact:** Non-blocking. The gateway starts and runs normally. The plugin simply isn't loaded. Model inference, channels, and other plugins are unaffected.

**Fix:** Requires the publisher to ship compiled JS. Until then, disable the plugin to silence warnings:
```bash
openclaw plugins disable openclaw-web-search
```
Or remove the extension directory:
```bash
rm -rf ~/.openclaw/extensions/openclaw-web-search
```

## Tailscale Serve Access Denied

**Symptom:** Gateway logs show:
```
tailscale serve failed: Command failed: /usr/bin/tailscale serve --bg --yes 18789
sending serve config: Access denied
```

**Root cause:** Tailscale requires root or operator permissions to configure serve. The gateway service (running as user) cannot call `tailscale serve` without either sudo or the `--operator=$USER` flag.

**Fix (one-time):**
```bash
sudo tailscale set --operator=$USER
```
Then restart the gateway:
```bash
systemctl --user restart openclaw-gateway
```

## Gateway Service PATH Mismatch

**Symptom:** Doctor reports "Gateway service PATH missing required dirs".

**Root cause:** The systemd user unit picks up a restricted PATH at service start time, which may not include `~/.npm-global/bin`, `~/.bun/bin`, or other custom PATH entries from your shell config.

**Fix:** Reinstall the gateway service to pick up the current environment:
```bash
openclaw gateway install --force
```
