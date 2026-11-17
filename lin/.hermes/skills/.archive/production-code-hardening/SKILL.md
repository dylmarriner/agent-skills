---
name: production-code-hardening
description: >-
  Audit and harden codebases to production-readiness standards. Multi-file security
  review, configuration hardening, error-handling fixes, secret scanning, shell-injection
  prevention, CORS/Docker/Env-var remediation. Use when the user says 'make this
  production ready', 'ensure everything is production ready', or 'harden for prod'.
  NOT for: one-off lint fixes, style-only changes, or CI pipeline setup.
domain: software-development
tags:
  - production-readiness
  - security-audit
  - code-hardening
  - error-handling
  - configuration
version: 1.1.0
author: agent
---

# Production Code Hardening

Audit a codebase for production-readiness issues and fix them systematically.

## When to Use

- User says "make this production ready", "ensure everything is production ready"
- User asks you to audit a project for deployment
- First-time deployment setup for a codebase that was prototyped or AI-generated
- Security review before open-sourcing or containerizing

Do NOT use for: one-off lint/style fixes, CI/CD pipeline setup, infrastructure provisioning, or adding tests alone.

## Workflow

### Phase 1: Discover files and dependencies

Identify the project structure, language, framework, and all config/source files.
Note the build system and package manager.

### Phase 2: Audit checklist

Run through each category below. For each issue found, fix it immediately — do not batch all findings into a report.

#### Security — CRITICAL priority

- [ ] **Hardcoded secrets**: scan all source for API keys, tokens, passwords, JWT secrets. Any string matching `sk-`, `api_key`, `secret`, `password =`, `token =` followed by a literal (not an env var). Fix: move to env vars, remove fallback literals.
- [ ] **shell=True in subprocess**: every `subprocess.run(..., shell=True, ...)` call. Fix: convert to `shell=False` with argument lists. For piped commands, filter stdout in Python.
- [ ] **Bare `except:` / `except Exception:`**: blocks that silently swallow without logging. Fix: catch specific exceptions, add `logger.exception()` to preserve stack traces.
- [ ] **Error messages leaking internals**: returning `str(e)` to the client in API responses. Fix: log the full error server-side, return a generic message.

#### Configuration — HIGH priority

- [ ] **Hardcoded filesystem paths**: any `/home/user/...`, `/Users/...`, `/tmp/...` paths. Fix: make them env-var configurable with a sensible default (usually `~/.project_name/something`).
- [ ] **Debug mode on by default**: Flask `debug=True`, Django `DEBUG = True`, etc. Fix: default to `False`, enable via env var only.
- [ ] **CORS wide open**: `CORS(app)` or `@cross_origin()` with no args. Fix: scope to specific origins from env var.
- [ ] **Unversioned Docker images**: `redis:latest`, `postgres:latest`, `nginx:latest`. Fix: pin to specific versions (`redis:7.4-alpine`).
- [ ] **Missing `restart: unless-stopped`** on Docker services. Fix: add restart policy.
- [ ] **Healthchecks missing** from Docker services that depend on others. Fix: add healthchecks.

#### Error Handling — HIGH priority

- [ ] **Deferred imports inside request handlers**: `from X import Y` inside a try block in a route handler. Fix: move to module level with graceful try/except for optionals.
- [ ] **`logger.error(f"...")` without exception**: should be `logger.exception(...)` inside except blocks.
- [ ] **Nested or deferred imports that hide dependency failures** — imports that only fail at runtime when a specific code path is hit.

#### Async/Threading Patterns — MEDIUM priority

- [ ] **`call_soon_threadsafe()` with keyword arguments** — `loop.call_soon_threadsafe(fn, arg, kwarg=val)` does NOT support keyword arguments for the callback. Fix: wrap in a lambda — `loop.call_soon_threadsafe(lambda: fn(arg, kwarg=val))`.
- [ ] **Nested `run_in_executor` inside a thread** — calling `loop.run_in_executor(None, work_fn).result()` from inside a function that is ITSELF already running in an executor thread. The `.result()` blocks the outer thread pointlessly. Fix: call `work_fn()` directly since you're already in a thread.
- [ ] **Lambda free-variable capture in exception handlers** — `lambda: fn(exc)` where `exc` is from `except Exception as exc:`. The lambda captures by reference, but `exc` may be garbage-collected or reassigned by the time the lambda runs. Fix: use a default argument — `lambda e=exc: fn(e)`.
- [ ] **Thread-unsafe blocking in async tasks** — synchronous blocking functions (yt-dlp downloads, ffmpeg conversions, SMB uploads) called inside `asyncio.create_task` block the event loop. Fix: run blocking work in `run_in_executor` and use `call_soon_threadsafe(lambda: ...)` for status updates.

