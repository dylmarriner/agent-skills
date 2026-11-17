---
name: video-processing-pipeline
description: >-
  Build a full video processing pipeline with yt-dlp download, ffmpeg
  transcoding (VR→flat, resolution scaling, format conversion), GPU
  acceleration (VAAPI/NVENC), SMB upload, progress tracking via thread-
  safe callbacks, and async API integration. Use when the user needs
  to convert, download, or process video files in a production backend.
domain: software-development
tags:
  - video-processing
  - ffmpeg
  - gpu-acceleration
  - vaapi
  - pipeline
  - vr-conversion
version: 1.0.0
author: agent
---

# Video Processing Pipeline

Build a robust video processing pipeline with download, transcode, upload,
and progress tracking. All blocking operations run in a thread pool to
keep the event loop responsive.

## When to Use

- User wants to download + convert + upload videos
- Building a VR-to-flat conversion service
- Processing pipeline with GPU acceleration (VAAPI for AMD, NVENC for NVIDIA)
- ffmpeg-based transcoding with progress feedback via API
- SMB or HTTP file upload after processing

## Architecture

```
API endpoint
  ↓ trigger
queue / direct execution
  ↓
download (yt-dlp) ──→ convert (ffmpeg) ──→ upload (SMB/SCP/HTTP)
       ↓                     ↓                     ↓
  progress              progress              progress
       ↓                     ↓                     ↓
  thread-safe callback ──→ async API SSE/poll
```

All blocking work runs via `loop.run_in_executor(None, sync_fn, ...)`.
Progress reaches the API via `loop.call_soon_threadsafe()`.

## Key Patterns

### 1. Probe Video Metadata

Before converting, probe the input to know its dimensions, codec, and format:

```python
def probe_video(path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", str(path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    data = json.loads(r.stdout)
    stream = next(s for s in data.get("streams", [])
                  if s.get("codec_type") == "video")
    return {
        "width": int(stream.get("width", 0)),
        "height": int(stream.get("height", 0)),
        "codec": stream.get("codec_name", "h264"),
        "duration": float(data["format"].get("duration", 0) or 0),
        "fps": float(eval(stream.get("r_frame_rate", "30/1"))),
    }
```

### 2. Detect VR Format from Dimensions

Classify the video layout so the correct ffmpeg filter is applied:

| Aspect Ratio | Format | Action |
|---|---|---|
| ratio ≥ 2.5 | Side-by-side (SBS) | Crop left half → scale |
| height ≥ 2×width | Over-under (OU) | Crop top half → scale |
| 1.8 ≤ ratio ≤ 2.2 | Equirectangular 360° | v360 equirect→flat |
| everything else | Flat/monoscopic | Scale + pad to 16:9 |

```python
def detect_vr_format(w: int, h: int) -> str:
    if w <= 0 or h <= 0: return "flat"
    ratio = w / h
    if ratio >= 2.5: return "sbs"
    if h >= 2 * w and h % 2 == 0: return "ou"
    if 1.8 <= ratio <= 2.2: return "equirect"
    return "flat"
```

### 3. GPU Detection

Detect available GPU encoding hardware:

```python
def detect_gpu() -> tuple[bool, str]:
    # NVIDIA NVENC
    r = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=5)
    if r.returncode == 0: return True, "nvenc"

    # AMD VAAPI (check ffmpeg encoder list)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"],
                       capture_output=True, text=True, timeout=10)
    if "h264_vaapi" in r.stdout: return True, "vaapi"
    if "h264_qsv" in r.stdout: return True, "qsv"
    return False, "cpu"
```

### 4. GPU-Accelerated ffmpeg Pipeline

**VAAPI (AMD / Intel):**
```python
cmd = [
    "ffmpeg",
    "-hwaccel", "vaapi",                       # hardware decode
    "-i", str(input_path),
    "-vf", "format=nv12,hwupload,scale_vaapi=1920:1080",  # GPU-side filters
    "-c:v", "h264_vaapi",
    "-global_quality", "23",
    "-vaapi_device", "/dev/dri/renderD128",
]
```

