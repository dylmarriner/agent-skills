# Dolphin-Yi-34B Heretic on RunPod (June 2026)

Session transcript: deploying `richardyoung/dolphin-yi-34b-heretic` (Yi-1.5-34B) on A40 via llama.cpp.

## What Actually Happened

### The Image Problem
`runpod/pytorch:2.4.0-py3.11-cuda12.4.0-devel-ubuntu22.04` no longer exists on Docker Hub. The RunPod MCP API accepted the create_pod request (no validation), but Docker daemon returned `IMAGE_NOT_FOUND` at startup. Pods transitioned RUNNING→EXITED in 1-5 seconds.

**Fix:** Use `runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04` (validated in RunPod docs) or `runpod/pytorch:latest` (resolves to a valid tag, but may be Ubuntu 24.04).

### The Port Health Check
RunPod kills any pod that exposes `8000/http` but doesn't serve on it within ~2-3 seconds. Even with a valid image, `dockerStartCmd` that runs `pip install + model download + server start` gets killed before the server starts. The same `sleep infinity` pod survives because there's no HTTP port check on port 22.

**Workaround A** (didn't work reliably with the MCP API): Start `python3 -m http.server 8000 --bind 0.0.0.0 &>/dev/null &` as the first command, then run setup in same process.

**Workaround B** (worked): Create pod WITHOUT port 8000, just `22/tcp`, with `dockerStartCmd: ["python3","-c","import time; time.sleep(999999)"]`. Pod stays alive. SSH in with matching SSH key, run setup interactively or via SCP + SSH.

### The dockerStartCmd Drop
The MCP `create_pod` tool accepted the request with `dockerStartCmd` set, but the response didn't include it. The pod ran the default `start.sh` → `sleep infinity` instead of the custom command. This was invisible until SSH-ing in and seeing no pip/python processes.

### What Worked
1. `runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04` image pulled successfully
2. SSH via terminal tool with matching `id_ed25519` key
3. `pip install huggingface-hub` worked, `hf_hub_download` downloaded the 20.8GB GGUF
4. `pip install llama-cpp-python` compiled CUDA kernels in ~3-5 min
5. A40 (48GB) with enough headroom for Q4_K_M + 32K context

## Current State
- Pod: `2k7hs1uiiyp9ix` (stopped)
- Image: `runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04`
- Model: `mradermacher/dolphin-2.9.1-yi-1.5-34b-heretic-GGUF` → `dolphin-2.9.1-yi-1.5-34b-heretic.Q4_K_M.gguf`
- Model downloaded to /workspace (not yet confirmed — process was still running)
- llama-cpp-python CUDA compile was in progress
