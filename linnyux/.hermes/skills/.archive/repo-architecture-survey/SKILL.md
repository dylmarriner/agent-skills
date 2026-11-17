---
name: repo-architecture-survey
description: "Map a repository's full surface area — discover all packages, their roles, components, API endpoints, CLI commands, integrations, and infrastructure in one structured pass."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [repo, architecture, survey, onboarding, monorepo, discovery, codebase]
    related_skills: [codebase-inspection, understand]
---

# Repository Architecture Survey

Map a repository's full surface area — all packages, their roles, views, API endpoints, CLI commands, integrations, and supporting infrastructure. Produces a structured, comprehensive report suitable for onboarding, architecture reviews, or documentation generation.

## When to Use

- User asks "what's in this repo?", "map the architecture", "give me the full surface"
- User asks "what packages are there?", "list all the things in this monorepo"
- User wants to understand a new codebase's structure for the first time
- User needs a comprehensive inventory before making cross-cutting changes
- User wants to document a repo's surface for a README, ADR, or architecture doc

## Workflow

### Phase 1: Root-level Discovery

Start by listing the top-level structure and reading the root workspace config:

```bash
ls -la /path/to/repo       # see all top-level dirs and files
```

```bash
# Read root configs that define the workspace structure
cat /path/to/repo/package.json      # npm workspaces
cat /path/to/repo/pyproject.toml    # Python workspace
cat /path/to/repo/Cargo.toml        # Rust workspace
```

Key things to identify from root configs:
- **Workspace array** in package.json — lists npm workspace packages
- **Subdirectories with package.json/pyproject.toml/Cargo.toml** — each is a package
- **Root scripts** — dev, build, test commands that coordinate the workspace
- **Dependency overrides** — security patches, version pins across the repo

### Phase 2: Parallel Package Probing

Once you know what packages exist, probe them **in parallel** (batch independent tool calls in one turn). For each package, determine what *kind* of package it is and probe accordingly:

#### For UI / Control Plane packages:
```
List component files: find package/src/components -name '*.tsx' | sort
Read package manifest: cat package.json  (focus on dependencies + scripts)
```

#### For API / Backend packages:
```
List all source files by extension: find package -name '*.py' | sort
Identify API endpoint surface from:
  - OpenAPI spec files: find package -name 'openapi.yaml' -o -name 'openapi.json'
  - Auto-generated SDK/route files (e.g., sdk.gen.ts, api_*.go, routers files)
  - Grep for route decorators/annotations (@app.get, router.get, @route, etc.)
List SDK functions to get the full endpoint catalog: grep -oP 'export const \w+' sdk.gen.ts
```

#### For CLI packages:
```
List source files: find package/src -type f | sort
Read Cargo.toml / package.json for command framework and dependencies
List command modules: cat src/commands/mod.rs  (or equivalent)
```

#### For Integration adapter directories:
```
List dirs: ls -1d integrations/*/
```

#### For Client SDK packages:
```
List source files and identify supported languages
Read the generated client files to understand the API surface
```

#### For Infrastructure packages:
```
List files: find docker/ -type f | sort
List files: find helm/ -type f | sort
List files: find monitoring/ -type f | sort
```

#### For Tool / Agent SDK packages:
```
Read the main source to understand exported tools and their signatures
List test files for usage examples
```

### Phase 3: Compile the Structured Report

Organize findings into this structure:

```
## 1. Top-Level Packages / Directories
[One-line per package: name, language/runtime, description]

## 2. [Control Plane / UI] Components
[If applicable: list feature views, then UI primitives]
[Key dependencies from package.json]

## 3. [API] Endpoints
[If applicable: organized by domain — banks, memory, documents, etc.]

## 4. Integrations
[If applicable: list all integration adapters]

## 5. CLI Commands
[If applicable: list all command modules]

## 6. Tools
[If applicable: list tool packages with their exported tools]

## 7. Additional Packages
[hindsight-embed, hindsight-all, hindsight-all-npm, etc.]

## 8. Infrastructure
[Docker compose profiles, Helm chart components, monitoring dashboards]

## 9. Scripts & CI
[Key script categories — release, dev, benchmarks, code generation]
```

## Pitfalls

1. **Don't stop at pygount** — LOC counts tell you nothing about architectural structure or package relationships.
2. **Use parallel tool calls** for independent probes. Reading the API package does not require the CLI package result first. Batch independent file listings and reads into a single turn.
3. **Always check root workspace config** — without reading package.json/pyproject.toml, you'll miss relationships between packages and how to build/run them.
4. **Don't crawl node_modules/venv/target/.next** — use find with `-not -path '*/node_modules/*'` and `-not -path '*/.git/*'` filters.
5. **If a package has no source files** (just pyproject.toml + README), note it as a stub — this is diagnostic information showing incomplete setup.
6. **For auto-generated clients**, prefer reading the generated SDK function list over the raw OpenAPI yaml — it's more compact and gives the exact endpoint names.
7. **Monorepos often have build-order dependencies** (e.g., client SDK must build before control plane). Note these from the root package.json scripts section.
8. **For integration directories**, just list directory names — drilling into each one is a separate deep-dive task.
