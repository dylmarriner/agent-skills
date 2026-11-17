---
name: ai-prototype-to-production
description: "Transform AI-generated prototype/skeleton code into a production-grade application: assess, classify, deduplicate, organize, audit for placeholders, then rebuild."
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [prototype, production, refactoring, code-quality, project-setup]
    related_skills: [code-reviewer, refactoring-specialist, audit, skill-creator]
---

# AI Prototype → Production

Transform a directory of AI-generated prototype/skeleton code into a working, production-grade application. This covers the full pipeline: assessing what you have, organizing into a proper structure, auditing for placeholder/simulated code, and rebuilding with real logic.

## When to Use This Skill

Trigger when the user:
- Has a directory full of AI-generated prototype code (often named `deepseek_*`, `claude_*`, or `chatgpt_*`)
- Wants to "set up" or "make work" a pile of generated files
- Has skeleton/prototype code that doesn't actually run
- Asks you to "make it production grade" or "set it up properly"
- Has loose files with no project structure, no package manager, no working entry point

## Workflow

### Phase 1: Assessment

Before touching anything, understand what you're working with:

```python
import os, re
from collections import defaultdict

d = "<project-directory>"

# 1. File inventory by type
extensions = defaultdict(list)
for f in os.listdir(d):
    ext = f.rsplit('.', 1)[-1] if '.' in f else 'none'
    extensions[ext].append(f)

print(f"Python: {len(extensions.get('py', []))}")
print(f"Vue/JS: {len(extensions.get('vue', [])) + len(extensions.get('js', []))}")
print(f"Config: {len(extensions.get('json', [])) + len(extensions.get('yaml', []))}")
print(f"Scripts: {len(extensions.get('sh', []))}")
print(f"Other: {sum(len(v) for k,v in extensions.items() if k not in ['py','vue','js','json','yaml','sh'])}")

# 2. Identify classes and imports
for f in sorted(f for f in os.listdir(d) if f.endswith('.py')):
    with open(os.path.join(d, f)) as fh:
        content = fh.read()
    classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)
    imports = re.findall(r'^(?:from|import)\s+([\w.]+)', content, re.MULTILINE)
    size = len(content)
    print(f"{f:<50s} {size:>6}b  classes={classes[:3]}")

# 3. Check for git
import subprocess
r = subprocess.run(["git", "log", "--oneline", "-1"], cwd=d, capture_output=True, text=True)
print(f"Git repo: {'YES' if r.returncode == 0 else 'NO'}")
```

### Phase 2: Classification

Group files into functional categories. Common categories for prototype code:

| Category | Description | Examples |
|----------|-------------|---------|
| `backend/api/` | Web framework endpoints (Flask, FastAPI, Express) | Route handlers, middleware |
| `backend/exploits/` | Attack/exploit modules | SS7, carrier, implant, zero-click |
| `backend/services/` | Business logic layer | CRUD, orchestration, analytics |
| `backend/models/` | Data models / ORM | SQLAlchemy, Django models |
| `backend/utils/` | Utility functions | Evasion, persistence, comms |
| `frontend/` | UI components | Vue, React, HTML/JS |
| `database/` | Schema and migrations | SQL files, Alembic |
| `config/` | Configuration files | YAML, JSON, Docker, Prometheus |
| `scripts/` | Deployment/tooling scripts | Bash, Python CLI wrappers |
| `tests/` | Test files | pytest, unittest |

### Phase 3: Deduplication

Prototype generators often create duplicate files with `(1)` suffixed names:

```bash
find <project-dir> -name "*(1)*" -delete
```

Compare sizes between duplicates before deleting. If multiple duplicates have different sizes, keep the largest (most recent generation).

### Phase 4: Organization

Create the directory structure and move files with meaningful names:

```bash
mkdir -p backend/{api,exploits,services,models,utils}
mkdir -p frontend/src
mkdir -p database
mkdir -p config
mkdir -p scripts
mkdir -p tests

# Move and rename
cp old_file.py backend/api/new_name.py
```

**Naming convention:** Use descriptive names based on the class/module's purpose, not the original generated filename. `deepseek_python_20260519_b6742d.py` → `backend/orchestrator/exploit_orchestrator.py`

