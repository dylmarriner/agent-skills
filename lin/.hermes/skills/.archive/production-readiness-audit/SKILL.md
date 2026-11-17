---
name: production-readiness-audit
description: |
  Multi-track production readiness audit. Orchestrates parallel subagents for
  security, frontend/UI/UX, code quality, SEO/AIEO, and infrastructure analysis.
  Compiles findings into a unified report with severity-graded issues and phased
  fix plans. Designed for high-value ($50K+) production deployments.
version: 1.1.0
toolsets: [delegation, terminal, file]
platforms: [linux, macos]
---

# Production Readiness Audit

Orchestrate a comprehensive multi-track audit of a web application codebase for
production deployment. Spawns parallel specialist subagents, then compiles their
findings into a unified severity-graded report with phased fix plans.

## When to Use

Use this skill when:

- The user asks to "make this production ready" or "audit for production"
- The user says a site/app needs to meet a specific dollar-value standard ($10K, $50K, etc.)
- Deploying a new application and need a comprehensive pre-launch checklist
- The user asks for a "full audit" or "everything check" of their codebase
- A previous audit existed and needs verification + extension
- Auditing a backend API / framework app (Flask, FastAPI, Express, etc.) for security and code quality

Also use this skill for:

- **Source-to-implementation gap audit**: The user provides original source files
  (prototypes, legacy code, vendor SDKs) and wants to know which classes have been
  ported to the current workspace. See `references/source-implementation-audit.md`
  for the full methodology with shell commands, grep patterns, and categorization
  rules.

Do NOT use this skill for:
- Quick CI/CD pipeline checks (use `audit-website` with `--coverage quick` directly)
- Single-aspect reviews like "check my SEO" or "review my security headers" alone
- Code review on a single PR (use `code-reviewer` instead)

## Audit Tracks

Spawn up to 3-4 parallel subagents. Each runs independently and returns a structured
summary. Pass the project root path and relevant context.

Choose tracks based on the project stack. For web apps, use all 4 tracks below.
For backend-only apps (Flask, FastAPI, Express, Rust, etc.), use Tracks 1, 3, and 5.

### Track 1: Security & Infrastructure (all stacks)
**Context to pass**: Project root, Dockerfile, docker-compose.yml, requirements.txt,
package.json, config files, main entrypoint.

**Checks**:
- Security headers (HSTS, CSP, XFO, XSS, Referrer-Policy, Permissions-Policy)
- CSRF/XSS protections (CSP directives, input sanitization, DOMPurify usage)
- Rate limiting on all POST/API endpoints
- Authentication on admin/API routes
- Secrets exposure in source code (hardcoded API keys, JWT secrets, passwords)
- Hardcoded filesystem paths (user-specific paths like `/home/user/...`)
- HTTPS redirect and CORS configuration
- Error messages leaking internal state to clients (`str(e)` in JSON responses)
- Debug mode / verbose logging enabled in production
- Shell injection vectors (`shell=True` in subprocess calls)
- Bare `except:` blocks that silence KeyboardInterrupt
- Generic `except Exception` swallowing without logging
- Database connection security
- JWT secret key management (env vars vs hardcoded placeholders)
- Docker image version pinning (no `:latest` tags)
- **Hardcoded model/API defaults**: Default model names hardcoded instead of
  configurable via env vars (e.g. `DEFAULT_MODEL = "deepseek-chat"` vs
  `os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")`)
- **Nonexistent method calls**: Methods called by wrong name (typos, renamed
  methods) that only fail at runtime — grep for `.method_name(` calls and
  verify the called name exists as a class method

### Track 2: Frontend / UI / UX (web apps only)
**Context to pass**: src/components/ path, src/app/ path, package.json.

**Checks**:
- Accessibility (WCAG 2.2 AA): skip links, keyboard nav, aria attributes, color contrast
- Error boundaries: error.tsx, loading.tsx, not-found.tsx presence
- Form validation UX: field-level errors, aria-invalid, focus management
- Mobile responsiveness across all pages
- Image optimization: next/image usage, lazy loading, sizes attributes
- React patterns: stable keys (no key={Math.random()}), component splitting
- Component duplication: multiple implementations of same concept
- Tailwind/CSS: no undeclared theme classes, proper plugin usage
- Empty states for all data-fetching components
- Console warnings and hydration mismatches

### Track 3: Code Quality & Architecture (all stacks)
**Context to pass**: Full source tree, package.json, requirements.txt, tsconfig.json,
existing test files, Makefile.

