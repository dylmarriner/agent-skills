# Conversation Export Pattern

Full implementation for exporting a DeepSeek/ChatGPT/etc conversations.json array into individual files with message-tree traversal.

## Data Structure

The source file is a JSON array. Each element has:

```json
{
  "id": "uuid",
  "title": "Conversation Title (may be empty)",
  "inserted_at": "ISO timestamp",
  "updated_at": "ISO timestamp",
  "mapping": {
    "root": { "id": "root", "parent": null, "children": ["1"], "message": null },
    "1": { "id": "1", "parent": "root", "children": ["2"],
      "message": {
        "model": "deepseek-chat",
        "inserted_at": "timestamp",
        "fragments": [
          {"type": "REQUEST", "content": "user message text"},
          {"type": "THINK", "content": "model thought process"},
          {"type": "RESPONSE", "content": "model response text"},
          {"type": "FILE", "content": "uploaded file text"}
        ]
      }
    }
  }
}
```

## Message Tree Traversal

The `mapping` is a tree where `root` has `children` pointing to the first message. Walk breadth-first from root's children to get chronological order. Fragment types: `REQUEST` = user, `RESPONSE` = assistant, `THINK` = model reasoning (skip in output), `FILE` = user upload.

## Key Implementation Detail

The `flatten_mapping` function uses a breadth-first stack: children from each node are inserted at the front of the stack to maintain chronological order. This is critical — other traversal orders produce scrambled conversations.

## Per-Message Formatting

```python
role_label = "🧑 **User**" if msg["role"] == "REQUEST" else "🤖 **Assistant**"
meta = f" ({msg['model']})" if msg["model"] != "unknown" else ""
```

Separate messages with `---` in Markdown output. Include ID, created/updated timestamps in the header.

## Output

Each conversation produces two files in `conversations_export/`:
- `<title-slug>__<uuid-prefix>.json` — raw single-conversation JSON
- `<title-slug>__<uuid-prefix>.md` — readable Markdown

## Script Files

The full scripts from the session are at:
- `split_conversations.py` — split JSON array into files with title-based naming
- `rename_conversations.py` — post-export rename pass (bare UUID → title-based)

---

## Post-Export Analysis: Scanning for Content & Extracting Code

After conversations are split into individual files, mine them for useful content.

### Step 1: Topic Scanning by Filename

Use semantic filenames to get a quick overview:

```bash
ls conversations_export/ | sed 's/__.*//' | sort -u
```

### Step 2: Keyword-Based Content Filtering

Scan first-request text from each file against a topic keyword set. Start broad, then thin-slice:

```python
signals = ["iphone", "android", "samsung", "frp", "mdm", "jailbreak",
           "icloud", "dfu", "ss7", "redmi", "bypass", "adb"]

candidates = []
for jf in sorted(os.listdir(outdir)):
    conv = json.load(open(os.path.join(outdir, jf)))
    # Build combined text from first 3-5 user requests
    combined = " ".join(texts[:5]).lower()
    matches = [s for s in signals if s in combined]
    if matches:
        candidates.append((slug, matches))
```

### Step 3: Thin-Slicing Promising Candidates

For narrowed list, read first user request + AI response:

```python
for node_id, node in sorted(mapping.items()):
    msg = node.get("message")
    if msg:
        for frag in msg.get("fragments", []):
            if frag.get("type") == "REQUEST":
                first_req = frag.get("content", "")[:150]
```

Classify as:
- **Definite** → move to target directory
- **Edge case** → read more or ask user
- **False positive** → keyword in jailbreak prompt, not content

### Step 4: Code Block Extraction

```python
import re
blocks = re.findall(r'```(\w*)\n(.*?)```', content, re.DOTALL)
for lang, code in blocks:
    code = code.strip()
    if len(code.split('\n')) >= 15 and lang in ('python', 'bash', 'sh'):
        # substantial code block worth extracting
```

### Step 5: Project Enrichment

Map the target project structure, identify gaps the conversation code fills, then create proper modules (not copy-paste). Wire through __init__.py.

### Pitfalls

- **Keyword scanning is noisy.** "call", "sim", "edl", "lte" appear in generic contexts. Use longer/stronger keywords.
- **Don't read full conversations.** Classify from first request + AI response. Only read deeper when uncertain.
- **Don't trust first-request alone.** A jailbreak-prompt starter may develop into useful content. Check 3-5 exchanges.
- **Conversation code is often synthetic.** Many AI responses contain refused code (GODMODE, leetspeak). Test before integrating.
- **"Skim read" means read first messages to classify.** Don't load full files into context.
- **Verify subagent output.** Delegated subagents that scanned large file sets return truncated summaries. Full output is at `/home/lin/.hermes/cache/delegation/` — page through with `read_file` offset/limit.
