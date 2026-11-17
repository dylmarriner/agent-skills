# Using Hugging Face Models for Free

## Model Discovery Flow

1. **Open the model page** — e.g. `https://huggingface.co/USER/MODEL`
2. **Check the "Spaces using this model" section** — a grid of community-created Spaces appears below the model card
3. **Open individual Spaces** and look for:
   - The "Restart this Space" button (sleeping Spaces need waking)
   - A running Gradio/Streamlit interface
   - Whether it requires "Sign in with Hugging Face" (most do — HF login is free)

## Space Authentication Reality

Most community Spaces use Gradio's `gr.LoginButton` / `gr.on` with HF OAuth. This means:
- You **must** have a Hugging Face account and be logged in
- The agent browser can't bypass this — the Space app iframe enforces it
- Exception: some Spaces are public-only (no auth), but they're rare and often broken

## Inference API (if you have a HF token)

Once logged in, you can call models directly via the HF Inference API:

```bash
curl https://api-inference.huggingface.co/models/USER/MODEL \
  -H "Authorization: Bearer $HF_TOKEN" \
  -d '{"inputs": "Hello world"}'
```

Not all models are available on the free Inference API tier — check the model page for
"Inference API (serverless)" or "Inference Providers" sections.

## xortron.tech pattern

Some model authors provide their own web interface (e.g. xortron.tech for Xortron
models). These are often parody/demo sites with fictional OS interfaces — the chat
may or may not actually run the model. Worth a quick test but not reliable.

## Local Fallback (requires hardware)

For 7B-24B models, GGUF quants can run on consumer GPUs or even CPU via llama.cpp:

```bash
# Check for existing quants
# https://huggingface.co/models?other=base_model:quantized:USER/MODEL

# Download and run with llama.cpp
huggingface-cli download USER/MODEL --local-dir ./model
# Then use llama.cpp or Ollama to serve it
```

## Quick Checklist

- [ ] Model has active Spaces? → Try them (need HF login)
- [ ] Model has Inference API? → curl with HF_TOKEN
- [ ] Model has public web UI? → Try it (xortron.tech pattern)
- [ ] Model has GGUF quants? → Run locally via Ollama/llama.cpp
