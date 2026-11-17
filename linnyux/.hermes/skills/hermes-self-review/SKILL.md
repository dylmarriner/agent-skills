# Hermes Self Review

Use after Hermes Agent code changes.

Review for:
- tool permission regressions
- unsafe file access
- config/env leakage
- broken terminal backend behavior
- broken skill loading
- broken plugin loading
- memory/session corruption risk
- async/concurrency bugs
- subprocess timeout bugs
- bad exception handling
- hidden behavior changes
- tests that pass accidentally

Checks:
- Inspect git diff.
- Check changed public functions and call sites.
- Run targeted tests first.
- Run lint/typecheck if available.
- Confirm no secrets or local config were modified.

Return:
1. Must fix
2. Should fix
3. Acceptable risks
4. Verification commands and results
