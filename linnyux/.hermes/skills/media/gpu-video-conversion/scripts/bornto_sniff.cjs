/**
 * bornto_sniff.cjs — Puppeteer: load borntobefuck player, click play, sniff HLS
 * Usage: cd /media/kubuntux/DEVELOPMENT1/video-downloader/backend/node_service
 *        node <path-to-script>/bornto_sniff.cjs <video_id>
 *
 * Navigates to https://borntobefuck.com/videos/{id}/player?lang=en,
 * registers a .m3u8 request listener, clicks play area selectors,
 * waits 8s for HLS manifest, returns JSON with m3u8s[].
 *
 * Handles both CDN backends:
 *   - Zavastream (content.zavastream.com/.../index.m3u8) — older videos
 *   - Bunny CDN (vz-*.b-cdn.net/.../playlist.m3u8) — newer videos
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
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');
    await page.setViewport({ width: 1280, height: 720 });
    const captured = new Set();
    page.on('request', req => { const url = req.url(); if (url.includes('.m3u8')) captured.add(url); });
    console.error(`Loading ${playerUrl} ...`);
    await page.goto(playerUrl, { waitUntil: 'networkidle2', timeout: 30000 });
    await new Promise(r => setTimeout(r, 3000));
    for (const sel of ['.active-video-player', '.player-container', '.video-player', '#player', 'video', 'button.play']) {
      const el = await page.$(sel);
      if (el) { await el.click().catch(() => {}); await new Promise(r => setTimeout(r, 2000)); }
    }
    if (!captured.size) { await page.mouse.click(640, 360); await new Promise(r => setTimeout(r, 5000)); }
    await new Promise(r => setTimeout(r, 5000));
    const m3u8s = [...captured].filter(u => u.includes('.m3u8'));
    console.log(JSON.stringify({ success: m3u8s.length > 0, m3u8s }));
    await browser.close();
  } catch (err) {
    if (browser) await browser.close().catch(() => {});
    console.log(JSON.stringify({ success: false, error: err.message }));
  }
})();