**Checks**:
- TypeScript any usage count and locations (TS projects)
- Code splitting: modules over 500 lines flagged
- Duplicate implementations (meta functions, schema components, button components)
- Lint suppression patterns (eslint-disable frequency)
- Dead code: unused imports, unreachable code paths
- Error handling patterns: bare except in Python, empty catch blocks in JS
- Import organization and tree-shaking capability
- Migration compatibility (e.g. Tailwind v3 config coexisting with v4)
- Test coverage gaps
- **Project structure duplication**: Check for root-level directories that share
  names with src/ subdirectories (e.g. root core/ shadows src/core/). Python
  resolves the current working directory before sys.path insertions, so duplicate
  root-level packages silently shadow the canonical src/ versions. Delete the
  root-level copy and verify all imports resolve correctly.
- **Stub/placeholder audit**: Hard requirement — zero stubs, zero placeholders,
  zero TODOs, zero "not yet implemented" in production code. Grep for:
  TODO, FIXME, placeholder, not yet implemented, would be implemented,
  "# stub", "# mock". For Python, check `rg 'def .*\):' -A1` to catch empty
  function bodies. Every function must have a real working implementation.
- **Duplicate script consolidation**: If 3+ files share >70% structural code
  (same imports, class instantiation pattern, loop structure, error handling),
  consolidate into one with `--mode` or named subcommand. Check via diff or
  manual grep comparison. Five scripts that all do the same
  proxy-manager / browser-bypass / downloader pipeline are one script, not five.
- **Stale environment cleanup**: Check for multiple venv/ / .venv/ directories
  (keep only one), obsolete requirements.txt files at project root when
  backend/requirements.txt exists, leftover node_modules/ outside .gitignore.
- **Hardcoded business data in source**: Grep for literal URL lists, SSH host
  strings, hardcoded IP addresses, array-of-dicts with repetitive structure.
  These should be env vars, config files, or external data sources.
- Python-specific: deferred imports inside function bodies, singleton thread safety,
  blocking time.sleep() in concurrent contexts, logger.error vs logger.exception
- Dockerfile: multi-stage builds, USER directive, WORKDIR, COPY order

### Track 4: SEO / AIEO / Content (web apps only)
**Context to pass**: src/app/ pages tree, next.config.ts, any existing SEO docs.

**Checks**:
- Meta titles (50-60 chars), descriptions (150-160 chars), unique per page
- og:image / twitter card presence on all pages
- JSON-LD schema: single implementation, no duplicates, proper @id linking
- AIEO readiness: llms.txt, pricing.md, robots.txt allowing AI crawlers
- Author attribution and last-updated dates on content
- Content thickness (300+ word minimum per page)
- E-E-A-T signals: named authors, cited sources, contact page, privacy policy
- URL structure: clean, keyword-inclusive
- Core Web Vitals: LCP, CLS, INP baseline from lighthouse or PageSpeed
- Canonical URLs and hreflang tags

### Track 5: Python Backend Audit (Python-only)
**Context to pass**: Full Python source tree, requirements.txt, Dockerfile,
docker-compose.yml, entrypoint files (main.py, app.py, wsgi.py).

**Checks**:
- **Secrets in source**: hardcoded API keys, JWT secrets, database passwords as plaintext fallbacks
- **Subprocess safety**: all subprocess.run with shell=True — flag each one; non-static
  commands (user input in args) are CRITICAL
- **Error handling**: bare except: clauses (Python anti-pattern), generic
  except Exception: pass with no logging, missing tracebacks (logger.exception vs logger.error)
- **Exception message leakage**: str(e) returned to HTTP clients in JSON responses
- **Hardcoded paths**: /home/user/... paths that won't work on other machines
- **Deferred imports**: import requests inside method bodies instead of module level
- **Singleton safety**: non-thread-safe _instance = None patterns
  in gunicorn/eventlet contexts
- **API security**: missing auth decorators on endpoints, permissive CORS (no args)
- **Rate limiting**: rate limiter module exists but never applied to endpoints
- **Input validation**: user input reaching business logic unvalidated
- **Blocking calls**: time.sleep() in async/eventlet contexts
- **Hardcoded timeouts**: magic number timeouts instead of configurable constants or env vars
- **gunicorn/WSGI**: app.run() instead of a proper wsgi.py entrypoint
- **Docker**: unversioned base images, no healthchecks, no restart policy, secrets in build args
- **Frontend serving**: send_from_directory catching all routes without proper path isolation
- **ANSI escape parsing**: When parsing CLI tool output (yt-dlp _percent_str, _speed_str),
  strip ANSI escape codes with regex before trying to convert to float/int. The pattern
  is `re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')`. Raw yt-dlp strings like " 12.5%" contain
  escape sequences that crash float() conversion.
