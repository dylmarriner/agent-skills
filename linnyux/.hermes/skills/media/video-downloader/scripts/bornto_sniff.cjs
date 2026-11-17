/**
 * bornto_sniff.cjs — Puppeteer: load borntobefuck player, click play, sniff HLS URL
 * Usage: node bornto_sniff.cjs <video_id>
 *
 * Must be run from within the node_service directory (or NODE_PATH set):
 *   cd /media/kubuntux/DEVELOPMENT1/video-downloader/backend/node_service
 *   node /path/to/bornto_sniff.cjs <video_id>
 */
const puppeteer = require('puppeteer');

const BASE = 'https://borntobefuck.com';
const vid = process.argv[2];
if (!vid) { console.error('Usage: node bornto_sniff.cjs <video_id>'); process.exit(1); }

const playerUrl = `${BASE}/videos/${vid}/player?lang=en`;

(async () => {
  let browser;
  try {
    browser = await puppeteer.launch({
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
      ignoreHTTPSErrors: true,
    });

    const page = await browser.newPage();
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
    await page.setViewport({ width: 1280, height: 720 });

    const captured = new Set();
    page.on('request', req => {
      const url = req.url();
      if (url.includes('.m3u8') || (url.includes('zavastream') && url.includes('.m3u8'))) {
        captured.add(url);
      }
    });

    console.error(`Loading ${playerUrl} ...`);
    await page.goto(playerUrl, { waitUntil: 'networkidle2', timeout: 30_000 });
    await new Promise(r => setTimeout(r, 3000));

    // Try clicking selectors in priority order
    const selectors = [
      '.active-video-player',
      '.player-container',
      '.video-player',
      '#player',
      'video',
      'button[aria-label*="play" i]',
      'button.play',
      '.play-btn',
      '[data-play]',
    ];

    for (const sel of selectors) {
      const el = await page.$(sel);
      if (el) {
        console.error(`Clicking "${sel}" ...`);
        await el.click().catch(() => {});
        await new Promise(r => setTimeout(r, 3000));
      }
    }

    // Fallback: click center of page
    if (!captured.size) {
      console.error('No selector matched — clicking center of page');
      await page.mouse.click(640, 360);
      await new Promise(r => setTimeout(r, 5000));
    }

    // Wait for HLS manifest to load
    await new Promise(r => setTimeout(r, 5000));

    const m3u8s = [...captured].filter(u => u.includes('.m3u8'));
    console.log(JSON.stringify({
      success: m3u8s.length > 0,
      m3u8s,
    }));

    await browser.close();
  } catch (err) {
    if (browser) await browser.close().catch(() => {});
    console.error('Error:', err.message);
    console.log(JSON.stringify({ success: false, error: err.message }));
  }
})();
