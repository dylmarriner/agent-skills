# SCOS Memory Fabric — a THIRD, distinct memory system

**Correction (user, 2026-08):** SCOS is NOT Nexus and NOT Synapse. It is a
separate memory substrate. Do not conflate them. The `synapse:` block in
Hermes config.yaml is Synapse — it has nothing to do with SCOS. A disabled
`synapse:` MCP block does NOT mean "SCOS is off." To check SCOS, check SCOS.

## What it is

"SCOS Memory Fabric" — a crash-resilient, permission-aware, model-neutral
memory substrate for SCOS, Nexus and heterogeneous AI agents. Written in Go
(memory gateway) + PostgreSQL with pgvector. Source:
`/media/kubuntux/DEVELOPMENT1/scos-memory/` on kubuntux.

## Where it runs (kubuntux, docker compose `scos-memory-integration_default`)

| Component | Address (tailnet) | Notes |
|---|---|---|
| memory-gateway | `100.93.75.87:8080` (HTTPS) | Auth-gated `/v1/*`; open health endpoints |
| memory-intelligence | `100.93.75.87:8089` | |
| Postgres | db `scos_memory`, user `scos` | sslmode=require in prod compose |
| Redis | `:6379` | |
| observability | `:8096` | |
| agent-registry | `:8093` (127.0.0.1) | |
| autonomous-control-plane | `:8081` (127.0.0.1) | |

Auth env tokens seen in the gateway container:
`SCOS_INTERNAL_SERVICE_TOKEN`, `SCOS_CONTROL_PLANE_TOKEN`,
`SCOS_AUTH_ISSUER_SECRET`.

## Health check (no auth needed)

```
curl -ks https://100.93.75.87:8080/health/live
curl -ks https://100.93.75.87:8080/health/ready   # checks postgres + process
curl -ks https://100.93.75.87:8080/v1/version     # → "authentication required" (gated)
```

## Hermes integration status: NOT BUILT (stubs)

`adapters/hermes/adapter.go` — `HermesBridge.SyncTurn()` validates the payload
then returns `nil` WITHOUT sending anything to the gateway. Placeholder.
`adapters/mcp/adapter.go` — MCP `Handler` returns a canned `{"status":"handled"}`
response; does no real work. No client SDK, no config wiring, nothing in
Hermes config.yaml points at SCOS. README lists "MCP and A2A adapters" as
**item 7 in the development order** — i.e. not yet implemented.

So: the fabric is alive/healthy, but there is NO working bridge between a
Hermes agent and SCOS yet. To build it: implement SyncTurn (or a real MCP
tool layer) against the authenticated `/v1/*` API, wire into Hermes config,
authenticate with the internal-service token.

## Readiness endpoints naming

Gateway uses `GET /health/live` and `GET /health/ready` (not `/health`), and
`GET /v1/version`. Compose service healthchecks use `wget -qO- .../health/ready`.
