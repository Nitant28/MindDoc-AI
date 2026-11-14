"""Multimodal document parsing.

PDF  → pypdfium2 text layer per page (Apache-2.0/BSD, ADR-0006; PyMuPDF is AGPL and no longer used); pages
       without a usable text layer are rendered at up to 2x and sent through the computer-vision OCR pipeline;
       ruled tables found by pdfplumber (MIT) are converted to Markdown; embedded images are counted as figures.
DOCX → paragraphs (with heading levels) + tables as Markdown.
IMG  → CV pipeline (quality, deskew, layout, OCR) + optional vision-LLM caption.
TXT/MD → decoded text.

Output is page-aware so every chunk (and therefore every citation) knows its page number.
"""
from __future__ import annotations

import io
import logging
import zipfile
from dataclasses import dataclass, field

from PIL import Image as PILImage

from app.core.config import settings
from app.vision import cv

logger = logging.getLogger(__name__)

try:
    import pypdfium2 as pdfium
    import pypdfium2.raw as pdfium_c
    PDFIUM_AVAILABLE = True
except ImportError:  # pragma: no cover
    PDFIUM_AVAILABLE = False

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


def _check_pages(n: int) -> None:
    if n > settings.max_pdf_pages:
        raise ValueError(f"PDF has {n} pages; the limit is {settings.max_pdf_pages}. Split the file and upload the parts.")


def _page_text(page) -> str:
    tp = page.get_textpage()
    try:
        text = tp.get_text_bounded() or ""
    finally:
        tp.close()
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "").replace("\ufffe", "")


def _page_tables(plumber_pdf, index: int) -> list[str]:
    """Ruled tables on one page as Markdown (pdfplumber's line strategy, like the previous table finder)."""
    if plumber_pdf is None:
        return []
    out = []
    try:
        page = plumber_pdf.pages[index]
        try:
            for t in page.find_tables():
                md = _table_to_md(t.extract())
                if md:
                    out.append(md)
        finally:
            page.close()
    except Exception:  # a table the parser cannot read never fails the page
        logger.debug("table extraction failed on page %s", index + 1, exc_info=True)
    return out


def parse_pdf(data: bytes) -> ParsedDocument:
    if not PDFIUM_AVAILABLE:
        raise RuntimeError("No PDF backend installed (pip install pypdfium2)")
    pages: list[Page] = []
    pdf = pdfium.PdfDocument(data)
    plumber_pdf = None
    try:
        _check_pages(len(pdf))
        if PDFPLUMBER_AVAILABLE:
            plumber_pdf = pdfplumber.open(io.BytesIO(data))
        for i in range(len(pdf)):
            page = pdf[i]
            try:
                text = _page_text(page)
                n_images = sum(1 for _ in page.get_objects(filter=[pdfium_c.FPDF_PAGEOBJ_IMAGE], max_depth=2))
                if len(text.strip()) >= MIN_TEXT_CHARS:
                    tables_md = _page_tables(plumber_pdf, i)
                    if tables_md:
                        text += "\n\n[Tables]\n" + "\n\n".join(tables_md)
                    report = {"method": "text", "ocr_confidence": None, "blur_score": None, "quality": "good",
                              "quality_score": 1.0, "skew_angle": 0.0, "tables_detected": len(tables_md),
                              "figures_detected": n_images}
                else:  # scanned / image-only page → computer vision OCR
                    w, h = page.get_size()
                    area = max(1.0, w * h)  # cap render size for huge page boxes
                    zoom = min(2.0, (settings.max_image_pixels / area) ** 0.5)
                    img = page.render(scale=zoom).to_pil()
                    ocr_text, report = cv.ocr_page_image(img)
                    text = ocr_text or text
            finally:
                page.close()
            pages.append(Page(i + 1, text.strip(), report))
    finally:
        if plumber_pdf is not None:
            plumber_pdf.close()
        pdf.close()
    return ParsedDocument(pages, "pdf")


def pdf_page_count(data: bytes) -> int:
    pdf = pdfium.PdfDocument(data)
    try:
        return len(pdf)
    finally:
        pdf.close()


def validate_upload(data: bytes, filename: str) -> None:
    """Cheap checks run before an upload is queued, so limit violations are an immediate 400, not a failed job.

    Reads only headers / page counts / zip directories — never decodes pages or inflates archives.
    """
    name = filename.lower()
    if name.endswith(".pdf"):
        try:
            _check_pages(pdf_page_count(data))
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Not a readable PDF: {type(e).__name__}") from e
    elif name.endswith(".docx"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                infos = z.infolist()
        except zipfile.BadZipFile:
            raise ValueError("Not a valid .docx file")
        total = sum(i.file_size for i in infos)
        if len(infos) > 5000 or total > settings.max_docx_uncompressed_mb * 1024 * 1024:
            raise ValueError(f"DOCX expands to {total // (1024 * 1024)} MB in {len(infos)} parts; "
                             f"the limit is {settings.max_docx_uncompressed_mb} MB")
    elif name.endswith(IMAGE_EXT):
        try:
            img = PILImage.open(io.BytesIO(data))
        except Exception as e:
            raise ValueError("Not a supported image") from e
        if img.width * img.height > settings.max_image_pixels:
            raise ValueError(f"Image is {img.width}×{img.height} px; the limit is {settings.max_image_pixels:,} pixels")


def parse_docx(data: bytes) -> ParsedDocument:
    if not DOCX_AVAILABLE:
        raise RuntimeError("python-docx is not installed")
    # A .docx is a zip: refuse zip bombs before python-docx inflates it.
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            infos = z.infolist()
    except zipfile.BadZipFile:
        raise ValueError("Not a valid .docx file")
    total = sum(i.file_size for i in infos)
    if len(infos) > 5000 or total > settings.max_docx_uncompressed_mb * 1024 * 1024:
        raise ValueError(f"DOCX expands to {total // (1024 * 1024)} MB in {len(infos)} parts; "
                         f"the limit is {settings.max_docx_uncompressed_mb} MB")
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
    img = PILImage.open(io.BytesIO(data))  # lazy: reads the header only, so the size check runs before decoding
    if img.width * img.height > settings.max_image_pixels:
        raise ValueError(f"Image is {img.width}×{img.height} px; the limit is {settings.max_image_pixels:,} pixels")
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
