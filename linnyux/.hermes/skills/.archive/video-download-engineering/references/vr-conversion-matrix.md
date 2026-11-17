# VR Format Detection & Conversion Matrix

## Format Classification

| Format | Aspect Ratio | Examples | Action |
|--------|-------------|----------|--------|
| SBS (Side-by-Side) | ≥ 2.5:1 | 3840×1080, 3840×960 | Crop left half, scale to 1920×1080 |
| OU (Over-Under) | height ≥ 2×width | 1080×2160 | Crop top half, scale to 1920×1080 |
| Equirectangular 360° | ~2:1 (±0.15) | 4320×2160, 3840×1920, 5760×2880 | v360 equirect→flat + scale |
| Flat | Everything else | 1920×1080, 2560×1440, 1080×1920 | Scale + pad to 1920×1080 |

## Filter Chain by Format

### SBS (most common VR format)
```
crop={half_w}:{crop_h}:0:0,scale={scale_w}:{scale_h}
```
half_w = w // 2, scale_h = out_h (1080), scale_w = half_w * (1080/h)

### Over-Under
```
crop={crop_w}:{half_h}:0:0,scale={scale_w}:{scale_h}
```
half_h = h // 2, scale_w = out_w (1920), scale_h = half_h * (1920/w)

### Equirectangular 360° / VR180
```
v360=equirect:flat:h_fov=120:v_fov=80,scale=1920:1080
```
- h_fov=120: horizontal field of view (wider = more immersive)
- v_fov=80: vertical field of view
- Output is always 1920×1080

### Already Flat
```
scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2
```

## VAAPI GPU Appendage

For ALL filter chains when using VAAPI (`h264_vaapi` encoder), append:
```
,format=nv12,hwupload
```

The final VAAPI filter chain for SBS becomes:
```
crop=1920:1080:0:0,scale=1920:1080,format=nv12,hwupload
```

## Test Vectors

| Input Size | Detected | Filter | Notes |
|-----------|----------|--------|-------|
| 3840×1080 | sbs | crop left half + scale | Standard SBS 180° |
| 4320×2160 | equirect | v360 full frame | 4K 360° monoscopic |
| 3840×1920 | equirect | v360 full frame | HD 360° monoscopic |
| 4096×2048 | equirect | v360 full frame | VR180 4K (each eye 2048²) |
| 5760×2880 | equirect | v360 full frame | SBS 360° equirect (each eye is equirect) |
| 1920×1080 | flat | scale+pad | Standard 1080p, no VR |
| 1080×2160 | ou | crop top half + scale | Over-under VR |
| 1920×2160 | flat | scale+pad | Not OU (h < 2×w) — ambiguous, treat as flat |
| 1080×1920 | flat | scale+pad | Portrait phone video — not VR |
