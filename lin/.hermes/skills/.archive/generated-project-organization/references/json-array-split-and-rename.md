# JSON Array Split & Rename

Split a large JSON file containing an array of objects into individual files, each named after a content-derived title. Also covers classification / content routing into subdirectories.

## When to Use

The user hands you a large export file (conversations, tickets, records, logs) where the root is a JSON array of objects, each with a unique ID and a human-readable name/title/description. They need those split into individual `.json` and/or `.md` files with names that mean something at a glance.

## Workflow

### Step 1: Inspect Structure (minimally)

Read just enough of the file to understand the array structure and the key field names:

```python
import json
with open("export.json") as f:
    data = json.load(f)
# Check: is it a list? is there an 'id' field? a 'title' field?
print(type(data), len(data))
print(json.dumps(data[0], indent=1)[:2000])
```

Don't read the whole file into your working context — the export could be 40MB+. Use a script.

### Step 2: Split Script

```python
import json, os
from pathlib import Path

SRC = Path("export.json")
OUT = Path("output_dir")
OUT.mkdir(exist_ok=True)

with open(SRC, encoding="utf-8") as f:
    items = json.load(f)

for item in items:
    item_id = item.get("id", "unknown")
    # Write raw single-object JSON
    (OUT / f"{item_id}.json").write_text(
        json.dumps(item, indent=1, ensure_ascii=False)
    )
```

### Step 3: Rename with Titles (slugify)

After splitting, rename files from UUIDs → slugified titles:

```python
import json, os, re

def slugify(text: str, max_len: int = 60) -> str:
    """Turn any title into a clean filesystem-safe slug."""
    if not text or not text.strip():
        return "untitled"
    s = text.strip().lower()
    s = re.sub(r"[^\w\s\-]", " ", s)  # replace special chars
    s = re.sub(r"\s+", " ", s).strip().replace(" ", "-")
    s = s.strip("-")
    s = re.sub(r"-+", "-", s)
    return s[:max_len].rstrip("-") or "untitled"

for jpath in sorted(OUT.glob("*.json")):
    conv_id = jpath.stem
    with open(jpath) as f:
        item = json.load(f)
    title = item.get("title", "").strip() or "untitled"
    slug = slugify(title)
    new_stem = f"{slug}__{conv_id[:8]}"
    jpath.rename(OUT / f"{new_stem}.json")
    if (OUT / f"{conv_id}.md").exists():
        (OUT / f"{conv_id}.md").rename(OUT / f"{new_stem}.md")
```

The `__{uuid_prefix}` suffix guarantees uniqueness when titles repeat.

### Step 4: Classify & Move (content-aware)

Keyword/title matching is too noisy (false positives from common tech words). Instead, **skim the actual user request messages** to determine category:

```python
# Grab first few REQUEST fragments from the mapping
def first_requests(mapping):
    texts = []
    for node_id, node in sorted(mapping.items(), key=lambda x: str(x[0])):
        msg = node.get("message")
        if msg:
            for frag in msg.get("fragments", []):
                if frag.get("type") == "REQUEST":
                    texts.append(frag.get("content", "").lower())
                    if len(texts) >= 3:
                        break
        if len(texts) >= 3:
            break
    return " ".join(texts)
```

Read the actual request text, don't trust the AI's response which may veer off-topic. The first 1-3 user messages are the strongest signal of what the conversation is actually about.

### Step 5: Move matched files

```python
import shutil, os

subdir = OUT / "category-name"
subdir.mkdir(exist_ok=True)
for f in list(OUT.glob(f"{slug_prefix}*")):
    shutil.move(str(f), str(subdir / f.name))
```

## Pitfalls

- **Keyboard+mouse signals beat keyword matching.** A file titled "car-seatbelts" could be about Redmi Note 13 FRP bypass. Read the actual first user message before classifying.
- **Slug truncation** at 60 chars is usually safe. Filesystem paths over ~200 chars cause issues on some tools.
- **Title duplicates** — Always append a unique suffix (uuid prefix, counter) to prevent collisions.
- **Mixed separator styles** — Some files use `__` (double underscore), others use `_` (single). Handle both.
- **Encoding** — JSON can contain CJK, Cyrillic, or special Unicode. Use `ensure_ascii=False` and `encoding="utf-8"` everywhere.
- **The rename script is one-time.** Once files are renamed, the original UUID is in the suffix. If the user wants to re-split with a different naming scheme, keep the raw split script around separately.