Key details:
- `-hwaccel vaapi` — decode on GPU
- `format=nv12,hwupload` — upload frame to GPU surface
- `scale_vaapi=` — use VAAPI-specific scaling (regular `scale=` won't work on GPU)
- v360 filter CANNOT run on VAAPI — for equirect conversion, fall back to CPU:
  `-vf "v360=equirect:flat:h_fov=120:v_fov=80,scale=1920:1080"` with software encoder

**NVENC (NVIDIA):**
```python
cmd = [
    "ffmpeg",
    "-hwaccel", "cuda",
    "-i", str(input_path),
    "-vf", "scale_cuda=1920:1080",             # GPU-side scaling
    "-c:v", "h264_nvenc",
    "-preset", "p4", "-rc", "vbr", "-cq", "23",
]
```

**Software fallback (libx264):**
```python
cmd = [
    "ffmpeg", "-i", str(input_path),
    "-vf", "scale=1920:1080",
    "-c:v", "libx264",
    "-preset", "medium", "-crf", "23",
]
```

### 5. Progress Tracking

Parse ffmpeg stderr for frame numbers to estimate transcoding progress:

```python
total_frames = int(duration * fps) if duration > 0 else 0
frame_re = re.compile(r"frame=\s*(\d+)")
proc = subprocess.Popen(
    cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
)

for line in iter(proc.stderr.readline, ""):
    m = frame_re.search(line)
    if m and total_frames > 0:
        pct = min(int(m.group(1)) / total_frames * 100, 99)
        callback(pct)            # thread-safe progress update

proc.wait()
if proc.returncode != 0:
    raise RuntimeError(...)
callback(100)
```

### 6. SMB Upload via smbclient CLI

More reliable than smbprotocol Python library:

```python
cmd = [
    "smbclient", f"//{server}/{share}",
    "-U", f"{user}%{password}",
    "-c", f"cd {remote_path}; put {local_file} {filename}",
]
r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
if r.returncode != 0:
    raise RuntimeError(f"SMB upload failed: {r.stderr[:300]}")
```

## VR Format-Specific Filter Chains

| Format | Filter | Output |
|---|---|---|
| SBS 180° | `crop=iw/2:ih:0:0,scale=1920:1080` | Flat 16:9 from left eye |
| OU | `crop=iw:ih/2:0:0,scale=1920:1080` | Flat 16:9 from top half |
| Equirect 360° | `v360=equirect:flat:h_fov=120:v_fov=80,scale=1920:1080` | Flat 16:9 panorama |

## Async Safety Pattern (FastAPI)

```python
from fastapi import FastAPI
import asyncio

app = FastAPI()
_tasks: dict[str, dict] = {}

@app.post("/convert")
async def start_convert(url: str):
    task_id = str(uuid.uuid4())
    _tasks[task_id] = {"status": "queued", "progress": 0}

    loop = asyncio.get_event_loop()
    # Launch blocking pipeline in thread pool — does NOT block the event loop
    loop.run_in_executor(None, _pipeline, task_id, url, loop)
    return {"task_id": task_id}

def _pipeline(task_id: str, url: str, loop: asyncio.AbstractEventLoop):
    def progress(pct: float):
        # Thread-safe update of the in-memory task dict
        loop.call_soon_threadsafe(
            _tasks[task_id].__setitem__, "progress", round(pct, 1)
        )

    # ... all blocking work here (yt-dlp, ffmpeg, SMB upload) ...
    progress(100)
    loop.call_soon_threadsafe(
        _tasks[task_id].__setitem__, "status", "completed"
    )

@app.get("/status/{task_id}")
async def get_status(task_id: str):
    return _tasks.get(task_id, {"status": "not found"})
```

## Pitfalls

- **v360 filter is CPU-only** — cannot run on VAAPI/NVENC. For equirect→flat
  on GPU-accelerated pipelines, use software encoding (libx264) for that
  segment, or convert to an intermediate format first.
- **VAAPI needs /dev/dri/renderD128** — the user running the process must be
  in the `video` and `render` groups. Check with `ls -la /dev/dri/`.
- **smbclient authentication** — passwords with special characters may need
  escaping or a credentials file (`-A /path/to/authfile`).
- **Progress estimation** — frame counting from ffmpeg stderr is approximate.
  For very short videos (< 1 second), progress jumps from 0→100 instantly.
- **Temp directory cleaning** — always use `shutil.rmtree(workdir, ignore_errors=True)`
  in a finally block, even on failure.
- **yt-dlp output location** — yt-dlp may rename files unexpectedly (adds
  extension, suffixes for different formats). Always probe the output directory
  for the most recently modified file after download, then rename to a known path.
- **Hardware probing** — `nvidia-smi` may be present but NVENC unavailable
  (headless server, driver mismatch). Always fall back to software encoding.
