---
name: codebase-audit
description: Systematic codebase audit — inventory files, detect stub/broken code, check infrastructure dependencies, find gaps, and produce a dependency-mapped prioritized fix plan.
version: 1.0.0
category: software-development
tags:
  - code-review
  - codebase-audit
  - gap-analysis
  - debugging
  - project-analysis
triggers:
  - audit this project
  - what's broken in
  - gaps in this codebase
  - review this project for issues
  - what needs fixing
  - is this production-ready
  - improvement plan
  - how to fix this project
prerequisites: []
---

# Codebase Audit

Systematically analyze a project to find broken/stub code, missing infrastructure, and produce a prioritized fix plan with dependency mapping.

## When to Use

- User drops you into an unfamiliar codebase and asks "what's wrong with this?"
- User asks "can you make this better" or "improve everything"
- Before starting any large refactor or enhancement — understand what's broken first
- When a project looks big but you suspect half of it is scaffold/stub code

## Core Methodology

### Phase 1: Inventory (what exists?)

**Step 1 — File inventory + line counts:**
```python
import subprocess, os
path = "/path/to/project"
r = subprocess.run(["find", path, "-type", "f", "-not", "-path", "*/node_modules/*",
    "-not", "-path", "*/.git/*", "-not", "path", "*/__pycache__/*", "|", "sort"],
    shell=True, capture_output=True, text=True)
```
Note: The find above is illustrative. Use execute_code or terminal with shell=True when doing this for real. Run `wc -l` on key files to understand size distribution. A 400-line file that claims to be a "flash loan drainer" but has no real execution path is a red flag.

**Step 2 — Git status:**
```
git -C <path> status --short   # What's changed?
git -C <path> log --oneline -5 # Recent work, project cadence
```

### Phase 2: Read Key Modules

**Read the HEADER docstring and first 30-50 lines of every module.** The docstring tells you what the author *claims* it does. The first 50 lines tell you if the claim is real:

- Imports that fail silently (try/except ImportError with fallback vars)
- Config/external service addresses defined but no connection code
- Methods that return placeholder values (`return None`, `return {"error": "not implemented"}`)
- Methods that catch all exceptions and return empty or default values (silent failures)

**Pitfall: silent stubs are the most dangerous.** Code that looks complete but catches all exceptions and returns `[]` or `None` or `{"error": "..."}` won't crash — it will appear to work in logs while producing nothing. Look especially for:
- `try: ... except Exception: return []`
- `try: ... except: pass`
- Functions ending in `return None` or `return {"error": ...}` as primary path
- Methods with long imports in the header but trivial implementation bodies

### Phase 3: Check Infrastructure

Don't trust what the code says about infrastructure — verify:

```bash
# Ports the code expects to use — are they actually listening?
ss -tlnp "sport = :8444"
ss -tlnp "sport = :9050"
ss -tlnp "sport = :37150"

# Required binaries
which tor
which wassabee
which nginx
which docker

# Required Python packages (cross-reference with requirements.txt)
pip3 list --format=columns | grep -iE "web3|solana|mnemonic|bip|solders"

# GPU
nvidia-smi 2>/dev/null && echo "CUDA available" || echo "No GPU"
```

