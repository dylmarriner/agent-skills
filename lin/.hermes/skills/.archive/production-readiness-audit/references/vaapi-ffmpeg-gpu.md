# VAAPI / FFmpeg GPU Acceleration (AMD RX 580)

## Problem
FFmpeg with `-hwaccel vaapi` for decoding produces GPU surface frames that
CPU-side filters (crop, scale, v360, drawtext) can't operate on — you get
"Impossible to convert between the formats" or "Failed to inject frame into
filter network: Function not implemented".

Even `-hwaccel_output_format nv12` doesn't fix this — the VAAPI decoder
still wraps frames in VAAPI surfaces that CPU filters can't read.

## The Fix (CPU filters → VAAPI encode)

```
ffmpeg -i input.mp4 \
  -vf 'filter1,filter2,...,format=nv12,hwupload' \
  -c:v h264_vaapi -vaapi_device /dev/dri/renderD128 \
  ...output...
```

Key rules:
1. **No `-hwaccel vaapi`** at all — CPU decode produces system memory frames
2. All CPU filters (crop, scale, v360, drawtext, pad) come BEFORE `hwupload`
3. The last filter must be `format=nv12,hwupload` to convert CPU NV12 to GPU surface
4. The VAAPI encoder receives GPU surfaces from `hwupload` and encodes on GPU

## Working Filter Chains

### SBS (side-by-side) → flat
```
crop=1920:1080:0:0,scale=1920:1080,format=nv12,hwupload
```

### Over-under → flat
```
crop=1920:1080:0:0,scale=1920:1080,format=nv12,hwupload
```

### Equirectangular 360° → flat
```
v360=equirect:flat:h_fov=120:v_fov=80,scale=1920:1080,format=nv12,hwupload
```
(v360 is always CPU — can't run on VAAPI)

### Flat video → re-encode
```
scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=nv12,hwupload
```

## Verification

```bash
# Test GPU encoding works
ffmpeg -f lavfi -i color=c=black:s=1920x1080:d=1 \
  -vf 'format=nv12,hwupload' \
  -c:v h264_vaapi -global_quality 23 -vaapi_device /dev/dri/renderD128 \
  -f null -

# Test full SBS crop chain
ffmpeg -f lavfi -i color=c=red:s=3840x1080:d=2 \
  -vf 'crop=1920:1080:0:0,scale=1920:1080,format=nv12,hwupload' \
  -c:v h264_vaapi -global_quality 23 -vaapi_device /dev/dri/renderD128 \
  -f null -
```

## Resources

- `vainfo` — check VAAPI driver and supported profiles
- `ls /dev/dri/` — check render nodes (usually renderD128)
- Kernel driver: `amdgpu` (RX 580 / Polaris)
