# VAAPI Troubleshooting

## Common Error Codes and Fixes

### Exit code 218: "Impossible to convert between the formats"

```
Impossible to convert between the formats supported by the filter
'Parsed_scale_1' and the filter 'auto_scale_0'
Error reinitializing filters!
Failed to inject frame into filter network: Function not implemented
```

**Cause**: `-hwaccel vaapi` produces GPU surfaces. CPU filters (crop, scale, v360)
cannot consume GPU surfaces. Even `-hwaccel_output_format nv12` may fail on some
driver versions.

**Fix**: Remove `-hwaccel vaapi` entirely. CPU decode → CPU filter chain →
`format=nv12,hwupload` → VAAPI encode.

### Exit code 244: "Function not implemented" with `hwupload`

**Cause**: A CPU filter (`crop`, `scale`) was placed AFTER `hwupload`. Once a frame
is on GPU, CPU filters can't touch it.

**Fix**: Move all CPU filters before `hwupload`:
```
GOOD:  crop=...,scale=...,format=nv12,hwupload
BAD:   format=nv12,hwupload,crop=...       # crop after upload → crash
```

### Exit code 1: "DRM_IOCTL_I915_GEM_APERTURE failed"

**Cause**: Running VAAPI on a system without Intel integrated graphics while
ffmpeg was compiled with i915 support. Usually on AMD-only systems.

**Fix**: Ignore — it's a harmless warning. Verify the encoder works with a
real `h264_vaapi` test: `ffmpeg -f lavfi -i color=c=black:s=1920x1080:d=1 -c:v h264_vaapi -f null -`

### VAAPI renderD128 not found

**Cause**: The user running ffmpeg doesn't have permission to access /dev/dri/renderD128,
or the GPU driver (amdgpu, i915) isn't loaded.

**Fix**:
```bash
# Check GPU driver
lsmod | grep -E 'amdgpu|i915|nvidia'

# Check render node
ls -la /dev/dri/
# crw-rw----+ 1 root video  226, 128  ... renderD128

# Add user to video and render groups
sudo usermod -a -G video $USER
sudo usermod -a -G render $USER
```

### NVENC: "Provided device doesn't support required NVENC capabilities"

**Cause**: Consumer NVIDIA cards (GeForce) have NVENC session limits (usually 3).
Too many concurrent encoding sessions.

**Fix**: Limit concurrent encoding sessions or use a professional card (Quadro/RTX).

## Driver Version Check

```bash
# VA-API version
vainfo | grep -E 'libva|Driver version'

# Mesa version (AMD/Intel)
glxinfo -B 2>/dev/null | grep "OpenGL version"

# ffmpeg VAAPI support
ffmpeg -hide_banner -encoders | grep vaapi
```

## Test VAAPI works

```bash
# Minimal test: synthetic input → VAAPI null output
ffmpeg -f lavfi -i color=c=black:s=1920x1080:d=1 \
  -c:v h264_vaapi -global_quality 23 \
  -vaapi_device /dev/dri/renderD128 -f null -

# Full pipeline test: SBS synthetic → VAAPI encode → file
ffmpeg -f lavfi -i "color=c=red:s=1920x1080:d=2" \
  -f lavfi -i "color=c=blue:s=1920x1080:d=2" \
  -filter_complex "hstack=inputs=2" \
  -c:v libx264 -preset fast -f mp4 /tmp/sbs_test.mp4 -y

ffmpeg -i /tmp/sbs_test.mp4 \
  -vf "crop=1920:1080:0:0,scale=1920:1080,format=nv12,hwupload" \
  -c:v h264_vaapi -global_quality 23 \
  -vaapi_device /dev/dri/renderD128 /tmp/flat_test.mp4 -y
```
