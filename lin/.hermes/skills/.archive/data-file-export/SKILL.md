---
name: data-file-export
description: "Split, rename, and organize large structured data files into individual records with semantic naming. Covers: JSON array splitting, metadata-based filename generation, category subdirectory organization, and dual-format output (raw + human-readable)."
version: 1.0.0
---

# Data File Export

Split a large structured data file (typically a JSON array of objects) into individual files, one per record, with filenames derived from record metadata rather than raw IDs.

## When to Use

Trigger when the user has a large JSON file (or similar structured format) containing an array of objects, and wants them split into individual files. Typical signals:

- "extract every conversation into its own file"
- "split this JSON array into separate files"
- "export each record individually with meaningful names"
- "organize these records into categories"

## Workflow

### Step 1: Understand the Structure

Read just enough of the file to understand its format:

```python
# Read first few bytes to check if it's a JSON array or NDJSON
with open("data.json", "r") as f:
    first = f.read(500)
```

Common formats:
- **JSON array**: `[{...}, {...}, ...]` — load the whole file, iterate
- **NDJSON/JSONL**: one JSON object per line — streaming-friendly
- **Wrapped JSON**: sometimes has a header line (e.g. `export_version=1`) before the array

### Step 2: Identify Semantic Filename Metadata

Each record object typically has fields usable for naming:

| Field Type | Example | Filename Use |
|------------|---------|-------------|
| Title/name | `"title": "How to..."` | Primary slug source |
| ID | `"id": "uuid"` | Uniqueness suffix |
| Timestamp | `"created_at": "2025-..."` | Date prefix |
| Category | `"type": "phone"` | Subdirectory target |

**Always use semantic names, never bare UUIDs.** The slug format:

```
{slugified-title}__{id-prefix}.{ext}
```

This wraps on two lines in most terminals, is unique, and scannable.

### Step 3: Write the Split Script

Standard Python pattern:

```python
import json, os, re
from pathlib import Path

INPUT = Path("data.json")
OUTDIR = Path("export/")

def slugify(text: str, max_len: int = 60) -> str:
    """Turn a title into a clean filesystem-safe slug."""
    if not text or text.strip() == "":
        return "untitled"
    s = text.strip().lower()
    s = re.sub(r"[^\w\s\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace(" ", "-")
    s = s.strip("-")
    s = re.sub(r"-+", "-", s)
    if len(s) > max_len:
        s = s[:max_len].rstrip("-")
    return s or "untitled"

def main():
    with open(INPUT, "r", encoding="utf-8") as f:
        records = json.load(f)
    
    print(f"Loaded {len(records)} records")
    OUTDIR.mkdir(parents=True, exist_ok=True)
    
    for i, record in enumerate(records):
        rec_id = record.get("id", f"record_{i}")
        title = record.get("title", "") or "untitled"
        slug = slugify(title)
        short_id = rec_id[:8]
        stem = f"{slug}__{short_id}"
        
        # Write raw JSON
        json_path = OUTDIR / f"{stem}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=1)
        
        # Optionally write a human-readable format (markdown, etc.)
        # ... see references/conversation-export-pattern.md

    print(f"Done — wrote {len(records)} files to {OUTDIR}")
```

### Step 4: Handle Large Files

For files over ~500MB where loading into memory is risky:

```python
import ijson  # streaming JSON parser
with open(INPUT, "rb") as f:
    parser = ijson.items(f, "item")
    for record in parser:
        # process one at a time
        pass
```

For NDJSON/JSONL, just iterate lines.

### Step 5: Category Organization

When records should be organized into subdirectories:

```python
category = classify_record(record)  # e.g., "phone", "finance", "security"
catdir = OUTDIR / category
catdir.mkdir(exist_ok=True)
# Move file into catdir
```

For keyword-based classification, use a focused keyword set rather than exhaustive matching. Let the user correct and expand.

### Step 6: Post-Export Renaming

If the initial export used bare IDs and the user wants semantic names, run a rename pass:

```python
import json, os, re
from pathlib import Path

OUTDIR = Path("export/")

def slugify(text: str, max_len: int = 60) -> str:
    s = text.strip().lower()
    s = re.sub(r"[^\w\s\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace(" ", "-").strip("-")
    s = re.sub(r"-+", "-", s)
    return (s[:max_len].rstrip("-")) or "untitled"

for jpath in sorted(OUTDIR.glob("*.json")):
    conv_id = jpath.stem
    with open(jpath, "r") as f:
        record = json.load(f)
    title = record.get("title", "").strip() or "untitled"
    slug = slugify(title)
    new_stem = f"{slug}__{conv_id[:8]}"
    
    for ext in (".json", ".md"):
        old = OUTDIR / f"{conv_id}{ext}"
        new = OUTDIR / f"{new_stem}{ext}"
        if old.exists() and old != new:
            old.rename(new)
```

## Dual-Format Output

When the user wants both raw data and readable output:

- **`.json`** — raw single-record JSON, identical format to original
- **`.md`** — human-readable Markdown with formatted fields, timestamps, and record content

See `references/conversation-export-pattern.md` for the full conversation-export implementation.

## Pitfalls

- **Don't read the whole file** into your context — read structure with `read_file(limit=10)` or `head`, process with a standalone script.
- **Always include a uniqueness suffix** — titles can be identical (duplicate titles from different prompts). The ID prefix guarantees unique filenames.
- **Clean slug edge cases** — titles with only special characters, empty titles, Chinese/Russian/emoji titles all need handling. Slugify must survive any Unicode input.
- **Rename both file pairs** — when you rename `.json` files, don't forget the paired `.md` (or other format) files.
- **Ask for category corrections** — keyword-based classification will miss things. After the first pass, show the counts and let the user point out misses.
