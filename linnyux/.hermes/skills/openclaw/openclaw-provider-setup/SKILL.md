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

## Step 3: Add Auth Profile

Add an auth profile entry in `auth.profiles`:

```json
"auth": {
  "profiles": {
    "<provider>:default": {
      "mode": "api_key",
      "provider": "<provider>"
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

## Step 5: Inject API Key

The DeepSeek/anthropic/etc. provider plugins read API keys from environment variables. The gateway runs as a systemd user service, so the key must be injected there:

```bash
systemctl --user edit --full openclaw-gateway.service
```

Add:
```
Environment=<PROVIDER>_API_KEY=<key>
```

Then:
```bash
systemctl --user daemon-reload
systemctl --user restart openclaw-gateway.service
```

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
- To see which env vars a provider expects, read the plugin manifest's `providerAuthEnvVars` section.
- The openclaw-web-search plugin is known to have TypeScript build issues (stale config entries cause harmless warnings in logs but can be cleaned up from `plugins.allow` and `plugins.entries`).
