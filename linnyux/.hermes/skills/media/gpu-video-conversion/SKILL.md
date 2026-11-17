---
name: gpu-video-conversion
description: Debug, verify, and optimize GPU-accelerated video conversion pipelines, especially VR-to-flat workflows using ffmpeg, VAAPI, NVENC, or QSV.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [video, ffmpeg, gpu, vaapi, nvenc, qsv, conversion, verification]
    related_skills: [systematic-debugging, video-production, performance-engineer]
---

# GPU Video Conversion

Use this skill when a task involves downloading, transcoding, or converting video with GPU acceleration, especially when the user asks to make a converter work on their hardware.

## What this skill covers
- Choosing the right encoder path for the machine: VAAPI on AMD/Radeon, NVENC on NVIDIA, QSV on Intel.
- Verifying that the GPU path actually exists before changing code.
- Keeping GPU conversion enabled by default when the runtime supports it.
- Validating the output with file size and `ffprobe`, not just command exit code.
- Treating a timeout as inconclusive if a usable output file already exists.

## Workflow

0. **Check for orphaned processes from prior sessions first.**
   Before starting a new conversion, look for leftover ffmpeg instances that may be orphaned from a prior Hermes session:
   ```bash
   pgrep -a -f "ffmpeg.*vr2normal\|ffmpeg.*input.mp4\|ffmpeg.*hequirect"
   ```
   Orphaned ffmpeg processes from dead sessions continue running silently, writing to deleted temp files (ghost I/O), consuming 200+ MB RAM each, and their `ffprobe` output is unreadable because `/proc/PID/fd/` shows `(deleted)` for all file handles. Kill them:
   ```bash
   pkill -f "ffmpeg.*vr2normal" 2>/dev/null
   ```
   Also check for leftover Python wrapper processes:
   ```bash
   pgrep -a -f "vr2normal convert\|videosnap dl.*vr"
   ```
   This prevents the temp-dir race problem where a previous session's ffmpeg survives but its temp directory has been cleaned up.

1. **Inspect the runtime before editing anything.
   - `vainfo` for VAAPI capability
   - `ffmpeg -hide_banner -encoders` for `h264_vaapi`, `h264_nvenc`, or `h264_qsv`
   - `nvidia-smi` only if NVIDIA is expected

2. Map hardware to encoder.
   - AMD/Radeon: VAAPI, usually `h264_vaapi`
   - NVIDIA: `h264_nvenc`
   - Intel: `h264_qsv`

3. Keep the GPU path enabled by default if detection succeeds.
   - Do not hard-disable `use_gpu` in the CLI just because the command path is ambiguous.
   - Prefer a runtime capability check over a vendor name check.

4. Verify the result, not the hope.
   - Check that the output file exists
   - Check non-zero file size
   - Run `ffprobe` to confirm codec, duration, dimensions, and stream count

5. If a command times out, inspect the artifact first.
   - A timeout can still leave behind a valid partial or completed MP4.
   - Only retry after checking the output file and probing it.

