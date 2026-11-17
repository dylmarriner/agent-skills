---
name: llm-chat-code-extraction
description: "Debug and fix code extraction from LLM chat UIs (DeepSeek, ChatGPT, Claude, etc.) and mine code from already-exported conversation markdown files. Covers DOM structure analysis, UI text contamination, language detection issues, deduplication bugs in userscripts, plus post-hoc extraction of real protocol/implementation code from exported conversation dumps."
version: 1.1.0
author: Hermes Agent
tags: [deepseek, tampermonkey, userscript, code-extraction, dom, debugging, export-mining]
---

# LLM Chat Code Extraction — Debugging

**Trigger:** User has a userscript that extracts code blocks from an LLM chat UI (DeepSeek, ChatGPT, Claude) and the output is wrong — wrong language, missing code, extra UI text, wrong file extensions, or duplicate entries.

## Common Bug Pattern: UI Text Contamination

The #1 cause of broken code extraction from LLM chat UIs is **UI button text getting mixed into the code content**. This happens because the extractor uses `textContent` on a parent element that contains both the code and the UI chrome (language label, Copy button, Download button) as sibling nodes.

### The Symptom

The `raw` code content starts with UI noise:

```
bash
Copy
Download
# Actual code starts here
sudo apt update
```

The first 1-3 lines are the language badge text ("bash", "python", "javascript") followed by "Copy" and "Download" button text.

### The Diagnosis

Look at the raw extracted content. If it starts with one of these patterns, UI contamination is present:

| Pattern | Meaning |
|---------|---------|
| `bash\nCopy\nDownload\n` + code | Language badge + Copy/DL buttons included |
| `python\nCopy\nDownload\n` + code | Same with Python label |
| Just `Copy\nDownload\n` + code | Labels in different position |
| `css` or `plaintext` in language field | The heuristic classifier is confused by the contaminated input |

### The Root Cause

Modern LLM chat UIs (especially DeepSeek) structure code blocks like:

```html
<div class="code-block-container">
  <div class="code-block-header">
    <span class="language-badge">bash</span>
    <button class="copy-btn">Copy</button>
    <button class="download-btn">Download</button>
  </div>
  <pre><code># Actual code here</code></pre>
</div>
```

If the userscript extracts from the outer `<div>` with `textContent` or `innerText`, it gets: `"bashCopyDownload# Actual code here"`.

### The Fix

After extracting `rawCode`, strip the leading UI noise:

```javascript
// Strip leading UI contamination lines
const UI_NOISE_LABELS = new Set([
  'bash', 'shell', 'python', 'javascript', 'typescript', 'json',
  'yaml', 'yml', 'css', 'html', 'xml', 'markdown', 'md', 'sql',
  'java', 'c', 'cpp', 'c++', 'c#', 'go', 'rust', 'php', 'ruby',
  'swift', 'kotlin', 'tsx', 'jsx', 'r', 'lua', 'perl', 'scala',
  'dockerfile', 'docker', 'powershell', 'pwsh', 'text', 'plaintext',
  'copy', 'copied', 'download', 'expand', 'collapse'
]);

rawCode = rawCode
  .split('\n')
  .filter((line, i, arr) => {
    // Skip leading lines that are only UI noise
    if (i < 4 && UI_NOISE_LABELS.has(line.trim().toLowerCase())) return false;
    return true;
  })
  .join('\n')
  .trim();
```

For a more robust approach, strip ALL leading lines that match ONLY a single known UI-noise word until you hit a line with actual code content:

```javascript
function stripUINoise(raw) {
  const lines = raw.split('\n');
  while (lines.length > 0) {
    const trimmed = lines[0].trim().toLowerCase();
    if (UI_NOISE_LABELS.has(trimmed) || trimmed === '') {
      lines.shift();
    } else {
      break;
    }
  }
  return lines.join('\n').trim();
}
```

### Language Detection Issues

Even after fixing the content, the `language` field in exports may be wrong because:
1. The heuristic classifier (`looksLikeYAML`, `detectLanguageByContent`) was trained on the contaminated input
2. The DOM-based language hint extraction (`extractLanguageHints`) may miss if the label is outside the container
3. The language badge text was stripped but the classifier already read the wrong input

Fix: Re-run language detection AFTER stripping UI noise, not before.

### Deduplication Failures

If the extractor hashes the contaminated `raw` content (including UI text) for deduplication, blocks that differ only in UI text will NOT be deduped properly:
- Block A: `"bash\nCopy\nDownload\nsudo apt update"`
- Block B: `"python\nCopy\nDownload\nsudo apt update"`

These hash differently even though the actual code is identical. Fix: hash AFTER stripping UI noise.

## DeepSeek-Specific DOM Notes

When debugging extraction from DeepSeek chat:
- Code blocks may not use `<pre>` elements — look for `<div class="...code-block...">` containers
- Language labels are typically `<span>` elements with class containing `lang` or `language`
- Copy/Download buttons are children of the same container as the code
- DeepSeek uses AWS WAF (CloudFront challenge) — direct curl/browser automation may be blocked
- The DOM structure changes frequently (every few months) — selectors may need updating

## Verification

After fixing the extraction:

```javascript
// Check: do any blocks start with known UI noise?
blocks.forEach(block => {
  const firstLine = block.rawCode.split('\n')[0].trim().toLowerCase();
  if (UI_NOISE_LABELS.has(firstLine)) {
    console.warn('UI contamination still present in block', block.id);
  }
});

// Check: is language detection running on clean input?
// The content passed to detectLanguageByContent should not include UI text
```

## Reference

- DeepSeek workspace exports (from Brainsync/Code Intelligence) show the exact contamination pattern in `raw` field values
- The export JSON metadata includes `language`, `confidence`, `hash`, `domIndex` fields useful for debugging extraction quality

## Mining Code from Already-Exported Conversation Files

When you have **markdown conversation export dumps** (not live DOM) and need to extract real protocol/implementation code from them, see:

→ [`references/conversation-export-mining.md`](references/conversation-export-mining.md)

That file covers: discovering code blocks via `search_files` without reading the raw noise, distinguishing real protocol bytes from simulated/leetspeak wrappers, deduplicating near-identical iterations from re-prompts, the backward-compatible integration pattern (delegation), and test-driven verification.
