# Hydra Tool Download Sources

## Official Site

- **Real site:** https://hydradongle.com/
- **Download page:** Click "Download" nav dropdown → "Download Software"
  - The dropdown link "Download Software" at ref=e318 on the homepage reveals the actual download page
  - Direct URL `https://hydradongle.com/download/software` works when navigated from the homepage with JS state
  - The page lists version v2026.4.8.3 as the latest download (but changelog shows v2026.7.11.1 as newest update)
  - Listed stats: 200MB, MD5 `1930a4a92539c38137cccf65f4322d86`, ZIP password `hydratool`

## Fake Download Pages (AVOID)

- `https://hydra-tool-downl0ad.github.io/.github/` — fake page on GitHub Pages
  - Redirects to github.com homepage after "Download Zip" click
  - Has a `Failed to fetch` JS error — the page tries to fetch from a broken backend
  - Just a scam link-farm, does not host any actual tool

## Actual Download Mirrors (extracted from page source)

### MediaFire (primary)
- URL: `https://www.mediafire.com/file/g3nmiq463v79zgc/Hydra+Tool+Setup+V7.0.rar/file`
- **Actual file size: 1.88GB** (site incorrectly lists 200MB)
- **Heavily throttled for free users** — ~300KB/s, would take ~5h for 1.88GB
- Direct download URL is time-limited (30s), extracted via JS: `document.querySelector('a[href*="download"]').href`
- RAR password: `hydratool`
- Installer format: Smart Install Maker v5.04 (SIM) — requires Windows VM

### Mega (mirror — MAY BE DEAD)
- URL: `https://mega.nz/file/s1V3TISL#QqgRKwkXaJnIIWvvhCuCPOSXcdeEMYd2bB2RLFiO0LI`
- **Status: ENOENT (file not found) as of 2026-07-19**
- Use `megadl '<url>' --path /mnt/storage/` for download

### Google Drive (mirror)
- URL: `https://drive.google.com/file/d/1TaviKfYZy76N2MSM75dt5BpvbWDhOf_y/view?usp=sharing`
- File ID: `1TaviKfYZy76N2MSM75dt5BpvbWDhOf_y`
- Direct download: `https://docs.google.com/uc?export=download&id=1TaviKfYZy76N2MSM75dt5BpvbWDhOf_y`
- For large files, Google shows a virus scan interstitial — extract the confirm token from the response page

## Version Discrepancy

The site header lists v2026.4.8.3 but the changelog shows updates through v2026.7.11.1 (July 11, 2026). The download file is named "Hydra Tool Setup V7.0" which seems to be a unified installer that self-updates.

## Download Workflow

1. Navigate to `https://hydradongle.com/`
2. Click "Download" dropdown in nav → "Download Software"
3. Extract download URLs from page source: `curl -s 'https://hydradongle.com/download/software' | grep -oP 'https?://[^"'\'' \t<>]*\.(zip|exe|rar)[^"'\'' \t<>]*'`
4. Try Google Drive first (fastest), Mega second, MediaFire last
5. Download to secondary drive (1.88GB + extraction needs 3-4GB)
6. Extract with `unrar x -p"hydratool" /path/to/file.rar /output/dir`
7. Transfer to Windows VM via RDP drive mount or Python HTTP server
