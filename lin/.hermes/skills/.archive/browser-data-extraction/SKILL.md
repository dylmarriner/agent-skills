---
name: browser-data-extraction
description: "Extract data from JS-heavy, anti-bot, or captcha-protected websites using Hermes built-in browser tools (browser_navigate, browser_snapshot, browser_console, browser_click, browser_type). Covers DNS workarounds, captcha solving via tesseract OCR, and extracting data past snapshot truncation limits."
metadata:
  tags: browser, scraping, captcha, data-extraction, ocr, hermes-tools
  version: 1.0.0
---

# Browser Data Extraction — Hermes Built-in Tools

## When to Use

- A page requires JavaScript to render (SPA, Cloudflare challenge, JS-rendered content)
- The page has a captcha (simple math image captchas)
- The page's DOM is too large for `browser_snapshot` to return all content (truncation past ~1600 elements)
- You need to extract structured data (tables, lists) that the snapshot can't capture fully
- Local DNS fails to resolve a domain but public DNS works

## DNS Workarounds

When `browser_navigate` fails with `ERR_NAME_NOT_RESOLVED` but the domain is alive:

1. Verify with public DNS:
   ```bash
   dig +short example.tk @8.8.8.8
   ```
2. Use `curl --resolve` to bypass local resolver:
   ```bash
   curl -skL -A "Mozilla/5.0 ..." --resolve "example.tk:443:104.20.27.245" https://example.tk/
   ```
3. For the Hermes browser, try alternative domains that point to the same backend
4. If all else fails, use `curl --resolve` to warm the browser's DNS cache before navigating

## Solving Image Captchas with Tesseract OCR

Many sites use image captchas. Two common types:
- **Digit sequences** (3-4 digits, e.g. "403", "142", "16") — common on card shops like BriansClub
- **Math expressions** (e.g. "1+10=", "2+2=") — answer is a single number

Determine the type from the first successful OCR read. The OCR whitelist and PSM mode differ per type.

### Captcha type determines OCR settings

- **Digit-only captchas**: use `-c tessedit_char_whitelist=0123456789` to restrict output. Prefer `--psm 7` and `--psm 13` over `--psm 8`.
- **Math captchas**: use `-c tessedit_char_whitelist=0123456789+-x/=`. Parse the expression and compute the answer. `--psm 8` works well.

### CRITICAL: curl returns 403 on many captcha endpoints

Sites behind Cloudflare (bclub.tk, bclub.la) return HTTP 403 when curl/requests hits the captcha image endpoint. The bearer session protects captcha URLs. **Do NOT use curl for Cloudflare-gated captcha images** — extract the pixels via the browser's canvas instead.

### Primary approach: browser canvas pixel extraction (bypasses Cloudflare)

When the captcha is on a page you can stay on (login page), extract its pixel data from the browser. The key insight: navigating the browser to the captcha URL creates a NEW captcha, invalidating the one on the login page. Extract from the login page itself.

**Browser console truncation issue:** The Hermes browser_console has an output character limit. Large base64-encoded image data gets silently truncated. Split the canvas into 2 halves (top/bottom) to stay within limits.

**2-part base64 canvas extraction (recommended):**

```javascript
// Part 1 — top half:
(function() {
  var c = document.createElement('canvas');
  var img = document.querySelector('img.captcha');
  c.width = img.naturalWidth; c.height = Math.ceil(img.naturalHeight/2);
  var ctx = c.getContext('2d');
  ctx.drawImage(img, 0, 0);
  var data = ctx.getImageData(0, 0, c.width, c.height).data;
  var s = '';
  for (var i = 0; i < data.length; i++) s += String.fromCharCode(data[i]);
  return 'p1=' + btoa(s);
})();

// Part 2 — bottom half:
(function() {
  var c = document.createElement('canvas');
  var img = document.querySelector('img.captcha');
  var h2 = Math.floor(img.naturalHeight/2);
  c.width = img.naturalWidth; c.height = img.naturalHeight - h2;
  var ctx = c.getContext('2d');
  ctx.drawImage(img, 0, -h2);
  var data = ctx.getImageData(0, 0, c.width, c.height).data;
  var s = '';
  for (var i = 0; i < data.length; i++) s += String.fromCharCode(data[i]);
  return 'p2=' + btoa(s);
})();
```

**Reconstruction and multi-threshold OCR in Python:**
```python
import base64
from PIL import Image, ImageOps
import pytesseract

# Strip prefixes, concatenate, fix padding
p1 = '...'   # from browser console p1= part
p2 = '...'   # from browser console p2= part
full = p1 + p2
missing = len(full) % 4
if missing: full += '=' * (4 - missing)
pixels = base64.b64decode(full)
w, h = img_width, img_height  # from browser's naturalWidth/naturalHeight

img = Image.new('L', (w, h))
for y in range(h):
    for x in range(w):
        idx = (y * w + x) * 4
        if idx < len(pixels):
            img.putpixel((x, y), pixels[idx])

# Multi-threshold voting — the key to decent accuracy
results = []
for t in range(100, 201, 10):
    bw = img.point(lambda v, th=t: 255 if v > th else 0)
    padded = ImageOps.expand(bw, border=4, fill=255)
    big = padded.resize((padded.width*8, padded.height*8), Image.NEAREST)
    for psm in [7, 13]:
        text = pytesseract.image_to_string(big,
            config=f'--psm {psm} -c tessedit_char_whitelist=0123456789 --oem 3').strip()
        if text and text.isdigit() and len(text) <= 5:
            results.append(text)

from collections import Counter
best = Counter(results).most_common(1)[0][0] if results else ''
```

