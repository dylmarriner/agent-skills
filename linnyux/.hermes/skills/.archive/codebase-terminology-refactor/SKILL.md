---
name: codebase-terminology-refactor
category: software-development
tags: [rename, refactor, bulk, terminology, grep, find-replace, codebase-wide]
description: |
  Bulk rename/reword of terminology across a codebase — find all occurrences
  of a term (e.g. 'bypass', 'exploit') and replace with civilized alternatives
  across files, class names, function names, variables, dict keys, and
  docstrings. Also covers renaming source files with problematic names.
---

# Codebase Terminology Refactor

Bulk rename/reword of problematic terminology across a project. Handles
file renames, class renames, method/function/variable renames, import
fixes, docstring rewording, and cross-reference updates.

## When to Use

The user says any of:
- "change any naming and wording that mentions X to something more civilized"
- "rename X to Y across the project"
- "replace all references to X with Y"
- "clean up the naming in this project"

## Workflow

### Phase 1 — Discover the Scope

Grep broadly first. Do NOT limit by file extension or directory on the
first pass:

```bash
grep -rn -i "bypass\|exploit" . | grep -v "archive/" | grep -v ".venv/" | grep -v "node_modules/"
```

**Adjust file extension filters to match the project's language mix:**
- Python-only project: `--include="*.py"`
- TypeScript/TSX + docs: `--include="*.ts" --include="*.tsx" --include="*.md" --include="*.txt"`
- Mixed-codebase: omit `--include` entirely, then filter by directory
- Non-Python cleanup pass: `--exclude="*.py"` to target only docs/TS/markdown

**Critical: search ALL directories** the project uses, including deeply
nested ones, `app/`, `src/`, `lib/`, `tools/`, `tests/` — every directory
that contains live code. The most common mistake is searching only the
obvious top-level `src/` and missing `app/` or `muts_tuner/`.

**Categorize** each hit:
- **Live source** — actively used, needs changing
- **Archive** (old/backup copies) — leave alone
- **Vendor/venv** — not project code, skip

Exclude archive paths explicitly in your grep (`grep -v archive/`). Don't
just "feel" they're excluded — be explicit.

### Phase 2 — Plan the Changes

Group the work into:

1. **File renames** — files whose names contain the problematic term
   - Use `git mv` (tracks history) or `mv` (if no git)
   - Update all imports across the project
   - Update the class/function name inside the file too

2. **Class renames** — class names containing the term
   - Rename in class definition + all usages

3. **Method/function/variable renames** — methods, functions, variables
   - Rename definition + all references
   - Update `__all__` exports
   - Update imports in other files

4. **Dict keys / config values** — string keys in dicts
   - Update all consumers that reference the key

5. **Docstrings / comments / log messages** — wording in prose
   - "Bypass" → "Access", "Override", "Patch", "Skip", "Perform"
   - "Exploit" → "Access", "Module", "Probe", "Mechanism"

### Phase 3 — Make Changes (Top-Down)

Do the renames in dependency order:

1. **Enums and models first** (other things depend on these)
2. **Base/abstract classes** (children inherit/import from them)
3. **Concrete implementations** (import from bases)
4. **Consumer files** (import from implementations)
5. **File renames last** (so imports are already correct for the new names)

For each change:
- Read the file first
- Apply the change (use the `patch` tool with `replace_all=true` for
  bulk variable/field renames; one `replace_all` call is faster and safer
  than N individual patches)
- Run linter if available
- Fix any LSP errors the rename introduced

### Phase 4 — Verify

After ALL changes, verify with a fresh grep:

```bash
grep -rn -i "bypass\|exploit" . | grep -v "archive/" | grep -v ".venv/" | grep -v "node_modules/"
```

If any hits remain in live code, fix them. Then grep *without* the archive
exclusion to confirm the only remaining hits are in archive/vendor dirs:

```bash
grep -rn -i "bypass\|exploit" . | grep -v ".venv/" | grep -v "node_modules/"
```

## Completing an Abandoned Mid-Rename

A previous pass may have started the rename and stopped: files renamed on
disk, imports rewritten, but nothing committed and docs/artifacts untouched.
The repo then looks half-old/half-new. Detect and finish it:

