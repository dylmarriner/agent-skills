# Serving a safetensors-only abliterated model as GGUF (Qwen3-VL-30B-A3B, session 2026-09-03)

Goal: run `huihui-ai/Huihui-Qwen3-VL-30B-A3B-Instruct-abliterated` on a rented GPU via llama.cpp.

## The model repo is safetensors-ONLY (no GGUF)

HF tags: `transformers, safetensors, qwen3_vl_moe, image-text-to-text, abliterated`. No GGUF, no mmproj in the repo. abliteration touched only the TEXT weights, not the vision tower (per README).

## Finding a GGUF quant of the SAME model (HF search API)

```bash
curl -s "https://huggingface.co/api/models?search=Huihui-Qwen3-VL-30B-A3B-Instruct-abliterated-GGUF" | python3 -c "import sys,json;[print(m['id']) for m in json.load(sys.stdin)]"
```
Quant repos that exist for this exact model: **mradermacher** (full ladder + mmproj — preferred), noctrex, Tipur, McG-221 (Q8_0).

### Real file sizes: use `?blobs=true` (HEAD content-length is absent on the HF redirect)

```bash
curl -s "https://huggingface.co/api/models/<owner>/<repo>?blobs=true" | python3 -c "import sys,json; d=json.load(sys.stdin); [print(s['rfilename'], round(s.get('size',0)/2**30,2),'GB') for s in d['siblings']]"
```

mradermacher ladder for the 30B-A3B VL MoE: **Q4_K_M 17.28 GB** (+mmproj-Q8_0 0.66 GB), Q4_K_S 16.26, Q5_K_M 20.23, Q6_K 23.37, Q8_0 30.25. mmproj is REQUIRED for vision (`--mmproj <file>`); Q4_K_M fits a 32 GB Blackwell cleanly, is tight on a 24 GB 4090 once VL image KV is added.

## Blackwell (RTX 5090) provisioning differs from the Ada (L40S/4090) recipe

- 5090 = GB202, **compute capability sm_120**. llama.cpp cmake MUST use `-DCMAKE_CUDA_ARCHITECTURES=120`, NOT the 89 used for Ada. Building with 89 on a 5090 fails.
- sm_120 needs nvcc from **CUDA ≥ 12.8**. Base image used: `nvidia/cuda:12.8.0-cudnn-devel-ubuntu22.04`. It is a LARGE multi-GB image — instance sits in `loading` (status_msg `Pulling fs layer`) for ~10+ min before SSH works. Billing starts at creation, not at running.
- llama.cpp MASTER supports the `qwen3_vl_moe` arch; no patch needed.
- Provision script mirrors the Ada one but swaps the arch flag and image tag.

## Instance + SSH timing

Instance 49647465: RTX 5090, `ssh5.vast.ai:17464`, ~$0.335/h total (US). SSH `root@ssh5.vast.ai -p <port>` with `~/.ssh/vast_id_rsa`.

- **SSH returns `Permission denied (publickey)` until `actual_status` == `running`.** While `loading`, vast has not injected the account key into the container. Don't hammer SSH — poll status to running first (watch a background script that reports ready).
- vast proxy TCP port is open before the key works; that's not a signal to retry.

## Verified quant sources

- mradermacher/Huihui-Qwen3-VL-30B-A3B-Instruct-abliterated-GGUF (full ladder + mmproj-Q8_0 / mmproj-f16)

## Fast HF download: anonymous is throttled PER-CONNECTION → use aria2 -x16

HF rate-limits anonymous downloads **per TCP connection**. A plain single `curl -sL` on a fresh vast IP crawls at ~0.7 MB/s (after a few hundred MB it can collapse to ~4 KB/s) — an 18 GB pull would take hours. Host bandwidth itself is fine (~54 MB/s to cachefly) — it is HF throttling, not the box.

Fix: parallel ranged download via **aria2** (`apt-get install -y aria2`):

```bash
aria2c -x16 -s16 -c -d /root/models -o <model>.gguf "https://huggingface.co/<owner>/<repo>/resolve/main/<file>.gguf"
```

16 parallel connections aggregate to **~68 MB/s** (18 GB in ~4 min). `-c` resumes partials. Dead ends tried: hf-mirror.com (0 B/s), and lin's own HF was also throttled — download on the GPU box with aria2, not via a local curl-then-scp path. Kill the slow single curl first (`pkill -f "curl -sL"`).

## A stalled image pull = pivot host + leaner image, don't wait it out

The `cudnn-devel` image is multi-GB; on a slow-disk host the pull sat **16+ min on the SAME `Pulling fs layer`** (status_msg never advanced) while billing ran. Unchanging status_msg = stalled pull, not progress. Fix: destroy, re-create on a fresh host with the leaner **`nvidia/cuda:12.8.0-devel-ubuntu22.04`** (no cudnn — llama.cpp does not need it) → boots to SSH in **~40 s**. A 256-core / ~1 TB RAM host makes the llama.cpp build fly (cmake configure + compile minutes, not tens of minutes).

## llama.cpp 0.3.0 new build layout (NOT a broken build)

Current master links **thin launchers**: `build/bin/llama-server` is only **~17 KB** and `--version` reports `0.3.0-dev (build 1)`. The real code lives in sibling `libllama-server-impl.so` (~7 MB) + `libggml-cuda.so` (~62 MB CUDA kernels). Do NOT judge the build by `llama-server`'s file size or version string — a small launcher over impl libs is NORMAL now. Verify instead: `ls src/models/` for the arch file (`qwen3vlmoe.cpp` present = Qwen3-VL MoE supported) and `git log -1` for commit recency.

## Proving a VL model actually sees (images and real PDFs)

- **Quick vision probe**: POST a small base64 PNG data-URI + "what color" → a correct one-word answer proves `--mmproj` loaded and image input works end-to-end.
- **Real-document (PDF) test**: render a page to PNG (`pdftoppm -png -r 150 -f 1 -l 1 in.pdf /tmp/page`) and send the PNG. A good VL model (Qwen3-VL is top-tier for documents) transcribes dense business content — line items, part numbers, per-line and grand totals — accurately. ~2 K tokens/page at 150 dpi means page-image workloads need far less context than a 1M text stream, so context is a non-issue for PDF work (don't size a box around it).
- **ARG_MAX gotcha**: base64 of a ~300 KB page image is ~400 KB → inlining it in `curl -d '{...}'` shell argv fails `OSError: [Errno 7] Argument list too long`. POST the JSON body from Python (`urllib.request` / requests, data-URI inside the payload), never via curl argv.
- **VRAM / ctx for this model**: 18 GB weights + mmproj + q8 KV fits **128K ctx on 32 GB** (~26 GB used). Native `max_position_embeddings` is 262144 but full-size won't fit 32 GB with the 18 GB model — ~200K is the practical ceiling.
