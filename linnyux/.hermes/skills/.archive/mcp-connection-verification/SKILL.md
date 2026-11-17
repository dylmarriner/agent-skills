---
name: mcp-connection-verification
description: Probe whether an MCP server is connected and scoped.
version: 1.0.0
metadata:
  category: mcp
  tags: [MCP, Verification, Credentials, Triage]
---

# MCP Connection Verification

Use when the question is "is <provider> MCP connected?", "why don't these tools work?", "can you use X
for me?", or any request that depends on a remote MCP (Cloudflare, Linear, Sentry, GitHub, hosted
relays) actually being live. The deliverable is a verdict backed by real calls, split into what works
and what is missing — not a reading of the config file.

## Rule zero

`enabled: true` in `~/.hermes/config.yaml` proves the entry exists. It says nothing about whether the
transport came up, whether discovery registered tools, or whether the credential has any scope. Never
answer a connectivity question without at least one real tool call.

## Probe ladder (stop at the first rung that fails)

1. **Confirm discovery ran.** `tool_search` with the provider name plus a concrete action/object
   ("cloudflare list zones", not "cloudflare"). A hits list containing `mcp__<server>__<tool>` names
   means startup discovery succeeded and the session is alive; the deferred catalog also reports the
   source's `tool_count`. No catalog entry for a configured server = discovery failed.
2. **Read the config entry, including exclusions.** The server's block in `~/.hermes/config.yaml`
   (`mcp_servers.<name>`) carries `url`/`command`, `headers` (often `Authorization: Bearer ${VAR}`
   interpolated from `~/.hermes/.env`), and `tools.include`/`tools.exclude` globs. A whole tool family
   can be absent by config while the provider serves it — check the exclude globs before telling the
   user a capability is unavailable.
3. **Make one cheap real call** — a list/verify/get on the provider's most basic resource. This is the
   only evidence that counts.
4. **Classify the outcome** (see next section) instead of collapsing it to yes/no.
5. **Probe the specific endpoint the user actually needs** (DNS records, workers scripts, load
   balancers). The gap is usually one permission group, not the whole server.

## Classify: transport failure vs credential scope

| Observation | Verdict |
|---|---|
| `Failed to connect to MCP server …`, no `tools/list` response, `mcp__<server>__*` prefix absent | Transport/connection failure — fix config, endpoint, network |
| Tool call returns a provider-shaped error body (`{"code": …, "message": …}`) | **Connected.** Transport, MCP session, and the injected credential header all work. Interpret the code |
| Per-tool HTTP 401/403, `insufficient_scope`, "Authentication error" with a numeric provider code | Connected, credential under-scoped for that resource |
| Failure on `/user/*`, `/memberships`, `/user/tokens/verify` with an account-scoped credential | Expected by design — not a fault. Re-probe on a resource the credential is scoped to |
| Capability absent from `tool_search` while the provider documents it | Check the config's `tools.exclude` globs — invisible by config, not by permission |

Provider-specific code → meaning tables live in `references/credential-scope-triage.md` (Cloudflare
codes and endpoints first). Add new providers there rather than in this file.

## Pitfalls

- **A provider error body is not a connection failure.** Reporting "not connected" when the provider
  returned `{code, message}` sends the user hunting for a networking problem that does not exist; the
  real gap is credential scope. Name the scope gap instead.
- **A `permissions` / `scopes` / `available_scopes` array on a resource object is an entitlement list,
  not your credential's grants.** Provider APIs attach feature entitlements to resources (a zone object
  can list `#dns_records:edit` while the token has no DNS grant), so reading them as the credential's
  scopes makes you promise work that dies with an authentication error on the endpoint you just listed.
  A credential's real scope is only visible from its own token/policy object — and reading that needs
  credential-management permission.
- **Do not test auth with user-level endpoints on an account-scoped credential.** `/user/*`,
  `/memberships`, `/user/tokens/verify` refuse account tokens by design and look like a dead integration.
- **Rotating a credential by cloning it strands it if management groups are dropped.** A replacement
  cloned without credential-management permission can never read or widen itself again, so every future
  scope gap becomes a manual dashboard re-mint. Keep the management groups on the replacement whenever
  self-service rotation is wanted, and say so when you hand the credential over.
- **A new credential value is not live until a full restart.** `${VAR}` interpolation from `.env` and
  MCP tool discovery both happen at startup; `/reset` is not sufficient.
- **Never claim a capability is unavailable from partial evidence.** Check all three sources — config
  exclude globs, credential scope, and a live probe — then state what was actually checked.

## Answer shape

Give the verdict first, then the evidence as a compact split:

- server + endpoint + how many tools registered (and which families config hides)
- what the credential reads successfully, with the real call that proved it
- exactly which capability fails, with the provider code and its meaning
- the concrete fix, named: which grants to add, or that a dashboard re-mint is the only path

The user wants execution and a verdict, not a menu of options. If the fix is a credential only the user
can mint (dashboard-only), say so in one line and offer to install and re-verify the moment they hand it
over — do not stall on clarifying questions you can answer yourself.

## Related

Connecting/configuring servers (`mcp_servers` shape, transports, restart semantics) and SSE/host-port
client debugging live in the `native-mcp` and `mcp-sse-endpoint-troubleshooting` skills — both are
user-owned; read them, do not edit them.
