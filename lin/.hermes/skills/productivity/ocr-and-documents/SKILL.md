---
name: ocr-and-documents
description: "Extract text from PDFs/scans (pymupdf, marker-pdf)."
version: 2.4.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [PDF, Documents, Research, Arxiv, Text-Extraction, OCR]
    related_skills: [powerpoint]
---

# PDF & Document Extraction

For DOCX: use `python-docx` (parses actual document structure, far better than OCR).
For PPTX: see the `powerpoint` skill (uses `python-pptx` with full slide/notes support).
This skill covers **PDFs and scanned documents**.

## Step 1: Remote URL Available?

If the document has a URL, **always try `web_extract` first**:

```
web_extract(urls=["https://arxiv.org/pdf/2402.03300"])
web_extract(urls=["https://example.com/report.pdf"])
```

This handles PDF-to-markdown conversion via Firecrawl with no local dependencies.

Only use local extraction when: the file is local, web_extract fails, or you need batch processing.

## Step 2: Choose Local Extractor

| Feature | pymupdf (~25MB) | marker-pdf (~3-5GB) |
|---------|-----------------|---------------------|
| **Text-based PDF** | ✅ | ✅ |
| **Scanned PDF (OCR)** | ❌ | ✅ (90+ languages) |
| **Tables** | ✅ (basic) | ✅ (high accuracy) |
| **Equations / LaTeX** | ❌ | ✅ |
| **Code blocks** | ❌ | ✅ |
| **Forms** | ❌ | ✅ |
| **Headers/footers removal** | ❌ | ✅ |
| **Reading order detection** | ❌ | ✅ |
| **Images extraction** | ✅ (embedded) | ✅ (with context) |
| **Images → text (OCR)** | ❌ | ✅ |
| **EPUB** | ✅ | ✅ |
| **Markdown output** | ✅ (via pymupdf4llm) | ✅ (native, higher quality) |
| **Install size** | ~25MB | ~3-5GB (PyTorch + models) |
| **Speed** | Instant | ~1-14s/page (CPU), ~0.2s/page (GPU) |

**Decision**: Use pymupdf unless you need OCR, equations, forms, or complex layout analysis.

If the user needs marker capabilities but the system lacks ~5GB free disk:
> "This document needs OCR/advanced extraction (marker-pdf), which requires ~5GB for PyTorch and models. Your system has [X]GB free. Options: free up space, provide a URL so I can use web_extract, or I can try pymupdf which works for text-based PDFs but not scanned documents or equations."

---

## pymupdf (lightweight)

```bash
pip install pymupdf pymupdf4llm
```

**Via helper script**:
```bash
python scripts/extract_pymupdf.py document.pdf              # Plain text
python scripts/extract_pymupdf.py document.pdf --markdown    # Markdown
python scripts/extract_pymupdf.py document.pdf --tables      # Tables
python scripts/extract_pymupdf.py document.pdf --images out/ # Extract images
python scripts/extract_pymupdf.py document.pdf --metadata    # Title, author, pages
python scripts/extract_pymupdf.py document.pdf --pages 0-4   # Specific pages
```

**Inline**:
```bash
python3 -c "
import pymupdf
doc = pymupdf.open('document.pdf')
for page in doc:
    print(page.get_text())
"
```

---

## marker-pdf (high-quality OCR)

```bash
# Check disk space first
python scripts/extract_marker.py --check

pip install marker-pdf
```

**Via helper script**:
```bash
python scripts/extract_marker.py document.pdf                # Markdown
python scripts/extract_marker.py document.pdf --json         # JSON with metadata
python scripts/extract_marker.py document.pdf --output_dir out/  # Save images
python scripts/extract_marker.py scanned.pdf                 # Scanned PDF (OCR)
python scripts/extract_marker.py document.pdf --use_llm      # LLM-boosted accuracy
```

**CLI** (installed with marker-pdf):
```bash
marker_single document.pdf --output_dir ./output
marker /path/to/folder --workers 4    # Batch
```

---

## Arxiv Papers

