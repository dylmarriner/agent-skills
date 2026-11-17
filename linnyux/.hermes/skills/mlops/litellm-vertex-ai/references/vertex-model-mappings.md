# Model Name Mapping: ai-system-495310

Discovered during a session on 2026-05-13. Verified working mappings through LiteLLM proxy.

## Vertex AI Model Availability

| Alias | Vertex AI backend | Location | Status |
|---|---|---|---|
| `gemini-3.1-pro-preview` | `vertex_ai/gemini-2.5-pro` | us-central1 | Works |
| `gemini-3.1-flash-lite` | `vertex_ai/gemini-3.1-flash-lite` | **global** | Works |
| `gemini-3.1-flash-lite-preview` | `vertex_ai/gemini-3.1-flash-lite-preview` | **global** | Works |
| `gemini-2.5-flash-lite` | `vertex_ai/gemini-2.5-flash-lite` | us-central1 | Works |
| `gemini-2.5-pro` | `vertex_ai/gemini-2.5-pro` | us-central1 | Works |
| `gemini-2.5-flash` | `vertex_ai/gemini-2.5-flash` | us-central1 | Works |
| `gemini-3.1-flash-image-preview` | `vertex_ai/gemini-2.5-flash-image` | us-central1 | Works |

## Key Finding: Global vs Regional Endpoint

Gemini 3.x models (3.1-flash-lite, 3.1-pro-preview, 3-flash-preview) are **only available on the global endpoint**. Using `us-central1` returns:

> Publisher Model `projects/{project}/locations/us-central1/publishers/google/models/gemini-3.1-flash-lite` was not found or your project does not have access to it.

The correct URL format for direct testing:
```
https://aiplatform.googleapis.com/v1/projects/{project}/locations/global/publishers/google/models/gemini-3.1-flash-lite:generateContent
```

## Direct Verification Commands

```bash
# Regional endpoint (Gemini 2.x)
TOKEN=$(gcloud auth print-access-token)
curl -s -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"contents":[{"role":"user","parts":[{"text":"say ok"}]}]}' \
  "https://us-central1-aiplatform.googleapis.com/v1/projects/ai-system-495310/locations/us-central1/publishers/google/models/gemini-2.5-flash:generateContent"

# Global endpoint (Gemini 3.x)
curl -s -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"contents":[{"role":"user","parts":[{"text":"say ok"}]}]}' \
  "https://aiplatform.googleapis.com/v1/projects/ai-system-495310/locations/global/publishers/google/models/gemini-3.1-flash-lite:generateContent"
```

## Service Account Config

- Service account: `dkmarriner-534@ai-system-495310.iam.gserviceaccount.com`
- Key path: `~/.config/gcloud/legacy_credentials/.../adc.json`
- Project: `ai-system-495310`
- LiteLLM master_key: `sk-litellm-local`
- LiteLLM port: `8899`
