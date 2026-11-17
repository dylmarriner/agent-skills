# Persian Document OCR/Analysis Strategy

When analyzing Persian documents (invoices, affidavits):
1. **Never rely on vision models if credit/API limits are a risk.**
2. **First step:** Convert PDF/image to text using `tesseract` with `-l fas+eng` (Persian and English).
3. **Second step:** If OCR fails to capture structured info, clean the image (deskew, increase contrast) using ImageMagick (`creative/message-screenshot-editor`) before retrying OCR.
4. **Final step:** Always extract clear text first — do not attempt structured JSON extraction via vision until raw text confirms readability.
