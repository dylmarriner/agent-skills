/**
 * playwright-intercept.js — Download videos from sites with
 * session-tokenized CDN URLs (Flowplayer/KT Player, etc.).
 *
 * Usage:
 *   npm install playwright
 *   npx playwright install chromium
 *   node playwright-intercept.js <url> [output.mp4]
 *
 * HOW IT WORKS:
 * 1. Opens the page in a headless Chromium browser
 * 2. Registers a response interceptor to capture video CDN URLs
 * 3. Clicks the video player to start playback
 * 4. Captures the session-tokenized remote_control.php or CDN URL
 * 5. Downloads the full video using the browser's cookies
 */

const { chromium } = require('playwright');
const fs = require('fs');
const https = require('https');
const http = require('http');

const TARGET_URL = process.argv[2];
const OUTPUT = process.argv[3] || 'download.mp4';

if (!TARGET_URL) {
  console.error('Usage: node playwright-intercept.js <url> [output.mp4]');
  process.exit(1);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  });
  const page = await context.newPage();

  let videoUrl = null;

  // Intercept all responses to find video CDN URLs
  page.on('response', (response) => {
    const url = response.url();
    const cl = response.headers()['content-length'];

    // Sites like PimpBunny serve the full video via remote_control.php
    if (url.includes('remote_control.php') && url.includes('file=')) {
      console.log('remote_control URL:', url);
      console.log('Status:', response.status(), 'Content-Length:', cl, 'bytes');
      videoUrl = url;
    }

    // Some sites use CDN URLs directly (bxcdn, sadbaguette, etc.)
    if ((url.includes('bxcdn') || url.includes('sadbaguette')) && url.includes('.mp4')) {
      console.log('CDN URL:', url, 'Content-Length:', cl, 'bytes');
      if (!videoUrl) videoUrl = url;
    }

    // get_file endpoints often redirect (302) to the real CDN
    if (url.includes('get_file') && !videoUrl) {
      console.log('get_file URL:', url, '(may redirect)');
    }
  });

  // Navigate to the page
  await page.goto(TARGET_URL, { waitUntil: 'domcontentloaded', timeout: 30000 }).catch(() => {});

  // Wait for page to settle (ads load, player initializes)
  await new Promise(r => setTimeout(r, 3000));

  // Start playback — click the video player
  await page.evaluate(() => {
    document.querySelectorAll('video, .fp-player, [class*="flowplayer"], [class*="kt"]').forEach(el => {
      if (el.click) el.click();
    });
  });

  // Wait for video to start loading (ads may play first)
  await new Promise(r => setTimeout(r, 10000));

  // Try to skip any ad
  await page.evaluate(() => {
    document.querySelectorAll('[class*="skip"], [aria-label*="skip"], [title*="skip"]').forEach(el => {
      if (el.click) el.click();
    });
  });

  // Give it more time for the video stream to start
  await new Promise(r => setTimeout(r, 5000));

  if (!videoUrl) {
    console.log('No video URL captured. Check if the site requires premium/login.');
    await browser.close();
    process.exit(1);
  }

  // Get cookies from the browser session for authenticated download
  const cookies = await context.cookies();
  const cookieStr = cookies.map(c => `${c.name}=${c.value}`).join('; ');

  console.log('\nDownloading...');
  const file = fs.createWriteStream(OUTPUT);

  await new Promise((resolve, reject) => {
    const opts = {
      headers: {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        'Referer': new URL(TARGET_URL).origin + '/',
        'Cookie': cookieStr
      }
    };
    const get = videoUrl.startsWith('https') ? https.get : http.get;

    get(videoUrl, opts, (res) => {
      // Follow redirects (get_file → remote_control → CDN)
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        console.log('Redirect →', res.headers.location);
        file.close();
        fs.unlinkSync(OUTPUT);
        const get2 = res.headers.location.startsWith('https') ? https.get : http.get;
        get2(res.headers.location, { ...opts }, (res2) => {
          pipeDownload(res2, file, OUTPUT, resolve, reject);
        }).on('error', reject);
        return;
      }
      pipeDownload(res, file, OUTPUT, resolve, reject);
    }).on('error', reject);
  });

  const stats = fs.statSync(OUTPUT);
  console.log(`\nSaved: ${(stats.size / 1024 / 1024).toFixed(1)}MB to ${OUTPUT}`);

  await browser.close();
})();

function pipeDownload(res, file, outputPath, resolve, reject) {
  const total = parseInt(res.headers['content-length'] || '0');
  let downloaded = 0;
  res.on('data', (chunk) => {
    downloaded += chunk.length;
    if (total) {
      const pct = (downloaded / total * 100).toFixed(1);
      process.stdout.write(`\r${pct}% (${(downloaded/1024/1024).toFixed(1)}MB / ${(total/1024/1024).toFixed(1)}MB)`);
    } else {
      process.stdout.write(`\r${(downloaded/1024/1024).toFixed(1)}MB`);
    }
  });
  res.pipe(file);
  file.on('finish', () => {
    file.close();
    resolve();
  });
  file.on('error', reject);
}