1. **Detect the abandoned state first** — before doing anything:
   ```bash
   git status --short          # 'RM old.py -> new.py' = staged rename, never committed
   git log --oneline -5        # no rename commit = work dangling in the index
   ```
   `RM` (or `R `) entries with no corresponding commit are the tell. The
   working tree may already have the NEW filenames — do not rename again.

2. **Verify the code side is actually complete** — imports and class names:
   - Grep for the old term in live `.py` files; zero hits = code is done.
   - Grep for old class/identifier names (e.g. `MazdaECUExploit`,
     `EEPROMAccess`) in `__init__.py` re-exports and consumer files.
   - Class names inside the renamed files must match what `__init__.py`
     imports.

3. **Sweep docs AND analysis artifacts** — this is what the first pass
   skipped:
   - `claude.md`, `.augment/rules/*.md`, `IMPL_PLAN.md`, cross-file-analysis
     docs often still carry the old term.
   - `analysis_artifacts/*.json` contain BOTH old filenames and inline
     code-sample strings (`"key = MazdaECUExploit()..."`). Replace both —
     use a Python multi-file pass, not hand patching.

4. **Know what to leave**:
   - `archive/`, `backend-archive-*` = frozen history. Do NOT rename inside
     them; the old names there are the historical record.
   - `per_file_analysis.jsonl` may legitimately quote old class names
     (`SRSAirbagExploiter`) because it analyzes the archived original — that
     is accurate history, not a missed rename.
   - Agent-state dirs (`.hermes/`, node_modules) are not project code.

5. **Commit** — the whole thing as one commit: renames + import fixes + doc
   + artifact updates. The first pass left it staged-but-uncommitted; leaving
   it again recreates the problem.

## Project Rebranding (fork-level rename)

When renaming an entire project (e.g. `kitty` → `cat` for a fork), the scope
is broader than a terminology cleanup — you're changing the project's identity.
Apply the terminology-refactor workflow above *plus* these extra phases.

### Phase 0 — Understand the project's build system first

Before running any replacements, survey:
- The main source directory name (Will rename break build includes?)
- Build system defines passed via `-D` flags (`KITTY_VERSION`, `KITTY_LIB_PATH`, etc.)
- The primary entry point / launcher C source files that hardcode the project name
- Any Go module path (`go.mod module line`)
- Package/dependency managers (`setup.py`, `pyproject.toml`)

### Phase 1 — Content rename (same as terminology-refactor)

Use a script for a 500+ file rebrand — manual patching doesn't scale. Apply
three case-sensitive replacements in order:

1. `KITTY` → `CAT` (all-caps: env vars, constants, compile-time defines)
2. `Kitty` → `Cat` (title case: project name in prose, class names)
3. `kitty` → `cat` (lowercase: package names, commands, paths)

Critical: use word-boundary regex (`\bkitty\b`, NOT just bare string replace)
to avoid mangling words that *contain* "kitty" (rare, but prevents bugs).

### Phase 2 — Directory renames

Rename directories bottom-up (deepest first) so parent paths don't invalidate
child paths mid-walk:

```bash
# Python module directory
mv kitty/ cat/
# Test directory
mv kitty_tests/ cat_tests/
```

### Phase 3 — Fix build system defines

After renaming the source dir, the build system likely passes compiler flags
with the old name. Find and fix:

```bash
grep -rn 'KITTY_VERSION\|KITTY_LIB_PATH\|KITTY_LIB_DIR\|KITTY_DEBUG' setup.py
```

Change these to `CAT_*` equivalents. The C source uses `CAT_VERSION` etc.

### Phase 4 — Fix broken include paths

Directory renames break `#include "../oldname/header.h"` references in
ancillary C directories (e.g. `glfw/` includes `../kitty/` headers).
Find and fix all of these:

```bash
grep -rn '#include.*"../kitty/' glfw/
```

Also fix any `open('../kitty/...')` references in code-generator scripts.

### Phase 5 — Fix internal imports

After the Python directory rename, fix module-level imports:

```bash
grep -rl 'kitty\.\|kitty_tests\.' --include='*.py' . | xargs sed -i 's/kitty\./cat./g; s/kitty_tests\./cat_tests./g'
```

### Phase 6 — CI / metadata / branding files

Don't miss:
- `.github/workflows/*.yml` — step names, grep paths, binary names
- `.github/workflows/*.py` — CI scripts with `build_kitty()`, `KITTY_BUNDLE` env vars
- `.github/FUNDING.yml`, `SECURITY.md`, `CONTRIBUTING.md`
- `shell-integration/ssh/cat` — user-facing strings
- Shell completion scripts and integration files (filenames with `kitty`)
- `README.*`, `INSTALL.md`, `CHANGELOG.rst`

