---
name: llm-cli-endpoint-routing
description: "Use when an LLM CLI cannot reach its model endpoint."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [llm-cli, routing, gateway, base-url, config, debugging]
    related_skills: [claude-code-troubleshooting, harness-plugin-wiring, hermes-agent]
---

# LLM CLI Endpoint Routing

## When to Use

Use for faults between an agent CLI and its model endpoint:

- the CLI reports "blocked by firewall", "network restricted", "proxy error", or "unable to connect"
- print/one-shot mode hangs with no output, or exits only when killed
- requests fail with `model not found` / provider resolution errors while auth looks healthy
- a settings key you deleted keeps reappearing
- a gateway on the LAN/tailnet answers but the CLI still fails

Auth and session-persistence faults belong to the CLI's own troubleshooting skill; this one owns the wire. Gateway response tables, OAuth model enumeration, and baseline-cleanup snippets: `references/gateway-triage.md`.

## Procedure

1. **Read the wording, then ignore it.** "Blocked by firewall / network restricted" is a generic connect-failure banner from most of these CLIs. Treat it as "endpoint unreachable" until proven otherwise.
2. **Find the effective override**, in this order:
   - the CLI's own settings file (Claude Code: `~/.claude/settings.json` → `env.ANTHROPIC_BASE_URL`, `ANTHROPIC_MODEL`, `ANTHROPIC_DEFAULT_*_MODEL`)
   - the local variant next to it (`settings.local.json`)
   - shell rc (`~/.bashrc`, `~/.profile`, `~/.zshrc`) — an export there breaks only shell-launched runs, which reads as "sometimes it works"
   - wrappers, launchers, and editor extensions (VS Code loads the same settings file)
3. **Is anything listening?** `ss -ltn | grep -E ':<port>'` (add `-p` with sudo to name the owner). No listener plus `curl: (7) Failed to connect` = dead endpoint. Stop the firewall hunt.
4. **Read firewall state only to rule it out**, one command: `iptables -S` / `nft list ruleset` / `ufw status`. A default-ACCEPT policy means the banner was never literal. Reaching the real provider and getting a `401` with no auth header also proves the network path is fine.
5. **Check the gateway speaks the right protocol** before trusting a `200` on `/v1/models` — response table in `references/gateway-triage.md`.
6. **Resolve model IDs from the source of truth**, never from a gateway alias. With Claude Code OAuth stored, enumerate via `GET https://api.anthropic.com/v1/models` using the access token (snippet in the reference).
7. **Prefer removing the override to repointing it** when valid credentials exist locally: direct-to-provider has fewer moving parts than a gateway whose upstreams may also be down. Repoint or reinstate the gateway only for a concrete reason (pooled key, org policy, model not offered directly) and only with its upstreams demonstrably up.
8. **Verify with a real session**, not by re-reading the file (see below).

## Rules

- Remove only the keys that control routing. `hooks`, `enabledPlugins`, `statusLine`, `extraKnownMarketplaces` are independent — dropping them silently disables the user's tooling.
- Gateway model aliases (`cc/<id>`, `provider/model`) resolve only on the gateway that defines them. Bypassing it without stripping the prefix gives a perfect handshake and `model not found` on every request.
- A gateway that is up is not a gateway that works: probe its upstreams. `could not auto resolve a provider`, `502 provider_connection_failed`, `dial tcp 127.0.0.1:<port>: connection refused`, and an empty `/v1/models` list are separate faults to fix independently of the base URL.
- Back up before editing: `cp <settings.json> <settings.json>.bak-$(date +%Y%m%d-%H%M%S)`.
- Do not swap the user's model choice to hide the fault; fixing routing must not silently change which model they get.

## Settings that heal themselves back

A key that reappears after you delete it is being restored from a snapshot by a session-start hook — not by the CLI and not by the user. Deleting it again is the wrong move; fix the baseline:

- Find the snapshot store. A settings-heal hook keeps `highwater.json` (the baseline), `highwater.meta.json` (`key_count`/`key_set`), plus `last_healthy.json` and `heal_log.jsonl` for history.
- Remove the key from the baseline and update `key_count`/`key_set` to match, or the next heal re-adds it.
- Write the key into that mechanism's tombstone (`tombstones.json` → `{"tombstoned_keys": ["<key>"]}`); heal restores keys that are *absent* from live settings unless tombstoned.
- Baselines often refresh only when live has MORE keys than stored, so a smaller cleaned file never overwrites a stale larger baseline on its own — the tombstone is what makes the removal stick.

## Verification (definition of done)

1. Run a real one-shot: `<cli> -p "say ok" --output-format json` → `is_error: false` with a sane `duration_ms`.
2. Re-read the settings file and assert the bad key is still absent **after** that run — hooks fire on session start, so only a live run proves the revert is dead.
3. Confirm identity/plan unchanged: `claude auth status --text` shows login method and org.

## Pitfalls

- Print mode can hang until killed while emitting nothing at all (the client silently retries a refused connection). Wrap probes in `timeout 60` and branch on `rc`, never on an empty stdout alone.
- A one-word prompt reporting non-trivial cost is not a routing bug: plugins and hooks inject large context every turn.
- Do not conclude "the gateway can't speak Anthropic protocol" from a `405` on `POST /v1/messages`; 405 = no route, 400 = route exists with a bad body. Probe the provider-prefixed path too.
- When the base URL is the host's own tailnet/LAN IP and nothing listens there, the gateway is simply not running — look for its binary, image, or unit before assuming a port move or rename.
