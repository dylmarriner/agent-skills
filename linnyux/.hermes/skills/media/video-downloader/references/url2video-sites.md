---
name: url2video-download
description: Download videos from pimpbunny.com and borntobefuck.com using site-specific extraction
---

# URL2Video Download Patterns

Use when the user sends video URLs from pimpbunny.com or borntobefuck.com.

## pimpbunny.com
1. Navigate to URL in browser
2. Extract direct video URL from `<video>` element's third source attribute via browser_console
3. Download with `curl -L -o "filename.mp4" "direct_url"` (avoid yt-dlp, it chokes on the PHP redirect)

## borntobefuck.com  
1. Extract HLS m3u8 URL: `curl -sL "https://borntobefuck.com/videos/{id}/player?lang=en" | grep -oP 'data-hls-url="[^"]*"'`
2. Download with yt-dlp on the m3u8 URL: `yt-dlp -f best -o "filename.%(ext)s" "m3u8_url"`
3. Run in background with notify_on_complete

## General rules
- The user sends URLs and expects silent action. No explanations, no questions.
- Confirm only: DONE: filename or FAILED: reason
- Run downloads in background so the user can keep sending URLs