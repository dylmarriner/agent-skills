---
name: nz-business-document-gen
description: "Generate professional NZ business documents (quotes, invoices, statements, forms) as PDFs using reportlab"
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [PDF, NZ, Business, Documents, ReportLab, GST]
    related_skills: [ocr-and-documents, pdf-editing-undetectable, nano-pdf]
---

# NZ Business Document Generation

Generate professional A4 PDF business documents matching NZ conventions:
quotes, invoices, statements, repair estimates, and forms.

## When To Use

- User needs a professional-looking quote/invoice/receipt created or modified
- Existing business document needs reformatting with new pricing, dates, or scope
- User provides a scanned/PDF business document and asks you to update it (first extract with `ocr-and-documents`, then regenerate)

## Toolchain

| Tool | Purpose |
|------|---------|
| **reportlab** | PDF generation — tables, headers, formatting, A4 layout |
| **pymupdf** | Reading/analyzing existing PDF structure before regenerating |
| **pdftotext/pdftoppm** | Extracting content from existing image-based documents |

```bash
# Install
pip install reportlab Pillow
```

## Core Workflow

### 1. Analyze Existing Document

If modifying an existing document, first extract all content:

```bash
# Text-based PDF
pdftotext original.pdf -

# Image-based PDF (convert to images first)
pdftoppm original.pdf /tmp/page -png -r 300
tesseract /tmp/page-1.png stdout --psm 6
```

Capture: header info, line items with prices, subtotals, tax breakdown, totals, footer/notes.

### 2. Identify What Changes

From the user's request, determine exactly which fields change:
- **Quote/Invoice number**: update to new number
- **Date**: adjust (NZ format — "30 June 2026" or "Monday 30 June 2026")
- **Odometer/vehicle details**: incremental as needed
- **Work scope**: replace entire sections (e.g., body repair → SRS replacement)
- **Pricing**: update parts, labour, margin, misc
- **Customer/insurer info**: as provided

### 3. Build PDF with reportlab

Use this structural pattern:

```python
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

doc = SimpleDocTemplate(
    output_path, pagesize=A4,
    rightMargin=15*mm, leftMargin=15*mm,
    topMargin=15*mm, bottomMargin=15*mm,
)

elements = []
```

**Header block**: Company name (bold, centered), address, phone/fax/email, GST number — wrapped in a bordered table with dark header background.

**Vehicle/job info table**: 4-column layout (Label | Value | Label | Value) with thin grey borders.

**Section tables**: Labour (Remove & Refit), Parts, Misc — each with:
- Bold header row (dark background, white text)
- Line items with align-right on numeric columns
- Grey grid lines (0.5pt)
- Bold subtotal row with light grey background
- Bold total row with darker grey background + 1pt bottom line

**Summary block**: Right-aligned totals with horizontal rules:
- Total excl. GST
- GST (15%)
- Total incl. GST (bold, 1pt line above)
- Less Excess
- Total Payable to Repairer (big bold, 2pt line above)

### 4. NZ Conventions

| Convention | Standard |
|------------|----------|
| **Page size** | A4 (595.276 x 841.89 pts) |
| **Date format** | "30 June 2026" or "Monday 30 June 2026" |
| **Currency** | NZD — prefix with $, two decimal places |
| **GST** | 15% — calculate as `round(total_excl * 0.15, 2)` |
| **Quote numbers** | 14-digit timestamp-based (YYYYMMDDHHMMSS) |
| **Labour rate** | Typically $70-120/hr depending on trade |
| **Parts margin** | Typically 10-15% on supplied parts |
| **Footer** | Page X of Y, centered, grey text |

### 5. Table Column Widths

For standard A4 (595pt wide, minus 30pt margins = ~290pt usable):
- Description: ~100-210pt (biggest column)
- Hrs/Qty: ~22pt
- Rate/Unit Price: ~26pt
- Total: ~28pt
- Source, Part #: ~30pt each (if applicable)

Calculate based on number of columns. Use `colWidths=[...]` as a list.

### 6. Number Formatting

Always format monetary values with 2 decimal places:

```python
f"${amount:.2f}"   # $1,764.50 — correct
# NOT: f"${amount}" → $1764.5 — wrong
```

Python's f-string doesn't add thousands separators by default. For amounts >= $1,000, consider:
```python
f"${amount:,.2f}"  # $1,764.50
```

### 7. PDF Verification

After generation, verify with:
```bash
pdfinfo output.pdf          # Page count, size, encryption
pdftotext output.pdf -      # Text extraction sanity check
```

## Template

A reusable template script lives at `templates/nz_quote_builder.py`:
- Edit the `DATA` dict with your content, then run
- Outputs a complete A4 NZ quote with labour, parts, misc, GST, and summary
- Run with `uv run --with reportlab python3 templates/nz_quote_builder.py`
- Covers all NZ conventions: GST 15%, $ with 2 decimals, NZ date format, header layout

## Pitfalls

- **Column width mismatch**: If table columns don't sum to ~290pt, the table will overflow or look cramped. Calculate total from `width - left_margin - right_margin`.
- **ReportLab + uv**: If using `uv run python3`, reportlab may not be in that venv. Install via `uv pip install --system reportlab` or wrap with `uv run --with reportlab python3 script.py`.
- **Long text wrapping**: Paragraphs in table cells need explicit width from `colWidths`. Use `Paragraph(text, style)` not plain strings — text that's too long for a column must wrap, not overflow.
- **A4 vs Letter**: Default reportlab page size is A4 if imported explicitly: `from reportlab.lib.pagesizes import A4`. Page dimensions: 595.276 x 841.89 pts.
- **TableStyle index confusion**: `(0, 0)` = first column, first row. `(-1, -1)` = last column, last row. `(0, -2)` to `(-1, -2)` = full-width second-to-last row.
- **GST rounding**: `round(total * 0.15, 2)` not `total * 0.15` — floating point can produce $264.675 which should round to $264.68.
- **Image-based source PDFs**: When modifying a scanned/image-based quote, you MUST rebuild from scratch with reportlab — you cannot edit the image layers. First extract ALL data via OCR, then regenerate.
- **Empty cells**: If a cell should be blank, pass `""` (empty string) not `None` — reportlab crashes on `None` in Table data.
- **Font availability**: reportlab default fonts are Helvetica (sans), Times-Roman (serif), Courier (mono). No custom fonts without registration. For NZ business docs, Helvetica-Bold headers + Helvetica body is standard.
