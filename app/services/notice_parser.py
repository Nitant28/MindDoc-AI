"""
notice_parser.py
Advanced document parsing and data extraction for tax notices and official documents.
Extracts PAN, assessment year, demand, deadlines, section references, and more from PDFs/images.
OCR fallback for scanned/image-based docs.
"""

import re
import pytesseract
import pdfplumber
import pandas as pd
import ocrmypdf
from pdf2image import convert_from_path
from PIL import Image
from datetime import datetime
from typing import Dict, Any, Optional
import tempfile
import os

# Utility regex patterns for Indian tax notices
PAN_PATTERN = r"[A-Z]{5}[0-9]{4}[A-Z]"
AY_PATTERN = r"\b(20\d{2})-(20\d{2})\b"
DEMAND_PATTERN = r"[Rr]s\.?\s?([0-9,]+)"
DATE_PATTERN = r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b"
SECTION_PATTERN = r"[Ss]ection\s*(\d+[A-Za-z]*)"


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF, fallback to OCR if needed."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception:
        text = ""
    if not text.strip():
        # Fallback to OCR
        text = ocr_pdf(pdf_path)
    return text


def ocr_pdf(pdf_path: str) -> str:
    """OCR the PDF and extract text."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ocr_path = os.path.join(tmpdir, "ocr.pdf")
        ocrmypdf.ocr(pdf_path, ocr_path, force_ocr=True, deskew=True, output_type="pdf")
        images = convert_from_path(ocr_path)
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img)
        return text


def extract_fields(text: str) -> Dict[str, Any]:
    """Extract structured fields from notice text."""
    fields = {}
    pan = re.search(PAN_PATTERN, text)
    ay = re.search(AY_PATTERN, text)
    demand = re.search(DEMAND_PATTERN, text)
    dates = re.findall(DATE_PATTERN, text)
    sections = re.findall(SECTION_PATTERN, text)
    fields["PAN"] = pan.group(0) if pan else None
    fields["AssessmentYear"] = ay.group(0) if ay else None
    fields["DemandAmount"] = demand.group(1) if demand else None
    fields["Dates"] = dates
    fields["Sections"] = list(set(sections))
    return fields


def parse_notice(pdf_path: str) -> Dict[str, Any]:
    """Main entry: parse a notice and extract all relevant fields."""
    text = extract_text_from_pdf(pdf_path)
    fields = extract_fields(text)
    fields["RawText"] = text
    return fields

# Example usage:
# result = parse_notice("/path/to/notice.pdf")
# print(result)
