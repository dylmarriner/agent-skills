# VR SBS vs Equirect Detection

Technique for distinguishing SBS 3D VR from 360° equirectangular when both use a 2:1 aspect ratio.

## The problem

At a 2:1 aspect ratio (e.g. 1440×720), video could be:
- **360° equirectangular**: single panoramic frame, full sphere mapped to 2:1
- **VR180 half-equirect**: 180°×180° dome mapped to 2:1 frame
- **SBS 3D VR**: two square eye frames (720×720 each) side by side

Applying the wrong conversion produces a massive black void in the centre of the output.

## The seam-detection method

SBS video has a splice line at the exact middle column (`x = w//2`) where the left and right eye frames meet. This seam is characteristically dark because:
- Most VR cameras have a small gap between the two lenses
- The encoder compression at the frame boundary creates a dark line
- The pixel values at the seam are uniformly low

Genuine equirectangular video has continuous, varied pixel values across the centre column (sky, walls, subjects).

**Critical improvement over earlier approach:** Do NOT extract the full-height center column. The top and bottom edges of the frame have content even at the seam line, which raises the column-averaged luminance and causes false negatives. Instead, sample the **center row** (1px tall, full width) and compare the seam pixel to its immediate neighbours.

### Detection code (Python)

```python
def _detect_sbs_seam(path: Path, w: int, h: int) -> bool:
    """Check if a 2:1 video is SBS by looking for a dark vertical seam at the centre."""
    seek = "30"  # skip intro frames
    cmd = [
        "ffmpeg", "-ss", seek, "-i", str(path),
        "-vframes", "1", "-vf", f"crop={w}:1:0:{h//2},format=gray",
        "-f", "rawvideo", "-",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=15)
        row = list(r.stdout)
        if len(row) < w:
            return False
        cx = w // 2

        # Primary check: seam pixel vs surrounding 10px each side
        seam = row[cx]
        left = sum(row[cx-10:cx]) / 10
        right = sum(row[cx+1:cx+11]) / 10
        surround = (left + right) / 2 or 1
        ratio = seam / surround
        if ratio < 0.3:
            return True

        # Fallback: left/right half brightness similarity
        # True equirect 360° has very different L/R content
        mid = w // 2
        left_avg = sum(row[:mid]) / mid
        right_avg = sum(row[mid:]) / mid
        if left_avg > 30 and right_avg > 30:
            brightness_ratio = max(left_avg, right_avg) / max(min(left_avg, right_avg), 1)
            return brightness_ratio < 1.5  # similar brightness = SBS
        return False
    except Exception:
        return False
```

### Threshold rationale

- **ratio < 0.3**: SBS seam — the centre pixel is at most 30% as bright as the surrounding area
- **ratio >= 0.3**: equirect/VR180 — the centre pixel is within normal brightness range of adjacent pixels
- **Fallback L/R similarity < 1.5×**: if the left and right halves of the frame are similarly bright, the content is symmetric (SBS). Many equirect 360° clips have very different left vs right content (front vs back of the scene).
- The `seek=30s` avoids title cards / black frames at the beginning of the video

## Integration into a conversion pipeline

1. Probe video dimensions with `ffprobe`
2. If `1.8 <= w/h <= 2.2` AND the width is even:
   - Call `_detect_sbs_seam()`
   - If SBS: crop one eye (`crop={w//2}:{h}:0:0`), apply `v360=hequirect:flat:h_fov=120:v_fov=80`
   - If not SBS: apply `v360=equirect:flat:h_fov=120:v_fov=80` (standard 360° conversion)

## SBS→flat conversion filter chain

For 1440×720 SBS (each eye 720×720):

```
crop=720:720:0:0,v360=hequirect:flat:h_fov=120:v_fov=80,scale=1920:1080
```

With VAAPI appendage:

```
crop=720:720:0:0,v360=hequirect:flat:h_fov=120:v_fov=80,scale=1920:1080,format=nv12,hwupload
```

## Edge cases

- **SBS with cropped eye at 16:9** (e.g. 3840×1080 → each eye 1920×1080): the eye is already flat, no v360 needed — just crop and scale.
- **Genuine equirect 360°**: centre pixel brightness matches surrounding pixels, `_detect_sbs_seam` returns False.
- **Very short videos (< 30s)**: reduce the `seek` value or skip it to avoid seeking past the end. The detection catches this case by returning False when ffmpeg emits 0 bytes.
- **SBS with wide black gap (50+ px)**: still detected — the centre pixel is black even if the gap is large. The surrounding window (10px each side) may also be black, which causes `surround = 0`, triggering the `or 1` fallback and ratio = 0 < 0.3 → SBS.

## Real-world session (2026-07-12)

This technique was developed debugging an eporner VR video (`huge-tits-vr`) that was 1440×720. The original code classified it as equirect and produced a black void in the center. The seam detection identified it as SBS, and cropping + hequirect conversion produced the correct flat output.

**Key debugging steps that led to the fix:**
1. Inspected the converted output with pixel-level analysis — found a massive black rectangle at center (not a circle)
2. Downloaded a short source segment (yt-dlp with `--download-sections "*120-140"`)
3. Analyzed the source frames — found the characteristic SBS seam: 3+ contiguous black pixels at x=w/2, left/right halves very similar (correlation ~0.86)
4. The initial detection used `crop=1:h:w//2:0` (full-height column) with `avg < 30` — this failed because the top ~15% and bottom ~7% of the column have bright content even at the seam
5. Switched to center-row sampling with ratio-based comparison — immediately detected the seam
6. Added L/R brightness similarity as a fallback for edge cases
