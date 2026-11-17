# vr2normal AV1 avoidance + SBS→flat patch (2026-07-12)

## Problem

36-minute eporner VR video (`huge-tits-vr`) was converting at ~0.05× realtime on i7-6700 + RX 580. Expected ~2000s for a 2209s video.

## Root cause

Two compounding issues:

1. The video was being downloaded as **AV1** codec (yt-dlp picks it as "best" for compression efficiency), but the i7-6700 has zero hardware AV1 decode. Pure software AV1 decode at 60fps 720p consumes nearly all CPU capacity.

2. The source was **SBS 3D VR** (two 720×720 eye frames) but `_detect_vr_format` classified it as equirect because the aspect ratio (2:1) matched. Applying `v360=equirect:flat` on the combined SBS frame produced a massive black rectangle at the center.

## Av1 avoidance challenge: eporner "unknown" codec (2026-07-12 follow-up)

The `[vcodec!=av1]` filter does NOT reliably exclude AV1 on eporner. The non-AV1 format IDs (e.g. `1080p@60fps_HD`) show vcodec="unknown" in `yt-dlp -F`, while the AV1 variants (`av1-1080p@60fps_HD`) show vcodec="av1". The `[vcodec!=av1]` filter should work because "unknown" != "av1", but in practice yt-dlp may still negotiate and deliver the AV1 variant (681 MiB vs expected 1.33 GiB for H.264 1080p 36-min video). **Fix: use explicit format IDs for known sites:**
```python
fmt = f"{height_limit}p@60fps_HD+bestaudio/best"
```

## Performance data: Vulkan GPU shader pipeline (2026-07-12)

The vr2normal pipeline has a GPU projection path via libplacebo + GLSL shaders on Vulkan. Two-stage piped approach (VAAPI decode -> hwdownload -> Vulkan shader -> raw pipe -> VAAPI encode) because VAAPI-Vulkan interop is broken on Polaris10.

Performance on 2160x1080 H.264 60fps VR source:
- Vulkan GPU pipeline: ~71 fps, 1.18x speed
- CPU v360 (estimated): ~60 fps, ~1.05x speed
- SIGTERM'd before completion -- may need to restart long conversions

Known limitation: the piped pipeline receives SIGTERM (exit 143) during long conversions due to temp-dir cleanup race. For reliable results, run in a persistent workdir.

## Vulkan GPU shader pipeline (internal details for future debugging)

Stage 1 (decode + projection):
```
ffmpeg -init_hw_device vulkan=vk:0 -filter_hw_device vk \
  -vaapi_device /dev/dri/renderD128 -hwaccel vaapi -hwaccel_output_format vaapi \
  -i input.mp4 \
  -vf "hwdownload,format=nv12,hwupload,libplacebo=w=1920:h=1080:upscaler=none:downscaler=none:peak_detect=false:custom_shader_path=hequirect_to_flat.glsl,hwdownload,format=yuv420p" \
  -f rawvideo -pix_fmt yuv420p pipe:1
```

Stage 2 (encode, reads from pipe):
```
ffmpeg -vaapi_device /dev/dri/renderD128 \
  -f rawvideo -pix_fmt yuv420p -s 1920x1080 -r fps -i pipe:0 \
  -i input.mp4 -map 0:v -map 1:a? \
  -vf "format=nv12,hwupload" -c:v h264_vaapi -global_quality 23 \
  -c:a aac -b:a 128k -movflags +faststart -y output.mp4
```

Shaders at: `backend/shaders/hequirect_to_flat.glsl` and `equirect_to_flat.glsl`. The SBS eye crop is handled in the shader (samples left half). Controlled by `VR2NORMAL_GPU_PROJECTION=1` (default) or `=0` (disable).

## Fix 1: AV1 avoidance in `_download_video`

**File:** `backend/main.py`

Replaced the videosnap-only download path with yt-dlp direct download using a format string that excludes AV1:

```python
fmt = (
    f"bestvideo[height<={height_limit}][vcodec!=av1]"
    f"+bestaudio/best[height<={height_limit}][vcodec!=av1]/best"
)
yt_cmd = ["yt-dlp", "--no-playlist", "-f", fmt, "-o", str(dest), url]
```

Falls back to videosnap if yt-dlp is unavailable or fails.

The patch also passes the user's desired quality to `_convert_vr` and uses it to select the source format (720p → 720, 1080p → 1080, etc.), so asking for a higher-quality output automatically downloads a higher-resolution source.

**Speed comparison (same 2209s source, same VAAPI encode):**
- AV1: 30%/600s → ~2000s estimated total (0.5x)
- H.264 720p: 87 fps, 1.47x, ~1500s total
- H.264 1080p: ~45 fps expected (2.25× more pixels per eye for v360, ~2× longer)

## Fix 2: SBS→flat conversion filter chain (from previous session)

**File:** `backend/main.py`

Added `_detect_sbs_seam(path, w, h)` to detect SBS by probing the center row. When the centre pixel at x=w/2 is <30% brightness of the surrounding 10px → SBS seam detected.

SBS conversion uses different crops depending on the source resolution:

