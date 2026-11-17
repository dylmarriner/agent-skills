# Codebase Development

Use when editing application code, websites, APIs, CLIs, automation tools, Rust projects, Python projects, TypeScript projects, or full-stack repos.

Core rules:
- First inspect repo state with git status --short.
- Identify the stack before editing.
- Read package files and existing patterns before changing code.
- Make the smallest correct change.
- Do not rewrite unrelated files.
- Do not invent APIs, schemas, files, fake data, or stub implementations.
- Do not add dependencies unless existing dependencies cannot reasonably solve the problem.
- Do not touch .env, secrets, credentials, private keys, or production config.
- Do not suppress errors to make checks pass.
- Prefer existing project architecture over new architecture.

Before editing:
1. Run git status --short.
2. Inspect package.json, pyproject.toml, Cargo.toml, Makefile, justfile, docker-compose.yml, or CI config.
3. Use rg to locate the relevant subsystem.
4. Identify exact files likely involved.
5. State the implementation plan briefly.
6. Then patch only relevant files.

Verification:
- Run the narrowest relevant check first.
- Then run the broader project check if appropriate.
- Show only final relevant output, not full logs.

Common checks:
- TypeScript: npm run typecheck, npm run lint, npm test
- Next.js: npm run build only after smaller checks pass
- Python: ruff check ., pyright, python -m pytest -q
- Rust: cargo fmt --check, cargo check --all-targets --all-features, cargo clippy --all-targets --all-features -- -D warnings, cargo nextest run
- Web UI: npx playwright test

Final output:
- What changed
- Files changed
- Commands run
- Result
- Remaining risks
