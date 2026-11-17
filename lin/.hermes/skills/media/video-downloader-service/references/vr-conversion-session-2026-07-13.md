# VR Conversion Session — 2026-07-13

## Overview

Processed 24 VR videos from eporner through vr2normal. Key learning: the `queue` CLI is the *only* correct way to batch VR conversions — not parallel background processes, not the API server.

## Correct Workflow (verified this session)

```bash
cd /media/kubuntux/DEVELOPMENT1/vr2normal

# 1. Add all URLs to queue
./vr2normal queue add "https://www.eporner.com/video-XXXXXX/" --quality 1080

# 2. Process one at a time
./vr2normal queue run

# 3. Monitor
./vr2normal queue list --all
```

## How NOT To Do It (user callouts from this session)

- Running 7 `./vr2normal convert` as parallel background processes — all compete for GPU bandwidth
- Starting the API server and POSTing 24 URLs to `/convert` — ThreadPoolExecutor still runs them concurrently
- A sequential bash script calling `./vr2normal convert` with piped filters — hides progress, bypasses built-in queue

## Queue Output Location

Queue stored at `~/.vr2normal/queue.json`. Converted files go to the output dir, each producing `flat_XXXXXXXX.mp4` with a random hash.

## SIGTERM (exit 143) on Long 1080p Conversions

The Vulkan pipe pipeline can trigger SIGTERM on very long sources (36-min 2209s videos). 720p quality path works reliably for long sources; 1080p may need retry or quality downgrade.

## Pimpbunny Extraction (re-verified)

Two videos extracted from pimpbunny via Puppeteer JSON-LD contentUrl:
- TanaBabyXO: 123MB — curl with cookies + referer
- AngelYoungs/Kait: 691MB — same method

`PHPSESSID` session cookie expires=-1 must be clamped to 0 for Netscape cookie format.