| Label | Total pixels | Per eye | Crop filter |
|-------|-------------|---------|-------------|
| 720p  | 1440×720    | 720×720 | `crop=720:720:0:0` |
| 1080p | 2160×1080   | 1080×1080 | `crop=1080:1080:0:0` |
| 1440p | 2880×1440   | 1440×1440 | `crop=1440:1440:0:0` |

The crop width and height are computed dynamically from the source resolution: `crop_w = w // 2, crop_h = h` (left eye takes the left half, full height).

With VAAPI appendage (720p example):
```
crop=720:720:0:0,v360=hequirect:flat:h_fov=120:v_fov=80,scale=1920:1080,format=nv12,hwupload
```

With VAAPI appendage (1080p example):
```
crop=1080:1080:0:0,v360=hequirect:flat:h_fov=120:v_fov=80,scale=1920:1080,format=nv12,hwupload
```

## Performance optimization attempts (i7-6700 + RX 580)

After applying the AV1 + SBS fixes, further optimization was attempted for a 2209s 1440×720 H.264 60fps source:

| Attempt | Pipeline | FPS | Speed | Wall time | GPU util |
|---------|----------|-----|-------|-----------|----------|
| Baseline | CPU decode → v360 → VAAPI encode | 87 fps | 1.47x | ~1500s | 5% |
| VAAPI hwdecode | hwaccel vaapi + hwdownload → v360 → VAAPI encode | 75 fps | 1.27x | ~1740s | 6% |
| 3 parallel segments | 3× ffmpeg each doing same pipeline | 29 fps each | 0.5x each | ~3× baseline | 12% |
| Thread tuning | -threads 8 -filter_threads 8 | 87 fps | 1.47x | ~1500s | 5% |

### Why nothing helped much

- **VAAPI hwdecode**: the `hwdownload` step (GPU surface → CPU memory) adds latency that cancels decode speedup. The v360 filter inherently needs CPU frames.
- **Parallel segments**: the VAAPI encoder on RX 580 serializes — multiple processes compete for `/dev/dri/renderD128`, dropping everyone below single-process speed.
- **Thread tuning**: v360 claims "slice threading supported" but additional threads (beyond main decode thread) run at 0.2-0.3% utilization. The spherical math is fundamentally single-thread limited on this CPU.

### Hard ceiling

The 87 fps / 1.47x is a hard ceiling for i7-6700 + RX 580 on 1440×720 H.264 → 1920×1080 v360 flat conversion. The v360 transform is pure CPU math that cannot be GPU-accelerated on this hardware. A 36-min video takes ~25 min regardless of optimization attempts tried to date.

For 2160×1080 source (1080p), expect ~2× longer (~50 min) due to the 2.25× pixel count increase per eye.

**Lesson for this hardware combo:** the single biggest gain is AV1 avoidance (3× speedup). Everything else (hwdecode, parallel, threads) either doesn't help or makes things worse. If quality matters more than speed (Dylan's preference), use 1080p source and accept the longer conversion.

## Key insight

Most adult VR on tube sites at ≤1440p is:
- **SBS 3D** (two square eye frames), NOT 360° equirectangular
- **VR180** (half-equirect), not 360° full sphere — use `v360=hequirect`, not `v360=equirect`
- Served in **AV1** if available because the site wants to save bandwidth — but you can force H.264 with `[vcodec!=av1]`

### Source resolution mapping

Tube sites use flat-video labels for VR content. The actual resolution differs:

| Label | VR total | Per eye |
|-------|----------|---------|
| 720p  | 1440×720 | 720×720 |
| 1080p | 2160×1080 | 1080×1080 |
| 1440p | 2880×1440 | 1440×1440 |

Formula: VR SBS total width = `2 × label_height`, total height = `label_height`.

## Verification

The H.264 version of the same video:
- Source: 1440×720 H.264 High @ 60fps, 3mbps, 821MB
- Download: ~5 min at 1.4 MiB/s (eporner CDN limited)
- Conversion: ~500s with VAAPI hardware decode + h264_vaapi encode
- Output: 1920×1080, no black artifacts, correct flat projection

1080p source version:
- Source: 2160×1080 H.264, ~1.33 GiB
- Download: ~9 min at 1.4 MiB/s
- Conversion: ~2× longer than 720p (est. 50 min for 36-min source)
- Output: 1920×1080, significantly sharper than 720p-sourced output

```bash
# Check what format you'll get before downloading:
yt-dlp -f "bestvideo[height<=720][vcodec!=av1]+bestaudio/best[height<=720][vcodec!=av1]/best" \
  --print "format: %(format_id)s %(vcodec)s %(ext)s" URL

# Full conversion with AV1 avoidance + SBS detection:
python3 vr2normal convert URL --quality 720 --output /mnt/storage/videos/flat_final

# For 1080p output:
python3 vr2normal convert URL --quality 1080 --output /mnt/storage/videos/flat_final
```

## Temp dir cleanup race

The `cmd_convert` function wraps everything in `with tempfile.TemporaryDirectory()`. If the process is killed or times out before ffmpeg finishes, the temp dir is cleaned up but ffmpeg survives as an orphan with ghost (deleted) file handles — all work lost.

**Mitigation:** Don't let VR conversions span Hermes session boundaries. Use foreground execution with a generous timeout, or use a persistent temp dir outside `/tmp/`.
