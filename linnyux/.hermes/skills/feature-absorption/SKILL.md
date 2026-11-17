---
name: feature-absorption
description: Absorb features from external memory/agent systems into Synapse Memory
---

# Feature Absorption Skill

## Trigger
When the user asks to absorb features from an external memory/agent system into Synapse Memory at `/mnt/development1/synapse-memory/`.

## Process

1. **Audit the source project** — list all packages, views, APIs, integrations, tools
2. **Map to Synapse gaps** — what doesn't Synapse have yet?
3. **Build client SDK first** — `clients/python/synapse_client/` with `Nexus` class matching the source project's client interface. This is the foundation every integration depends on.
4. **Port integrations batch** — integrations are thin wrappers that import the client SDK. Batch by language (Python -> TypeScript -> rest)
5. **Port CRUD layer** — peer model, sessions, messages, observations, webhooks as `app/adopted/` modules
6. **Port infrastructure** — queue system, multi-backend LLM, vector stores, telemetry, workers, webhooks
7. **Port CLI and client SDKs** — Rust CLI, TypeScript client
8. **Port monitoring** — Grafana dashboards

## Layer Structure

```
synapse-memory/
├── app/adopted/          -- Every new feature as an adopted module (self-contained, additive)
├── clients/              -- SDKs: python/synapse_client, typescript/, cli/
├── integrations/         -- Agent framework adapters: python/, typescript/
└── monitoring/           -- Grafana dashboards
```

## Key Principles

- **No branding** from the source project
- **Self-contained** — each adopted module is independently importable
- **Additive** — patterns extend existing code, never modify it
- **Client-first** — build the client SDK before any integration
- **Zero stubs** — every function does real work or fails cleanly
- **Refer to ABSORPTION_PLAN.md** for the full phased implementation blueprint
