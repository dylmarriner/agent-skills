# Persian / Arabic OCR Notes

## Session 1 (prior): Tesseract-only
- tesseract-ocr-fas gave poor results on scanned CamScanner document
- Multiple preprocessing methods tried (grayscale, adaptive threshold) — marginal improvement
- Deepseek provider does not support vision/image inputs

## Session 2 (May 2026): EasyOCR

**Document:** 2-page scanned PDF, Persian (Farsi), gold/jewelry invoice
**Source:** ZOMORROD GOLD GALLERY (Bandar Abbas, Iran)
**Phone:** +9891****027

### What worked

| Method | Result |
|--------|--------|
| `pdftotext` | Empty (scan) |
| `tesseract -l fas+eng` @300/600DPI + preprocessing | Poor — garbled output |
| `pipx install easyocr` | Failed — GPU incompatible (MX150, CC 6.1 < 7.5) |
| Manual venv + CPU-only torch + easyocr | **Good** — readable Persian text, numbers, column headers |
| Cropping into 3 regions (header/body/footer) | Better table structure recognition |
| Filtering by confidence > 0.3 | Cleaner output, less noise |

### Key commands used

```bash
# Setup for old GPU (MX150 CC 6.1)
python3 -m venv /tmp/easyocr_venv
source /tmp/easyocr_venv/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install easyocr

# OCR with confidence filtering + y-position for table layout
easyocr -l fa -f /tmp/page-1.png --detail=1 --gpu=false

# Python API with confidence filtering
python3 << 'EOF'
import easyocr
reader = easyocr.Reader(['fa', 'en'], gpu=False)
results = reader.readtext('page.png', detail=1)
for bbox, text, conf in results:
    if conf > 0.3:
        print(f"[{conf:.2f}] {text}")
EOF
```

### Document structure identified

The invoice had a consistent columnar layout:
- **Header:** Shop name (طلاسازی زمرد), invoice number (شماره), date (مورخ), buyer (خریدار)
- **Body:** Table with columns for type (نوع کالا), weight (وزن), carat/purity (عیار), price (قیمت)
- **Footer:** Total, gallery name (گالری زمرد), address (بندرعباس...), phone (+9891****027)

### Persian invoice vocabulary observed

| Persian | English |
|---------|---------|
| شماره | Number/Invoice # |
| طلاسازی | Goldsmith / Gold workshop |
| زمرد | Zomorrod (Emerald — shop name) |
| مورخ / تاریخ | Dated |
| خریدار | Buyer |
| نوع کالا | Product type |
| وزن | Weight |
| عیار | Carat / Purity |
| قیمت | Price |
| توصیحات | Description |
| طلای خام | Raw gold |
| بندرعباس | Bandar Abbas (city) |

### Optimizations for future
- Start with EasyOCR immediately for Persian/Arabic scanned docs — skip tesseract
- Always install CPU-only torch if machine has old GPU (SM < 7.5)
- Crop document into horizontal regions before OCR for table-heavy documents
- Use `detail=0` with `paragraph=True` for rough document overview, `detail=1` with confidence filtering for precise extraction

## Session 3 (May 2026 — font & color matching)

After OCR extraction, attempted to edit the scanned PDF by erasing text with white rectangles and overlaying clean Persian text. **User rejected the result twice** — first for font mismatch, then for "logos and colour".

### What went wrong
1. Used pure black ink (0,0,0) — original was dark reddish-brown (R=164, G=70, B=33)
2. Used Noto Sans Arabic (modern sans-serif) — original was Naskh-style print
3. Erased with pure white rectangles — destroyed warm paper tone and colored design elements
4. Converted to grayscale before editing — destroyed colored stamps and gold logos

### Correct approach for editing scanned Persian documents
```python
# Step 1: Analyze ink color from original
from PIL import Image
img = Image.open("page-1.png").convert("RGB")
px = img.load()
r_sum = g_sum = b_sum = count = 0
for x in range(1200, 2200):
    for y in range(160, 370):  # text region
        r, g, b = px[x, y]
        if r < 200 or g < 200 or b < 200:  # non-white = ink
            r_sum += r; g_sum += g; b_sum += b; count += 1
ink_color = (r_sum//count, g_sum//count, b_sum//count) if count else (0,0,0)

# Step 2: Use Naskh font (more natural for Persian docs)
font = ImageFont.truetype(
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf", 72)

# Step 3: Sample background color too, use it for erasure
bg_color = ...  # sample from edge of white space near text

# Step 4: Erase with background color, write with ink color
draw.rectangle([1200, 160, 2200, 370], fill=bg_color)
draw.text((2150, 210), "طلاسازی زمرد", fill=ink_color, font=font)
```

## Session 4 (May 2026 — HTML-to-PDF with handwritten font)

After the failed PDF edit attempts, user wanted an editable handwritten-looking PDF. The solution: recreate the document as HTML with Noto Nastaliq Urdu (calligraphic font) and convert via Chrome headless.

### Chrome headless PDF conversion

```bash
google-chrome --headless --disable-gpu --no-margins \
  --print-to-pdf-no-header \
  --print-to-pdf="/path/to/output.pdf" \
  --page-size=A4 \
  "file:///path/to/document.html"
```

### Key HTML structure

