"""
pdf_extractor.py
Extracts all text and tables from a PDF (with OCR fallback) for legal data ingestion.
"""

import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import ocrmypdf
import tempfile
import os


def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text += page_text + "\n"
    except Exception:
        text = ""
    if not text.strip():
        text = ocr_pdf(pdf_path)
    return text


def ocr_pdf(pdf_path):
    with tempfile.TemporaryDirectory() as tmpdir:
        ocr_path = os.path.join(tmpdir, "ocr.pdf")
        ocrmypdf.ocr(pdf_path, ocr_path, force_ocr=True, deskew=True, output_type="pdf")
        images = convert_from_path(ocr_path)
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img)
        return text


def extract_tables_from_pdf(pdf_path):
    tables = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    tables.append(table)
    except Exception:
        pass
    return tables


def main():
    pdf_path = "sample.pdf"  # Update path if needed
    text = extract_text_from_pdf(pdf_path)
    tables = extract_tables_from_pdf(pdf_path)
    with open("sample_pdf_text.txt", "w", encoding="utf-8") as f:
        f.write(text)
    with open("sample_pdf_tables.json", "w", encoding="utf-8") as f:
        import json
        json.dump(tables, f, ensure_ascii=False, indent=2)
    print("PDF extraction complete. Text and tables saved.")


if __name__ == "__main__":
    main()
