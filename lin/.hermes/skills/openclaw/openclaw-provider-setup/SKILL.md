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

## Step 1: Identify the Plugin and Its Auth Contract

Use OpenClaw's supported CLI as the source of truth for installed and enabled state:

```bash
openclaw plugins list
openclaw plugins info <plugin-id>
openclaw plugins doctor --json
```

For community packages, also inspect `openclaw plugins search <name> --json`, npm metadata, the upstream README, package manifest, and `openclaw.plugin.json`. Determine the auth mode from documented setup and metadata such as `providerAuthChoices`, `providerAuthEnvVars`, `syntheticAuthRefs`, and `setup`; do not assume every provider needs an API key.

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

## Step 3: Connect Using the Provider's Auth Flow

For a CLI-backed provider, first verify the CLI login under the same user and environment the Gateway uses. For Antigravity, run `agy models`; a returned model list confirms the existing local login is usable. If the plugin exposes a provider **Reconnect** action, use it to validate that login and import the model rows into OpenClaw. Reconnect reuses the CLI's stored credentials; it is not a request to sign in again or provide an API key.

For an API-key provider, add an auth profile only when its documentation calls for one:

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

Pitfall: enabling a provider plugin only loads its runtime; model discovery may remain empty until its explicit Connect/Reconnect flow completes.

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

## Step 5: Inject API Key (API-key Providers Only)

Do this only when Step 3 and the provider documentation specify an API-key environment variable. CLI-backed providers keep credentials in their own local auth store; do not copy those tokens into OpenClaw config or the Gateway environment. For API-key plugins, the Gateway runs as a systemd user service, so inject the documented variable there:

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

## Step 6: Verify the exact route, not just config validity

1. Run `openclaw config validate`, then `openclaw models status --json`; confirm `resolvedDefault`, the provider auth source, and `modelRouteIssues`.
2. Check `agents.defaults.modelPolicy.allow` as well as `agents.defaults.models`. A configured primary model can still be rejected at runtime if absent from the policy allowlist; add the exact full route to both as needed.
3. Probe the provider directly with a tiny `POST /v1/chat/completions` request (`max_tokens` 16, simple prompt), using the key from its protected store without printing it. Test the requested model and a known-good provider/router model separately to distinguish auth/config errors from one upstream model outage.
4. Check `/health` and the gateway listener before attributing a timeout to the model. Restart only after config changes that are not hot-reloaded; after restart wait for readiness before testing.
5. If the requested model times out but another free/known-good model succeeds, preserve the requested model as selectable and use the confirmed working route as primary or fallback so the client remains usable. Re-test the final selected route with one tiny completion.

Check gateway logs for the model being picked up:
```bash
journalctl --user -u openclaw-gateway.service -n 30 --no-hostname -o cat | grep "agent model"
```
For a CLI-backed provider, also check `openclaw models list --all --provider <provider-id>` after Reconnect; a successful catalog listing alone does not prove that chat completions work.

## Pitfalls

- The `plugins.allow` list **blocks** plugin enablement — you must add the provider there BEFORE running `openclaw plugins enable <provider>`. The CLI will tell you "blocked by allowlist" if you forget.
- Editing `installs.json` directly is NOT supported — use `openclaw plugins enable/disable`. The file header says "DO NOT EDIT".
- Bundled plugins that use `providerAuthEnvVars` read the env var at gateway startup. Adding the key to `~/.bashrc` or similar won't affect the running gateway service — it must be in the systemd unit's `Environment=` directive.
- The `openclaw plugins enable <provider>` command also adds `plugins.entries.<provider>` automatically — do not add it manually or you'll get a duplicate.
- If an explicit `openclaw config set plugins.entries.<provider>.enabled true` is refused with an exclusive offline state ownership error, stop the user Gateway service, rerun that exact command offline, and restart the service through an `EXIT` trap so a failed config write cannot leave the Gateway down. Verify the provider is loaded and Gateway connectivity is healthy afterward.
- Bundled plugins can have `enabledByDefault: true` in their manifest but still be disabled after a prior migration or manual change. Check actual state with `openclaw plugins info <id>` or `openclaw plugins list`, not the manifest default or raw registry files.
- To see which env vars a provider expects, read the plugin manifest's `providerAuthEnvVars` section.
- The openclaw-web-search plugin is known to have TypeScript build issues (stale config entries cause harmless warnings in logs but can be cleaned up from `plugins.allow` and `plugins.entries`).
