---
name: JSON Array Extraction
title: JSON Array Extraction
description: Extract items from a large JSON array file into individual files with smart naming, multiple output formats, and duplicate-title handling.
tags:
  - json
  - data-export
  - etl
  - file-splitting
---

# JSON Array Extraction

Split a large JSON array (e.g. `conversations.json`, exported data dumps) into individual files, one per element.

## Trigger

User says "split this JSON into separate files", "extract each conversation", "break up this JSON array", or similar.

## Workflow

### 1. Inspect the file minimally

Do NOT read the full file into context — it can be huge (10M+ tokens). Instead:

- Run `stat` or `read_file(limit=5)` to confirm it's a JSON array and identify the key fields per object (e.g. `id`, `title`, key nested structures).
- Look for a `title` / `name` / `label` field — that's the semantic key for output filenames.

### 2. Write an extraction script

Pattern:

```python
import json
from pathlib import Path

INPUT = Path("conversations.json")
OUTDIR = Path("export")

with open(INPUT) as f:
    items = json.load(f)  # list of dicts

OUTDIR.mkdir(parents=True, exist_ok=True)

for item in items:
    item_id = item.get("id", "unknown")
    # ... extract what matters
```

### 3. Name files by semantic content — NOT raw UUIDs

**Critical preference**: the user expects descriptive filenames, not opaque IDs.

```python
def slugify(text, max_len=60):
    """Clean a title into a filesystem-safe slug."""
    s = text.strip().lower()
    s = re.sub(r"[^\w\s\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace(" ", "-").strip("-")
    s = re.sub(r"-+", "-", s)
    return s[:max_len].rstrip("-")[:max_len] or "untitled"
```

Append a short UUID prefix for uniqueness when titles repeat:

```
{title_slug}__{uuid[:8]}.json
```

### 4. Provide multiple output formats when useful

- Raw JSON preserves original data losslessly.
- Markdown/human-readable format adds value (formatted headers, readable structure).

### 5. Handle edge cases

| Problem | Solution |
|---------|----------|
| Empty/trivial items (no content) | Skip, report count |
| Duplicate titles | Append UUID short prefix to guarantee uniqueness |
| Missing title field | Fallback to `"untitled"` |
| Non-ASCII titles (Chinese, emoji, etc.) | Slugify handles them; write JSON with `ensure_ascii=False` |

### 6. Report results

Summary line showing: items found, written, skipped, errors, and output directory.

## Support files

- `templates/rename_by_title.py` — reusable script template: rename exported files by a semantic field. Drop into any project, adapt `KEY_FIELD`.
- `references/deepseek-conversations-export.md` — session example: BFS message-tree walk for nested conversation JSON with parent-children mapping.

## Pitfalls

- **Don't read the full JSON into chat context.** Use a Python script or terminal to process it — the file can be hundreds of MB.
- **Don't use UUID-only filenames.** The user will call them out as untitled/unhelpful. Always extract a semantic key (title, name, label) for the filename.
- **Don't assume unique titles.** Multiple items can share the same title. Always append a disambiguator (UUID prefix, sequence number) to the slug.
- **Don't use `json.dump(obj, f, indent=0)`** — single-line output for huge arrays can be fine for the parent, but individual item files deserve proper indentation for human readability.
- **Breadth-first walk for message trees.** When extracting nested message trees (parent-children mapping), use BFS (not DFS) to preserve chronological order.