```
# Abstract only (fast)
web_extract(urls=["https://arxiv.org/abs/2402.03300"])

# Full paper
web_extract(urls=["https://arxiv.org/pdf/2402.03300"])

# Search
web_search(query="arxiv GRPO reinforcement learning 2026")
```

## Split, Merge & Search

pymupdf handles these natively — use `execute_code` or inline Python:

```python
# Split: extract pages 1-5 to a new PDF
import pymupdf
doc = pymupdf.open("report.pdf")
new = pymupdf.open()
for i in range(5):
    new.insert_pdf(doc, from_page=i, to_page=i)
new.save("pages_1-5.pdf")
```

```python
# Merge multiple PDFs
import pymupdf
result = pymupdf.open()
for path in ["a.pdf", "b.pdf", "c.pdf"]:
    result.insert_pdf(pymupdf.open(path))
result.save("merged.pdf")
```

```python
# Search for text across all pages
import pymupdf
doc = pymupdf.open("report.pdf")
for i, page in enumerate(doc):
    results = page.search_for("revenue")
    if results:
        print(f"Page {i+1}: {len(results)} match(es)")
        print(page.get_text("text"))
```

No extra dependencies needed — pymupdf covers split, merge, search, and text extraction in one package.

---

## EasyOCR (high-quality OCR for complex scripts)

When tesseract quality is poor — especially for Persian/Arabic, handwritten text, or low-quality scans — use **EasyOCR** (PyTorch-based). It consistently outperforms tesseract on non-Latin scripts.

**Installation (CPU-only, for machines with old/incompatible GPUs):**

```bash
# Check GPU compatibility first — if SM < 7.5 (e.g. GeForce MX150 CC 6.1), CPU-only is required:
python3 -c "import torch; print(torch.cuda.get_device_capability())"
# If this errors or reports CC < 7.5, use the CPU path below.

# CPU path (works on any machine):
python3 -m venv /tmp/easyocr_venv
source /tmp/easyocr_venv/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install easyocr

# GPU path (CC >= 7.5):
pipx install easyocr
```

**Basic usage:**

```bash
# CLI mode
source /tmp/easyocr_venv/bin/activate
easyocr -l fa -f document_page.png --detail=1 --gpu=false

# With English + Persian (good for bilingual invoices)
easyocr -l fa+en -f document_page.png --detail=0
```

**Inline Python (for region cropping & custom processing):**

```python
import easyocr
reader = easyocr.Reader(['fa', 'en'], gpu=False)
results = reader.readtext('page.png', detail=1)
for bbox, text, conf in results:
    if conf > 0.3:
        y_center = (bbox[0][1] + bbox[2][1]) / 2
        print(f"y={y_center:6.0f} [{conf:.2f}] {text}")
```

**Best practices for Persian/Arabic documents:**

1. **Convert PDF to high-DPI PNGs first:**
   ```bash
   pdftoppm document.pdf /tmp/page -png -r 600
   ```

2. **Crop into regions** for table-heavy documents (invoices, receipts):
   ```python
   from PIL import Image
   img = Image.open("/tmp/page-1.png")
   w, h = img.size
   # Top third (header)
   img.crop((0, 0, w, h//3)).save("/tmp/header.png")
   # Middle third (body/table)
   img.crop((0, h//3, w, 2*h//3)).save("/tmp/body.png")
   # Bottom third (footer)
   img.crop((0, 2*h//3, w, h)).save("/tmp/footer.png")
   ```

3. **Paragraph mode** groups related text blocks — good for invoices with mixed layout:
   ```python
   results = reader.readtext('page.png', detail=0, paragraph=True)
   ```

4. **Filter by confidence** — discard noise below 0.3:
   ```python
   text = ' '.join(t for _, t, c in results if c > 0.3)
   ```

**When to use EasyOCR vs tesseract vs marker-pdf vs PaddleOCR:**

| Tool | When to use |
|------|-------------|
| **tesseract** | Latin scripts, clean scans, ~2s startup (instant) |
| **EasyOCR** | Persian/Arabic/Chinese, complex scripts, ~30s startup — **best balance of quality and ease** |
| **PaddleOCR v2.10** | **Best for Persian character-level recognition** — Arabic model handles RTL well. Requires Python 3.11. See `references/persian-arabic-ocr.md` for setup. |
| **DocTR** | English only — no Arabic/Persian model available. Skip for non-Latin scripts. |
| **marker-pdf** | Full-page layout, equations, forms, tables (~3-5GB) |
| **OCRMypdf** | Adding searchable text layer to scans while keeping original appearance |