- **Python package structure**: Every subdirectory that should be a package needs
  an __init__.py (even if empty). Also check for orphan init.py (no underscores)
  files that are dead code alongside the real __init__.py.

## Orchestration Workflow

### Phase 1: Project Recon (30 seconds)
```bash
# Identify stack
cat requirements.txt package.json Cargo.toml 2>/dev/null
find . -maxdepth 3 -type f -name '*.py' -o -name '*.js' -o -name '*.ts' | head -30

# Check entrypoint
cat backend/app/main.py 2>/dev/null | head -20
cat src/main.rs 2>/dev/null | head -20

# Check Docker config
cat docker-compose.yml 2>/dev/null | head -30
cat Dockerfile 2>/dev/null
```

### Phase 2: Spawn Parallel Subagents
Spawn 3-4 subagents using `delegate_task` with the `tasks` array for parallelism.
Each task MUST specify:
- `goal`: what to audit (from the track checklists above)
- `context`: project root path, key files to check, stack info
- `toolsets`: ["terminal", "file"] for each

```javascript
tasks: [
  {
    goal: "Run Track 1: Security & Infrastructure audit",
    context: "Project at /path/to/project. Stack: Python Flask + PostgreSQL + Redis.",
    toolsets: ["terminal", "file"]
  },
  {
    goal: "Run Track 5: Python Backend Audit",
    context: "Project at /path/to/project. Entrypoint: backend/app/main.py.",
    toolsets: ["terminal", "file"]
  },
  // ... up to 4 parallel tasks (delegation.max_concurrent_children default is 3)
]
```

### Phase 3: Automated Remediation (if user asks for fixes)
After the audit completes and findings are compiled, apply fixes directly
rather than just reporting. This phase is the key differentiator from
read-only audits.

Work through findings in priority order:
1. **CRITICAL first**: secrets removal, shell injection fixes, hardcoded paths, missing auth
2. **HIGH second**: CORS hardening, debug mode off, error message sanitization, rate limiting
3. **MEDIUM third**: logging improvements, thread safety, configurable constants, docker hardening

For each fix:
1. Read the source file
2. Apply the fix with `patch` or `write_file`
3. Re-run imports to verify nothing broke
4. Move to the next finding

Common fix patterns for Python backends (see `references/python-backend-fix-patterns.md`):

| Finding | Fix pattern |
|---------|-------------|
| Hardcoded API key | Replace with os.environ.get("KEY", "") with no fallback |
| shell=True | Convert to argument list with shell=False |
| Bare except: | Change to except Exception: or specific exception type |
| Error leak to client | Change str(e) to generic message + logger.exception() |
| Hardcoded user path | Replace with env var defaulting to os.path.expanduser("~/.dir") |
| Deferred import | Move to module level |
| CORS all origins | Add origins= parameter with env-var config |
| Debug default true | Change default to false |
| No auth on endpoints | Apply @token_required decorator or reject unauthorized |
| Unpinned Docker image | Pin to specific version (e.g. redis:7.4-alpine) |
| Missing healthcheck | Add to docker-compose.yml |

Re-verify all fixes with a final import test across every module.

### Phase 4: Compile Unified Report (read-only mode only)
Collect all subagent summaries. Structure the report:

1. **Executive Summary**: Overall grade, key score, verdict (production ready or not)
2. **CRITICAL issues**: Blocks deployment, must fix first
3. **HIGH issues**: Fix before launch
4. **MEDIUM issues**: Fix post-launch or first sprint
5. **Previous Audit Reconciliation**: If an earlier report exists, verify each claim
6. **AIEO / AI SEO section**: LLM citation readiness
7. **Phased Fix Plan**: Ordered by dependency, estimated effort per phase
8. **Appendices**: Full finding details, source file references

Write the report to `<project>/PRODUCTION_AUDIT_REPORT.md` (or create a v2 if one exists).

## Report Format Rules

- Every CRITICAL finding must have a specific file path and line number
- Severity rubric:
  - **CRITICAL**: Site won't function or is actively exploitable
  - **HIGH**: Won't pass a professional QA review or security audit
  - **MEDIUM**: Technical debt that compounds over time
  - **LOW**: Nice-to-have polish