### Phase 7 — Verify build compiles

Run the build before declaring done. Common failures:
- **Include path drift** — C files in `glfw/`, `glad/` reference `../kitty/`
- **Compile-time defines** — `setup.py` passes `-DKITTY_VERSION` but C expects `CAT_VERSION`
- **Launcher binary** — `main.c: CAT_VERSION` not defined
- **Go module compilation** — `go.mod` module path still references old org/repo

### Phase 8 — Final verification

```bash
grep -rnI 'oldname' . --exclude-dir=.git --exclude-dir=3rdparty | grep -v 'docs/protocol-name'
ls -d newname/ newname_tests/
./newname/launcher/newname --version
```

### Pitfalls specific to rebranding

- **External protocols in docs** — e.g. "kitty keyboard protocol", "kitty graphics
  protocol" are standards. Leave these as-is unless the fork renamed the protocol.
- **Binary logo files** — `.png`, `.icns`, `.svg` with the old name. Rename files but
  content is a logo, not text.
- **CI env vars** — `KITTY_BUNDLE`, `KITTY_CODEQL`, `KITTY_SANITIZE` etc.
- **termcap/terminfo** — `xterm-kitty` should become `xterm-cat`.
- **Shell completion scripts** — filenames like `_kitty`, `kitty.bash` need
  renaming AND their internal content updated.

## Pitfalls

### There's always more files than your first search found

The #1 mistake: searching `src/` but not `app/`, `tools/`, `muts_tuner/`,
or other project directories. **Always do a top-level recursive search**
first to see the full scope before planning.

When the user says "there's more files" and you thought you got them all,
stop and re-search from the project root. Don't re-search with the same
limited scope — search EVERYTHING.

### File renames break imports

When you rename a file (e.g. `exploiter.py` → `access.py`), every file
that imports from it breaks. Fix in order:
1. The renamed file itself (class name + `__all__`)
2. The `__init__.py` that re-exports it
3. All consumer files

### Common alternative mappings

| Problematic term | Good alternatives |
|----------------|-----------------|
| bypass (noun) | access, override, patch, skip |
| bypass (verb) | perform, authorize, execute, patch, skip |
| bypass (property name, e.g. bypassForAdmin) | skipForAdmin, overrideForAdmin |
| exploit (noun) | access, module, mechanism, probe |
| exploit (verb) | access, use, leverage, utilize |
| exploiter (class/class) | access, module, operations |
| Exploit (in class name, e.g. MazdaECUExploit) | Access (e.g. MazdaECUAccess) |
| Exploiter (in class name, e.g. EEPROMExploiter) | Access (e.g. EEPROMAccess) |
| Exploits (in class name, e.g. DiagnosticExploits) | Access (e.g. DiagnosticAccess) |
| security_bypass | security_access |
| checksum_bypass | checksum_override, checksum_patch |

Pick the most precise alternative for the context. "Override checksum" is
better than "patch checksum" when the intent is to bypass a validation
gate. "Access framework" is better than "exploitation framework" to
describe the same technical capability without the loaded language.

### Archive directories are traps

Projects often have `archive/`, `archive-original/`, `backup/`,
`backend-archive-*` directories that contain copies of the same files with
the old terminology. Grep output from these dirs looks like the term is
still in live code. Explicitly exclude them:

```bash
grep -rn "term" . | grep -v "archive/" | grep -v "backend-archive-"
```

### Don't skip docstrings

Prose in docstrings, comments, and print statements often has the most
aggressive language ("ECU EXPLOITATION FRAMEWORK", "FULL SECURITY BYPASS").
These are user-visible and need rewording. Search for the term
case-insensitively to catch ALL_CAPS variants.

### Verify the grep is clean — not just "fewer"

"50 occurrences left, down from 200" sounds good but the user will find
them. Zero tolerance. Grep again with `wc -l` and don't stop until
the count is zero for live paths.

## Worked Example: MUTS Project

The full MUTS project rename (bypass/exploit → civilized) is documented in
`references/muts-terminology-rename.md` which includes the exact grep
patterns, file-by-file changes, and the full list of replacement mappings.