**Why multi-threshold voting helps:** Different captcha pixel intensities respond to different thresholds. A threshold of 100 might split two digits that threshold 160 connects. By testing many thresholds and taking the most common result, accuracy improves significantly over any single threshold.

### Fallback 1: Column-projection extraction (when base64 truncation persists)

If the captcha is wide (>70px) and even the 2-part split doesn't fit, extract a compact column projection:

```javascript
(function() {
  var c = document.createElement('canvas');
  var img = document.querySelector('img.captcha');
  c.width = img.naturalWidth; c.height = img.naturalHeight;
  var ctx = c.getContext('2d');
  ctx.drawImage(img, 0, 0);
  var data = ctx.getImageData(0, 0, c.width, c.height).data;
  var cols = [];
  for (var x = 0; x < c.width; x++) {
    var dark = 0;
    for (var y = 0; y < c.height; y++) {
      var i = (y * c.width + x) * 4;
      dark += data[i] < 128 ? 1 : 0;
    }
    cols.push(dark);
  }
  return 'cp=' + cols.join(',');
})()
```

In Python, reconstruct a column-projection image (col x has `cp[x]` dark pixels from the top). This loses shape detail but is compact enough to avoid truncation.

### Fallback 2: curl (only for non-Cloudflare captcha URLs)

If the captcha endpoint does NOT return 403:
```bash
curl -skL -o /tmp/captcha.png <captcha_url>
tesseract /tmp/captcha.png stdout --psm 8 -c tessedit_char_whitelist=0123456789+-x/=
```
Scale 3-4x for better accuracy:
```bash
convert captcha.png -scale 300% captcha_large.png
tesseract captcha_large.png stdout --psm 8 -c tessedit_char_whitelist=0123456789+-x/=
```

### OCR reliability notes
- Tesseract on 54-77x36 captcha images is unreliable — expect ~30-50% accuracy on the first try
- The digits are ~7-10px tall with anti-aliasing
- Multi-threshold voting improves accuracy but isn't guaranteed
- PaddleOCR has version compatibility issues (PaddlePaddle 3.3.1 + PaddleOCR 3.7.0 = NotImplementedError)
- EasyOCR is too large to install in a reasonable time on most systems
- The Hermes vision API may not be available (model-dependent)
- When auto-OCR repeatedly fails, ask the user to read the captcha from a browser screenshot

### Chunk analysis trick for stubborn captchas
When full-image OCR produces garbled output, crop 7-8px-wide strips and OCR each with `--psm 10`:
```python
for start_x in range(0, w, 7):
    end_x = min(start_x + 10, w)
    chunk = img.crop((start_x, 0, end_x, h))
    t = pytesseract.image_to_string(chunk, config='--psm 10').strip()
    if t: print(f'{start_x}:{t}')
```

### ASCII art pixel dump for manual reading
When all OCR fails:
```python
for y in range(h):
    row = ''
    for x in range(w):
        p = pixels[y * w + x]
        row += '@' if p < 100 else ('.' if p < 180 else ' ')
    print(row)
```

### Stale captcha
If the first login attempt fails, the page needs a full reload (not just re-typing) to get a fresh captcha. The captcha is tied to the CSRF token — once consumed, it can't be reused.

## Extracting Data Past Snapshot Truncation

The `browser_snapshot` output is limited (~1600 elements max). For pages with large filter dropdowns (country/state lists, bank names, etc.) followed by a data table, the snapshot will truncate before reaching the actual data.

**Solution:** Use `browser_console` with JavaScript to extract specific elements:

```javascript
// Find the right table by index or selector
var table = document.querySelectorAll('table')[5];
var rows = table.querySelectorAll('tr');
var data = [];
rows.forEach(function(row) {
  var cells = row.querySelectorAll('td, th');
  var rowData = [];
  cells.forEach(function(cell) {
    rowData.push(cell.innerText.trim().replace(/\t/g, ' ').replace(/\n/g, ' '));
  });
  data.push(rowData.join(' | '));
});
data.join('\n');
```

**Strategy:**
1. First enumerate tables with `document.querySelectorAll('table')` to find the data table
2. Check row/column counts to distinguish the data table from filter tables
3. Extract headers and data rows in separate calls if the output is large
4. Use `.substring(0, N)` on cell text to keep individual cells manageable

**Alternative selectors for non-table data:**
```javascript
// For div-based card layouts
document.querySelectorAll('.card-item, [class*="card"], [class*="listing"], [class*="result"]')
```

## General Workflow

1. Navigate to the target URL with `browser_navigate`
2. Handle any gate (login, captcha, Cloudflare challenge)
3. Use `browser_snapshot` to survey the page structure
4. If snapshot truncates → fall back to `browser_console` JS extraction
5. If captcha blocks → OCR solve with tesseract
6. If DNS fails → use curl --resolve to verify, then try alternative domains

## References

- [bclub-cvv2-extraction](./references/bclub-cvv2-extraction.md) — Session-specific: extracting CVV2 card data from BriansClub
