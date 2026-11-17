# OpenCode v1.14.43 — Google Gemini Model Catalog

Captured from `opencode models` on 2026-05-10.

## Full Google Model List

```
google/gemini-1.5-flash
google/gemini-1.5-flash-8b
google/gemini-1.5-pro
google/gemini-2.0-flash
google/gemini-2.0-flash-lite
google/gemini-2.5-flash
google/gemini-2.5-flash-image
google/gemini-2.5-flash-image-preview
google/gemini-2.5-flash-lite
google/gemini-2.5-flash-lite-preview-06-17
google/gemini-2.5-flash-lite-preview-09-2025
google/gemini-2.5-flash-preview-04-17
google/gemini-2.5-flash-preview-05-20
google/gemini-2.5-flash-preview-09-2025
google/gemini-2.5-flash-preview-tts
google/gemini-2.5-pro
google/gemini-2.5-pro-preview-05-06
google/gemini-2.5-pro-preview-06-05
google/gemini-2.5-pro-preview-tts
google/gemini-3-flash-preview
google/gemini-3-pro-preview
google/gemini-3.1-flash-image-preview
google/gemini-3.1-flash-lite
google/gemini-3.1-flash-lite-preview
google/gemini-3.1-pro-preview
google/gemini-3.1-pro-preview-customtools
google/gemini-embedding-001
google/gemini-flash-latest
google/gemini-flash-lite-latest
google/gemini-live-2.5-flash
```

## Key Observations

- **No plain `gemini-3.1-flash`** exists in OpenCode's catalog. The flash variants are:
  - `google/gemini-3.1-flash-lite` (fast, cheap)
  - `google/gemini-3.1-flash-image-preview` (multimodal)
  - `google/gemini-3.1-flash-lite-preview`
- **Best 3.1 Pro model:** `google/gemini-3.1-pro-preview`
- **Latest Gemini 3 (non-3.1):** `google/gemini-3-flash-preview`, `google/gemini-3-pro-preview`
- **Workhorse models for reliability:** `google/gemini-2.5-pro`, `google/gemini-2.5-flash`

## Troubleshooting

- If `opencode models` shows fewer Google models than listed above, the API key may have restricted access
- All models listed above returned by `opencode models` on a machine with valid Gemini API credentials
- To refresh the model list: `opencode models` (re-queries the provider API)