### Phase 5: Placeholder Audit

Scan every Python file for these common placeholder patterns:

| Pattern | Severity | What It Means |
|---------|----------|---------------|
| `time.sleep(N)` | **HIGH** | Simulated processing — code pretends to do work by sleeping |
| `return {"status": "compromised/success"}` | **HIGH** | Static mock return — no actual computation or side-effect |
| `raise NotImplementedError` | **HIGH** | Stub — function exists but does nothing |
| `def func(): pass` | **MEDIUM** | Empty body — never implemented |
| Hardcoded RFC1918 IPs (10.x.x.x, 192.168.x.x) | **LOW** | Placeholder network data, not real infrastructure |
| `# TODO`, `# FIXME`, `# HACK` | **MEDIUM** | Unfinished sections |
| Comments containing "simulate", "demo mode", "for demonstration" | **MEDIUM** | Explicit simulation markers |

**Automated audit script:**

```python
import os, re

d = "<project-dir>"
findings = []
for root, dirs, files in os.walk(d):
    for f in files:
        if not f.endswith('.py') or '.venv' in root:
            continue
        fpath = os.path.join(root, f)
        with open(fpath) as fh:
            content = fh.read()
        
        # Count sleep calls
        sleeps = re.findall(r'time\.sleep\(', content)
        if len(sleeps) >= 2:
            findings.append((fpath, f"HIGH: {len(sleeps)}x time.sleep() calls"))
        
        # Check for static returns
        if re.search(r"return\s*\{[^}]*'status'[^}]*\}", content):
            findings.append((fpath, "HIGH: Static mock return data"))
        
        # Check for stubs
        if 'NotImplementedError' in content:
            findings.append((fpath, "HIGH: NotImplementedError stub"))
        
        # Check for simulation comments
        if any(w in content.lower() for w in ['placeholder', 'simulate', 'demo mode']):
            findings.append((fpath, "MEDIUM: Simulation/placeholder comments"))

for path, issue in sorted(findings):
    print(f"{os.path.relpath(path, d):<50s} {issue}")
```

### Phase 6: Rebuild (Production-Grade)

Replace placeholder code with real implementations. For each identified placeholder module:

1. **Define the data model** — SQLAlchemy/Pydantic models with proper types
2. **Build the service layer** — Async/await business logic on top of database
3. **Create the API** — FastAPI endpoints with proper error handling, status codes, auth
4. **Wire up dependencies** — pyproject.toml with pinned versions, dev extras
5. **Add infrastructure** — Dockerfile, docker-compose, CI/CD, logging, monitoring

**Preferred technology stack:**
- **Framework:** FastAPI (async, auto-docs, Pydantic validation)
- **ORM:** SQLAlchemy 2.0 async (mapped_column style, not legacy Column)
- **Database:** SQLite for dev, PostgreSQL for prod
- **Auth:** JWT (python-jose) with OAuth2 bearer
- **Logging:** structlog (JSON in prod, pretty console in dev)
- **Packaging:** pyproject.toml with hatchling, ruff for linting
- **Migrations:** Alembic
- **Frontend:** Keep existing Vue/React components, wire to new API

### Phase 7: Production Hardening Audit (Hostile Review)

Run a multi-track hostile audit using parallel subagents when the goal is "production ready" or "$50K quality." This catches issues that a single pass always misses — architectural, security, frontend, and infrastructure blind spots are different specialties.

**Parallel audit structure** (run via `delegate_task` batch mode):

| Subagent | Scope | Sample Checks |
|----------|-------|--------------|
| **Backend/Lib** | All library code, config, middleware, env, pricing, email, RBAC | Rate limit scalability, error propagation, mock functions in prod, env validation bypass, empty secret fallbacks, RBAC role hierarchy gaps |
| **Frontend/UI/UX** | All page files, components, forms, a11y, SEO, Tailwind theme | Missing generateMetadata, wrong design system on some pages, dead components, duplicate implementations, keyboard a11y holes, color contrast failures |
| **Collections/API/Tests/CI** | CMS collections, globals, API routes, migrations, tests, docs, CI/CD | Unauthenticated endpoints, collection privacy leaks, non-existent module imports, broken CI workflows, test data mismatch with schemas, missing migration infrastructure |

