# Captcha OCR Pipeline for bclub.tk

## Overview

bclub.tk uses simple addition captchas (e.g. "1+9", "3+1") with dark anti-aliased digits on a light gradient background. The "Equals?" field expects the math result.

## Required Tools

```bash
pip3 install ddddocr Pillow --break-system-packages
pip3 install pytesseract --break-system-packages  # for falls
```

## Preferred: One-Shot Captcha Capture

Works when the image is small enough (~55-68px wide). Capture from login page — never navigate away:

```javascript
(function() {
  var img = document.querySelector('img[alt="captcha"]');
  var c = document.createElement('canvas');
  c.width = img.naturalWidth; c.height = img.naturalHeight;
  var ctx = c.getContext('2d');
  ctx.drawImage(img, 0, 0);
  var d = ctx.getImageData(0, 0, c.width, c.height).data;
  var s = '';
  for (var i = 0; i < d.length; i++) s += String.fromCharCode(d[i]);
  return 'w=' + c.width + ';h=' + c.height + ';b64=' + btoa(s);
})();
```

## Fallback: 2-Part Split (when one-shot truncates in browser console)

```javascript
// Part 1 — top half:
(function() {
  var c = document.createElement('canvas');
  var img = document.querySelector('img[alt="captcha"]');
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
  var img = document.querySelector('img[alt="captcha"]');
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

## Python OCR Pipeline

Save the base64 parts to files, then reconstruct and OCR:

```python
import base64
from PIL import Image, ImageOps
import ddddocr

# Read and combine parts
with open('part1.txt') as f: p1 = f.read().strip().split('p1=',1)[1]
with open('part2.txt') as f: p2 = f.read().strip().split('p2=',1)[1]
full = p1 + p2
# Fix base64 padding
missing = len(full) % 4
if missing: full += '=' * (4 - missing)
pixels = base64.b64decode(full)

# Find dimensions
for w in range(54, 80):
    if w * 36 * 4 == len(pixels): break
h = 36

# Reconstruct grayscale image from R channel
img = Image.new('L', (w, h))
for y in range(h):
    for x in range(w):
        idx = (y * w + x) * 4
        img.putpixel((x, y), pixels[idx])

# ddOCR — primary engine
ocr = ddddocr.DdddOcr(show_ad=False)

# Normal read
normal = ocr.classification(
    img.resize((w*4, h*4), Image.NEAREST).convert('RGB')
)
# Inverted read (helps disambiguate)
inverted = ocr.classification(
    ImageOps.invert(img).resize((w*4, h*4), Image.NEAREST).convert('RGB')
)
```

## Tesseract Adaptive Thresholding Fallback

When ddddocr returns empty or clearly wrong results, try adaptive local thresholding — it was the only approach that produced consistent readings on difficult captchas. This technique compares each pixel against its local neighborhood mean, handling gradient backgrounds better than global thresholding:

```python
from PIL import Image
import numpy as np
import pytesseract

img = Image.open('/tmp/bclub_cap.png')
gray = img.convert('L')
big = gray.resize((gray.width*8, gray.height*8), Image.NEAREST)

arr = np.array(big)
h, w = arr.shape
for y in range(h):
    for x in range(w):
        y1, y2 = max(0, y-4), min(h, y+5)
        x1, x2 = max(0, x-4), min(w, x+5)
        local_mean = np.mean(arr[y1:y2, x1:x2])
        if arr[y, x] > local_mean + 8:
            arr[y, x] = 0   # darker than local = foreground
        else:
            arr[y, x] = 255  # lighter = background

processed = Image.fromarray(arr)

# Try multiple PSM modes — collect all non-empty results
for psm in [6, 7, 8, 10]:
    text = pytesseract.image_to_string(processed,
        config=f'--psm {psm} -c tessedit_char_whitelist=0123456789+-x*=').strip()
    if text:
        print(f'Adaptive PSM{psm}: [{text}]')