#### Implementation Gaps — CRITICAL priority

- [ ] **NotImplementedError stubs**: any `raise NotImplementedError(...)`. Fix: implement with real logic.
- [ ] **`pass` as sole function body**: `def func(): pass`. Fix: implement or delete.
- [ ] **Stub return strings**: functions that return a descriptive message instead of actual data, e.g. `return "WEP exploitation would be implemented here"`, `return "placeholder for now"`. These are NOT marked with NotImplementedError — they look like real returns but do no work. Fix: implement the actual logic.
- [ ] **"would be implemented here" / "implement later" / "stub"** in comments or string literals. Fix: implement now or delete the function.
- [ ] **TODO / FIXME / HACK / XXX comments** in source code. Fix: resolve each one in the same pass. If genuinely deferred, make it a GitHub issue — don't leave it in code.
- [ ] **Catch-all exceptions with no side effects** — `except: pass` or `except: return None` where the caller never checks the None. Fix: log the exception or re-raise meaningfully.
- [ ] **Empty `__init__.py` files** in subpackages — should export their modules via `__all__` + explicit imports. Fix: add proper exports so `from package import X` works.
- [ ] **Orphan `init.py` files** alongside `__init__.py` — dead unimportable files. Fix: delete.
- [ ] **Duplicated modules** — same class defined in both `root/module.py` and `src/module/module.py` where one version is inferior. Fix: pick the superior version, delete the other.
- [ ] **Hardcoded fallback data (mock/placeholder)** — static dicts returned instead of real computation, hardcoded interface lists, canned "success" responses. Fix: replace with real detection or runtime logic.

- [ ] **Dict key-value confusion** — accessing a dict value by a key that lives in the outer key not the value struct. Example: a networks dict keyed by BSSID where `auto_exploit(bssid)` calls `network['bssid']`, but the dict values contain `{'ssid', 'channel', 'rssi', 'encryption'}` — the BSSID is the outer key, not a field. Fix: include the redundant key in the value struct (`"bssid": bssid`) for defensive access, OR use the already-available parameter.

- [ ] **GUI thread blocking** — long-running synchronous operations (scans, downloads, conversions) called directly from the UI event thread, freezing the interface. Fix: move to QThread (PyQt) or `asyncio.create_task` (async GUI). Ensure progress callbacks are thread-safe.

- [ ] **Approach-loop iteration bug** — iterating over a static list of fallback approaches where the inner body modifies state the loop doesn't re-evaluate. Fix: push new approaches dynamically onto the list as they become available, or use a while loop with explicit fallback state.

- [ ] **Conference-call requirements.txt** — two or more `requirements.txt` files where one pins `puppeteer==0.0.0` (nonexistent pip package) while the actual Puppeteer lives in a node_service. Fix: pick one authoritative file, delete the rest.

**Real-implementation rule (hard gate):** Every function that ships must do real work or fail meaningfully. A function that catches all exceptions and always returns `None` is indistinguishable from a stub. A string like `"WPS: not yet implemented"` IS a stub and will be rejected for production code. The user demands "highest standards of real working code implementations" — no exceptions. This is not aspirational — it is a hard gate. If a function cannot be implemented because a system binary or hardware peripheral is missing, report the specific gap with a helpful error message — never fall back to a fake return value.

#### Docker / Deployment — MEDIUM priority

- [ ] **Source baked into image**, not mounted as volume. Fix: add volume mount for development iterations, or rebuild on changes.
- [ ] **Ports exposed to 0.0.0.0** when they only need local access. Fix: `127.0.0.1:PORT:PORT`.
- [ ] **No .dockerignore** or wrong one. Fix: exclude venv, __pycache__, .git, node_modules.
- [ ] **Missing gunicorn/uWSGI entrypoint** when gunicorn is in requirements. Fix: add wsgi.py or gunicorn command.
- [ ] **Container runs as root**. Fix: add USER directive.

