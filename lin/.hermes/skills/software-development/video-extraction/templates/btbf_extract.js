const puppeteer = require('puppeteer');

/**
 * btbf_extract.js — Extract HLS URLs from borntobefuck.com videos.
 *
 * Usage:
 *   NODE_PATH=/path/to/node_service/node_modules node btbf_extract.js
 *
 * Edit the urlsToExtract array below with the BTBF watch page URLs.
 * Outputs: <watch_url>|<hls_master_url> per line to stdout.
 */
(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });

  // EDIT THIS: list the BTBF watch URLs to extract
  const urlsToExtract = [
    'https://borntobefuck.com/watch/34142',
    'https://borntobefuck.com/watch/33974',
  ];

  for (const videoUrl of urlsToExtract) {
    const page = await browser.newPage();
    await page.setUserAgent(
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    );

    const hlsUrls = [];
    await page.setRequestInterception(true);
    page.on('request', req => {
      const u = req.url();
      if (u.includes('.m3u8') && u.includes('zavastream') && u.includes('index.m3u8')) {
        hlsUrls.push(u);
      }
      req.continue();
    });

    await page.goto(videoUrl, { waitUntil: 'networkidle2', timeout: 30000 });
    await new Promise(r => setTimeout(r, 3000));

    await page.evaluate(() => {
      const iframe = document.querySelector('iframe');
      if (iframe) {
        try {
          const d = iframe.contentDocument || iframe.contentWindow.document;
          const b = d.querySelector('button');
          if (b && b.textContent.toLowerCase().includes('play')) b.click();
        } catch (e) {}
      }
    });

    await new Promise(r => setTimeout(r, 10000));

    const unique = [...new Set(hlsUrls)];
    console.log(videoUrl + '|' + (unique[0] || 'none'));
    await page.close();
  }

  await browser.close();
})();