```html
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
<link href="https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;700&display=swap" rel="stylesheet">
<style>
@page { size: A4; margin: 0; }
body { background: #e8e0d0; font-family: 'Noto Nastaliq Urdu', serif; color: #2a1a0a; }
.page { width: 800px; margin: auto; background: #f5efe6; padding: 50px; min-height: 1050px; page-break-after: always; }
</style>
</head>
<body>
<div class="page">Page 1 content here...</div>
<div class="page">Page 2 content here...</div>
</body>
</html>
```

### Results
- 2-page A4 PDF, 187KB
- Noto Nastaliq Urdu font (handwritten calligraphy)
- Warm beige background (#f5efe6), dark brown text (#2a1a0a)
- Clean page breaks
- Shared memory error is harmless: `Failed global descriptor lookup: 7`

### Pitfalls
- Both `@page` CSS rule AND `--page-size=A4` Chrome flag needed — either alone may be ignored
- `page-break-after: always` on each `.page` div ensures 1-page-per-div
- 3-page output means content overflowed — reduce min-height or font sizes
- Google Fonts requires internet connection; for offline use pre-download the font
- The resulting PDF (~200KB) is much lighter than the original scanned PDF (~883K)

## Session 5 (May 2026 — PaddleOCR for Persian, exhaustive OCR comparison)

**Goal:** Read handwritten product names from a low-quality CamScanner Persian invoice
**Result:** Even the best OCR couldn't read the product column — handwriting too small/faint

### OCR Engine Comparison (Persian scanned document)

| Engine | Order tried | Quality | Notes |
|--------|------------|---------|-------|
| **EasyOCR** v1.7.2 | 1st | Good — reads labels + numbers clearly | Best balance of quality vs ease of setup. Persian model available. CPU-only path works everywhere. |
| **DocTR** (python-doctr) | 2nd | **No Persian support** | Only English/Latin recognition model (`crnn_vgg16_bn`). Arabic/Persian not supported. Skip for Persian documents. |
| **PaddleOCR** v3.5 | 3rd | Version mismatch — failed at runtime | `NotImplementedError` with PIR executor on Python 3.14. Requires older version. |
| **PaddleOCR** v2.10 + Python 3.11 | 4th | **BEST** for Persian text recognition | Arabic model (`arabic_PP-OCRv4_rec_infer`) actually reads Persian characters. Handles RTL partially. Best character-level recognition, but splits text oddly and reverses RTL order. |
| **OCR.space** (free API) | 5th | Persian not supported in free tier | Requires paid API key for Persian. Free tier: English only, max 1MB. |
| **Surya-OCR** | — | Failed to install | Pillow build failure with Python 3.14. |

### Verdict for Persian OCR on scanned documents

Start with **EasyOCR** (easiest setup, good results for labels/numbers/structure). If EasyOCR can't read specific Persian text and you need better character recognition, switch to **PaddleOCR v2.10** with Python 3.11.

### PaddleOCR Setup (Python 3.11, CPU-only, Arabic model)

```bash
# PaddleOCR v2.10 requires Python 3.11 (not 3.12/3.13/3.14)
# Check if available:
ls /usr/bin/python*  # or check ~/.local/bin/

# Create venv with Python 3.11
python3.11 -m venv /tmp/paddle_venv
source /tmp/paddle_venv/bin/activate

# Install PaddlePaddle (CPU)
pip install paddlepaddle

# Install PaddleOCR v2.10
pip install "paddleocr<3.0"

# Basic usage
python3 << 'EOF'
from paddleocr import PaddleOCR
ocr = PaddleOCR(use_angle_cls=False, lang='fa', use_gpu=False)
result = ocr.ocr('page.png')
for line in result[0]:
    bbox, (text, conf) = line
    print(f"[{conf:.2f}] {text}")
EOF
```

**Important:** PaddleOCR v2.10 uses PP-OCRv3 detection + Arabic PP-OCRv4 recognition. It handles Persian characters well but:
- Splits long Persian words awkwardly (reads "طلاسازی زمرد" as two separate pieces)
- May reverse RTL character order in some readings
- Best for short text segments (headers, table cells)

### DocTR — Not suitable for Persian

```bash
# DocTR only has English/Latin recognition models
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
model = ocr_predictor(pretrained=True)  # English-only

# Result: garbled "ATA", "ob", "gajajlullh", etc. — English model hallucinating Persian as English
# No Arabic/Persian recognition model is available in DocTR's model zoo
```

### What definitively did NOT work for this document

| Approach | Why |
|----------|-----|
| Tesseract (any PSM/OEM) | Persian characters garbled regardless of preprocessing |
| EasyOCR on product name cells | Numbers OK, but handwriting too small — output is noise |
| PaddleOCR on cropped product cells | Same limitation — handwriting resolution too low |
| Any binary/adaptive thresholding | Helps with uniform text but destroys handwritten detail |
| Any zoom / super-resolution | OCR models trained on ~48px text height; the handwriting was ~20px even at 600DPI scan |

### Lesson: when OCR truly fails

The product names in a scanned Persian gold invoice were **handwritten** at very small size, on a low-quality CamScanner photo. No OCR engine — Tesseract, EasyOCR, PaddleOCR, or cloud API — could read them. The practical limit for Persian handwriting OCR from scans appears to be:
- Minimum text height: ~40px at recognition input resolution
- Minimum DPI: 300 minimum, 600 preferred
- Handwriting legibility: print > cursive; avoid CamScanner-style compression artifacts

If the user needs the product names, the only reliable option is: (a) get a better-quality scan, or (b) ask a human reader to transcribe them.