### Phase 3: Verify fixes

1. Run a syntax/import check on all modified files
2. Verify each fix by reading the file back and confirming the pattern was removed
3. If Docker, do a `docker compose build` (or at minimum validate the compose file parses)
4. Report: "N files modified, N issues fixed" with a summary table organized by severity

## Code Generation Standards (Write-Time)

These rules apply when WRITING new production code, not just auditing existing code.

### Hard Gate: No Stubs, Placeholders, or Mock Data

Every function must do real work or fail meaningfully. Forbidden patterns in generated code:

| Pattern | Example | Fix |
|---------|---------|-----|
| Fake IDs (MSC001, VLR001) | `msc: "MSC001".into()` | `Err("not found")` or real communication |
| Simulated states | `"assumedIdle"` | Return actual parsed data or omit |
| Hardcoded fallback lists | Static vec of IPs | Real USB/network discovery |
| Canned success | `"SUCCESS"` without doing work | Only return after real operation |
| Stub strings | `"WEP: not yet implemented"` | Don't write the function |
| NotImplementedError | `raise NotImplementedError` | Don't write the function |

**When a dependency is missing:** log the gap, return Err/raise — never return Ok with fake data.

### Gunicorn App Factory Import

Gunicorn resolves `backend.app:create_app` at the **package** level (`__init__.py`), not in a submodule.

If `create_app` lives in `app/main.py`, the `__init__.py` MUST re-export it:
```python
from .main import create_app
```

**Failure mode:** Empty `__init__.py` → `gunicorn.errors.HaltServer: App failed to load.` → container restart loop.

### Empty Package Pattern

Every `__init__.py` should export its modules:
```python
from .main import create_app
__all__ = ["create_app"]
```

An empty `__init__.py` with just a comment will cause import failures when Flask apps try to discover routes or when Gunicorn tries to load the WSGI entry point.

## Common Pitfalls

- **Don't batch fixes without testing each one** — a single bad patch can break imports. Verify after each batch.
- **Don't delete files without explaining why first** — when removing duplicate modules, orphan files, or stale directories, state the reason explicitly in your response before the deletion. The user may not see the duplicates the same way you do, and silent deletions erode trust. Say "I'm deleting X because Y shadows the canonical Z" before you `rm`.
- **Don't use `yaml.dump()` to rewrite config files** — it alphabetizes keys and destroys comments. Use targeted `yq` or `sed` or write the file fresh with correct ordering.
- **Don't fix shell=True in one file without checking all subprocess calls** across the whole project. `grep -rn 'shell=True'` is your friend.
- **Don't remove a secret without checking git history** — it's still in the log. Instruct the user to rotate the key.
- **Don't over-abstract** — env vars with clear defaults are better than config classes for small projects.
- **Don't stop after a security-only pass.** The user saying "make this production ready" includes implementation completeness — stubs, placeholders, TODOs, mock data, and dead orphan files are all production defects. Run the Implementation Gaps checklist alongside Security. The user will reject a codebase that has clean secrets management but stubs pretending to be real functions.

## References

When fixing shell injection vulnerabilities:
- Replace `subprocess.run(f"adb shell {cmd}", shell=True)` with `subprocess.run(["adb", "shell", arg1, arg2], shell=False)`
- For pipelines: run each command separately, filter output in Python
- For long-running subprocesses needing managed lifecycle (airodump-ng,
  hcxdumptool, capture tools, servers): use process group pattern —
  `Popen(cmd, start_new_session=True)` isolates the tree; kill with
  `os.killpg(os.getpgid(proc.pid), signal.SIGTERM)` + wait + SIGKILL
  fallback. Plain `proc.terminate()` only kills the shell, not the child tool.

When fixing hardcoded paths:
- Use `os.environ.get("KEY", os.path.expanduser("~/.default_path"))`
- Not `os.environ.get("KEY") or "/home/user/hardcoded"`

See `references/placeholder-stub-patterns.md` for exact grep commands and concrete examples of stub return strings, NotImplementedError traps, orphan init.py files, duplicate module trees, and hardcoded mock data found in real production audits.

See `references/queue-system-pattern.md` for the SQLite-backed persistent async queue pattern — state machine, background worker, Semaphore concurrency, CLI/API integration, and lifecycle management.
