# Selecting a local vision model for DOCUMENT viewing/editing (not general OCR)

Validated while swapping the vast 5090 doc-viewer serve (30B Q4 → 8B Q8). Research current as of Sep 2026.

## The workload matters
- User runs a vision serve specifically to VIEW/read documents (invoices, forms, scanned PDFs, receipts) and edit/reason about them. That needs a **general instruct VLM**, NOT a pure OCR/parser extractor.
- Pure extractors (GutenOCR-7B, Infinity-Parser-7B, NuMarkdown-8B, Granite-Docling-258M) convert doc → markdown/JSON with bboxes but CANNOT reason, chat, or emit an edited document. Wrong tool when the ask includes "edit" or Q&A.

## Current pick: Qwen3-VL-8B-Instruct-abliterated (huihui) @ Q8_0
- DocVQA 96.1 (best sub-10B doc/OCR score; beats every Gemma 3 size incl 27B). 4B sibling = 95.3 but weaker general reasoning/edit.
- Native 256K ctx (Qwen3-VL family), ~6 GB total at Q4 (5.1 GB + 0.9 mmproj), 8.7 GB + 0.75 mmproj at Q8_0.
- General instruct VLM → does reading AND the editing half (read → rewrite → emit edited doc).
- Same Qwen3-VL arch as the 30B → existing llama.cpp build runs it, no rebuild.

## HF repo traps (verify before choosing a download)
- **`...-FP8` huihui repos are NOT servable models.** They ship a single `model.safetensors` (no config.json, no tokenizer, no mmproj) built as a drop-in text_encoder for `ideogram-ai/ideogram-4-fp8`. llama-server loads GGUF only, and even the file alone can't run standalone. Read the repo siblings + README before trusting a URL.
- Servable equivalent of the same huihui VL-8B abliterated weights: `mradermacher/Huihui-Qwen3-VL-8B-Instruct-abliterated-GGUF` (Q8_0 ≈ FP8-grade near-lossless, or Q4_K_M for speed). Has `.Q8_0.gguf` + `.mmproj-Q8_0.gguf`.
- Always check `GET /api/models/<repo>` siblings (not just the tree page, which can render empty) to see exactly what's shipped.

## VRAM/ctx reality on a 32 GB single 5090
- Weights + KV both count. 8B Q8_0 (~8.9 GB) + q8 KV for 262K ≈ 30.2 GB used → fits, ~2 GB headroom. Good: more ctx + freed VRAM vs a 30B at 131K.
- 30B GQA at 131K q8 was 26.3/32 GB (~6 GB headroom) — that is the 30B single-card wall; do not promise 256K+ on a 30B GQA on 32 GB.
- Keep the SAME `--alias` (e.g. `qwen3-vl-30b-a3b-ablit`) on the swapped model so every client is unchanged; verify via `/v1/models` shows the alias + a real completion.

## Actually reading a document the USER sends (the whole point of the serve)

- **`read_file` CANNOT read a scanned / image-based PDF.** Hermes `read_file` does TEXT extraction only; a scanned PDF has a 0-char text layer, so it errors `document extraction failed — UnsupportedError` and the agent falls into an infinite retry loop (see SKILL.md runaway-client pitfall). This is not a model problem — it's a tool limitation.
- **Correct pipeline:** pull the PDF → `pdftoppm -png -r 200 <doc>.pdf page` (or PyMuPDF) → downscale each page to ~1000 px wide (`PIL LANCZOS`; a 200-DPI 1653×2337 render blows up vision-token count and slows/destabilizes generation) → send each PNG as an `image_url` data-URI through the normal chat-completions path.
- A 1000-px page transcribes cleanly in ~8 s at 1500 max_tokens, temperature 0 — full text/numbers/tables preserved.
- User's doc viewer exists to read a specific Telegram-sent PDF. If the agent can't route PDF pages to the VL model, the whole serve is useless to them — verify this path end-to-end on a real page image, not just a synthetic invoice.

## Measured numbers from the swap
- 8B Q8_0 at 262K: decode ~155 tok/s; ~945 tok/s prompt eval; model loaded in ~5.6 s; VRAM 30.2 GB idle (weights + reserved 262K q8 KV).
- Prior 30B-A3B Q4 at 131K: decode ~274 tok/s (MoE active-params advantage), 26.3/32 GB.
- Vision end-to-end verified by generating a text PNG (PIL on lin), base64-ing it, sending as `image_url` data URI through the full Bifrost path — model read the invoice fields correctly.
