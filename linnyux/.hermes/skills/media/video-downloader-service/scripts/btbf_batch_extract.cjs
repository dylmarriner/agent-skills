/**
 * btbf_batch_extract.cjs — Batch borntobefuck HLS extraction
 * Usage: node btbf_batch_extract.cjs <id1> <id2> ...
 *
 * Runs multiple video IDs through a single Puppeteer session (reuses
 * the browser), extracting HLS URLs for each. Much more efficient
 * than launching a browser per ID.
 *
 * Outputs JSON array: [{id, success, m3u8s[]}, ...]
 *
 * Run from node_service directory:
 *   cd /media/kubuntux/.../backend/node_service
 *   NODE_PATH=$(pwd)/node_modules node btbf_batch_extract.cjs 29099 24178 11410
 */
const puppeteer = require('puppeteer');

const ids = process.argv.slice(2);
if (!ids.length) { process.exit(1); }

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
    ignoreHTTPSErrors: true,
  });

  const results = [];
  for (const id of ids) {
    const playerUrl = `https://borntobefuck.com/videos/${id}/player?lang=en`;
    try {
      const page = await browser.newPage();
      await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');
      await page.setViewport({ width: 1280, height: 720 });

      const captured = new Set();
      page.on('request', req => { if (req.url().includes('.m3u8')) captured.add(req.url()); });

      await page.goto(playerUrl, { waitUntil: 'networkidle2', timeout: 30000 });
      await new Promise(r => setTimeout(r, 3000));

      for (const sel of ['.active-video-player', '.player-container', 'video']) {
        const el = await page.$(sel);
        if (el) { await el.click().catch(() => {}); await new Promise(r => setTimeout(r, 2000)); }
      }
      if (!captured.size) {
        await page.mouse.click(640, 360);
        await new Promise(r => setTimeout(r, 5000));
      }
      await new Promise(r => setTimeout(r, 5000));

      results.push({ id, success: captured.size > 0, m3u8s: [...captured].filter(u => u.includes('.m3u8')) });
      await page.close();
    } catch (e) {
      results.push({ id, success: false, error: e.message });
    }
  }

  console.log(JSON.stringify(results));
  await browser.close();
})();
