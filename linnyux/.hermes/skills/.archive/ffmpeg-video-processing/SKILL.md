---
name: ffmpeg-video-processing
description: Video processing pipelines with ffmpeg — VAAPI GPU acceleration, VR-to-flat conversion (v360 filter), crop/scale chains, format auto-detection, and progress tracking. Covers both CPU and hardware-accelerated paths for AMD/NVIDIA GPUs.
trigger: user wants to transcode, convert, or process video with ffmpeg, especially with hardware acceleration (VAAPI, NVENC), VR-to-flat conversion, or custom filter chains.
---

# ffmpeg Video Processing

Video transcoding pipelines using ffmpeg — hardware acceleration, VR conversion, and robust filter chain construction.

## Platform Detection

### VAAPI (AMD/Intel GPUs)

```python
def detect_gpu():
    """Return (available, encoder_type)."""
    # NVIDIA
    r = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=10)
    if r.returncode == 0:
        return True, "nvenc"
    # AMD VAAPI
    r = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"],
                       capture_output=True, text=True, timeout=10)
    if "h264_vaapi" in r.stdout:
        return True, "vaapi"
    # Intel QSV
    if "h264_qsv" in r.stdout:
        return True, "qsv"
    return False, "cpu"
```

Verify VAAPI is working: `vainfo` — should show driver version for AMD/Intel.

## CRITICAL: VAAPI Filter Chain Pattern

**The most common ffmpeg VAAPI failure:** mixing CPU and GPU filters incorrectly.

### FAILS (exit code 218/244):
```
-vf "crop=1920:1080:0:0,scale=1920:1080"              # CPU filters need CPU input
-hwaccel vaapi                                          # decoder produces GPU surfaces
```

### CORRECT — CPU filters + VAAPI encoder:
```
# CPU filters (crop, scale, v360) → format=nv12 → hwupload → VAAPI encoder
-vf "crop=1920:1080:0:0,scale=1920:1080,format=nv12,hwupload"
-c:v h264_vaapi -vaapi_device /dev/dri/renderD128
```

**Rule:** Do NOT use `-hwaccel vaapi`. CPU decode → CPU filters → `hwupload` at end → VAAPI encoder. The VAAPI encoder automatically receives the uploaded GPU surfaces.

### Hardware encoders and their options:

| Encoder | GPU | Options |
|---------|-----|---------|
| `h264_vaapi` | AMD/Intel | `-global_quality 23 -vaapi_device /dev/dri/renderD128` |
| `h264_nvenc` | NVIDIA | `-preset p4 -rc vbr -cq 23` |
| `h264_qsv` | Intel | `-global_quality 23` |
| `libx264` | CPU (fallback) | `-preset medium -crf 23` |

### NVENC fallback (no HW upload needed):
```
-c:v h264_nvenc -preset p4 -rc vbr -cq 23
```

## VR-to-Flat Conversion Pipeline

### Video Format Detection

```python
def detect_vr_format(w, h):
    """Classify video by dimensions."""
    if w <= 0 or h <= 0: return "flat"
    r = w / h
    # SBS: ratio > 2.5 (two ~16:9 frames side by side)
    if r >= 2.5: return "sbs"
    # Over-under: height >= 2*width (two views stacked)
    if h >= 2 * w and h % 2 == 0: return "ou"
    # 2:1 ratio — equirectangular 360° or VR180
    if 1.8 <= r <= 2.2: return "equirect"
    # Standard flat video
    return "flat"
```

### Filter Chains for Each Format

SBS (3840x1080, etc.): crop left half → scale to 16:9
```
crop=1920:1080:0:0,scale=1920:1080,format=nv12,hwupload
```

Over-under (1080x2160, etc.): crop top half → scale to 16:9
```
crop=1080:1080:0:0,scale=1920:1080,format=nv12,hwupload
```

Equirectangular 360° (4320x2160, etc.): v360 to flat → scale
```
v360=equirect:flat:h_fov=120:v_fov=80,scale=1920:1080,format=nv12,hwupload
```
Note: v360 can't run on VAAPI GPU — the filter runs on CPU, then hwupload passes to encoder.

Flat (1920x1080, etc.): just scale + pad to 16:9
```
scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=nv12,hwupload
```

## Progress Tracking

Parse ffmpeg stderr for `frame=N` to estimate progress:

```python
dur = probe_ffprobe(input_path)["duration"]
fps = probe_ffprobe(input_path)["fps"]
total_frames = int(dur * fps)
frame_re = re.compile(r"frame=\s*(\d+)")

proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
for line in iter(proc.stderr.readline, ""):
    m = frame_re.search(line)
    if m and total_frames > 0:
        pct = min(int(m.group(1)) / total_frames * 100, 99)
        prog(pct)
proc.wait()
```

## Probing With ffprobe

```python
def probe_video(path):
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json",
           "-show_streams", "-show_format", str(path)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    data = json.loads(r.stdout)
    stream = next((s for s in data["streams"] if s["codec_type"] == "video"), {})
    fmt = data.get("format", {})
    dur = fmt.get("duration", "0")
    return {
        "width": int(stream.get("width", 0)),
        "height": int(stream.get("height", 0)),
        "codec": stream.get("codec_name", "h264"),
        "duration": float(dur) if dur else 0,
        "fps": float(eval(stream.get("r_frame_rate", "30/1"))),
    }
```

## Thread-Pool Execution

Blocking ffmpeg calls MUST NOT run on the asyncio event loop:

```python
# In FastAPI endpoint:
loop = asyncio.get_event_loop()
loop.run_in_executor(None, blocking_convert_function, arg1, arg2, loop)

# Inside the blocking function:
def progress(pct, stage=None, msg=None):
    kw = {"progress": round(pct, 1), "status": stage or "queued"}
    if stage: kw["stage"] = stage
    if msg: kw["message"] = msg
    # call_soon_threadsafe doesn't accept **kwargs — use lambda
    loop.call_soon_threadsafe(lambda: _update_task(task_id, **kw))
```

## Pitfalls

- **hwupload after CPU filters** — `format=nv12,hwupload` must be the LAST step in the filter chain, after ALL CPU filters. Putting a CPU filter (crop, scale, v360) after hwupload will fail because it can't operate on GPU surfaces.
- **-hwaccel vaapi flag** — Do NOT use this for filter chains. It makes the decoder output VAAPI surface frames that CPU filters can't process. Use CPU-only decode and just add `,format=nv12,hwupload` at the end of the filter chain for the encoder.
- **v360 filter** — Can't run on VAAPI GPU. For equirectangular content, the v360 filter runs on CPU, then hwupload passes to GPU for encoding. This is intentional.
- **crop dimensions** — SBS crop uses `iw/2:ih:0:0` (left half). For non-SBS content, this would crop half the frame. Always detect the format first.
- **frame rate parsing** — `r_frame_rate` is a fraction string like "30/1". Use `eval()` or parse manually. `float(eval(...))` works but use carefully.
- **ffmpeg exit codes** — 218 = format negotiation failure (wrong filter chain), 244 = general error (check stderr).
