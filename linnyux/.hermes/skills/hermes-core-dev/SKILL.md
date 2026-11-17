---
name: hermes-core-dev
description: "Edit, debug, refactor, or review the Hermes Agent codebase"
---
# Hermes Core Development

Use when editing, debugging, refactoring, or reviewing the Hermes Agent codebase.

References:
- `references/config-loader.md` — Config loader pipeline (load_config/read_raw_config/save_config), env var denylist, corruption handling, caching, and three-process architecture (gateway vs dashboard vs CLI/TUI).
- `references/plugin-interaction.md` — Loading Hermes plugin modules from cron/sandbox/terminal context (importlib.util.spec_from_file_location pattern), since execute_code isolates sys.path from Hermes plugin directories.

Core rules:
- First inspect repo state with git status.
- Identify the exact subsystem before editing.
- Read only relevant files.
- Prefer smallest correct change.
- Do not rewrite architecture unless explicitly requested.
- Do not edit user config, .env, tokens, credentials, or private memory.
- Do not modify generated files unless the generator is also updated.
- Do not add mock/stub/null implementations unless explicitly requested for tests.
- Do not silence errors to make tests pass.
- Do not change public interfaces without checking call sites.

Before editing:
1. Run git status --short.
2. Inspect pyproject.toml, package.json, Makefile, justfile, or CI config for official checks.
3. Locate relevant files using rg.
4. Summarize the intended change in 3 bullets.
5. Then patch only the relevant files.

Verification:
- Run the narrowest test first.
- Then run formatting/lint/type checks relevant to the changed area.
- Prefer:
  - ruff check .
  - ruff format --check .
  - pyright
  - python -m pytest path/to/test.py -q
- If frontend files changed:
  - npm test
  - npm run lint
  - npm run typecheck

Output after changes:
- Root cause
- Files changed
- Commands run
- Result
- Remaining risk

Self-editing warning:
- If editing Hermes itself, avoid changing files that affect the currently running session unless necessary.
- If changing tool execution, file editing, config loading, memory, skills, plugins, or terminal backends, require extra review before finalizing.
