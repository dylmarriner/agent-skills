# File Compression

Compress a context file into caveman format to cut input tokens on every future request.

## Usage

```
/cc compress <filepath>
```

## Steps

1. Read the file at `<filepath>`
2. Save backup to `<filepath>.original.md` (never overwrite existing backup)
3. Two-pass compression:

   **Pass 1 — Algorithmic:**
   - Drop articles (a, an, the)
   - Drop filler phrases (Sure!, I'd be happy to, Please note that, etc.)
   - Replace verbose synonyms: use/utilize, add/implement, show/demonstrate, but/however, so/therefore
   - Drop hedging: might, potentially, seems to, could potentially
   - Preserve ALL code blocks, URLs, numbers exactly

   **Pass 2 — Semantic:**
   - Merge sentences expressing same idea
   - Remove statements obvious from context
   - Collapse multi-sentence explanations to one tight sentence
   - Convert narrative prose to fragments or bullets where meaning preserved
   - Strip preamble/summary sections that restate the body

4. Write compressed text back to `<filepath>`
5. Report: original token estimate, compressed estimate, % saved

## Rules

- Never compress if backup already exists (prevents double-compression)
- If file does not exist, say so and stop
- If `<filepath>` not provided, ask which file to compress
- Technical accuracy is non-negotiable — when in doubt, keep content