**Pitfalls:**
- First run downloads detection + recognition models (may take minutes)
- CPU mode is slow (~30-60s per 600 DPI page on a laptop)
- `--gpu=false` doesn't help if PyTorch was compiled with incompatible CUDA — use CPU-only torch as shown above
- EasyOCR may hallucinate digits on noise — always filter by confidence > 0.3
- The `easyocr` CLI from pipx may crash on old GPUs (SM < 7.5 with incompatible CUDA runtime); the manual venv approach avoids this
- **For better Persian character recognition**, use PaddleOCR v2.10 with Python 3.11 (see `references/persian-arabic-ocr.md`). PaddleOCR's Arabic recognition model handles Persian text that EasyOCR struggles with.
- **DocTR has NO Arabic/Persian model** — don't waste time trying it for Persian documents


## Lightweight OCR with tesseract

When marker-pdf is too heavy (~3-5GB) or unavailable, use **tesseract** for OCR on scanned documents. Works best for straightforward text scans (no complex layouts, equations, or tables).

**Prerequisites:**
```bash
sudo apt-get install -y tesseract-ocr
# Language packs (install as needed):
sudo apt-get install -y tesseract-ocr-fas   # Persian/Farsi
sudo apt-get install -y tesseract-ocr-ara   # Arabic
sudo apt-get install -y tesseract-ocr-deu   # German
sudo apt-get install -y tesseract-ocr-fra   # French
sudo apt-get install -y tesseract-ocr-rus   # Russian
# Full language list: apt search tesseract-ocr-
```

**Step-by-step (scanned PDF):**

```bash
# 1. Check if it's text-based first (fastest)
pdftotext document.pdf - | head -50

# 2. If empty → convert to images
pdftoppm document.pdf /tmp/doc_page -png -r 300
# Or for higher quality: -r 600

# 3. OCR with appropriate language(s)
tesseract /tmp/doc_page-1.png stdout -l fas+eng --psm 4
```

**Page segmentation modes (--psm):**
- `3` — Fully automatic (good default)
- `4` — Assume a single column of text of variable sizes
- `6` — Assume a single uniform block of text
- `11` — Sparse text (for things like receipts, business cards)
- Try multiple values if quality is poor.

**Image preprocessing for better results:**

```bash
# Grayscale + sharpen + normalize (helps most scans)
convert input.png -colorspace Gray -sharpen 0x2 -normalize output.png

# Adaptive thresholding (for uneven lighting)
convert input.png -colorspace Gray -negate -lat 30x30+5% -negate output.png

# Binarization (for high-contrast text)
convert input.png -colorspace Gray -threshold 50% output.png
```

**Troubleshooting:**
- If OCR reads garbled Persian/Arabic text, the image quality or preprocessing is the issue — try higher DPI (600) and adaptive thresholding
- `pdfinfo document.pdf` gives page count and metadata before processing
- The vision_analyze / browser_vision tools depend on the LLM provider — providers like `deepseek` may reject image_url inputs entirely; in that case, fall back to tesseract immediately

---

## Notes

- `web_extract` is always first choice for URLs
- pymupdf is the safe default — instant, no models, works everywhere
- marker-pdf is for OCR, scanned docs, equations, complex layouts — install only when needed
- tesseract is the lightweight OCR fallback when marker-pdf is too heavy — installs in seconds, works offline, covers 100+ languages
- Both helper scripts accept `--help` for full usage
- marker-pdf downloads ~2.5GB of models to `~/.cache/huggingface/` on first use
- For Word docs: `pip install python-docx` (better than OCR — parses actual structure)
- For PowerPoint: see the `powerpoint` skill (uses python-pptx)

## Making Scanned PDFs Searchable (OCR Text Layer)