**Instructions to each subagent:** Tell them to be "hostile" — show NO mercy, mock bad patterns, be specific with file paths and line numbers. Role boundaries are hard (no mixing sources).

**Severity classification** for all findings:

| Tier | Label | Response |
|------|-------|----------|
| CRITICAL | Production Collapse | Fix immediately — blocks shipping |
| HIGH | Security/Revenue Risk | Fix before deploy |
| MEDIUM | Quality/Legibility | Fix in current sprint |
| LOW | Polish | Track for later |

After collecting all findings, **cross-reference with the live production site** to catch data accuracy issues: phone numbers, email, address, service names, pricing, copyright, social links. Navigate to the live site and verify every business detail matches.

**During the fix phase, ALSO load and apply UI/UX design skills.** The user expects visual polish as part of a production audit, not just code correctness. Load skills like `frontend-design`, `ui-ux-pro-max`, `premium-frontend-ui`, or `ckm:*` and apply their guidance to improve spacing, typography, color application, and component styling across the frontend. A site that passes every security check but looks bare is not production-grade.

### Phase 8: Batch Remediation

Fix the identified issues in parallel batches organized by severity. This pattern finishes in hours what would take days serially.

**Batch strategy (use `delegate_task` for each):**

| Batch | Focus | Items |
|-------|-------|-------|
| Batch 1 | Production collapses + security | 8-10 most critical items (CSP, auth bypass, empty secret fallbacks, broken CI, mock pricing) |
| Batch 2 | API/Security hardening | 8-10 items (analytics persistence, email confirmation, auth on unprotected endpoints, collection access controls) |
| Batch 3 | Frontend/UX/SEO | 8-10 items (missing metadata, wrong design system, dead components, sitemap gaps, 404 pages) |
| Batch 4 | Code quality polish | 8-10 items (RBAC hierarchy, collection constraints, test/docs/seed fixes, env docs) |

Each batch subagent gets:
- The exact list of issues to fix (file paths, line numbers from the audit)
- Clear instructions: "Read each file first. Build after."
- Independence: batch items should not conflict (if they do, split into separate batches)

After each batch, mark items as done. Run `npx next build` (or equivalent) after ALL batches complete to verify nothing broke.

**Final verification:** Re-audit the fixed items by loading the dev server and running through the full user journey: homepage → service pages → forms → quote builder → 404 page → robots.txt → sitemap.xml. Check browser console for zero JS errors. **Verify CSS is actually rendering** by checking the browser computed style on `document.body` — font should resolve to the configured brand font (e.g. Inter), not Times New Roman or system default. A stale dev server can serve unstyled pages even after a successful build; always kill and restart the dev server after major CSS/config changes.

## Common Pitfalls

1. **Don't try to preserve the original files.** Once you've copied them into the structure with meaningful names, delete the originals. The old names are garbage.

2. **Prototype code often has syntax errors.** AI generators sometimes emit invalid Python (missing parens, broken indentation). Check `python3 -c "import ast; ast.parse(open('file.py').read())"` after moving.

3. **Imports will be broken.** The original code references modules by paths that don't exist (`from backend.exploits.nz_carriers import X`). Don't try to fix these in the old code — you're replacing it.

4. **Check for duplicate content across files.** Generators sometimes emit the same class in multiple files. Compare class lists before moving.

5. **The launcher script is always fake.** The CLI wrapper that prints "Step 1/5: Reconnaissance..." and sleeps is pure theater. Rebuild it as a real CLI or ignore it entirely.

6. **Use subagents for large rebuilds.** If the prototype has 40+ files, delegate the API layer, service layer, and Docker infrastructure to parallel subagents while you handle classification and audit.

7. **Document what was placeholder vs production in a README.** Future sessions need to know what's real and what's fake in the final project.

8. **Test imports after every phase.** After moving files, run `import ast; ast.parse(...)` on each .py file. Broken syntax is easier to fix immediately than after 20 more moves.
