/**
 * pimpbunny_extract.cjs — Load pimpbunny page, extract JSON-LD contentUrl
 * Usage: cd /media/kubuntux/DEVELOPMENT1/video-downloader/backend/node_service
 *        node <path-to-script>/pimpbunny_extract.cjs <url>
 *
 * Returns JSON: {success, url, title, cookies}
 * Download the extracted URL with curl using the returned cookies + Referer.
 */
const puppeteer = require('puppeteer');

const url = process.argv[2];
if (!url) { console.error('Usage: node pimpbunny_extract.cjs <url>'); process.exit(1); }

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
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
    await new Promise(r => setTimeout(r, 3000));

    const result = await page.evaluate(() => {
      const scripts = document.querySelectorAll('script[type="application/ld+json"]');
      for (const s of scripts) {
        try {
          const data = JSON.parse(s.textContent);
          if (data.contentUrl) return { url: data.contentUrl, title: data.name || '' };
          if (data.video && data.video.contentUrl) return { url: data.video.contentUrl, title: data.video.name || '' };
        } catch(e) {}
      }
      return null;
    });

    const cookies = await page.cookies();
    console.log(JSON.stringify({
      success: !!result,
      ...(result || { error: 'No video URL found' }),
      cookies: cookies.map(c => ({ name: c.name, value: c.value })),
    }));
    await browser.close();
  } catch (e) {
    if (browser) await browser.close().catch(() => {});
    console.log(JSON.stringify({ success: false, error: e.message }));
  }
})();