When the user wants text to be selectable/copyable while keeping the **exact original visual appearance** (logos, stamps, colors, handwriting all intact), use **OCRMypdf**:

```bash
# Install
sudo apt-get install -y ocrmypdf    # or: pipx install ocrmypdf

# Add invisible text layer to scanned PDF
ocrmypdf --language fas+eng \
  --output-type pdfa \
  --skip-text \
  original.pdf output.pdf
```

This creates a PDF/A-2B compliant file where:
- The **visual appearance is 100% identical** to the original (it embeds the original scanned images)
- Text is **selectable, searchable, and copyable** via an invisible OCR layer underneath
- File size is typically similar to or smaller than the original (OCRMypdf optimizes images)

**When to use OCRMypdf vs alternative approaches:**

| Goal | Tool | Why |
|------|------|-----|
| **Selectable text + original look** | `ocrmypdf` | Keeps original images, adds text layer |
| **Clean up visuals only** | ImageMagick filters | Contrast, despeckle, watermark removal |
| **Edit/replace text** | PIL + ImageMagick | Erase old text, overlay new |
| **HTML-to-PDF replica** | Chrome headless | For handwritten-style editable replacement |

**Key flags:**
- `--language fas+eng` — Persian + English (add others as needed)
- `--output-type pdfa` — produces standards-compliant PDF/A for archival
- `--skip-text` — don't re-OCR pages that already have text

## Cleaning & Editing Scanned PDFs

After OCR extraction, you often need to clean or edit the scanned document. See `references/cleaning-editing-scanned-pdfs.md` for the full workflow covering:

- **Visual cleanup**: removing CamScanner watermarks, normalizing contrast/sharpen, despeckling noise
- **CRITICAL**: Only erase original text when the user explicitly asks to change content. For cleanup/restoration, do visual enhancement only — never destroy logos, stamps, colored ink, or design elements.
- **When the user says "clean up" they mean image filters ONLY** — no white rectangles, no erasing, no text replacement. Just contrast, noise removal, watermark crop. Any erasure of original content will destroy logos/colors/stamps.
- **Even when text editing IS authorized** (user says "edit the pdf"), you must match: (a) original ink color — never assume pure black; do pixel sampling to find the actual color; (b) font style — Persian invoices typically use Naskh-style fonts, not sans-serif; (c) background color — sample the region's background, don't use pure white.
- **GPU compatibility check for EasyOCR**: run `python3 -c "import torch; print(torch.cuda.get_device_capability())"` first. If SM < 7.5 or CUDA error → must use CPU-only torch install path (see EasyOCR section in SKILL.md body).
- **Text editing**: erasing OCR'd text regions and overlaying new Persian/Arabic text using PIL — always match original ink color from pixel analysis, never assume pure black
- **PDF reassembly**: converting edited images back into a PDF

## HTML-to-PDF with Handwritten Persian Fonts

When a plain-scanned PDF can't be edited directly (user wants editable handwritten-style text), reproduce the document as HTML with a calligraphic font and convert via Chrome headless:

```bash
google-chrome --headless --disable-gpu --no-margins \
  --print-to-pdf-no-header \
  --print-to-pdf="output.pdf" \
  --page-size=A4 \
  "file:///path/to/document.html"
```

**Required HTML structure:**

| Setting | Purpose |
|---------|---------|
| `<html dir="rtl" lang="fa">` | Right-to-left for Persian |
| `@page { size: A4; margin: 0; }` | Forces A4 page in print |
| `page-break-after: always` on each `.page` div | Clean multi-page output |
| `font-family: 'Noto Nastaliq Urdu'` (via Google Fonts) | Handwritten Persian calligraphy |
| Background `#f5efe6`, text `#2a1a0a` | Warm paper tone, dark brown ink |

**Font choices:** Noto Nastaliq Urdu (handwritten), Noto Naskh Arabic (printed book style), Noto Sans Arabic (modern), IBM Plex Sans Arabic (modern).

**Pitfalls:** Set both `@page` CSS and `--page-size=A4` Chrome flag; Google Fonts need internet; 3-page output = overflow, reduce font/page height; shared memory error `Failed global descriptor lookup: 7` is harmless.
