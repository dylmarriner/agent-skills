# Code Extraction from LLM Conversation Files

Extraction pipeline for extracting code from DeepSeek/ChatGPT/Claude markdown exports and integrating into projects.

## When to Use This

You have `.md` files from an LLM conversation export (typically a `conversations_export/` directory with `<title>__<id>.md` files). You need to extract all code blocks and integrate them into a project.

## Step 0: Check if codegraph already has the target

If the target project is a codebase (not raw markdown), use `codegraph_explore()` first — it returns verbatim source with line numbers. Only reach for extraction scripts when the target is unindexed `.md` files.

## Step 1: Extraction Script

```python
#!/usr/bin/env python3
import json, re, sys
from pathlib import Path
from collections import Counter

CONV_DIR = Path("conversations_export/unlock-suite")
OUTPUT = Path("extracted")
OUTPUT.mkdir(parents=True, exist_ok=True)

DEVICE_PATTERNS = {
    "xiaomi": re.compile(r'redmi|xiaomi|miui|xiaomifrp', re.I),
    "samsung": re.compile(r'samsung|galaxy|a546|knox|exynos', re.I),
    "iphone": re.compile(r'iphone|ios|ipad|apple|icloud|iboot|checkm8|dfu', re.I),
    "android": re.compile(r'android|frp|adb|fastboot|bootloader', re.I),
    "ss7": re.compile(r'ss7|signaling|gsm|vlr|hlr|imsi', re.I),
}
TECHNIQUE_PATTERNS = {
    "frp": re.compile(r'\bfrp\b|factory.*reset|google.*account', re.I),
    "mdm": re.compile(r'\bmdm\b|mobile.*device.*management|knox', re.I),
    "edl": re.compile(r'\bedl\b|emergency.*download|qualcomm.*9008|firehose', re.I),
    "icloud": re.compile(r'icloud|activation.*lock|apple.*id|find.*my', re.I),
}

all_blocks = []
for md_path in sorted(CONV_DIR.glob("*.md")):
    content = md_path.read_text(encoding="utf-8", errors="replace")
    title = md_path.stem.split("__")[0].replace("-", " ").title()
    for m in re.finditer(r'```(\w*)\n(.*?)```', content, re.DOTALL):
        lang, code = m.group(1) or "text", m.group(2).strip()
        if not code or len(code) < 50:
            continue
        text = content + "\n" + code
        cat = next((d for d, p in DEVICE_PATTERNS.items() if p.search(text)), "general")
        tech = next((t for t, p in TECHNIQUE_PATTERNS.items() if p.search(text)), "general")
        all_blocks.append({"conv_title": title, "language": lang, "code": code,
                           "category": cat, "technique": tech, "source_file": md_path.name})

useful = [b for b in all_blocks if b["language"] in ("python", "bash", "sh", "shell", "javascript", "js", "rust", "c", "cpp", "go", "swift", "java")]
(OUTPUT / "code_index.json").write_text(json.dumps(useful, indent=1, ensure_ascii=False))

cat_counts = Counter(b["category"] for b in useful)
tech_counts = Counter(b["technique"] for b in useful)
print(f"Extracted {len(all_blocks)} blocks, {len(useful)} useful")
print(f"By device: {dict(cat_counts.most_common())}")
print(f"By technique: {dict(tech_counts.most_common())}")
```

## Step 2: Read Source Files Directly

The extraction step classifies blocks by language marker. Code blocks without an explicit ` ```python ` marker get labelled "text" — these are often the best blocks. Always read source files directly for the heaviest conversations.

## Step 3: Parallel Module Generation via delegate_task

```python
# Dispatch subagents for large conversations
from hermes_tools import terminal  # not actually — this is conceptual
# Each subagent reads a conversation.md directly and writes a module
# Give each a specific module path and class names to export
```

### Pitfalls
- **Subagents override your files** — dispatch to files that DON'T exist yet
- **Class name drift** — subagent may call the class `EDLForcer` while your `__init__.py` expects `EDLExploitFramework`. Always verify `import` after subagent completes
- **__init__.py mismatch** — the most common failure. Check after every subagent batch
- **Language markers lie** — many code blocks in DeepSeek exports have no ` ```python `, only ` ``` ` (bare)
- **40%+ is noise** — jailbreak prompts, safety-bypass attempts, prompt-injection content. Filter aggressively
- **Scan class names, not titles** — a file named `pegasus-and-mobile.md` contains `ImplantBuilder`, `C2Server`, `HeliosC2Server`, `AndroidDataExtractor`. Running `grep -n '^class '` on the file before deciding what to build prevents building the wrong tool class (defensive analyzer vs deployment toolkit).
- **Zero stubs or reject** — no `MSC001`, `VLR001`, `assumedIdle` or any mock data. Every function must do real work or return `Err`. If a protocol layer can't actually communicate, propagate the error — don't paper over it with fake success strings. The user will catch this immediately.
- **Subagent-generated code needs compile verification** — always run `cargo build` or `python3 -c "import X"`. Subagents rename classes, change signatures, and write code that doesn't compile.
