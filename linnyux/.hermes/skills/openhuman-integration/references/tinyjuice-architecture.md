# TinyJuice Architecture Reference

Deep-dive from examining OpenHuman's vendored TinyJuice engine at `vendor/tinyjuice/`.
The Hermes TokenJuice plugin (`~/.hermes/plugins/tokenjuice/`) is a Python port.

## Content Detection Pipeline

`detect_content_kind(content, hint) -> ContentKind`

Resolution order (cheapest first):
1. **hint.explicit** — hard override, returned immediately
2. **hint.mime / hint.extension** — unambiguous type tags (e.g. `application/json` -> Json, `.rs` -> Code). A sanity check overrides the tag if the body is clearly a diff.
3. **hint.source_tool** — tool-name prior: `grep`/`rg` -> absolute Search. `read_diff`/`git diff` -> Diff. Others get Auto pass-through.
4. **Full structural detection** (fallback), priority-ordered:
   - **JSON** — `serde_json::from_str` parse check: needs 2+ items with 1+ object (arrays) or 2+ keys (objects).
   - **Diff** — first 400 lines checked for `diff --git` / `Index:` / `@@ ... @@` headers.
   - **HTML** — doctype/`<html`/`<head>`/`<body>` markers, or 1.0+ tag-density ratio (first 200 non-blank lines, 8 KB head window).
   - **Search** — 60%+ of lines parse as `path:line:body` (grep format, handles Windows C:\ paths).
   - **Code** — 40%+ code-like lines (keywords, brace/semicolon endings) with 2+ brace lines, first 400 lines.
   - **Log** — 50%+ lines carry error/warning signal keywords.
   - **PlainText** — catch-all.

Supported `ContentKind` variants: `Json`, `Code`, `Log`, `Search`, `Diff`, `Html`, `PlainText`.

## Compressor Registry

Static `compressor_for(kind) -> &'static dyn Compressor`:

| ContentKind | CompressorKind | Strategy |
|---|---|---|
| Json | SmartCrusher | Object-array to Markdown table |
| Code | Code | Declaration-skeleton heuristic |
| Log | Log | Signal-based / rule engine |
| Search | Search | Relevance ranking, top-K per file |
| Diff | Diff | Context collapse, lockfile summary |
| Html | Html | Markup to readable text |
| PlainText | MlText | ML model (opt-in, behind `ml_text_enabled`) |
| (fallback) | Generic | Head/tail summariser (command output only) |

All compressors implement `async fn compress(&self, input, opts) -> Option<CompressOutput>`.
They return `None` to decline (too small, wrong shape, wouldn't shrink).

## CCR Cache (Compress-Cache-Retrieve)

The CCR makes lossy compression safe: every dropped byte is recoverable on demand.

- **Content-addressed**: Key = first 16 bytes of SHA-256 hex digest (32 hex chars).
- **Two-tier**: In-memory HashMap + optional on-disk directory under `<workspace>/.tinyjuice/ccr/`.
- **Bounded**: Default 256 entries / 64 MiB total. FIFO eviction respects both caps. Optional TTL.
- **Disk tier**: Best-effort mirror. Amortised GC every 128 writes. Path traversal prevention via `is_valid_token()` (strict hex check).
- **Retrieval**: retrieve(hash) -> memory first, disk fallback. `retrieve_range(hash, start, end, unit)` for byte-range or line-range retrieval without returning the whole original.
- **Markers**: Canonical [tj:<hash>] inline markers; per-block markers let each omitted gap be individually retrievable.
- **Recovery footer**: `"\n\n[PARTIAL view - full original (N bytes): call tinyjuice_retrieve with token "<hash>"]"` appended to compacted output.
- **Recovery tools**: `tinyjuice_retrieve`, `tokenjuice_retrieve` (legacy), `retrieve_tool_output` (legacy). These are never re-compacted.

## Full Pipeline

```
Tool output arrives
  |
  v
compact_tool_output_with_policy()
  +-- Agent profile check (Off? -> passthrough)
  +-- Recovery tool check (skip compaction)
  +-- Extract command/argv/extension/query from JSON args
  +-- Build ContentHint
  |
  v
route(input, opts)
  +-- Size floor check (min_bytes_to_compress: 2048 / log: 512)
  +-- detect_content_kind(content, hint)
  |    1. explicit override
  |    2. MIME/extension -> reconcile_tag (diff override)
  |    3. tool prior (Search is absolute)
  |    4. structural: JSON -> Diff -> HTML -> Search -> Code -> Log -> PlainText
  |
  +-- Per-kind compressor gate (search_enabled, code_enabled, html_enabled)
  +-- compressor_for(kind) -> primary compressor
  +-- If primary declines -> generic_compressor (command output only)
  |
  +-- If compressor returns text:
  |    +-- Reject if text didn't shrink (size check)
  |    +-- CCR threshold check (ccr_min_tokens: 500)
  |    +-- If lossy && no CCR && !lossy_without_ccr -> passthrough
  |    +-- Offload original to CCR cache (memory + optional disk)
  |    +-- Append recovery footer with hash token
  |    +-- Record savings (tokens + cost for dashboard)
  |
  +-- Return CompressedOutput { text, content_kind, compressor, lossy, applied, ccr_token }
  |
  v
Agent receives compacted text with recovery footer
  +-- If agent needs the full original -> calls tinyjuice_retrieve(token)
```

## Key Design Principles

- **Pass-through safe**: Every path falls through to returning the original unchanged. Compressors that can't shrink decline.
- **Lossy-by-default requires CCR**: Without the CCR cache, information-dropping compressors pass through untouched - only faithful reformats (JSON tables, HTML extraction, RLE log collapse) apply without a recovery path.
- **Three agent profiles**: `Full` (default, everything on), `Light` (coding agents - only lossless reductions), `Off` (bypass).
- **Token-juice decoupling**: The engine is a portable Rust crate. OpenHuman configures it via `install_config()` at startup with limits, disk path, and toggles.
- **Per-block retrievability**: Beyond the full-original footer, each omitted gap in logs/diffs/search/code can carry its own marker for block-level recovery without fetching the whole payload.
