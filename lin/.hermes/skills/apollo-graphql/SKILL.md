---
name: apollo-graphql
description: >
  Complete Apollo GraphQL platform toolkit: Client (React/Android), Server, Federation, & Router.
  Use this skill for: (1) Apollo Client setup in React/Kotlin, (2) Apollo Server resolvers/schemas,
  (3) Federation subgraph design (@key, @external, @requires), (4) Apollo Router configs
  (v1/v2), (5) Connectors for REST integration, (6) GraphQL Codegen, (7) troubleshooting Apollo tools.
license: MIT
metadata:
  author: apollographql
  version: "1.0.0"
---

# Apollo GraphQL Platform

## Overview

This is the consolidated Apollo GraphQL skill, covering the entire Apollo platform:

| Subtopic | Description |
|----------|-------------|
| **1. Apollo Client** | React/Android GraphQL client (Apollo Client 4.x, Apollo Kotlin) |
| **2. Apollo Server** | GraphQL server setup (Apollo Server 5.x) |
| **3. Apollo Federation** | Subgraph schema design (@key, @external, @requires, @provides) |
| **4. Apollo Router** | Supergraph router configs (v1.x and v2.x) |
| **5. Apollo Connectors** | REST-to-GraphQL integration (@source, @connect directives) |

## Section 1: Apollo Client

### React (Apollo Client 4.x)
See: `references/client/react.md`
- Hooks: useQuery, useMutation, useSuspenseQuery
- Caching strategies, data masking, Suspense patterns
- Integration: Next.js, React Router, TanStack Start

### Kotlin (Apollo Kotlin 4.x)
See: `references/client/kotlin.md`
- Gradle setup, schema download/codegen
- ApolloClient configuration (auth, interceptors)
- Target platforms: JVM, Android, KMP

## Section 2: Apollo Server

See: `references/server/apollo-server.md`
- Schema definition, resolvers, context/auth
- Server frameworks: Express, Fastify, standalone
- Plugins, data sources, error handling

## Section 3: Apollo Federation

See: `references/federation/subgraphs.md`
- Entity patterns (`@key`, `@shareable`)
- Field distribution (`@external`, `@requires`, `@provides`, `@override`, `@inaccessible`)
- Composition troubleshooting

## Section 4: Apollo Router

See: `references/router/config.md`
- **Version selection critical:** v1.x vs v2.x (incompatible configs)
- Production vs development templates
- Features: JWT auth, CORS, Connectors (v2 only), telemetry, traffic shaping

## Section 5: Apollo Connectors

See: `references/connectors/rest-integration.md`
- @source, @connect directives
- Selection mapping, batching, error handling
- Validation with rover CLI

## Ground Rules

- **ALWAYS** determine which Apollo sub-platform (Client/Server/Federation/Router/Connectors) before answering
- **ALWAYS** use Apollo Client 4.x patterns (not v3 or earlier) for React
- **ALWAYS** use Apollo Server 5.x patterns (not v4 or earlier) for Node.js
- **ALWAYS** use Federation 2.x syntax with `@link` directive
- **ALWAYS** determine Router version (v1/v2) before generating configs
- **ALWAYS** validate Router configs with `references/router/validation.md` after generation
- **NEVER** expose APOLLO_KEY in logs or version control
- **PREFER** GraphOS-managed mode for production (automatic updates, metrics)
- **PREFER** Suspense hooks in modern React applications for better DX

## Reference Files

### Client
- `references/client/react.md` — React Client 4.x main guide
- `references/client/integrations.md` — Next.js, React Router, TanStack Start
- `references/client/kotlin.md` — Kotlin/Android/KMP guide
- `references/client/codegen.md` — Schema download and GraphQL CodeGen

### Server
- `references/server/apollo-server.md` — Apollo Server 5.x main guide
- `references/server/resolvers.md` — Resolver patterns and best practices
- `references/server/context-auth.md` — Auth and context setup
- `references/server/plugins.md` — Plugins and data sources

### Federation
- `references/federation/subgraphs.md` — Federation 2 schema design
- `references/federation/directives.md` — All federation directives reference
- `references/federation/composition.md` — Composition errors and debugging

### Router
- `references/router/config.md` — Router config v1/v2 (master reference)
- `references/router/divergence-map.md` — v1 ↔ v2 config differences
- `references/router/validation.md` — Post-generation checklist
- `references/router/telemetry.md` — Tracing, metrics, logging

### Connectors
- `references/connectors/rest-integration.md` — REST API integration guide
- `references/connectors/grammar.md` — Selection mapping grammar
- `references/connectors/entities.md` — Entity patterns and batching
- `references/connectors/troubleshooting.md` — Common errors

## Scripts
- `scripts/list-apollo-kotlin-versions.sh` — List Apollo Kotlin versions
- `scripts/list-apollo-kotlin-cache-versions.sh` — List Apollo cache library versions

## Integration
**Related Skills:** graphql-schema, graphql-operations, rover  
**External Tools:** Rover CLI, Apollo DevTools, GraphOS MCP