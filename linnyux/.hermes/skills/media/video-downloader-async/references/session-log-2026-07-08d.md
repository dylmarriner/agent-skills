# Session Log: 2026-07-08d — borntobefuck cracked, 12 videos batch

## Downloads completed (12 videos, ~2.3GB total)

| Video | Site | Size | Method |
|-------|------|------|--------|
| ANGELA WHITE - POV Threesome w/ Mia Malkova | pornhub | 135MB | yt-dlp --impersonate chrome |
| Step Bro S15E4 | pornhub | 157MB | yt-dlp --impersonate chrome |
| BANGBROS - Blonde PAWG Mia Malkova | pornhub | 313MB | yt-dlp --impersonate chrome |
| Mia Malkova Blowjob Fucking POV | eporner | 132MB | yt-dlp direct |
| A Lucky Guy Fucks Mia Malkova (cached) | eporner | 278MB | yt-dlp (already on disk) |
| BANGBROS - Bailey Brooke & Mia Malkova | xnxx | 238MB | yt-dlp --impersonate chrome |
| VRBangers - Mia Malkova + Riley Reid | xhamster | 76MB | yt-dlp --impersonate chrome |
| Louisa Rain Enjoys Riding Her Dildo | pimpbunny | 104MB | Puppeteer→JSON-LD→cookies+curl |
| Wettmelons Gets Creampied In White Lingerie | borntobefuck | 192MB | Puppeteer→iframe click→HLS→yt-dlp |
| Lana Rhoades Sextape Gets Railed | borntobefuck | 296MB | Puppeteer→iframe click→HLS→yt-dlp |
| Naughty Japanese Goddess Got Fucked | eporner | 171MB | yt-dlp direct |
| Big Bouncing Boobs Compilation POV | eporner | 246MB | yt-dlp direct |

## Step-by-step: borntobefuck extraction

### Confirmed working pipeline (2026-07-08)

The earlier session log (session-log-2026-07-08c.md) marked borntobefuck as "not reliably extractable" due to its canvas-based player. This session PROVED extraction is possible via HLS stream capture.

**The trick:** Although the video renders to a `<canvas>` element (no `<video>` in DOM), the underlying HLS manifest URL on `content.zavastream.com` is still visible via Puppeteer network interception. The canvas player uses MediaSource to feed HLS fragments, and the manifest URL is fetched as an XHR request that Puppeteer can intercept.

**Full extraction script pattern:**
```javascript
const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox','--disable-setuid-sandbox','--disable-dev-shm-usage'] });
  const page = await browser.newPage();
  await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');

  // Intercept network requests for HLS manifests
  const hlsUrls = [];
  await page.setRequestInterception(true);
  page.on('request', req => {
    const url = req.url();
    if (url.includes('.m3u8') && url.includes('zavastream')) {
      hlsUrls.push(url);
    }
    req.continue();
  });

  // Load main page
  await page.goto('https://borntobefuck.com/watch/<ID>', { waitUntil: 'networkidle2', timeout: 30000 });
  await new Promise(r => setTimeout(r, 3000));

  // Click Play inside the iframe
  await page.evaluate(() => {
    const iframe = document.querySelector('iframe');
    if (iframe) {
      try {
        const doc = iframe.contentDocument || iframe.contentWindow.document;
        const btn = doc.querySelector('button');
        if (btn && btn.textContent.toLowerCase().includes('play')) btn.click();
      } catch(e) {}
    }
  });

  // Wait for HLS manifest to load
  await new Promise(r => setTimeout(r, 8000));

  // Get unique master playlist URLs
  const masterUrls = [...new Set(hlsUrls.filter(u => u.includes('index.m3u8')))];
  console.log('HLS:', masterUrls[0] || 'none');

  await browser.close();
})();
```

**Download the extracted HLS URL:**
```bash
yt-dlp --impersonate chrome --output "filename.mp4" \
  --referer "https://borntobefuck.com/" \
  --add-header "Origin:https://borntobefuck.com" \
  "https://content.zavastream.com/<num>/<uuid>/index.m3u8"
```

### Ad-gating behavior
- Landing page shows "Unlock the video (4 clicks left)" overlay
- The iframe (`/videos/<id>/player?lang=en`) contains a "Play" button
- Clicking Play starts the HLS stream even though the player is canvas-based
- No actual click-through of ads was needed — the Play button in the iframe sufficed
- The `content.zavastream.com` CDN accepts yt-dlp directly without additional auth

### NODE_PATH pitfall
When running Puppeteer scripts from `/tmp/`, the node binary can't find `puppeteer` even though it's installed in `node_service/node_modules/`. Fix:
```bash
NODE_PATH=/path/to/node_service/node_modules node /tmp/script.js
```

## Step-by-step: pimpbunny extraction (re-verified)

Confirmed working as documented in session-log-2026-07-08b.md. Key points:
1. Puppeteer service extracts JSON-LD from `<script type="application/ld+json">`
2. The `contentUrl` field contains the direct video path
3. Cookies from the Puppeteer session are needed for anti-hotlink bypass
4. curl downloads with `-b <cookie_file> -H "Referer: <page_url>"`

**Verification:** The extracted 720p URL returned a 1x1 GIF without cookies, but a full 104MB video with cookies+Referer.

## File locations
- All downloads: `/mnt/storage/videos/` (SMB `\\kubuntux\videos`)
- VideoSnap project: `/media/kubuntux/DEVELOPMENT1/video-downloader/`
