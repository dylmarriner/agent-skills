---
name: llm-gateway-endpoint-diagnosis
description: "Use when an LLM client reports firewall/network errors."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [llm, gateway, endpoint, networking, config, claude-code, bifrost, litellm]
---

# LLM Gateway / Endpoint Diagnosis

Use when a client (Claude Code, Hermes, an IDE plugin, a raw SDK script) fails with
network/firewall/proxy wording, when requests are routed through a local gateway or
router (Bifrost, LiteLLM, claude-code-router, an omniroute-style proxy), or when an
endpoint fix "does not stick". The client's error text names the wrong layer; this
skill finds the right one.

## When to Use

- a client fails every request with firewall / proxy / "network may be blocked" wording
- a client is configured to route through a local gateway or router
- an endpoint or model fix "does not stick" after a restart
- you need to place a break precisely: client config, gateway, or the provider behind it

## Rule 0 — the client's network wording is not evidence

Clients print one generic "your network may be blocked, check your firewall/proxy"
banner for **every** failed connection, including a refused port on `127.0.0.1` or a
configured Tailscale address. There is no firewall to inspect until the configured
endpoint is proven reachable. Diagnose the endpoint; never the message.

## Procedure

1. **Enumerate every source that can set the endpoint and model, before reading any of
them.** The effective value can come from the app's own settings file (an `env` block
with `BASE_URL` / `MODEL` / `DEFAULT_*_MODEL` keys), a `settings.local.<ext>`
override, a shell rc file (`~/.bashrc`, `~/.profile`, `~/.zshrc`), a `.env`, or a
launcher/wrapper script. Grep the variable name across all of them, then confirm which
value the process actually sees (`env | grep -i <PREFIX>`).
2. **Prove the port exists.** `ss -ltn | grep <port>` and
`curl -sS -m5 -o /dev/null -w '%{http_code}\n' <base>/v1/models`. Nothing listening
means a stale pointer, not a policy block. Check whether the address is even this
machine (`tailscale ip -4`, `ip -4 addr`): pointing a host at its own tailnet IP looks
remote and fails exactly like a block.
3. **Identify the protocol the endpoint actually speaks.** An OpenAI-compatible server
answers `/v1/chat/completions`; an Anthropic-speaking client needs `/v1/messages` (or a
path prefix such as `/anthropic/v1/messages`). `405` on `POST /v1/messages` means the
route does not exist. Do not repoint a client at an endpoint that speaks the other
protocol: that trades a clear connection error for a confusing parse error.
4. **Separate client-side alias names from provider model ids.** Gateways namespace
models with prefixes (`cc/<model>`, `provider/model`) that exist only inside the
gateway. Going direct means stripping the prefix **and** fetching the canonical ids from
the real API with the stored credential, rather than trusting the alias list.
5. **Check the gateway's upstreams, not just its port.** A healthy container/process
with an empty `/v1/models`, or `provider_connection_failed` / `dial tcp ...: connection
refused` in its log, means the break is behind the gateway (local model servers,
provider keys, DNS). Repointing the client fixes nothing in that state.
6. **After fixing config, find what restores it.** If an edit survives one run and reverts
on the next, you are fighting a restore mechanism, not a cache. See
`references/config-heal-and-restore.md`.

## Verification (do all three)

- `curl` the endpoint you configured and confirm a real HTTP status.
- Run the client for real and check the structured result — e.g.
`claude -p "reply with exactly: pong" --output-format json` must report `is_error: false`.
- Re-read the config file **after** that run: session-start hooks fire during it, so this
is the only check that a removed key stayed removed.

## Pitfalls

- **A running gateway is not a working gateway.** An open port says nothing about the
providers behind it.
- **A valid login is not a valid endpoint.** Auth can be perfectly fine while every
request fails on a dead base URL; the failure then looks like an auth problem and a
network problem at once, and is neither.
- **A dead pointer reads as policy.** Treat "blocked by firewall" as "connection failed"
until the port has been probed.
- **A fix that reverts means a restore mechanism.** Grep the plugin/agent tree for the
value, not only the primary config file — a baseline snapshot is what re-adds it.
- **Do not "fix" a working component into the path.** If the gateway is unrelated to the
client's endpoint, say so and stay on the client's own config; adding it to the path
adds a failure mode.

## References

- `references/config-heal-and-restore.md` — snapshot/heal baselines, tombstones, and how
to make a config removal permanent.
