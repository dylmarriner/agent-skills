---
name: webcam-rtsp-bridge
description: Troubleshoot Linux webcam-to-RTSP streaming with ffmpeg, MediaMTX, v4l2, and camera-driver resets.
---

# Webcam to RTSP Bridge

Use this skill when the user wants to publish a Linux webcam to an RTSP stream, usually with ffmpeg pushing into MediaMTX / rtsp-simple-server / similar backends, or when the camera is stuck, busy, or the stream refuses to start.

## When to use

- `/dev/videoX` exists but ffmpeg fails
- ffmpeg reports `Device or resource busy`
- ffmpeg reports `Connection refused` to the RTSP endpoint
- the camera only works with a specific input format like `mjpeg` / `mjpg`
- MediaMTX or another RTSP server is already running or conflicting on ports
- the webcam needs a driver reset (`uvcvideo` reload)
- PipeWire / WirePlumber / portal services need to be restarted to release the device

## Core workflow

1. Identify the camera device and who owns it.
   - `v4l2-ctl --list-devices`
   - `fuser -v /dev/video0 /dev/video1`
   - `lsof /dev/video0 /dev/video1`
   - `ps -ef | egrep 'ffmpeg|mediamtx|frigate|pipewire|wireplumber'`

2. Restart user media plumbing if the device is stuck.
   - `systemctl --user restart pipewire wireplumber xdg-desktop-portal`
   - If `xdg-desktop-portal-kde` is absent, do not fail the workflow; continue with what exists.

3. Reset the webcam driver only if needed.
   - `sudo modprobe -r uvcvideo`
   - `sudo modprobe uvcvideo`
   - Re-check `/dev/video*` and `v4l2-ctl --list-devices` after the reload.

4. Test capture before streaming.
   - Prefer a short `ffplay` or `ffmpeg` read test.
   - For MJPEG cameras, explicitly specify `-input_format mjpeg`.
   - Common test:
     - `ffplay -f v4l2 -input_format mjpeg -video_size 1280x720 -i /dev/video0`

5. Ensure the RTSP server is running.
   - Check port 8554 first:
     - `ss -ltnup | egrep ':8554|:8000|:18000|:18001'`
   - If MediaMTX is used, start it in the correct directory with the correct config.
   - If MediaMTX fails with RTP/RTCP port errors, inspect `mediamtx.yml` and make RTP/RTCP ports consecutive.

6. Start the publisher with conservative, low-latency settings.
   - Example publish command:
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

7. Verify the stream from the consumer side.
   - `ffprobe rtsp://127.0.0.1:8554/laptopcam`
   - If using Frigate, wire the RTSP URL into the camera config and restart Frigate.

## MediaMTX gotchas

- MediaMTX may fail if UDP ports are already occupied.
- A common fix is to keep RTSP on `:8554` but move RTP/RTCP to a free consecutive pair, for example:
  - `rtpAddress: :18000`
  - `rtcpAddress: :18001`
- If MediaMTX refuses to start, read the exact config error before changing anything else.
- If the user already has a working MediaMTX instance, prefer reusing it instead of installing another RTSP server.

## Camera-format gotchas

- Many laptop webcams expose MJPEG at higher resolutions.
- If ffmpeg guesses incorrectly, it may fail or produce a blank stream.
- When the camera supports it, explicitly set:
  - `-input_format mjpeg`
- If MJPEG still errors with APP-field warnings but streaming works, treat the warnings as noisy but non-fatal unless frames are actually missing.

## Permissions and safety

- Be careful changing `/dev/video*` permissions.
- Temporary `chmod 666` can be useful for troubleshooting, but should be reverted afterward.
- Prefer group-based permissions for long-term access.

## Verification checklist

- `/dev/video0` exists after any driver reload
- the device can be opened by ffplay/ffmpeg
- MediaMTX listens on 8554
- ffmpeg is actually publishing without `Connection refused`
- the consumer can read the RTSP stream

## Reusable troubleshooting pattern

1. Release the webcam.
2. Reload the webcam driver.
3. Confirm the camera mode.
4. Confirm the RTSP server ports.
5. Start MediaMTX.
6. Start ffmpeg with `-input_format mjpeg`.
7. Verify with `ffprobe`.

## Notes from a real-world debug session

- Restarting `pipewire`, `wireplumber`, and `xdg-desktop-portal` can help release webcam locks.
- `fuser` and `v4l2-ctl` are the fastest first checks.
- `uvcvideo` reload can restore a wedged webcam without rebooting.
- A hidden MediaMTX port conflict can look like an ffmpeg problem when it is actually a server startup/config issue.
- If MediaMTX dies on startup, inspect the config for RTP/RTCP port collisions before changing the stream command.
- When the camera is MJPEG-only at the chosen resolution, forgetting `-input_format mjpeg` is a common failure mode.
