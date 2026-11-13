"""Pixel-level provenance: render a PDF page with the cited passage highlighted."""
from __future__ import annotations

import io
import re
from typing import Optional

from PIL import Image, ImageDraw

try:
    import fitz
except ImportError:  # pragma: no cover
    fitz = None


def _fragments(passage: str, max_frags: int = 80) -> list[str]:
    """Lines of the passage long enough to be unambiguous search keys."""
    out = []
    for line in passage.splitlines():
        line = re.sub(r"\s+", " ", line).strip(" |")
        if len(line) >= 12 and len(line.split()) >= 3 and not line.startswith(("--- Page", "[Tables]", "| ---")):
            out.append(line[:140])
        if len(out) >= max_frags:
            break
    if not out and passage.strip():
        words = passage.split()
        out = [" ".join(words[i:i + 6]) for i in range(0, min(len(words), 60), 6) if len(words[i:i + 6]) >= 3]
    return out


def render_pdf_page_boxes(path: str, page_no: int, boxes_pt: list, zoom: float = 2.0) -> tuple[bytes, int]:
    """Render a page with explicit boxes (points, top-left origin, as produced by pdfplumber) highlighted.

    Uses pypdfium2 (Apache-2.0 / BSD-3) — the licence-clean renderer that replaces PyMuPDF (AGPL) per ADR-0006."""
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(path)
    try:
        if not 1 <= page_no <= len(pdf):
            raise IndexError("page out of range")
        img = pdf[page_no - 1].render(scale=zoom).to_pil().convert("RGBA")
    finally:
        pdf.close()
    if boxes_pt:
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        for x0, top, x1, bottom in boxes_pt:
            draw.rectangle([x0 * zoom - 3, top * zoom - 3, x1 * zoom + 3, bottom * zoom + 3],
                           fill=(250, 204, 21, 90), outline=(217, 119, 6, 230), width=2)
        img = Image.alpha_composite(img, overlay)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue(), len(boxes_pt)


def render_pdf_page(path: str, page_no: int, passage: Optional[str] = None, zoom: float = 2.0) -> tuple[bytes, int]:
    if fitz is None:
        raise RuntimeError("PyMuPDF not installed")
    doc = fitz.open(path)
    try:
        if not 1 <= page_no <= len(doc):
            raise IndexError("page out of range")
        page = doc[page_no - 1]
        rects = []
        for frag in _fragments(passage or ""):
            rects += page.search_for(frag)
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGBA")
    finally:
        doc.close()
    if rects:
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        for r in rects:
            box = [r.x0 * zoom - 2, r.y0 * zoom - 2, r.x1 * zoom + 2, r.y1 * zoom + 2]
            draw.rectangle(box, fill=(250, 204, 21, 90), outline=(217, 119, 6, 230), width=2)
        img = Image.alpha_composite(img, overlay)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue(), len(rects)
