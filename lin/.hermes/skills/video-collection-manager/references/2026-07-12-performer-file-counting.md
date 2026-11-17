# Performer file counting notes — 2026-07-12

Use this when the user asks for counts of actual downloaded videos by performer.

Key lessons from the session:
- Separate queued URL counts from downloaded file counts. Queue files can be highly misleading.
- For actual downloads, scan `/mnt/storage/videos/` directly and exclude `/mnt/storage/videos/.queue/`.
- Count only media extensions (`.mp4`, `.mkv`, `.webm`, `.mov`, `.m4v`, `.avi`, `.mpg`, `.mpeg`, `.ts`).
- Split the report into mainstream/western and Asian/Asian-American sections when the roster provides those sections.
- Filename matching is a heuristic, not truth. It can undercount files with generic titles and overcount when multiple performer names appear in the same filename.
- If the user wants “how many videos do I have of each performer,” say whether the number is:
  1) queue URLs matched by performer, or
  2) actual files on disk matched by filename.

Practical scan shape:
- Build the performer list from `performer_directory.txt`.
- Scan all media files under `/mnt/storage/videos/` excluding `.queue`.
- Lowercase filenames before matching.
- Normalize by replacing `&` with `and` and collapsing non-alphanumeric characters to spaces.
- Prefer full-name matches and strip obvious junk like `[viewkey]`, quality tags, and site prefixes.
- Save the report as `/mnt/storage/videos/.queue/performer_video_counts.md`.
- Report totals and mention that counts are not mutually exclusive if one file contains multiple performer names.

Pitfalls:
- Generic or studio-only filenames may be uncategorized.
- Some files match more than one performer.
- Do not use queue file counts as a proxy for downloaded inventory.
