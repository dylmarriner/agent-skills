# Source-to-Implementation Gap Audit

Given a set of reference source files (original prototypes, legacy code, vendor SDKs)
and a current codebase, determine which classes/functions have been ported,
which are partially done, and which are entirely missing.

## When to Use

- User says "audit these original sources against the workspace"
- Migrating from monolithic prototype files to a structured modular architecture
- Comparing reference SDK/API implementations against your port
- Verifying all capabilities from specification source files are accounted for

## Methodology

### Step 1: Inventory the Sources

```bash
ls archive/original_sources/
# Count them
find archive/original_sources -name '*.py' | wc -l
```

Categorize sources by prefix/author to understand groupings (e.g. `muts1-16`,
`mds1-15`, `versa1-19`, `cobb1-12`, `add1-24`, `mpsrom1-4`, tune profiles).

### Step 2: Extract Classes from Each Source

For each source file, extract all top-level class definitions:

```bash
grep '^class ' archive/original_sources/muts1.py
```

Build a dict per source file mapping source → [class1, class2, ...].
Note duplicates across files (some sources are copies: `muts6 == muts15`,
`cobb7 == cobb10`, `mpsrom2 == mpsrom3 == mpsrom4`).

### Step 3: Get Current Workspace Class Inventory

```bash
# All class names in the current codebase (excluding archives)
grep -rn '^class ' --include='*.py' . 2>/dev/null \
  | grep -v '/archive/' \
  | grep -v '/backend-archive-' \
  | sed 's/.*:class //' | sed 's/(.*).*//' | tr -d ' ' | sort -u
```

### Step 4: Match Each Source Class Against the Workspace

For each class in each source file:
- **Exact match**: check if it exists in workspace class list
- **Partial/renamed match**: grep for the concept (e.g. `DPF_EGR_Manager` for `DPFEGR`)
- **Functional equivalent**: does another class serve the same purpose under a different name?

Categorize each source file:
- **FULLY IMPLEMENTED**: all classes found
- **PARTIAL**: some classes found, some missing
- **MISSING**: no classes found
- **NO CLASSES**: file is API routes, config, entry points, tests — check separately

### Step 5: Method-Level Verification (deep audit)

For files marked FULLY IMPLEMENTED, do a quick method-count sanity check:

```bash
# Methods in original source
grep '    def ' archive/original_sources/muts1.py | wc -l
# Methods in workspace equivalent
grep '    def ' app/muts/security/security_engine.py | wc -l
```

If the workspace version has significantly fewer methods, it's not truly implemented.

### Step 6: Identify No-Class Files

Files without classes may contain:
- **API routes** (Flask/FastAPI endpoints) — diff against existing router
- **Reference data** (constants, specs, config dicts) — check if data is replicated
- **CLI entry points** (argparse main functions) — check for equivalent
- **Test classes** — check if corresponding test files exist
- **Package init** (imports, `__version__`) — trivial

Check each category:
```bash
# For route files — does the workspace have equivalent endpoints?
grep -n 'route\|@app\.\|@router\.' app/api/main.py | head -20

# For data files — are the constants replicated somewhere?
grep 'ENGINE_SPECS\|SAFETY_LIMITS' app/muts/data/ -r | head -5
```

### Step 7: Write Audit Report

Write results to `AUDIT_RESULTS.md` with:

```
# Category MUTS (16 files)
| File   | Status | Missing |
|--------|--------|---------|
| muts1  | ◐ 3/4  | DPFEGR  |
| muts2  | ✓ FULL |         |

# Overall
- ✓ FULL: 55 files
- ◐ PARTIAL: 12 files
- ✗ MISSING: 5 files
- No classes: 7 files
- Duplicates: 13 files
- Total: 92/92
```

## Pitfalls

- **Class name != implementation**: A class may exist by the same name but be a stub.
  Always check file size and method count.
- **Renamed across versions**: Legacy code often renames classes during refactoring.
  Grep for conceptual keywords, not just exact class names.
- **Collapsed duplicates**: Multiple original sources (e.g. `muts6 == muts15`) may
  count as "missing" when they're just copies of the same thing. Deduplicate first.
- **No-class files**: API routes (Flask blueprints), entry points, and pure config
  files have zero classes. These need separate verification against the workspace.
- **Test files**: Some original sources are pure test files. Don't flag them as
  "missing production code" — they're meant to test what's already built.
- **False negative from grep truncation**: Large grep results truncate with
  `+more. Use `wc -l` for accurate counts on large result sets.
