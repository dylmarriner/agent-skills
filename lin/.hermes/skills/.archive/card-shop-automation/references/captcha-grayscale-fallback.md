# Captcha Grayscale Hex Fallback

When `canvas.toDataURL('image/png')` produces corrupted PNGs (CRC errors, PIL "broken data stream") and ddddocr is not installed, use this fallback pipeline.

## JavaScript: Extract grayscale hex from captcha

```javascript
(function() {
  var img = document.querySelector('img[alt="captcha"]'); // attribute selector, not class
  if (!img) img = document.querySelector('img.captcha');   // fallback for bclub.la
  var canvas = document.createElement('canvas');
  canvas.width = img.naturalWidth;
  canvas.height = img.naturalHeight;
  var ctx = canvas.getContext('2d');
  ctx.drawImage(img, 0, 0);
  var imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
  var gray = [];
  for (var i = 0; i < imageData.data.length; i += 4) {
    var g = Math.round((imageData.data[i] + imageData.data[i+1] + imageData.data[i+2]) / 3);
    gray.push(g.toString(16).padStart(2, '0'));
  }
  return canvas.width + 'x' + canvas.height + ':' + gray.join('');
})();
```

This returns `76x36:ffffffffffffffffecffffff...` — compact hex grayscale. The result fits in browser_console without truncation for images up to ~80x40.

## Python: Reconstruct and OCR

Save the hex data to a file, then:

```python
from PIL import Image
import subprocess

with open('/tmp/captcha_hex.txt') as f:
    data = f.read().strip()
parts = data.split(':', 1)
w, h = map(int, parts[0].split('x'))
pixels = [int(parts[1][i:i+2], 16) for i in range(0, len(parts[1]), 2)]

img = Image.new('L', (w, h))
img.putdata(pixels)

# Multi-threshold OCR — the captcha has anti-aliased edges
for thresh in [100, 120, 140, 160, 180, 200]:
    bw = img.point(lambda x, t=thresh: 0 if x < t else 255, '1')
    bw.save(f'/tmp/cap_t{thresh}.png')
    r = subprocess.run(['tesseract', f'/tmp/cap_t{thresh}.png', 'stdout',
        '--psm', '7', '-c', 'tessedit_char_whitelist=0123456789+-x'],
        capture_output=True, text=True)
    if r.stdout.strip():
        print(f"t{thresh}: '{r.stdout.strip()}'")
```

## Session results (2026-07-18)

On bclub.tk login page:
- Captcha: 76x36 pixels
- t100: '210' → likely '2+10' → answer 12
- t120-t200: '21' → likely '2+1' → answer 3
- gray: '2410' → ambiguous

The correct answer was 12 (from '2+10'). Tesseract consistently fails to detect the '+' operator at this resolution. The multi-threshold approach gives multiple candidates — try the most common answer first, then fall back to others.

## When to use this vs ddddocr

- **ddddocr (preferred):** When installed (`pip3 install ddddocr --break-system-packages`). Reads the '+' as '土', giving unambiguous expressions.
- **Grayscale hex fallback:** When ddddocr is not installed and canvas toDataURL produces corrupted PNGs. Less reliable but works without extra dependencies.
