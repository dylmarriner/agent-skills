# Workspace Export File Extraction

When extracting code blocks from LLM chat workspace exports (Brainsync/Code Intelligence .json or .md files):

## The Contamination Problem

LLM chat UIs (DeepSeek, Claude, ChatGPT) render code blocks with:
- A **language label** (e.g. "python", "bash")
- **Copy button** text
- **Download button** text
These UI elements sit inside the same parent DOM container as the code content. Text extraction (`textContent`, `innerText`) picks up all of them:

```
raw = "python\nCopy\nDownload\nimport os\nprint('hello')"
```

## Stripping UI Noise

```python
noise = {'bash', 'shell', 'python', 'javascript', 'typescript', 'json',
         'yaml', 'css', 'copy', 'download', 'plaintext', 'text'}
lines = raw.split('\n')
while lines and lines[0].strip().lower() in noise:
    lines.pop(0)
cleaned = '\n'.join(lines).strip()
```

## Heredoc Handling

If the code was written as a shell heredoc (`cat > file << 'EOF'`...`EOF`), extract the inner content:

```python
import re
m = re.search(r"<<\s*'?\w+'?\s*\n(.*?)\n\s*EOF", content, re.DOTALL)
if m:
    python_code = m.group(1)
```

## Deduplication

Workspace exports often contain multiple captures of the same code block (same chat message rendered/re-captured). Use the first 100 chars of cleaned content as a dedupe key.

## Language Misclassification

The export tool often mislabels languages:
- Bash scripts tagged as "css"
- Python tagged as "javascript" or "typescript"
- Code blocks with no language tag labeled "plaintext"
Trust content-based detection over the export's `language` field.
