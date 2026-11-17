# DeepSeek Workspace Export Format Reference

When debugging code extraction from DeepSeek, the Brainsync/Code Intelligence workspace exports show the exact data structure.

## Export JSON Fields

```json
{
  "id": "cb_<timestamp>_<random>",
  "raw": "bash\nCopy\nDownload\n# Actual code here",
  "url": "https://chat.deepseek.com/a/chat/s/<session-uuid>",
  "title": "Conversation title - DeepSeek",
  "extractedAt": "2026-06-24T10:18:25.816Z",
  "domIndex": 0,
  "workspaceId": "ws_default",
  "tabId": "tab_default",
  "language": "css",
  "confidence": 0.7,
  "hash": "<sha256>",
  "tags": []
}
```

## Known Bug Signature

In a broken export, the `raw` field includes UI button text before the actual code. A bash script gets exported as:

```
bash\nCopy\nDownload\n# Update system\nsudo apt update...
```

The content before `# Update system` is UI chrome — language badge ("bash"), Copy button, Download button. These lines should be stripped.

The `language` field will also be wrong because the classifier ran on contaminated input. Common wrong classifications: `css`, `plaintext`.

## Healthy Export Pattern

After proper stripping, `raw` should start with actual code and `language` should reflect the real language (`bash`, `python`, `javascript`).

## Markdown Export Format

The same data is also exported as markdown (`workspace-markdown-*.md`) with sections:

```markdown
## Title - DeepSeek (css)
* **Source URL:** https://chat.deepseek.com/a/chat/s/<uuid>
* **Captured:** timestamp

\`\`\`<language>
(contaminated raw content)
\`\`\`
```

The language in parentheses after the title is the misclassified language.
