---
name: fork-rebrand
description: Bulk rebrand a forked/cloned repository — rename all codebase references from an old project name to a new one. Covers content replacement, directory/file renaming, import fixes, and post-cleanup of CI, shell scripts, and config.
---

# Fork Rebrand

Rebrand a forked repository from `old-name` → `new-name`. This is the full workflow for cloning a fork and systematically replacing every reference.

## When to Use

- You cloned a fork of an existing project and need to rename it
- User says "clone this into X and rebrand everything to Y"
- Bulk project rename across a codebase

## Workflow

### 1. Clone and position

```bash
gh repo clone $OWNER/$REPO
# Move to target directory if needed
mv $REPO $TARGET_DIR
```

### 2. Content replacement (core)

Use a script that replaces the name in file contents with proper case variants:

| Variant | Example | When |
|---------|---------|------|
| lowercase | `kitty` → `cat` | module names, commands, imports |
| TitleCase | `Kitty` → `Cat` | project display names |
| UPPERCASE | `KITTY` → `CAT` | env vars, constants |

**Regex approach** (word-boundary aware to avoid matching inside longer words):

```python
import re, os
text = re.sub(r'(?<![a-zA-Z])KITTY(?![a-zA-Z])', 'CAT', text)
text = re.sub(r'(?<![a-zA-Z])Kitty(?![a-zA-Z])', 'Cat', text)
text = re.sub(r'(?<![a-zA-Z])kitty(?![a-zA-Z])', 'cat', text)
```

### 3. Directory renames

```bash
mv old_name_dir new_name_dir     # e.g. kitty/ -> cat/
mv old_name_tests new_name_tests # e.g. kitty_tests/ -> cat_tests/
```

Rename directories **bottom-up** (deepest first) to avoid invalidating paths mid-walk.

### 4. File renames

Find all files with the old name in their filename:

```bash
find . -type f -iname '*oldname*' 2>/dev/null
```

Rename each with simple string replacement in the filename. Files to watch for:
- Shell integration scripts (`oldname.bash`, `oldname.zsh`, `oldname.fish`)
- Shell completions (`_oldname`, `clone-in-oldname.fish`)
- Terminfo files (`xterm-oldname`, `oldname.terminfo`, `oldname.termcap`)
- Logos and icons (`oldname.png`, `oldname.svg`, `oldname.icns`)
- C/Go source files with old name

### 5. Import fixes (post-directory-rename)

After renaming the source directory, fix all internal imports:

```python
text.replace('old_name.', 'new_name.').replace('old_name_tests.', 'new_name_tests.')
```

### 6. Post-cleanup targeted fixes

After bulk replacement, find remaining references with:

```bash
grep -rnI 'oldname' . --exclude-dir=.git --exclude-dir=3rdparty | grep -v 'docs/protocol-name'
```

Files that commonly still have the old name after bulk replace:
- `.github/workflows/*.yml` — CI step names, grep paths, artifact names
- `.github/workflows/*.py` — CI helper scripts, bundle URLs, env vars
- `.github/copilot-instructions.md` — build path references
- `.github/ISSUE_TEMPLATE/*.md` — user-facing instructions
- `shell-integration/ssh/oldname` — bootstrap script error messages
- `setup.py` — include paths, build targets
- C source (`cat/launcher/main.c`, etc.) — version/credits strings
- Env vars: `OLDNAME_BUNDLE`, `OLDNAME_CODEQL`, `OLDNAME_SANITIZE`
- URL references (funding, download URLs, upstream links)
- Protocol docs that mention the old project name

## Pitfalls

- **Binary files**: Logos (`.png`, `.icns`, `.svg`) need manual replacement — you can't text-replace binary content. Either regenerate or accept the old branding.
- **3rdparty/vendored code**: Skip `3rdparty/`, `glad/`, `glfw/` and similar vendored libraries. They're upstream code, not your project.
- **Protocol standards**: If the old name is part of a protocol standard (e.g. "kitty keyboard protocol"), consider keeping the reference — it's the name of the protocol spec, not your project.
- **Always word-boundary**: `re.sub(r'kitty', 'cat', text)` will match inside "mykitty" — use `(?<![a-zA-Z])` lookbehind/lookahead to prevent this on the first pass, then handle `mykitty` → `mycat` examples individually.
- **Case ordering matters**: Replace UPPERCASE first, TitleCase second, lowercase last. Otherwise `KITTY` → `CAT` would also catch `CAT` inside already-replaced content.
- **Double-check CI workflow files**: `.github/workflows/` files have their own `name:` fields, `run:` commands with directory paths, and env var refs — they're the most commonly missed.
- **Shell completion files**: These often have the old name in the filename itself AND the file contents (zsh `_oldname`, fish `oldname.fish`, bash `oldname.bash`).
