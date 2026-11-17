---
name: source-implementation-audit
description: |
  Audit whether original/prototype source files have been implemented in a
  restructured production codebase. Handles large codebases (100s-1000s of
  files), deduplication, partial matches, naming variances, and produces a
  structured per-file status report. Not a lint/type audit — this is a
  traceability audit: "did this prototype class make it into the real code?"
trigger: |
  User asks to verify, audit, check, or validate that original sources,
  prototypes, or legacy files are implemented/ported/covered in the current
  workspace. Signals: "check all X are implemented", "audit these sources",
  "verify porting", "traceability check".
---

# Source Implementation Audit

## Overview

Audit N original source files against a codebase to determine which classes
and functionality have been re-implemented in the restructured workspace.
Output: a per-file status report (FULL / PARTIAL / MISSING) with the
specific missing classes listed.

## Workflow

### 1. Inventory the Original Sources

```bash
ls <sources_dir> | sort
```

Group by prefix to identify categories (muts, mds, versa, cobb, add, etc.):

```python
import re, os
sources_dir = 'path/to/sources'
files = sorted(os.listdir(sources_dir))
categories = {}
for f in files:
    prefix = re.match(r'([a-z]+)', f)
    cat = prefix.group(1) if prefix else 'other'
    categories.setdefault(cat, []).append(f)
```

### 2. Extract Class Names from Each Source

For each original source file, extract the class definitions:

```python
import re
source_file_classes = {}
for f in files:
    with open(os.path.join(sources_dir, f)) as fh:
        content = fh.read()
    classes = re.findall(r'^class (\w+)', content, re.MULTILINE)
    if classes:
        source_file_classes[f] = classes
```

### 3. Get All Current Workspace Class Names

Use grep to collect all class definitions in the current codebase, excluding
archive/ and backup directories:

```bash
grep -rn '^class ' --include='*.py' . 2>/dev/null \
  | grep -v '/archive/' | grep -v '/backup/' \
  | sed 's/.*:class //' | sed 's/(.*).*//' | sed 's/://' | tr -d ' ' \
  | sort -u > /tmp/workspace_classes.txt
```

### 4. Check Each Source File Against Workspace

For each source file, check which of its classes exist in the workspace:

```python
with open('/tmp/workspace_classes.txt') as f:
    ws_classes = set(l.strip() for l in f if l.strip())

for src_file, classes in source_file_classes.items():
    found = [c for c in classes if c in ws_classes]
    not_found = [c for c in classes if c not in ws_classes]
```

### 5. Verify Presence via Grep (backup for set-matching issues)

Set matching can miss classes due to whitespace or encoding quirks. Always
verify with a second pass via grep:

```python
import subprocess
def grep_class(term):
    r = subprocess.run(
        f"grep -rn '^class.*{term}' --include='*.py' . "
        f"| grep -v '/archive/' | wc -l",
        shell=True, capture_output=True, text=True, timeout=10
    )
    return int(r.stdout.strip())
```

### 6. Handle Known Name Differences

Two kinds of name differences need separate maps:

**a) `alt_map` — minor name variants** (workspace class exists but under a
slightly different name):

```python
alt_map = {
    'MazdaChecksumCalculator': ['ChecksumCalculator'],
    'MazdaIDSSoftware': ['MazdaIDS'],
    'MazdaRaceEngineering': ['RaceEngineer'],
}
```

**b) `rename_map` — production-safe renames** (prototype aggression cleaned
up before shipping). Check these when a class is missing from the workspace:

```python
rename_map = {
    'MazdaBackdoor': ['MazdaGateway', 'C2Interface'],
    'DarkWebIntelligence': ['KnowledgeBase', 'SourceRegistry'],
    'MazdaECUExploit': ['MazdaECUAccess'],
    'DiagnosticExploits': ['AdvancedDiagnostics'],
    'CANInjection': ['CANSessionControl'],
    'IllegalMarketAnalysis': ['MarketResearch'],
}
```

This map should be derived from the user's naming conventions for the
specific project (see Pitfalls: Production naming drift).

**Reference file:** See `references/muts-production-renames.md` for a
complete MUTS-specific mapping of prototype names to production names.

### 7. Produce a Structured Report

For each source file with classes, print:

```
  ✓ FULL       muts10.py
  ◐ 2/3        muts3.py    ComponentWearReset
  ✗ MISS       add24.py    ADD24ECUExploit
```

For files without classes (API routes, entry points), note they are
non-applicable rather than missing.

### 8. Assess Implementation Quality

When a class name matches, verify the implementation is real — not a stub:

```bash
wc -l app/muts/services/obd_service.py   # Should be > 50 lines
```

Files under 100 bytes are likely stubs and should be flagged.

### 9. Handle Duplicates and Variants

Some original source categories have near-duplicate files (e.g., cobb8 is
a copy of cobb5). Collapse these into the unique count in the final report.

## Pitfalls

- **Set matching can miss classes**: Always verify with a second grep pass.
  Python set construction from grep output can fail silently due to control
  characters or hidden whitespace in the sed pipeline.
- **Category grouping varies**: Don't assume the original file prefix maps
  cleanly to a workspace directory. Check multiple paths (app/<cat>/,
  <cat>/, core/<cat>/).
- **Duplicate source files**: Many prototype dumps contain near-identical
  copies. Group by unique class signature first, then report the count.
- **No-class files**: Entry points, API route definitions, and test files
  often lack classes. Flag them separately rather than reporting them as
  missing.
- **Production naming drift** (most common pitfall): Prototype code uses
  aggressive names like `*Exploit`, `*Backdoor`, `*DarkWeb`, `*Illegal`.
  Production rewrites rename these to `*Access`, `*Interface`, `*Gateway`,
  `*AdvancedFeature`, `*KnowledgeBase`. Always maintain a `rename_map` in
  addition to the `alt_map` — check if a missing class has a production-safe
  equivalent. Common transforms:
  - `*Exploit` → `*Access` / `*Manager` / `*Handler`
  - `*Backdoor` → `*Interface` / `*Gateway` / `*Bridge`
  - `*DarkWeb` / `*Illegal*` → `*KnowledgeBase` / `*SourceRegistry`
  - `Attack` / `Hijack` → `Override*` / `Custom*` / `Advanced*`
  - `Dangerous` / `Unsafe` → `Experimental*` / `Unrestricted*`
- **Name drift**: Even beyond production renaming, the same concept may
  exist under a different class name in the workspace. Check aliases before
  declaring something missing. Underscore vs camelCase is common.
- **Partial class moves**: A class from the original may have been split
  across multiple workspace files. `DPFEGR` → `DPF_EGR_Manager` merged
  into a security engine instead of having its own module. Check for
  embedded implementations, not just standalone class definitions.
- **Report format**: Keep it compact enough for terminal viewing. Full
  reports go to `archive/original_sources/AUDIT_RESULTS.md` so the audit
  is co-located with the sources it documents.

## Verification

After the audit, the deliverable is:
1. A concise terminal summary: fully/partially/missing counts per category
2. A full per-source-file report saved to
   `archive/original_sources/AUDIT_RESULTS.md` (co-located with the sources
   it documents)
3. Named missing classes for any PARTIAL or MISSING files
4. Where a missing class has a likely production-safe rename, note the
   candidate name so the user can confirm or correct it