## Pitfalls
- `check` commands can be misleading if they only look for NVIDIA.
- `h264_vaapi` support in ffmpeg is more relevant than `nvidia-smi` on AMD machines.
- Some VR videos report as equirectangular even if the file name says otherwise; rely on probing.
- GPU-accelerated encode can succeed even when the wrapper process times out.
- **SBS vs equirect confusion**: Adult VR at 1440×720 (2:1 ratio) is almost always **SBS 3D** (two 720×720 eye frames side by side), NOT 360° equirectangular. Treating SBS as equirect produces a massive black rectangle/void in the center of the output.
- **SBS detection** in code: for 2:1 ratio videos, probe the **center row** (not full-height column). A near-black seam pixel at w/2 that's <30% brightness of the surrounding 10px = SBS seam. Genuine equirect has non-dark pixels crossing the center.
- **SBS→flat conversion**: crop one eye first, *then* apply `v360=hequirect:flat:h_fov=120:v_fov=80` on the cropped eye. Never apply v360 directly on the combined SBS frame.
- **VR180 vs 360**: Most adult VR at ≤1440p is VR180 (half-equirect/hequirect), not 360° equirect. Use `hequirect` in v360, not `equirect`.
- For the v360 filter, the `hequirect` input format treats the frame as a 180°×180° dome, while `equirect` expects a 360°×180° full sphere.
- **Temp dir race in CLI conversions**: The `cmd_convert` function in `cli_impl.py` wraps the pipeline in `with tempfile.TemporaryDirectory(prefix="vr2normal_")`. If the Python process is terminated (session boundary, timeout, kill) while ffmpeg is still running, the temp dir is cleaned up immediately. ffmpeg survives as an orphan writing to ghost (deleted) files — all work is lost. Fix: ensure the conversion runs to completion in a single foreground process, or use a persistent work directory outside `/tmp/`. Never rely on a background process that spans Hermes sessions for VR conversions — the parent process termination between sessions orphans ffmpeg.
- **AV1 decode bottleneck**: Source videos in AV1 codec are extremely CPU-intensive to decode. Even with VAAPI GPU encoding, the decode bottleneck limits throughput. Expect roughly 30%/600s (~2000s total) for a 36-minute AV1 video. Consider re-encoding the source to h264 first if repeated conversions are needed, or accept the long runtime.
- **AV1 avoidance during download** (IMPORTANT — the fix, not just the symptom): The best solution to the AV1 bottleneck is to **never download AV1 in the first place**. yt-dlp considers AV1 "best" because of compression efficiency, but on machines without hardware AV1 decode (i7-6700, RX 580, any pre-2020 hardware) this is catastrophically slow. Use yt-dlp format filtering to exclude AV1:
  ```
  bestvideo[height<=720][vcodec!=av1]+bestaudio/best[height<=720][vcodec!=av1]/best
  ```
  This grabs H.264 (or H.265/VP9 if available) instead. H.264 can use VAAPI hardware decode on the RX 580, making the entire pipeline GPU-bound rather than CPU-bound. The i7-6700 + RX 580 combination saw ~12× realtime for AV1→flat dropping to ~2× for H.264→flat.

  **Implementation in download code:**
  ```python
  height_limit = quality.replace("p", "")  # "720p" → 720
  fmt = (f"bestvideo[height<={height_limit}][vcodec!=av1]"
         f"+bestaudio/best[height<={height_limit}][vcodec!=av1]/best")
  subprocess.run(["yt-dlp", "-f", fmt, "-o", dest, url], timeout=600)
  ```

  **Pitfall: eporner "unknown" codec — `[vcodec!=av1]` is unreliable here.** On eporner, `yt-dlp -F` shows the non-AV1 format ID with vcodec="unknown" and the AV1 format ID with vcodec="av1". The `[vcodec!=av1]` filter should exclude the AV1 format, but in practice yt-dlp may still negotiate and serve the AV1 variant (681 MiB vs expected 1.33 GiB for H.264 1080p 36-min video). **Fix: use explicit format IDs for known sites:** `fmt = f"{height_limit}p@60fps_HD+bestaudio/best"`. This bypasses the `bestvideo` selector's negotiation ambiguity.

  **Double-check what you'll get:**
  ```bash
  yt-dlp -f "bestvideo[height<=720][vcodec!=av1]+bestaudio/best[height<=720][vcodec!=av1]/best" \
    --print "format: %(format_id)s %(vcodec)s" URL
  ```

  Also patch the `_download_video` function in any converter to try yt-dlp with this format first, falling back to the default downloader (videosnap, etc.) if yt-dlp is unavailable. See session 2026-07-12 for the patch applied to vr2normal's `backend/main.py`.

- **VAAPI hardware decode (hwaccel) doesn't help for v360 workflows.** On i7-6700 + RX 580 with H.264 input:
  - Pure software decode + v360 + VAAPI encode: **87 fps (1.47x)** — fastest
  - VAAPI hwdecode + hwdownload → v360 → VAAPI encode: 75 fps (1.27x) — slower due to GPU→CPU transfer overhead
  - The `hwdownload` step that moves frames from GPU surfaces to CPU memory for the v360 filter cancels any decode speedup
  - **Recommendation:** Don't add `-hwaccel vaapi` to v360 conversion pipelines. The v360 filter needs CPU-accessible frames, so the extra transfer kills performance.

