# Android Studio Download URLs (Current as of 2026-04-29)

## Primary Download Sources

### Android Studio Panda4 (2025.1.x)
- https://edgedl.me.gvt1.com/android/studio/ide-zips/2025.1.1.2/android-studio-2025.1.1.2-linux.tar.gz
- https://edgedl.me.gvt1.com/android/studio/ide-zips/2025.1.1.15/android-studio-2025.1.1.15-linux.tar.gz
- https://edgedl.me.gvt1.com/android/studio/ide-zips/2025.1.1.20/android-studio-2025.1.1.20-linux.tar.gz

### Android Studio Standard (2024.2.x)
- https://redirector.gvt1.com/edgedl/android/studio/install/2024.2.1.22/android-studio-2024.2.1.22-linux.tar.gz

### Fallback: Android Studio AI
- https://redirector.gvt1.com/edgedl/android/studio/ai-install/2024.1.1.21/android-studio-ai-2024.1.1.21-linux.tar.gz

## Command-line Tools Only

### Latest (2025)
- https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip

## Official Download Page

If the above URLs fail (they expire frequently), use:
**https://developer.android.com/studio#downloads**

Click "Download Android Studio" and select "Linux" version.

## Mirror Sources

Google Cloud DNS Mirror:
- https://redirector.gvt1.com/edgedl/android/studio/install/{VERSION}/android-studio-{VERSION}-linux.tar.gz

## Version History

| Version | Release Date | Download Size | Notes |
|---------|-------------|---------------|-------|
| 2025.1.1.2 | 2026-01 | ~1.4 GB | Latest stable |
| 2024.2.1.22 | 2024-09 | ~1.3 GB | Stable |
| 2024.1.2.19 | 2024-06 | ~1.2 GB | Older stable |
| 2024.1.1.22 | 2024-04 | ~1.2 GB | Legacy |
| AI 2024.1.1.21 | 2024-04 | ~1.5 GB | AI features |

## Troubleshooting Downloads

### 404 Not Found
- Download URL has expired
- Try an older version
- Use official download page instead

### File size < 100 MB
- Likely an error page, not the actual installer
- Delete and try again with different version

### Download incomplete
- Resume with: `wget -c -O filename.zip URL`
- Or use `curl -L -C - -O URL`

## Maintenance Notes

**Update frequency:** Check these URLs quarterly as they change monthly
**Last verified:** 2026-04-29
**Next review:** 2026-07-29
