# Example: Hindsight Monorepo Survey

Hindsight is a semantic memory system for AI agents. This reference shows the output of a full architecture survey applied to that repo.

## Root Config

- `package.json` — npm workspaces: `hindsight-clients/typescript`, `hindsight-control-plane`, `hindsight-docs`, `hindsight-all-npm`, `hindsight-tools/hindsight-agent-sdk`
- `pyproject.toml` — Python project (uv), builds `hindsight` package
- `ruff.toml` — Python linter config
- Versions pinned via `uv.lock` (955K) and `package-lock.json` (1.2M)

## Top-Level Packages (21 directories)

| Package | Language | Role |
|---|---|---|
| hindsight-control-plane | TypeScript/Next.js | Web UI, port 9999 |
| hindsight-api-slim | Python/FastAPI | Core API server |
| hindsight-api | — | Stub (empty) |
| hindsight-cli | Rust | CLI binary (hindsight) |
| hindsight-clients | Go + TS | Generated client SDKs |
| hindsight-embed | Python | Embed library + control center |
| hindsight-all | Python | Server + embed combined |
| hindsight-all-npm | TypeScript | NPM wrapper for full stack |
| hindsight-all-slim | — | Stub |
| hindsight-tools | TypeScript | Agent SDK (8 knowledge tools) |
| hindsight-integrations | — | 47 integration adapters |
| hindsight-integration-tests | Python | E2E smoke tests |
| hindsight-docs | — | Docs site + blog |
| hindsight-dev | Python | Benchmarks + OpenAPI coverage |
| cookbook | — | README only |
| docker | Dockercompose | 11 compose profiles + Dockerfile |
| helm | Helm/K8s | Full K8s chart |
| monitoring | Grafana | 3 dashboards |
| scripts/ | Shell | 40 scripts (release, dev, gen) |
| skills/ | Markdown | Agent skills for Hindsight |