- **Parallel segments make conversion SLOWER.** Splitting the video into 3 segments and running 3 ffmpeg instances in parallel on the same GPU:
  - 3 parallel processes: 29 fps (0.5x) each, ~3x wall time
  - 1 process: 87 fps (1.47x), ~1x wall time
  - **Cause:** The VAAPI encoder (`/dev/dri/renderD128`) serializes encode jobs on the RX 580. Multiple processes compete for the same hardware encoder, dropping everyone's throughput below single-process speed.
  - **Recommendation:** Never split VR conversion across parallel ffmpeg instances on a single GPU. The encoder is a serial resource.

- **`-threads` and `-filter_threads` don't help v360 slice threading.** Despite v360 advertising "slice threading supported", additional threads beyond the main decode thread are barely utilized (0.2-0.3% each vs main thread at 29%). The v360 filter is fundamentally single-thread compute on i7-class CPUs regardless of thread count.

- **Vulkan GPU shader pipeline (vr2normal two-stage approach):** The vr2normal project has a GPU projection path that runs the VR180/equirect to flat transform on GPU shader cores via libplacebo + GLSL shaders, instead of the CPU v360 filter. Direct VAAPI-Vulkan interop does not work on Polaris10 (RX 580), so it runs two ffmpeg processes connected by a raw yuv420p pipe:

  Stage 1 (decode + projection): `ffmpeg -init_hw_device vulkan=vk:0 -filter_hw_device vk -vaapi_device /dev/dri/renderD128 -hwaccel vaapi -hwaccel_output_format vaapi -i input.mp4 -vf "hwdownload,format=nv12,hwupload,libplacebo=w=1920:h=1080:upscaler=none:downscaler=none:peak_detect=false:custom_shader_path=hequirect_to_flat.glsl,hwdownload,format=yuv420p" -f rawvideo -pix_fmt yuv420p pipe:1`

  Stage 2 (encode): `ffmpeg -vaapi_device /dev/dri/renderD128 -f rawvideo -pix_fmt yuv420p -s 1920x1080 -r fps -i pipe:0 -i input.mp4 -map 0:v -map 1:a? -vf "format=nv12,hwupload" -c:v h264_vaapi ...`

  Raw yuv420p pipe avoids a 145GB FFV1 intermediate (disk-filling) or a CPU-intensive libx264 intermediate (300% CPU). For SBS VR180, the eye crop is handled in the GLSL shader (samples left half). Enabled by `VR2NORMAL_GPU_PROJECTION=1` (default). Shaders at `backend/shaders/hequirect_to_flat.glsl` and `equirect_to_flat.glsl`. Known issue: piped pipeline can receive SIGTERM (exit 143) during long conversions -- the RuntimeError propagates through `_convert_vr()` and the `TemporaryDirectory` context cleanup kills the temp dir.

- **User preference: always use the existing pipeline.** On Dylan's machines, when `vr2normal convert` exists, USE IT. Do not bypass it with hand-written ffmpeg commands, even if you know the exact filter chain. The pipeline encodes SBS vs equirect auto-detection, VAAPI device discovery, Vulkan GPU projection when available, and proper temp-dir management. The user explicitly corrected this pattern: "i killed it so it runs through the actual pipeline". Hand-writing ffmpeg misses all of these; any filter-chain adjustments belong in the pipeline code, not in one-off commands.

