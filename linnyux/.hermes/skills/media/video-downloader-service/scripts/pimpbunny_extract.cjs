/**
 * pimpbunny_extract.cjs — Extract video URL from pimpbunny via JSON-LD
 * Usage: node pimpbunny_extract.cjs <page_url>
 * Output: JSON {success, url, title, cookies[], error?}
 *
 * Uses Puppeteer to load the page, then extracts contentUrl from
 * <script type="application/ld+json"> in the rendered HTML.
 * Returns cookies for subsequent curl/aria2c download.
 *
 * Download with:
 *   curl -L --cookie <cookies_file> -H "Referer: <page_url>" -o output.mp4 <contentUrl>
 *
 * Pitfalls:
 *   - contentUrl is always 720p (*_720p.mp4). 1080p variants exist but have
 *     different session-signed hashes that return HTTP 400.
 *   - Cookies have expires=-1 (session cookies). Clamp to 0 in Netscape format.
 *   - get_file URLs redirect through remote_control.php — yt-dlp chokes on this.
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

    // Extract JSON-LD for contentUrl
    const result = await page.evaluate(() => {
      const scripts = document.querySelectorAll('script[type="application/ld+json"]');
      for (const s of scripts) {
        try {
          const data = JSON.parse(s.textContent);
          if (data.contentUrl) return { source: 'json-ld', url: data.contentUrl, title: data.name || '' };
          if (data.video && data.video.contentUrl)
            return { source: 'json-ld', url: data.video.contentUrl, title: data.video.name || '' };
        } catch(e) {}
      }
      // Fallback: look for video source elements
      const vids = document.querySelectorAll('video source');
      if (vids.length) return { source: 'video-source', url: vids[0].src, title: document.title };
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
