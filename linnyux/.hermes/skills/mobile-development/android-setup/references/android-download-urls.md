Android Studio and SDK download URLs (tested during 2026-04-29 session)

## Download URLs (Working as of 2026-04-29)

### Android Studio
- **Panda4 Linux (Latest)**: `https://edgedl.me.gvt1.com/android/studio/ide-zips/2025.3.4.6/android-studio-panda4-linux.tar.gz`
  - Size: ~1.4 GB
  - Version: 2025.3.4.6
  
- **Alternative version (if 404)**: `https://redirector.gvt1.com/edgedl/android/studio/install/2024.2.1.22/android-studio-2024.2.1.22-linux.tar.gz`
  - May return 404 for older versions
  
- **Common working patterns**:
  - `2024.2.1.22` (stable, tested)
  - `2025.3.4.6` (latest, working)
  - `2025.3.4.5` (alternative latest)

**⚠️ 404 Errors**:
- Old versions like `2024.1.1.22` often return 404
- Newer versions in 2024.2.x and 2025.x work reliably
- Check https://developer.android.com/studio#downloads for current version

### Platform Tools (ADB, Fastboot)
- **URL**: `https://dl.google.com/android/repository/platform-tools-latest-linux.zip`
- **Size**: ~8 MB
- **Content**: adb, fastboot, hprof-conv, etc.

### Command Line Tools
- **URL**: `https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip`
- **Size**: ~146 MB
- **Content**: sdkmanager, avdmanager, etc.

### System Images (downloaded via sdkmanager)
- Use sdkmanager to download, not direct URLs
- Format: `system-images;android-34;google_apis;x86_64`

## Download Verification

After download, verify file size:
- Android Studio tar.gz: Should be ~1.4 GB (1400+ MB)
- Platform-tools zip: Should be ~8 MB (8000+ KB)
- Command-line-tools zip: Should be ~146 MB (146000+ KB)

Files under 100 MB are likely HTML error pages.

## Session Notes

2026-04-29 session discovered:
- `2024.1.1.22` returns 404 on multiple attempts
- `2025.3.4.6` (panda4) works reliably
- Nested directory structure in platform-tools zip requires manual extraction fix
- Java 17+ required for SDK tools (Java 11 fails)