- **User preference: use vr2normal SERVE mode for batch VR queueing, not parallel background processes.** When you have MULTIPLE VR videos to convert, DO NOT launch `./vr2normal convert` as separate background processes. The user explicitly corrected this: "start every vr video again and queue it to this tool". Parallel background processes all launch their own ffmpeg instances simultaneously, overloading the VAAPI encoder and Vulkan shader stack. Instead:

  1. Start the API server: `cd /media/kubuntux/DEVELOPMENT1/vr2normal && ./vr2normal serve`
  2. Queue each URL via POST /convert:
     ```
     curl -s -X POST http://localhost:8000/convert \
       -H "Content-Type: application/json" \
       -d '{"video_url": "<URL>", "quality": "1080"}'
     ```
  3. Each POST returns a task_id. Poll progress: `curl -s http://localhost:8000/status/<task_id>`

  The server manages concurrency via ThreadPoolExecutor (internal queue), sequencing the GPU pipeline properly and avoiding temp-dir races.

  One-off conversions are fine with `./vr2normal convert`. Batch jobs (3+ videos) MUST go through the API server.

- **Puppeteer browser bypass service must be running for blocked sites.** Before running batch downloads involving sites like eporner, redtube, or beeg, start the Puppeteer service on port 3001: `cd /media/kubuntux/DEVELOPMENT1/video-downloader/backend/node_service && NODE_PATH=$(pwd)/node_modules node index.js`. The service provides cookie/header extraction via POST /extract-cookies and POST /extract-page. The browser_bypass.py wrapper is in the same directory. Without this service, batch scripts report "Browser bypass unavailable" on every blocked URL.

- **Expected performance ceiling on i7-6700 + RX 580 for VR conversion:**
  - Source: 1440×720 H.264 60fps, 2209s duration (36 min)
  - Output: 1920×1080 flat via v360=hequirect
  - Pipeline: CPU decode → crop → v360 → scale → hwupload → h264_vaapi
  - Performance: ~87 fps, ~1.47x real-time, ~1500s (~25 min) wall time
  - GPU utilization: 4-6% (h264_vaapi encoder waiting for CPU v360 frames)
  - **This is a hard ceiling** — the v360 spherical transform is pure CPU math that no GPU on this system can accelerate. Accept the ~25 min for 36-min videos.

## Verification
Use the narrowest proof possible:

```bash
ffmpeg -hide_banner -encoders | grep -E 'h264_vaapi|h264_nvenc|h264_qsv'
vainfo
ffprobe -v error -show_streams -show_format output.mp4
```

## VR format detection (SBS vs equirect vs VR180)

When converting VR-to-flat, the source format must be identified correctly or the output is garbage. Adult VR content on tube sites (eporner, etc.) at 1440×720 (2:1 ratio) is almost always **SBS 3D VR** — two square 720×720 eye frames side by side — NOT 360° equirectangular.

### Detection rules
1. **Aspect ratio ≥ 2.5**: definitely SBS (two ~16:9 frames side by side)
2. **Aspect ratio 1.8–2.2**: could be equirect 360°, VR180 (hequirect), or SBS — probe the content
3. **Aspect ratio < 1.8 or > 0.5**: flat (monoscopic)

### SBS seam detection (for 2:1 ratio videos)
Do NOT extract the full-height center column — the top and bottom edges of the frame often have content even at the seam, raising the average and causing false negatives. Instead, sample the **center row** (1px tall, full width) and compare the seam pixel to surrounding pixels:

```bash
ffmpeg -ss 30 -i input.mp4 -vframes 1 -vf "crop={w}:1:0:{h//2},format=gray" -f rawvideo -
```

**Detection logic:**
1. Extract the center row as raw grayscale
2. Check the seam pixel at `x = w//2`
3. Compare brightness to the 10px on each side
4. If the seam pixel is **<30%** brightness of the surrounding area → SBS
5. **Fallback**: if the left and right halves of the row have similar average brightness (within 1.5×), it's also likely SBS — true equirect has very different L/R content

```python
cx = w // 2
seam = row[cx]
left = sum(row[cx-10:cx]) / 10
right = sum(row[cx+1:cx+11]) / 10
surround = (left + right) / 2 or 1
ratio = seam / surround
if ratio < 0.3:
    return True  # SBS seam detected

# Fallback: L/R brightness similarity
left_avg = sum(row[:mid]) / mid
right_avg = sum(row[mid:]) / mid
if left_avg > 30 and right_avg > 30:
    if max(left_avg, right_avg) / min(left_avg, right_avg) < 1.5:
        return True  # similar brightness = SBS
```

