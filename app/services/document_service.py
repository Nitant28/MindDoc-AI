"""Multimodal document parsing.

PDF  → PyMuPDF text layer per page; pages without a usable text layer are rendered at 2x and sent
       through the computer-vision OCR pipeline; native tables are converted to Markdown; embedded
       images are counted as figures (and the largest one can be captioned by a vision LLM).
DOCX → paragraphs (with heading levels) + tables as Markdown.
IMG  → CV pipeline (quality, deskew, layout, OCR) + optional vision-LLM caption.
TXT/MD → decoded text.

Output is page-aware so every chunk (and therefore every citation) knows its page number.
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from typing import Optional

from PIL import Image as PILImage
from sqlalchemy.orm import Session

from app.vision import cv

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except Exception:
    DOCX_AVAILABLE = False

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif", ".webp")
TEXT_EXT = (".txt", ".md", ".markdown", ".csv")
ALLOWED_EXT = (".pdf", ".docx", *IMAGE_EXT, *TEXT_EXT)
MIN_TEXT_CHARS = 40


@dataclass
class Page:
    number: int
    text: str
    report: dict = field(default_factory=dict)


@dataclass
class ParsedDocument:
    pages: list[Page]
    kind: str

    @property
    def text(self) -> str:
        if len(self.pages) == 1:
            return self.pages[0].text
        return "\n\n".join(f"--- Page {p.number} ---\n{p.text}" for p in self.pages if p.text.strip())

    @property
    def vision(self) -> dict:
        reports = [{"page": p.number, **p.report} for p in self.pages]
        scores = [r.get("quality_score", 1.0) for r in reports]
        return {"overall_quality": round(sum(scores) / len(scores), 3) if scores else None,
                "ocr_pages": sum(r.get("method") == "ocr" for r in reports), "pages": reports}


def _table_to_md(rows: list[list]) -> str:
    rows = [[("" if c is None else str(c)).replace("\n", " ").strip() for c in r] for r in rows if r]
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    out = ["| " + " | ".join(rows[0]) + " |", "|" + " --- |" * width]
    out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(out)


def parse_pdf(data: bytes) -> ParsedDocument:
    pages: list[Page] = []
    if FITZ_AVAILABLE:
        doc = fitz.open(stream=data, filetype="pdf")
        try:
            for i, page in enumerate(doc, start=1):
                text = page.get_text("text") or ""
                n_images = len(page.get_images(full=True))
                tables_md = []
                try:
                    for t in page.find_tables().tables:
                        md = _table_to_md(t.extract())
                        if md:
                            tables_md.append(md)
                except Exception:
                    pass
                if len(text.strip()) >= MIN_TEXT_CHARS:
                    if tables_md:
                        text += "\n\n[Tables]\n" + "\n\n".join(tables_md)
                    report = {"method": "text", "ocr_confidence": None, "blur_score": None, "quality": "good",
                              "quality_score": 1.0, "skew_angle": 0.0, "tables_detected": len(tables_md),
                              "figures_detected": n_images}
                else:  # scanned / image-only page → computer vision OCR
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    img = PILImage.open(io.BytesIO(pix.tobytes("png")))
                    ocr_text, report = cv.ocr_page_image(img)
                    report["tables_detected"] = max(report["tables_detected"], len(tables_md))
                    text = ocr_text or text
                pages.append(Page(i, text.strip(), report))
        finally:
            doc.close()
    elif PDFPLUMBER_AVAILABLE:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if len(text.strip()) < MIN_TEXT_CHARS:
                    text, report = cv.ocr_page_image(page.to_image(resolution=200).original)
                else:
                    report = {"method": "text", "quality": "good", "quality_score": 1.0}
                pages.append(Page(i, text.strip(), report))
    else:
        raise RuntimeError("No PDF backend installed (pip install pymupdf)")
    return ParsedDocument(pages, "pdf")


def parse_docx(data: bytes) -> ParsedDocument:
    if not DOCX_AVAILABLE:
        raise RuntimeError("python-docx is not installed")
    d = DocxDocument(io.BytesIO(data))
    parts = []
    for para in d.paragraphs:
        t = para.text.strip()
        if not t:
            continue
        style = (para.style.name or "").lower() if para.style is not None else ""
        if style.startswith("heading"):
            level = "".join(ch for ch in style if ch.isdigit()) or "2"
            parts.append("#" * min(int(level), 6) + " " + t)
        else:
            parts.append(t)
    for table in d.tables:
        md = _table_to_md([[c.text for c in row.cells] for row in table.rows])
        if md:
            parts.append(md)
    return ParsedDocument([Page(1, "\n\n".join(parts), {"method": "text", "quality": "good", "quality_score": 1.0})],
                          "docx")


def parse_image(data: bytes) -> ParsedDocument:
    img = PILImage.open(io.BytesIO(data))
    try:
        img.seek(0)  # first frame of animated GIF / multi-page TIFF
    except Exception:
        pass
    img = img.convert("RGB")
    text, report = cv.ocr_page_image(img)
    caption = cv.caption_image(img)
    if caption:
        report["caption"] = caption
        text = f"{text}\n\n[Image description] {caption}".strip()
    return ParsedDocument([Page(1, text.strip(), report)], "image")


def parse_text(data: bytes) -> ParsedDocument:
    for enc in ("utf-8-sig", "utf-16", "latin-1"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    return ParsedDocument([Page(1, text, {"method": "text", "quality": "good", "quality_score": 1.0})], "text")


def parse_document(data: bytes, filename: str) -> ParsedDocument:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return parse_pdf(data)
    if name.endswith(".docx"):
        return parse_docx(data)
    if name.endswith(IMAGE_EXT):
        return parse_image(data)
    if name.endswith(TEXT_EXT):
        return parse_text(data)
    raise ValueError(f"Unsupported file type: {filename}")


# ------------------------------------------------------------------------- v1 compatibility

def extract_text_from_file(file_obj, filename: str) -> str:
    try:
        file_obj.seek(0)
    except Exception:
        pass
    return parse_document(file_obj.read(), filename).text


def save_document(db: Session, filename: str, content: str, tenant_id: int, owner_id: Optional[int] = None):
    """Index plain text as a document (kept for scripts written against v1)."""
    from app.services.ingestion import ingest_parsed
    parsed = ParsedDocument([Page(1, content, {"method": "text", "quality": "good", "quality_score": 1.0})], "text")
    return ingest_parsed(db, parsed, filename, tenant_id, owner_id)