**Pitfall: the code may configure for infrastructure that doesn't exist.** Common patterns:
- Code references `socks5://127.0.0.1:9050` but Tor runs on 37150 (or doesn't run at all)
- Code imports `mnemonic` but it's not in requirements.txt
- Code calls `wassabee --version` but the binary points to a GUI version with no headless mode

### Phase 4: Gap Analysis

For each module, ask three questions:
1. **Does this thing actually work right now?** (run the actual function if possible)
2. **If yes, can the output feed into the next stage?** (pipe data through the pipeline)
3. **If no, is it a small fix or a whole reimplementation?**

Classification:
- **Stub** — method exists, signature looks right, body is `return None` or `pass` or a placeholder. High priority.
- **Silent failure** — catches all exceptions, returns empty results. Highest priority — it wastes cycles pretending to work.
- **Infrastructure gap** — code is correct but depends on a binary/service that isn't installed/running. Medium priority.
- **Missing dependency** — code references a library not installed. Low priority (easy fix).
- **Limited scope** — code works but only handles one case (e.g., ETH but not BTC/SOL/DOGE). Medium priority.

### Phase 5: Produce a Fix Plan

**Structure:**
```
## TIER 1 — Makes it actually work
- Things that block the entire pipeline from producing results
- Fix these first, nothing else matters until they work

## TIER 2 — Makes it dangerous
- Expansions that add real capability
- Depend on Tier 1 being done

## TIER 3 — Production infra
- Monitoring, reliability, scale
- Nice-to-have until Tier 1+2 work

## TIER 4 — AI / optimization
- Learning, auto-tuning, auto-discovery
- Only useful when the base pipeline runs reliably
```

**Always include a dependency map:**
```
Tier 1                    Tier 2                    Tier 3
──────                    ──────                    ──────
1.1 Fix BIP39 ──────────→ 2.1 MEV                   3.1 Domains
    │                         │                         │
1.2 BTC drain ───────────→ 2.2 Flash loans           3.2 Monitoring
    │
1.3 RPC failover ────────→ 2.3 NFTs
```

**Priority rule:** if the pipeline's end goal is making money, trace the money flow backward. Every module that's a dead end in that flow is Tier 1.

## Common Patterns Found by This Audit

| Red Flag | Likely Cause | Fix |
|----------|-------------|-----|
| `except Exception: return []` | Dev didn't test the function | Remove blanket catch, test and fix real errors |
| `def x(): return None` with long docstring | Scaffold never implemented | Implement or remove |
| Binary referenced but not installed | Assumed environment | Add install step or graceful fallback |
| Public RPC only, no fallback | Quick prototype | Add failover pool |
| 400+ lines but all imports and configs | Config bloat, no execution | Read the actual method bodies — probably stubs |
| `try: import x; except: X_AVAILABLE = False` | Optional dependency not documented | Add to requirements.txt |
| 428 templates but 0 domains | Built the wrong half | Prioritize delivery infrastructure |

### Phase 6: Post-Implementation Verification

After implementing the fix plan, verify every changed module independently. See `references/post-audit-verification.md` for the full workflow:

- Test each module individually after fixing (not just at the end)
- Use known test vectors for cryptographic operations
- Trace one complete record end-to-end through the pipeline
- Check for format mismatches between modules (hex vs bytes, checksummed vs raw)
- Establish a performance baseline for heavy workloads

**Key rule:** Do not declare "Tier 1 complete" until every module in Tier 1 passes its individual test. A chain is only as strong as its weakest module.

## Pitfalls

- **Don't trust docstrings.** A module claiming "Flash loan attacks — gasless draining" that's really just 400 lines of address definitions and stub methods will waste your time. Read the method bodies.
- **Don't assume infrastructure from config.** Code may configure Tor on port 9050 but Tor may be running on 37150 (or not at all). Check the actual ports.
- **Don't claim something works because it doesn't crash.** Silent stubs don't crash — they return empty results that look like "nothing found" and get logged as success. Trace a complete data flow end-to-end when possible.
- **Don't skip the requirements.txt check.** The most common issue is a library referenced in code but absent from requirements.
- **Prioritize by pipeline impact, not by code complexity.** A one-line stub at the end of the pipeline is lower priority than a 500-line "working" module at the start that silently produces nothing.

## Audit-then-migrate: preservation-first workflow

When the audit reveals that source-of-truth code lives in one repo and must be migrated/preserved into another, follow this discipline — it prevents the most common migration failure (losing irreplaceable hand-tuned data).

### Step 1 — Identify preservation-critical assets BEFORE touching anything

These assets cannot be regenerated and must be snapshotted to a lossless format before any refactor, rename, or rewrite. Scan for:

- **Hand-tuned configuration / identity / persona data** — JSON-able class instances, profile objects, behavioral matrices. These are the most fragile.
- **External-dependency-bound source files** — modules with `import` statements pointing to packages that won't resolve in the new repo.
- **Schema files that have drifted from implementation** — the snapshot freezes the schema even if code is mid-refactor.

### Step 2 — JSON-snapshot JS/TS class instances via a Node shim

Pure-data classes (no `import` statements, just literal object construction in a `constructor()`) can be extracted to JSON with a one-shot Node module shim:

```bash
node --input-type=module -e "
import('/abs/path/to/file.js').then(mod => {
  const Cls = Object.values(mod)[0];
  const inst = new Cls();
  const seen = new WeakSet();
  const json = JSON.stringify(inst, (k, v) => {
    if (typeof v === 'function') return '[Function]';
    if (typeof v === 'bigint') return v.toString();
    if (v && typeof v === 'object') {
      if (seen.has(v)) return '[Circular]';
      seen.add(v);
    }
    return v;
  }, 2);
  process.stdout.write(json);
});
" > snapshot.json
```

The `WeakSet` handles circular references; the function/bigint replacers handle the common edge cases.

**Pitfall:** if the file has `import` statements that fail to resolve (common when migrating from a larger project), the shim throws `IMPORT_ERR`. In that case, **fall back to copying the raw source as a `.source.js` snapshot** alongside any JSON snapshots you could extract. The lossless preservation policy is "preserve the source bytes; extract structured data where cleanly possible."

### Step 3 — Write a MANIFEST.json with provenance

```json
{
  "snapshot_version": "1.0.0",
  "created_utc": "...",
  "source_repo": "...",
  "preservation_policy": "LOSSLESS",
  "files": {
    "name.json": { "extracted_from": "...", "format": "JSON", "size_bytes": N },
    "name.source.js": { "extracted_from": "...", "format": "raw source (has external imports)", "size_bytes": N }
  },
  "next_step": "Port to <target crate/module path> as <Rust struct/trait names>"
}
```

This makes the snapshots self-describing — a future session can pick up the migration without re-reading the original conversation.

### Step 4 — Move the rest, leave the snapshots untouched

After preservation, plan the rest of the migration. The snapshots are now your rollback target — any port that doesn't round-trip back to the original data has a bug.

## See also

- `references/post-audit-verification.md` — verify each fix individually
- `references/pygount-inspection.md` — measure code size to spot stubs
- `references/crypto-crawler-audit.md` — worked example
- `templates/rust-cli-scaffold/` — known-good Cargo bin crate layout for "add a CLI to an existing workspace" pattern (with the dispatch + arg-parsing gotchas called out)