**Pitfalls:**
- `seek=30s` overshoots clips shorter than ~30s (returns 0 bytes). Handle the empty-result case or use a smaller seek for short clips.
- The seam can be 3–50+ pixels wide, not just 1. Single-pixel check still works because the seam pixel is the darkest.
- Some SBS videos have a wide black gap between eyes (50+ px). Center pixel check still works — the seam region is uniformly dark.

### Conversion pipeline per format

| Detected format | ffmpeg filter chain |
|----------------|-------------------|
| **Equirect 360°** | `v360=equirect:flat:h_fov=120:v_fov=80,scale=1920:1080` |
| **SBS (any ratio)** | Crop one eye first, then VR→flat: `crop={half_w}:{h}:0:0,v360=hequirect:flat:h_fov=120:v_fov=80,scale=1920:1080` |
| **VR180 (hequirect)** | `v360=hequirect:flat:h_fov=120:v_fov=80,scale=1920:1080` |
| **Flat** | `scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2` |

### VAAPI appendage
For `h264_vaapi` encoder, always append `,format=nv12,hwupload` to the end of the filter chain before the encoder. Example: `crop=720:720:0:0,v360=hequirect:flat:h_fov=120:v_fov=80,scale=1920:1080,format=nv12,hwupload`

## Source resolution mapping for VR on tube sites

Tube sites (eporner, xhamster, etc.) label VR SBS videos with flat-video resolution names. The actual pixel dimensions differ because VR SBS doubles the width:

| Label | Flat meaning | VR SBS total | VR SBS per eye | Crop |
|-------|-------------|-------------|----------------|------|
| 720p  | 1280×720    | 1440×720    | 720×720        | `crop=720:720:0:0` |
| 1080p | 1920×1080   | 2160×1080   | 1080×1080      | `crop=1080:1080:0:0` |
| 1440p | 2560×1440   | 2880×1440   | 1440×1440      | `crop=1440:1440:0:0` |
| 2160p | 3840×2160   | 4320×2160   | 2160×2160      | `crop=2160:2160:0:0` |

**Formula:** VR SBS total width = `2 × label_height`, total height = `label_height`. Each eye is `label_height × label_height` square.

**Download size expectations** for a 36-min 60fps H.264 VR video on eporner:
- 720p source: ~821 MB, download ~5 min at 1.4 MiB/s
- 1080p source: ~1.33 GiB, download ~9 min at 1.4 MiB/s

**Performance impact of higher source resolution:**
- 1080p source (2160×1080) has 2.25× more pixels per eye than 720p (1440×720)
- v360 filter on CPU scales roughly linearly with pixel count
- Expect ~2× longer conversion time for 1080p source
- Quality improvement is significant — 1080×1080 per eye gives much better detail after v360→flat than 720×720

**User preference (Dylan):** When offered the choice between speed and quality on VR conversions, the expected answer is "go even higher if that will make output quality better" — quality trumps speed for this user. Do not ask unless the difference is extreme. Capture this preference in the `_download_video` call: set `--quality` to the user's desired output resolution, not a downscaled source.

## Reference material
- See `references/amd-vaapi-checklist.md` for the RX580/VAAPI smoke-test recipe and failure signatures.
- See `references/vr-sbs-detection.md` for the SBS vs equirect detection technique (centre-row seam analysis).
- See `references/vr2normal-av1-fix.md` for the session-2026-07-12 patch: AV1 avoidance via yt-dlp format filtering and the complete SBS→flat filter chain with speed benchmarks.
- See `scripts/bornto_sniff.cjs` — Puppeteer-based borntobefuck HLS stream extractor. Loads player page, clicks play, captures .m3u8 from network requests.
- See `scripts/pimpbunny_extract.cjs` — Puppeteer-based pimpbunny video URL extractor. Parses JSON-LD contentUrl and returns cookies for curl download.