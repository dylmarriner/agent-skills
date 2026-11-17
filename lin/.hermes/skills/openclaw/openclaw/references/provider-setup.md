---
name: openclaw-provider-setup
description: Add or reconfigure an AI provider in OpenClaw (bundled plugins, auth profiles, primary model, env vars).
category: openclaw
emoji: 🔌
requires:
  bins: [openclaw]
trigger: Configure a new AI provider in OpenClaw, enable a bundled model provider, change the primary agent model, or add API credentials to the gateway.
---

# OpenClaw Provider Setup

Add a new AI provider to OpenClaw (bundled plugin, custom provider, or OpenRouter-based model).

## Trigger Conditions

Use this skill when:
- The user says "add deepseek/gemini/anthropic/... to OpenClaw"
- "configure OpenClaw to use provider X"
- "fix OpenClaw to use model Y"
- "enable [provider] plugin in OpenClaw"
- "change primary model in OpenClaw"
- "add API key for [provider] to OpenClaw gateway"

## Step 0: Verify CLI Works

Before doing anything, confirm `openclaw` resolves to the real binary:

```bash
which openclaw && openclaw --version
```

If that fails or returns a bogus version, check for stale stubs:

```bash
cat $(which openclaw)   # Should not be "Not Found" or a tiny text file
ls -la ~/.npm-global/bin/openclaw /usr/local/bin/openclaw 2>/dev/null
```

If the real binary lives at `~/.npm-global/bin/openclaw` but a stale stub at `~/.local/bin/openclaw` (often 9 bytes, "Not Found") is shadowing it due to PATH priority:

```bash
rm ~/.local/bin/openclaw && hash -r
```

Re-verify: `openclaw --version`.

## Step 1: Identify the Plugin

OpenClaw bundles provider plugins in `~/.npm-global/lib/node_modules/openclaw/dist/extensions/<provider>/openclaw.plugin.json`.

```bash
# List all bundled plugins (look for pluginId matching your provider)
cat ~/.openclaw/plugins/installs.json | python3 -c "
import json,sys
data = json.load(sys.stdin)
for p in data.get('plugins', []):
    if '<provider>' in p['pluginId']:
        print(json.dumps(p, indent=2))
"
```

Check if the plugin is already enabled:
```bash
cat ~/.openclaw/plugins/installs.json | python3 -c "
import json,sys
data = json.load(sys.stdin)
for p in data.get('plugins', []):
    if '<provider>' in p['pluginId']:
        print(f\"enabled: {p.get('enabled', 'unknown')}\")
"
```

## Step 2: Enable the Plugin

The plugin may be blocked by the allowlist. First, add it to `plugins.allow` in `~/.openclaw/openclaw.json`:

```json
"plugins": {
  "allow": [
    ...existing...,
    "<provider>"
  ]
}
```

Then enable it via CLI:
```bash
openclaw plugins enable <provider>
```

This adds an entry under `plugins.entries.<provider>` automatically.

## Step 3: Add Auth Profile (determine if needed)

Not all providers need an explicit entry in `auth.profiles`. Some read API keys from environment variables only — adding an inline `apiKey` field to the auth profile for those causes `"auth.profiles.<provider>:default: Invalid input"` errors and may block gateway startup.

**How to tell if a provider uses env vars:** read its plugin manifest at `~/.npm-global/lib/node_modules/openclaw/dist/extensions/<provider>/openclaw.plugin.json`. Look in TWO places:
- `providerAuthEnvVars` (top-level, used by older plugins)
- `setup.providers[].envVars` (used by newer plugins like Venice)

If either exists, the API key is read from that environment variable — **do NOT add an inline `apiKey` to the auth profile**. Just set the env var via Step 5.

For providers with no env var support, add an auth profile:

```json
"auth": {
  "profiles": {
    "<provider>:default": {
      "mode": "api_key",
      "provider": "<provider>",
      "apiKey": "<your-api-key>"
    }
  }
}
```

## Step 4: Set Primary Model

Set the primary model and optionally add fallbacks:

```json
"agents": {
  "defaults": {
    "model": {
      "fallbacks": [
        "<provider>/<fallback-model-1>",
        "<provider>/<fallback-model-2>"
      ],
      "primary": "<provider>/<primary-model>"
    },
    "models": {
      "<provider>/<primary-model>": {
        "alias": "Friendly Name"
      }
    }
  }
}
```

Available models for each provider are defined in the plugin's `modelCatalog` section.

## Step 5: Inject API Key (env-var-based providers)

The DeepSeek/Venice/anthropic/etc. provider plugins read API keys from environment variables. The gateway runs as a systemd user service, so the key must be injected there.

**Drop-in approach (works without TTY, survives package updates):**

```bash
mkdir -p ~/.config/systemd/user/openclaw-gateway.service.d
cat > ~/.config/systemd/user/openclaw-gateway.service.d/<provider>.conf << 'EOF'
[Service]
Environment=<PROVIDER>_API_KEY=<key>
EOF
systemctl --user daemon-reload
systemctl --user restart openclaw-gateway.service
```

Note: `systemctl --user edit` (interactive editor) does NOT work when called from an agent — it requires a TTY. Always use the drop-in file approach above.

The env var name comes from the plugin manifest — check `providerAuthEnvVars` or `setup.providers[].envVars`.

## Step 6: Verify

Check gateway logs for the model being picked up:
```bash
journalctl --user -u openclaw-gateway.service -n 30 --no-hostname -o cat | grep "agent model"
# Expected: agent model: <provider>/<model> (thinking=..., fast=...)
```

## Pitfalls

- The `plugins.allow` list **blocks** plugin enablement — you must add the provider there BEFORE running `openclaw plugins enable <provider>`. The CLI will tell you "blocked by allowlist" if you forget.
- Editing `installs.json` directly is NOT supported — use `openclaw plugins enable/disable`. The file header says "DO NOT EDIT".
- Bundled plugins that use `providerAuthEnvVars` read the env var at gateway startup. Adding the key to `~/.bashrc` or similar won't affect the running gateway service — it must be in the systemd unit's `Environment=` directive.
- The `openclaw plugins enable <provider>` command also adds `plugins.entries.<provider>` automatically — do not add it manually or you'll get a duplicate.
- Bundled plugins can have `enabledByDefault: true` in their manifest but still be `enabled: false` in `installs.json` (e.g., due to a prior migration or manual disable). Always check `installs.json` for the actual enabled state, not just the manifest default.
- To see which env vars a provider expects, read the plugin manifest's `providerAuthEnvVars` section OR `setup.providers[].envVars` — newer plugins use the latter. If a plugin has env var declarations in either location, do NOT add an inline `apiKey` to the auth profile or it will cause "Invalid input" errors.
- The openclaw-web-search plugin is known to have TypeScript build issues (stale config entries cause harmless warnings in logs but can be cleaned up from `plugins.allow` and `plugins.entries`).
- **Broken CLI binary stub:** `~/.local/bin/openclaw` may contain a stale 9-byte stub file with content "Not Found" from a prior broken installation or wrapper script. This shadows the real binary at `~/.npm-global/bin/openclaw` (or `/usr/local/bin/openclaw`) when `~/.local/bin` is earlier in `PATH`. Fix: `rm ~/.local/bin/openclaw` then `hash -r; which openclaw` to confirm the real binary is picked up.
- **Run `doctor` after setup:** `openclaw doctor --fix` catches common issues (Ollama params, directory permissions, gateway service PATH) in one pass. Run it after any provider change.
- **Update before setup if behind:** `openclaw update` upgrades both the CLI and the gateway. Gateway is stopped and restarted automatically during update.
