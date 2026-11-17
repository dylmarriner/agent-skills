# Pre-Abliterated Models (30B+ Tier)

Ready-made uncensored models you can download and run directly — skip running OBLITERATUS yourself if someone's already done it well.

## Top Pick (Mid-2026)

### Qwen3.5/3.6-35B-A3B Aggressive (HauhauCS)
- **Size:** 35B MoE (3B active per token) — runs on 24 GB VRAM at Q4_K_M
- **HuggingFace:** `HauhauCS/Qwen3.5-35B-A3B-Uncensored-HauhauCS-Aggressive`
- **Ollama:** `fredrezones55/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive`
- **Context:** 262K (Qwen3.6)
- **Method:** Advanced orthogonal vector removal, aggressive variant
- **Claim:** Zero refusals, no personality changes, lossless uncensoring
- **Notes:** Multimodal (vision). Most aggressively uncensored model in the 30B+ tier as of June 2026.

## Close Seconds

### Gemma 4 31B Heretic (Stabhappy)
- **Size:** 31B dense — ~17 GB at Q4_K_M
- **Model:** `Stabhappy/gemma-4-31B-it-heretic-Gguf`
- **Method:** HERETIC abliteration method
- **Notes:** Native vision, tool calling. Very clean refusal removal, minimal coherence degradation.

### Gemma 4 26B MoE HERETIC
- **Size:** 26B brain with 4B active — MoE-fast inference
- **Notes:** Lower VRAM peak than the 31B dense version.

### Hermes 3 70B (Nous Research)
- **Size:** 70B dense — ~40 GB at Q4_K_M (needs 48 GB VRAM)
- **Method:** Full finetune on uncensored data (not abliteration)
- **Notes:** Battle-tested production uncensored model. Frontier-tier quality.

### GLM 5.1 Heretic (huihui-ai)
- **Size:** 754B MoE — 236 GB at IQ2_M
- **Model:** `huihui-ai/Huihui-GLM-5.1-abliterated-GGUF`
- **Notes:** Not consumer hardware — Mac Studio M4 Ultra territory. Strongest open abliterated model by raw capability.

## How to Pull

```bash
# Ollama (simplest)
ollama pull fredrezones55/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive

# HuggingFace (for llama.cpp / vLLM)
huggingface-cli download HauhauCS/Qwen3.5-35B-A3B-Uncensored-HauhauCS-Aggressive

# Locally Uncensored app
# Open Model Manager > Discover > Text > UNCENSORED filter tab
# 34 curated abliterated GGUFs available with one-click download
```

## Hardware Guide

| VRAM | Best Pick |
|:-----|:----------|
| 16 GB | Gemma 4 31B Heretic Q4_K_M |
| 24 GB (3090/4090) | Qwen3.5-35B-A3B Aggressive Q4_K_M |
| 48 GB+ | Hermes 3 70B Q4_K_M |

## Source
- Research from June 2026 — most-abliterated-30B+ query via web search
- Confirmed via HuggingFace hub, Ollama community, and Reddit r/LocalLLaMA