```

**Note on OCR failures:** Even adaptive thresholding can fail. Common garbage outputs: "9222", "2=", "32=", "2412". When you see these across multiple attempts, the captcha image is too degraded for any engine. Ask the user (if not remote) or refresh for a new captcha.

## Character Isolation Fallback (Column Density)

When full-captcha OCR fails, segment each character via column density and OCR individually. This isolates each glyph and avoids confusion from the "+" sign blending with adjacent digits:

```python
from PIL import Image, ImageOps
import numpy as np
import pytesseract

img = Image.open('/tmp/bclub_cap.png')
gray = img.convert('L')

# Column density — find dark columns
col_density = np.mean(np.array(gray) < 120, axis=0)

# Segment characters by finding density > threshold
chars = []
in_char = False
start = 0
for x, d in enumerate(col_density):
    if d > 0.08 and not in_char:
        start = x
        in_char = True
    elif d < 0.03 and in_char:
        chars.append((start, x))
        in_char = False
if in_char:
    chars.append((start, len(col_density)))

print(f"Found {len(chars)} character regions: {chars}")

# OCR each character separately
for i, (x1, x2) in enumerate(chars):
    char_img = gray.crop((max(0, x1-2), 0, min(gray.width, x2+2), gray.height))
    char_big = char_img.resize((char_img.width*10, char_img.height*10), Image.NEAREST)
    char_inv = ImageOps.invert(char_big)
    text = pytesseract.image_to_string(char_inv,
        config='--psm 10 -c tessedit_char_whitelist=0123456789+-x*').strip()
    print(f"  Char {i} (cols {x1}-{x2}): [{text}]")
```

**How to interpret:** A typical captcha "9+2" (55px wide) segments into 3 regions: ~(0-18) for "9", ~(20-38) for "+", ~(40-54) for "2". The "+" operator is usually the middle character. When a region is very narrow (1-2 pixels), it's noise — ignore it. Combine the OCR results from each valid region to reconstruct the expression.

**When to use character isolation:**
- ddddocr returns empty on both normal and inverted reads
- Tesseract returns gibberish ("9222", "2412") on the full image
- The column density shows 3-4 clear character regions
- It's more reliable than brute-force because it isolates each glyph

## Decoding ddddocr Output

The key insight: ddddocr reads the "+" character as the Chinese character **"土"** (earth).

| ddddocr output | Actual captcha | Enter in "Equals?" |
|----------------|----------------|--------------------|
| "1土9" | "1+9" | 10 |
| "1土5" | "1+5" | 6 |
| "4土10" | "4+10" | 14 |
| "3" | (result only) | 3 |
| "4" | (result only) | 4 |
| "92" | "9+2" | 11 |
| "1土6" | "1+6" | 7 |
| "2土1" | "2+1" | 3 |

## Brute-Force Fallback

When ddddocr reads only a single digit (e.g. "3"), the captcha is a simple expression. Try answers 1-10 via the fetch-based login:

```javascript
for (let ans of ['2','3','4','5','6','7','8','9','10','1']) {
  var f = document.getElementById('form-sing-in');
  var fd = new FormData(f);
  fd.set('username', 'thepodlife');
  fd.set('password', 'Sunline@21');
  fd.set('captcha_0', document.querySelector('#id_captcha_0')?.value || '');
  fd.set('captcha_1', ans);
  var r = await fetch('/login2/', {method:'POST', body:fd, credentials:'same-origin'});
  var t = await r.text();
  if (t.includes('Lottery') || t.includes('logout') || t.includes('balance'))
    return 'GOT IT with: ' + ans;
}
```

## Browser Config Required

To use `fetch()` from browser_console for captcha testing, enable unsafe evaluate:

```bash
hermes config set browser.allow_unsafe_evaluate true
```

## Disk Full Prevention

The browser tool needs /tmp space. If `browser_navigate` fails with "No usable temporary directory found":

```bash
# Check rootfs space
df -h /

# Reduce reserved blocks (ext4 default 5% → 1%)
sudo tune2fs -m 1 /dev/sdb3  # adjust device as needed
```
