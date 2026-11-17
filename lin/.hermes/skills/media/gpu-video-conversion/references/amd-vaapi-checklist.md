# AMD VAAPI checklist for VR2Normal

Session-proven smoke test for RX580 / Radeon boxes.

## Confirm hardware and VAAPI support
- `test -e /dev/dri/renderD128`
- `vainfo`
- `ffmpeg -hide_banner -encoders | grep -E 'h264_vaapi|hevc_vaapi'`

Expected on the RX580 box:
- VA-API driver loads from `radeonsi_drv_video.so`
- `vainfo` reports Radeon RX 580 Series
- `h264_vaapi` appears in ffmpeg encoders

## CLI behavior to preserve
- GPU encode should remain enabled by default when VAAPI exists.
- The CLI should not force `use_gpu=False` for convert mode.
- GPU detection should report AMD/Radeon as VAAPI, not NVIDIA-only labels.

## Minimal functional verification
1. Convert a real equirectangular/VR URL.
2. Wait until the converter writes an output MP4.
3. If the parent command times out, inspect the file anyway.
4. Verify the file with:
   - `stat -c '%n %s bytes' output.mp4`
   - `ffprobe -v error -show_entries format=duration,size -show_streams -of json output.mp4`

## Success signature
- output exists
- output size is non-zero
- `ffprobe` shows:
  - video codec `h264`
  - encoder tag `h264_vaapi`
  - 16:9 flat output, e.g. 1920x1080

## Common failure signatures
- `NVIDIA GPU` is false but VAAPI is present: fix the detector, not the machine.
- Conversion timeout with a valid output file: treat as partial success and verify with ffprobe.
- Output missing after ffmpeg finishes: rename/copy logic is wrong.
