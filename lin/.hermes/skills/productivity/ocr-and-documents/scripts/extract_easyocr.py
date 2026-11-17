#!/usr/bin/env python3
"""Extract text from scanned PDFs using EasyOCR. Best for Persian/Arabic and other complex scripts.

Usage:
    python scripts/extract_easyocr.py document.pdf
    python scripts/extract_easyocr.py document.pdf --langs fa+en
    python scripts/extract_easyocr.py document.pdf --dpi 600
    python scripts/extract_easyocr.py document.pdf --min-conf 0.3
    python scripts/extract_easyocr.py document.pdf --paragraph
    python scripts/extract_easyocr.py document.pdf --crop

Requirements (CPU path for old GPUs):
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
    pip install easyocr
"""

import argparse
import os
import subprocess
import sys
import tempfile


def pdf_to_images(pdf_path, dpi=600):
    tmpdir = tempfile.mkdtemp(prefix="easyocr_")
    prefix = os.path.join(tmpdir, "page")
    subprocess.run(
        ["pdftoppm", pdf_path, prefix, "-png", "-r", str(dpi)],
        check=True, capture_output=True
    )
    images = sorted([os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.endswith(".png")])
    return images, tmpdir


def crop_regions(image_path, output_dir):
    from PIL import Image
    img = Image.open(image_path)
    w, h = img.size
    name = os.path.splitext(os.path.basename(image_path))[0]
    regions = {}
    for i, (y_start, label) in enumerate([(0, "top"), (h//3, "mid"), (2*h//3, "bot")]):
        out = os.path.join(output_dir, f"{name}_{label}.png")
        img.crop((0, y_start, w, y_start + h//3)).save(out)
        regions[label] = out
    return regions


def main():
    parser = argparse.ArgumentParser(description="Extract text from scanned PDFs using EasyOCR")
    parser.add_argument("path", help="Path to PDF or image file")
    parser.add_argument("--langs", default="fa", help="Language codes (e.g. fa, fa+en, ar)")
    parser.add_argument("--dpi", type=int, default=600, help="DPI for PDF-to-image conversion")
    parser.add_argument("--min-conf", type=float, default=0.3, help="Minimum confidence threshold")
    parser.add_argument("--paragraph", action="store_true", help="Use paragraph mode")
    parser.add_argument("--crop", action="store_true", help="Crop into 3 horizontal regions")
    parser.add_argument("--gpu", action="store_true", help="Use GPU if available")
    args = parser.parse_args()

    import easyocr

    lang_list = args.langs.replace("+", ",").split(",")
    path = args.path
    cleanup_dirs = []

    if path.lower().endswith(".pdf"):
        print(f"Converting PDF to images ({args.dpi} DPI)...", file=sys.stderr)
        images, tmpdir = pdf_to_images(path, args.dpi)
        cleanup_dirs.append(tmpdir)
    else:
        images = [path]

    reader = easyocr.Reader(lang_list, gpu=args.gpu)
    print(f"EasyOCR ready (languages: {lang_list}, gpu={args.gpu})", file=sys.stderr)

    for img_path in images:
        print(f"\n{'='*60}")
        print(f"  {os.path.basename(img_path)}")
        print(f"{'='*60}")

        if args.crop:
            crop_dir = tempfile.mkdtemp(prefix="easyocr_crop_")
            cleanup_dirs.append(crop_dir)
            regions = crop_regions(img_path, crop_dir)
            for label, region_path in regions.items():
                print(f"\n--- {label} ---")
                detail = reader.readtext(region_path, detail=1, paragraph=args.paragraph)
                for entry in detail:
                    if args.paragraph:
                        print(f"  {entry}")
                    else:
                        bbox, text, conf = entry
                        if conf >= args.min_conf:
                            y = (bbox[0][1] + bbox[2][1]) / 2
                            print(f"  y={y:6.0f} [{conf:.2f}] {text}")
        else:
            detail = reader.readtext(img_path, detail=1, paragraph=args.paragraph)
            for entry in detail:
                if args.paragraph:
                    print(f"  {entry}")
                else:
                    bbox, text, conf = entry
                    if conf >= args.min_conf:
                        y = (bbox[0][1] + bbox[2][1]) / 2
                        print(f"  y={y:6.0f} [{conf:.2f}] {text}")

    for d in cleanup_dirs:
        import shutil
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    main()
