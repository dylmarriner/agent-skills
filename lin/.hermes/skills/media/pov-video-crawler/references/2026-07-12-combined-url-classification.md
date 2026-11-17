# Combined URL Pool Classification Notes (2026-07-12)

Session lesson: a merged crawl pool can contain a lot of non-video junk even when the source filenames say "POV".

Observed on the combined file:
- 204 unique URLs after cross-file dedupe
- only 58 looked like direct video pages by path shape
- 146 were search/profile/social/ambiguous pages

Common junk classes to strip before download:
- Instagram / TikTok / YouTube / X links
- IMDb / IAFD / performer-profile pages
- search pages (`/search`, `/discover`, `/popular`)
- detail/chat/profile pages
- generic catalog pages with no single playable video

Practical rule:
1. Merge all crawl outputs.
2. Deduplicate exact URLs.
3. Classify each URL as direct-video vs non-video/ambiguous.
4. Keep only direct-video URLs in the download queue.
5. Run title verification only on the direct-video queue.

Useful heuristics for direct-video URLs:
- `/video-.../slug`
- `/videos/...`
- `/scene/...`
- direct `view_video.php?viewkey=`-style pages
- site-specific video pages that clearly contain a single playable item

Heuristics for non-video pages:
- `/search`, `/discover`, `/popular`, `/details`, `/chat`, `/fullcredits`, `/plotsummary`
- performer pages and tag pages
- social/video-index pages that list results rather than hosting one video

This lesson came from a session where the user expected a cleaned POV pool, but the merged file still contained a large amount of site/navigation noise. The fix is to add a classification gate before any download step.
