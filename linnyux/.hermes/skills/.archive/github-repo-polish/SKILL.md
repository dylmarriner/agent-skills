---
name: github-repo-polish
description: "Make a GitHub repo look enterprise-grade and professional. Badges, arch diagrams, community standards, CI/CD, docs."
version: 1.0.0
author: agent
---

# GitHub Repo Polish — Enterprise Overhaul

Make any GitHub repo look production-ready with badges, architecture diagrams, community standards, CI/CD, and documentation.

## Trigger Conditions

Use when the user says:
- "make this the best looking repo on github"
- "enterprise grade repo overhaul"
- "professional README"
- repo is missing standards files

## File Inventory

### 1. Community Standards (Root)

| File | Content | Purpose |
|------|---------|---------|
| `LICENSE` | MIT with current year + user name | Required for public repos |
| `CODE_OF_CONDUCT.md` | Contributor Covenant v2.1 | GitHub community standard |
| `CONTRIBUTING.md` | Dev setup, PR workflow, coding standards | Onboard contributors |
| `SECURITY.md` | How to report vulnerabilities, GPG key | Trust signal for security researchers |

### 2. README.md

Structure:
```
[Logo/Banner image]
[Badge row: CI · License · Version · Python · Framework · DB · Status · Stars]
[Navigation links: Quick Start · Architecture · API · Clients · Deployment · Dev]

--- tagline ---

[Two-column feature table]

## Quick Start (clone + run + verify)
## Architecture (diagram link)
## API (endpoint table + MCP tool list)
## Client Integration (config blocks for each agent type)
## Deployment (Docker, env vars table, standalone)
## Development (setup, test, lint, project structure)
## Contributing / License
```

**Badge sources:**
```
CI:     https://img.shields.io/github/actions/workflow/status/{owner}/{repo}/ci.yml
License: https://img.shields.io/badge/license-MIT-{color}
Version: https://img.shields.io/github/v/release/{owner}/{repo}
Python:  https://img.shields.io/badge/python-3.11+-{color}
Stars:  https://img.shields.io/github/stars/{owner}/{repo}
Status: https://img.shields.io/badge/status-production-{color}
```

### 3. Architecture Diagram

Create an interactive SVG architecture diagram:

```
docs/architecture.html
```

Use the `architecture-diagram` skill for generation. Dark theme, JetBrains Mono font, component categories with semantic colors (cyan=frontend, emerald=backend, violet=database, amber=subsystem, rose=security).

### 4. GitHub Configuration

```
.github/
├── workflows/
│   ├── ci.yml              # Lint → TypeCheck → Test → Build → Push
│   └── release.yml         # On tag v* → Build + Release
├── dependabot.yml          # pip/docker/actions weekly
├── ISSUE_TEMPLATE/
│   ├── bug_report.yml      # YAML form with env/version/logs/reproduction
│   ├── feature_request.yml # YAML form with problem/solution/alternatives
│   └── config.yml          # Blank issues disabled
├── PULL_REQUEST_TEMPLATE.md # Checklist (quality, testing, docs, compat)
└── FUNDING.yml             # Placeholder
```

### 5. CI/CD Workflow Pattern

```yaml
# ci.yml — runs on push/PR to main
jobs:
  lint:     ruff check .
  typecheck: mypy app/
  test:     pytest tests/ -v (with service containers for DB + Redis)
  build:    docker build . → push to ghcr.io/{owner}/{repo}:{sha}
```

```yaml
# release.yml — on push tag v*
jobs:
  release:
    - docker tag + push {semver} and {latest}
    - gh release create with changelog
```

### 6. Dependabot

```yaml
# .github/dependabot.yml
updates:
  - package-ecosystem: "pip"     (weekly, group PRs)
  - package-ecosystem: "docker"  (weekly)
  - package-ecosystem: "github-actions" (weekly)
```

### 7. .gitignore

Comprehensive: Python caches, virtual envs, IDE files, OS files, Docker volumes, logs, DB files, agent-specific files.

## Pitfalls

- **Don't hardcode the user's secret token** in git remote URL after push. Reset it to HTTPS without token.
- **Badge URLs** must point to raw.githubusercontent.com or shields.io, not local paths.
- **SVG arch diagrams** must be self-contained (no JS, inline CSS, Google Fonts CDN is OK).
- **CI secrets**: The CI workflow needs `REGISTRY_TOKEN` or `GITHUB_TOKEN` for Docker push.
- **Docs link in README** must point to `docs/architecture.html` not outside the repo.
