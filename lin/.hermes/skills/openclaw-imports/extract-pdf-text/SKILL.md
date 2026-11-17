---
name: Extract PDF Text
slug: extract-pdf-text
version: 1.1.0
description: Full Hermes document intake — MCP servers first, Python fallback. Covers Filesystem, MarkItDown, and Docling MCP servers plus PyMuPDF, pymupdf4llm, OCRmyPDF, Tesseract.
metadata: {"clawdbot":{"emoji":"📄","requires":{"bins":["python3"],"pip":["pymupdf"]},"os":["linux","darwin","win32"],"install":[{"id":"pymupdf","kind":"pip","package":"PyMuPDF","label":"Install PyMuPDF"}]}}
---

## When to Use

Agent needs to read, extract, or process documents (PDF, DOCX, PPTX, XLSX, scanned images, EPUB, HTML).

## Principle: MCP First

In Hermes, MCP servers are the primary path for document intake — not inline Python, not plugins. Three MCP servers form the intake stack:

1. **Filesystem MCP** — browse/find/list documents in allowed directories
2. **MarkItDown MCP** — lightweight PDF/DOCX/PPTX/XLSX/HTML → Markdown
3. **Docling MCP** — heavy PDF parsing (OCR, layout, tables, formulas, scanned docs)
4. **Python fallback** — PyMuPDF / pymupdf4llm when MCP isn't loaded

See `references/hermes-document-mcp-setup.md` for full install/config/verify.

## MCP Tier Guide

| Tier | MCP Server | When |
|------|-----------|------|
| Browse | Filesystem | Find/list documents, check existence, read .md/.txt |
| Convert | MarkItDown | Normal PDFs, DOCX, PPTX, XLSX |
| Parse | Docling | Scanned PDFs, tables, layout-reliant docs, OCR |
| Fallback | pymupdf4llm / PyMuPDF | MCP unavailable or fails |

## Quick Reference

| Topic | File |
|-------|------|
| MCP server setup (primary path) | `references/hermes-document-mcp-setup.md` |
| Code examples | `examples.md` |
| OCR setup | `ocr.md` |
| Troubleshooting | `troubleshooting.md` |

## Core Rules

### 1. Install PyMuPDF First

```bash
pip install PyMuPDF
```

Import as `fitz` (historical name):
```python
import fitz  # PyMuPDF
```

### 2. Basic Text Extraction

```python
import fitz

doc = fitz.open("document.pdf")
text = ""
for page in doc:
    text += page.get_text()
doc.close()
```

### 3. Pick the Right Method

| PDF Type | Method |
|----------|--------|
| Text-based | `page.get_text()` — fast, accurate |
| Scanned | OCR with pytesseract — slower |
| Mixed | Check each page, use OCR when needed |

### 4. Check for Text Before OCR

```python
def needs_ocr(page):
    text = page.get_text().strip()
    return len(text) < 50  # Likely scanned if very little text
```

### 5. Handle Errors Gracefully

```python
try:
    doc = fitz.open(path)
except fitz.FileDataError:
    print("Invalid or corrupted PDF")
except fitz.PasswordError:
    doc = fitz.open(path, password="secret")
```

## Extraction Traps

| Trap | What Happens | Fix |
|------|--------------|-----|
| OCR on text PDF | Slow + worse accuracy | Check `get_text()` first |
| Forget to close doc | Memory leak | Use `with` or `doc.close()` |
| Assume page order | Wrong reading flow | Use `sort=True` in get_text() |
| Ignore encoding | Garbled characters | PyMuPDF handles UTF-8 |

## Scope

This skill provides instructions for using PyMuPDF to extract PDF text.

This skill ONLY:
- Gives code examples for PyMuPDF
- Explains OCR setup when needed
- Troubleshoots common issues

This skill NEVER:
- Accesses files without user request
- Sends data externally
- Modifies original PDFs

## Security & Privacy

**All processing is local:**
- PyMuPDF runs entirely on your machine
- No external API calls
- No data leaves your system

## Output Formats

### Plain Text
```python
text = page.get_text()
```

### Structured (dict)
```python
blocks = page.get_text("dict")["blocks"]
for b in blocks:
    if b["type"] == 0:  # text block
        for line in b["lines"]:
            for span in line["spans"]:
                print(span["text"], span["size"])
```

### JSON
```python
import json
data = page.get_text("json")
parsed = json.loads(data)
```

## Full Example

```python
import fitz

def extract_pdf(path):
    """Extract text from PDF, with OCR fallback for scanned pages."""
    doc = fitz.open(path)
    results = []
    
    for i, page in enumerate(doc):
        text = page.get_text()
        method = "text"
        
        # If very little text, might be scanned
        if len(text.strip()) < 50:
            # OCR would go here (see ocr.md)
            method = "needs_ocr"
        
        results.append({
            "page": i + 1,
            "text": text,
            "method": method
        })
    
    doc.close()
    return {
        "pages": len(results),
        "content": results,
        "word_count": sum(len(r["text"].split()) for r in results)
    }

# Usage
result = extract_pdf("document.pdf")
print(f"Extracted {result['word_count']} words from {result['pages']} pages")
```

## Feedback

- Useful? `clawhub star extract-pdf-text`
- Stay updated: `clawhub sync`
