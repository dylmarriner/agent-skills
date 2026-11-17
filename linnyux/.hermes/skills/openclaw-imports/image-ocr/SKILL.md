---
name: image-ocr
description: "Extract text from images using Tesseract OCR. Lightweight entry point — for the full Hermes OCR/document pipeline (EasyOCR, marker-pdf, OCRmyPDF, pymupdf4llm), load the builtin `ocr-and-documents` skill instead."
metadata:
  {
    "openclaw":
      {
        "emoji": "👁️",
        "requires": { "bins": ["tesseract"] },
        "install":
          [
            {
              "id": "dnf",
              "kind": "dnf",
              "package": "tesseract",
              "bins": ["tesseract"],
              "label": "Install via dnf (Fedora)",
            },
            {
              "id": "apt",
              "kind": "apt",
              "package": "tesseract-ocr",
              "bins": ["tesseract"],
              "label": "Install via apt (Debian/Ubuntu)",
            },
          ],
      },
  }
---

# Image OCR

Extract text from images using Tesseract OCR. Supports multiple languages and image formats including PNG, JPEG, TIFF, and BMP.

## Commands

```bash
# Extract text from an image (default: English)
image-ocr "screenshot.png"

# Extract text with a specific language
image-ocr "document.jpg" --lang eng
```

## Install

```bash
# Debian/Ubuntu
sudo apt install tesseract-ocr

# Fedora
sudo dnf install tesseract
```

## For Full Document OCR Pipeline

This skill covers basic Tesseract-only OCR. For the full pipeline (EasyOCR, marker-pdf, OCRmyPDF, pymupdf4llm, scanned PDFs, layout analysis), load the builtin `ocr-and-documents` skill.
