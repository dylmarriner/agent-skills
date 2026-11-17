---
name: ffmpeg-linux-gpu
description: |-
  Hardware-accelerated video encoding on Linux GPUs via ffmpeg.
  Covers VAAPI (AMD/Intel) and NVENC (NVIDIA) encoder setup, filter chain
  ordering, device path configuration, and common pitfalls.
version: 1.0.0
tags: [ffmpeg, gpu, vaapi, nvenc, video, encoding]
toolsets: [terminal]
platforms: [linux]
---

# ffmpeg Linux GPU Encoding

Hardware-accelerated video encoding/transcoding on Linux using ffmpeg.
Covers VAAPI (AMD Radeon, Intel integrated) and NVENC (NVIDIA).

## Detection

```bash
# Check VAAPI driver availability
vainfo

# List available hardware encoders
ffmpeg -hide_banner -encoders | grep -E 'vaapi|nvenc|qsv'

# Check render nodes exist
ls -la /dev/dri/
# renderD128 = first GPU, renderD129 = second, etc.
```

## GPU Detection (Python)

```python
import subprocess, shutil

def detect_gpu() -> tuple[bool, str]:
    """Return (available, encoder_type).  One of: vaapi, nvenc, cpu."""
    # NVIDIA
    try:
        r = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return True, "nvenc"
    except Exception:
        pass
    # AMD / Intel VAAPI
    try:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"],
                           capture_output=True, text=True, timeout=10)
        if "h264_vaapi" in r.stdout:
            return True, "vaapi"
    except Exception:
        pass
    return False, "cpu"
```

## Filter Chain Ordering (CRITICAL)

The most common ffmpeg VAAPI error is mixing CPU and GPU filters in the wrong order.
VAAPI decoders produce GPU-surface frames; CPU filters (`crop`, `scale`, `v360`)
operate on system-memory frames. The `h264_vaapi` encoder expects GPU-surface input.

### Correct pattern: CPU filters → upload → encode (no hwaccel decode)

```bash
# SBS crop + scale + VAAPI encode
ffmpeg -i input.mp4 \
  -vf "crop=1920:1080:0:0,scale=1920:1080,format=nv12,hwupload" \
  -c:v h264_vaapi -global_quality 23 -vaapi_device /dev/dri/renderD128 \
  output.mp4
```

Key rules:
1. **Do NOT use `-hwaccel vaapi`** — it makes the decoder output GPU surfaces that
   CPU filters can't process. Even `-hwaccel_output_format nv12` fails on some
   drivers. CPU decode → CPU filters → upload → GPU encode always works.
