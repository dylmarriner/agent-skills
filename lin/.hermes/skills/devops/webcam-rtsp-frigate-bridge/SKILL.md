---
name: webcam-rtsp-frigate-bridge
description: Set up a Linux webcam to publish via FFmpeg over RTSP (typically MediaMTX) and wire that stream into Frigate or similar consumers, handling device busy issues, MJPEG camera quirks, and RTSP server port conflicts.
---

# Webcam to RTSP / Frigate Bridge

Use this skill when the user wants to publish a local Linux webcam as an RTSP stream and consume it from Frigate or another video pipeline.

## When to use

- The webcam is exposed as /dev/video* and needs to be streamed via FFmpeg
- The user wants an RTSP URL like rtsp://127.0.0.1:8554/laptopcam
- MediaMTX or another RTSP server is already installed, or needs to be started
- Frigate should read the stream from another machine or from the local host
- The camera only works reliably with MJPEG at a specific resolution/framerate

## Core workflow

1. Discover the camera and confirm it exists:
   - `v4l2-ctl --list-devices`
   - `ls -l /dev/video*`
   - If needed, check who owns the device with `fuser -v /dev/video0 /dev/video1` or `lsof /dev/video0`

2. If the device is stuck, reset the driver:
   - `sudo modprobe -r uvcvideo`
   - `sudo modprobe uvcvideo`

3. Test the webcam directly before streaming:
   - Prefer a command that matches the camera’s actual mode, commonly MJPEG:
     - `ffplay -f v4l2 -input_format mjpeg -video_size 1280x720 -i /dev/video0`
   - If FFmpeg or FFplay reports decode warnings like MJPEG APP-field messages, check whether the stream still works before trying to “fix” them.

4. Start or verify the RTSP server:
   - If MediaMTX is used, confirm it is listening on 8554.
   - Be aware MediaMTX can fail if its UDP RTP/RTCP ports are already in use.
   - Common symptom:
     - `listen udp :8000: bind: address already in use`
   - If that happens, inspect `mediamtx.yml` for `rtpAddress` and `rtcpAddress`.
   - Ensure the RTP/RTCP ports are consecutive and not conflicting with another service.

5. Publish the webcam to RTSP with FFmpeg:
   - Typical working pattern for MJPEG webcams:

```bash
ffmpeg -loglevel error -f v4l2 \
  -input_format mjpeg \
  -framerate 15 \
  -video_size 1280x720 \
  -i /dev/video0 \
  -an \
  -c:v libx264 -preset ultrafast -tune zerolatency -pix_fmt yuv420p \
  -f rtsp -rtsp_transport tcp rtsp://127.0.0.1:8554/laptopcam
```

6. Verify the publisher:
   - `ffprobe rtsp://127.0.0.1:8554/laptopcam`
   - or `ffplay rtsp://127.0.0.1:8554/laptopcam`

7. Wire Frigate to the correct RTSP URL:
   - Update the camera path in Frigate’s `config.yml`
   - Make sure the Frigate host can reach the RTSP server IP and port
   - Restart Frigate and verify logs show the camera processor and capture process started

## Practical lessons learned

- MJPEG webcams often need `-input_format mjpeg`; letting FFmpeg guess can fail or behave inconsistently.
- MJPEG APP-field warnings are often harmless if the stream still runs.
- If MediaMTX fails at startup with a UDP port conflict, fix the RTP/RTCP ports in the config instead of assuming FFmpeg is broken.
- If Frigate says the camera stream is timing out, check that the RTSP URL points to the correct host/IP, not just `127.0.0.1`.
- If Frigate is on another machine, the camera source can be on one box and the RTSP consumer on another; the RTSP URL must point to the streaming host.
- When troubleshooting, change one thing at a time and verify after each change.

## Verification checklist

- `v4l2-ctl --list-devices` shows the webcam
- `ffplay` can open the webcam directly
- MediaMTX starts without port conflicts
- FFmpeg publishes to the RTSP endpoint
- `ffprobe` or `ffplay` can read the RTSP stream
- Frigate logs show the camera processor and capture process started

## Safety / cleanup

- Revert temporary broad permissions on /dev/video* after testing.
- Prefer persistent udev rules or group membership over `chmod 666`.
- Keep MediaMTX config changes minimal and documented.
- If a change breaks the stream, restore the previous config before trying a new approach.

## Common troubleshooting commands

- `ss -ltnup | egrep ':8554|:8000|:8001'`
- `systemctl status docker`
- `docker compose logs --tail=50 frigate`
- `docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'`
- `grep -n 'rtpAddress\|rtcpAddress' mediamtx.yml`