- Each finding gets a unique ID (C1, C2, H1, H2, M1, M2, etc.)
- Phased fix plan must be ordered: fixes earlier phases unblock later ones
- Verdict must be explicit: "PRODUCTION READY", "NOT PRODUCTION READY", or "CONDITIONAL"
- If conditional, list the exact conditions for sign-off

## Pitfalls

- **Live site != codebase**: The production URL may be an old Wix/WordPress site
  while the audit target is a new build. Always verify what's live.
- **Previous audit overconfidence**: Always verify resolved claims by checking
  actual source files, not just trusting the report.
- **Parallel exhausts context**: Subagent summaries are self-reported. Always
  verify critical claims by checking source files yourself.
- **CSP prod vs dev**: Production CSP often removes unsafe-eval/unsafe-inline but
  may break CSS-in-JS or hot reload. Always validate both modes.
- **squirrelscan binary**: The GitHub release URL uses `squirrelscan/squirrelscan`
  org, not `squirrelscan/squirrel`. Download from the
  [download page](https://squirrelscan.com/download), not a guessed URL pattern.
- **Rate limiting gaps**: Form POST endpoints are often rate-limited but webhooks,
  health checks, and analytics endpoints are not. Check ALL POST routes.
- **Duplicate JSON-LD**: Common when two developers independently implement schema
  components. Check for script type="application/ld+json" duplicates in the DOM.
- **tailwind.config.ts + globals.css @theme**: If both exist simultaneously in
  Tailwind v4 migration, theme tokens may not resolve. Delete the v3 config file.
- **import fix verification**: After fixing a file, always run a Python import test
  (python3 -c "from backend.module import ClassName") to catch indentation errors
  and import cycle regressions — patch can mangle indentation on multi-line edits.
- **log level damage**: logger.exception() inside a bare except: doesn't help
  because it also catches KeyboardInterrupt. Always fix bare except: FIRST,
  then switch logger.error to logger.exception.
- **Docker build order**: If app code is baked into a Docker image (not volume-mounted),
  changes to source files require a docker compose build to take effect. Check the
  Dockerfile: COPY . . means the code is in the image, not a bind mount.
- **Model default staleness**: Codebases hardcode model names like deepseek-chat
  that go stale when providers rename models. Always check for hardcoded DEFAULT_MODEL
  or equivalent and make them env-var-configurable with the current model as default.
- **Method call typos**: After finding a shell=True or similar fix, grep the class
  for all calls like .method_name( against the defined methods. Python has no
  compile-time check for wrong method names — a typo is invisible until runtime.
- **App code in Docker image vs volume**: Before editing source files, check if the
  Dockerfile uses COPY . . (code in image, needs rebuild) or a volumes: bind
  mount (code on host, hot-reloads). If in image, you MUST rebuild.
- **Parallel health check pattern**: When health-checking N items (proxies, endpoints,
  servers), use asyncio.gather for parallel checks. A serial loop over 100+ proxies
  with 5-second timeouts each takes 500+ seconds. Parallel reduces this to the
  single slowest check.
- **Directory shadowing**: If both root/core/ and src/core/ exist, Python loads
  root/core/ first (CWD is searched before sys.path). Always delete the root-level
  copy and fix the import chain before making other fixes.
- **Stub deletion requires explanation**: When deleting a stub/placeholder function,
  tell the user why — "this was a placeholder returning a string, I replaced it
  with a real implementation using X tool". Silent deletion of code the user may
  have intended to fill in themselves creates confusion.
- **Async FastAPI with blocking FFmpeg/yt-dlp/SMB ops**: Running yt-dlp.download(),
  ffmpeg subprocess, or SMB upload inside asyncio.create_task() blocks the event
  loop — the server stops responding. Fix: wrap each blocking stage in
  `loop.run_in_executor(None, _blocking_fn, ...)` and use
  `loop.call_soon_threadsafe()` for thread-safe progress updates from inside the
  blocking function. Each stage (download -> convert -> upload) gets its own
  executor call so stages that error cleanly fail without leaking temp files.
- **`call_soon_threadsafe` doesn't accept kwargs**: `loop.call_soon_threadsafe(fn, **kw)`
  raises `TypeError: unexpected keyword argument`. The callback and its args must
  be positional only. Fix: wrap in `loop.call_soon_threadsafe(lambda: fn(**kw))`.
  Also watch for lambda free-variable capture in exception handlers — use
  `lambda e=exc:` to snapshot the exception value at definition time instead of
  referencing it from the enclosing scope at call time.
- **Prefer smbclient CLI over Python SMB libraries**: Libraries like smbprotocol
  and pysmb have protocol-timing requirements, fragile path construction, and poor
  timeout handling. The `smbclient` CLI is widely available and simpler:
  `smbclient //SERVER/SHARE -U USER%PASS -c "cd path; put local remote"`. Use
  subprocess.run() with timeout. Only fall back to Python libs when smbclient is
  unavailable or advanced features (streaming reads, tree diff) are needed.
- **CLI fast --help via deferred imports**: Entry-point scripts that import heavy
  deps (yt-dlp, playwright, torch) at module level take 3-10s just for --help.
  Fix: keep argparse at module level only; import command implementations inside
  handler functions after args.parse_args(). Pattern:
  `if args.command == "dl": from cli_impl import cmd_dl; asyncio.run(cmd_dl(args))`.
- **SSE EventSource requires GET**: The browser EventSource API only supports GET.
  If frontend does `new EventSource('/api/download?url=...')` but backend only has
  `@app.post('/api/download')`, add `@app.get('/api/download')` that reads Query
  params and delegates to the same logic. Keep POST for API clients.
- **SQLite as zero-dependency queue**: For single-server background job queues
  that don't need Redis (BullMQ, RQ), SQLite with WAL mode + busy_timeout is a
  zero-infra alternative. Schema: `jobs` table with status enum
  (pending/running/completed/failed/cancelled). Worker: async loop polls for
  pending jobs, processes with `asyncio.Semaphore(max_concurrent)` for throughput
  limiting. WAL mode allows concurrent reads during writes.
- **Frontend-backend API path mismatch**: When auditing full-stack apps (Next.js +
  FastAPI, Django + React, etc.), the most common integration defect is frontend
  API call paths that don't match backend routes. Fix sequence: (1) grep frontend
  for all fetch/EventSource/axios call URLs, (2) grep backend for all route
  decorators, (3) cross-reference every frontend path against backend routes, (4)
  add backend aliases or proxy rewrites for mismatches. Special case: EventSource
  requires GET endpoints — if your backend POST /api/download but frontend uses
  `new EventSource('/api/download?url=...')`, add a GET wrapper.
- **Subprocess process tree termination**: When spawning managed background
  subprocesses, `proc.terminate()` only kills the shell, not the child tool.
  Fix: `Popen(cmd, start_new_session=True)` creates a process group; kill the
  group with `os.killpg(os.getpgid(proc.pid), signal.SIGTERM)`; wait with
  `proc.wait(timeout=5)`; force-kill with `SIGKILL` if still alive.
- **VAAPI ffmpeg with CPU filters (AMD GPUs)**: When using VAAPI encoding
  (h264_vaapi) with CPU-side filter chains (crop, scale, v360), omit
  `-hwaccel vaapi` entirely (CPU decode + CPU filters), then append
  `,format=nv12,hwupload` to the end of the filter chain so the VAAPI encoder
  receives GPU surfaces. Pattern:
  `ffmpeg -i in.mp4 -vf 'crop,scale,format=nv12,hwupload' -c:v h264_vaapi`.
  Never put CPU filters after hwupload — they can't operate on GPU surfaces.
  For v360: `v360=equirect:flat,scale,format=nv12,hwupload`.
  Reference: `references/vaapi-ffmpeg-gpu.md`.
- **yt-dlp custom extractor pattern for blocked sites**: When yt-dlp can't
  handle a site, build a custom extractor registered via `@register`. Pattern:
  (1) Register URL pattern + extraction function in extractors/__init__.py,
  (2) Use Puppeteer (`POST /extract-page`) to load page with JS + stealth,
  (3) Return rendered HTML, (4) Parse for JSON-LD contentUrl, get_file URLs,
  or video tag src, (5) Return `{url, title, ext, source, cookie_file, referer}`.
  Pass direct URL + cookies + Referer to yt-dlp for download.
  Reference: `references/custom-extractors-ytdlp.md`.
- **yt-dlp format fallback chain**: When a quality format fails, fall back
  through: (1) quality-filtered, (2) bestvideo+bestaudio/best, (3) best.
  Catch each error and continue; raise last error only if ALL fail.

## Related Skills

- `audit-website` — squirrelscan-based automated website scanning (230+ rules)
- `ai-seo` — AI search engine optimization / LLM citation strategy
- `website-seo` — Comprehensive on-page SEO system
- `seo-audit` — Traditional SEO audit methodology
- `qa-expert` — Testing strategies and quality assurance
- `security-review` — Codebase security scanning