2. **CPU filters FIRST** (`crop`, `scale`, `v360`, etc.) operate on system memory.
3. **`format=nv12,hwupload` LAST** — converts to NV12 (VAAPI's native format) and
   uploads to GPU memory right before the encoder.
4. **VAAPI encoder** (`h264_vaapi`, `hevc_vaapi`) receives the uploaded frames.

### Wrong pattern that crashes (exit code 218 / 244):

```bash
# DON'T: hwaccel + CPU filter after upload
ffmpeg -hwaccel vaapi -i input.mp4 \
  -vf "format=nv12,hwupload,crop=1920:1080:0:0" \    # crop can't run on GPU
  -c:v h264_vaapi ...                                 # crash

# DON'T: hwaccel + hwaccel_output_format + CPU filter
ffmpeg -hwaccel vaapi -hwaccel_output_format nv12 -i input.mp4 \
  -vf "scale=1920:1080" \                             # format mismatch
  -c:v h264_vaapi ...                                 # crash
```

### Equirectangular (v360) on CPU + VAAPI encode:

```bash
ffmpeg -i input.mp4 \
  -vf "v360=equirect:flat:h_fov=120:v_fov=80,scale=1920:1080,format=nv12,hwupload" \
  -c:v h264_vaapi -global_quality 23 -vaapi_device /dev/dri/renderD128 \
  output.mp4
```

The `v360` filter is CPU-only. That's fine — CPU filter → format nv12 → hwupload →
VAAPI encode works correctly.

### Software encode (libx264) — no upload needed:

```bash
ffmpeg -i input.mp4 \
  -vf "crop=1920:1080:0:0,scale=1920:1080" \
  -c:v libx264 -preset medium -crf 23 \
  output.mp4
```

No `hwupload` — libx264 expects CPU frames.

## Encoder Options

### VAAPI (AMD/Intel)
```bash
-c:v h264_vaapi -global_quality 23 -vaapi_device /dev/dri/renderD128
```
- `-global_quality`: 1-51 (lower = better quality, 23 = default)
- `-vaapi_device`: DRM render node (check `ls /dev/dri/`)

### NVENC (NVIDIA)
```bash
-c:v h264_nvenc -preset p4 -rc vbr -cq 23 -b:v 0
```
- `-preset`: p1 (fastest) to p7 (slowest/best quality)
- `-rc`: rate control (vbr, cbr, constqp)
- `-cq`: constant quality (lower = better)

## Device Paths

| GPU | Driver | Device Path |
|-----|--------|-------------|
| AMD Radeon (RX 400/500/5000+) | amdgpu + radeonsi | `/dev/dri/renderD128` |
| Intel integrated (HD 4000+) | i915 | `/dev/dri/renderD128` |
| Intel Arc (DG2+) | i915 | `/dev/dri/renderD128` |
| NVIDIA (Quadro/GeForce) | nvidia | No DRM path — NVENC uses nvidia-smi |

## Progress Tracking

When running ffmpeg as a subprocess, parse stderr for frame numbers to estimate
progress:

```python
import re, subprocess

# Get total frame count first
dur_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", str(input_path)]
dur_r = subprocess.run(dur_cmd, capture_output=True, text=True, timeout=30)
fps = 30  # or read from ffprobe
total_frames = int(float(dur_r.stdout.strip()) * fps) if dur_r.stdout else 0

frame_re = re.compile(r"frame=\s*(\d+)")
proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
assert proc.stderr is not None
for line in iter(proc.stderr.readline, ""):
    m = frame_re.search(line)
    if m and total_frames > 0:
        pct = min(int(m.group(1)) / total_frames * 100, 99)
        update_progress(pct)
proc.wait()
```

## VR Format Detection

For VR video conversion, classify the input by dimensions:

```python
def detect_vr_format(w: int, h: int) -> str:
    """Returns 'sbs', 'ou', 'equirect', or 'flat'."""
    if w <= 0 or h <= 0:
        return "flat"
    ratio = w / h
    # Side-by-side: ratio > 2.5 (two ~16:9 frames side by side)
    if ratio >= 2.5:
        return "sbs"
    # Over-under: height >= 2*width
    if h >= 2 * w and h % 2 == 0:
        return "ou"
    # 2:1 ratio — equirectangular 360° or VR180
    if 1.8 <= ratio <= 2.2:
        return "equirect"
    return "flat"
```

Corresponding filter chains for each format with VAAPI:

| Format | Filter chain |
|--------|-------------|
| sbs | `crop=W/2:H:0:0,scale=1920:1080,format=nv12,hwupload` |
| ou | `crop=W:H/2:0:0,scale=1920:1080,format=nv12,hwupload` |
| equirect | `v360=equirect:flat:h_fov=120:v_fov=80,scale=1920:1080,format=nv12,hwupload` |
| flat | `scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=nv12,hwupload` |

See `references/vaapi-troubleshooting.md` for common error codes and fixes.

## Pitfalls

- **`hwupload` after CPU filters, never before**. A CPU filter after `hwupload`
  crashes with exit code 244. All `crop`/`scale`/`v360` must come before
  `format=nv12,hwupload`.
- **Do not use `-hwaccel vaapi` when CPU filters are involved**. It produces GPU
  frames that CPU filters reject. Let ffmpeg use its default CPU decoder, apply
  CPU filters, then upload for the VAAPI encoder.
- **`call_soon_threadsafe` does not accept kwargs**. When using
  `loop.call_soon_threadsafe()` from a worker thread to update progress, wrap in
  a lambda: `loop.call_soon_threadsafe(lambda: _update_task(**kw))`. Passing
  `**kw` as keyword arguments to `call_soon_threadsafe` itself raises
  `TypeError: unexpected keyword argument`.
- **v360 filter is CPU-only**. Cannot run on VAAPI GPU surfaces. If your pipeline
  needs v360 (equirect↔flat conversion), the filter runs on CPU after decode and
  before upload. This is fine — just keep the full chain on CPU side and upload
  only for the encoder.
- **ffprobe duration may be "N/A"** for streaming URLs. In that case total_frames
  stays 0 and progress tracking falls back to time-based estimation.
