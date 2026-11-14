"""Pixel-level provenance: render a PDF page with the cited passage (or explicit boxes) highlighted.

Rendering and text search use pypdfium2 (Apache-2.0 / BSD-3), the licence-clean replacement for PyMuPDF (AGPL)
required by ADR-0006."""
from __future__ import annotations

import io
import re
from typing import Optional

from PIL import Image, ImageDraw

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


def _to_png(img: Image.Image, boxes_px: list) -> bytes:
    if boxes_px:
        img = img.convert("RGBA")
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        for box in boxes_px:
            draw.rectangle(box, fill=(250, 204, 21, 90), outline=(217, 119, 6, 230), width=2)
        img = Image.alpha_composite(img, overlay)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def find_text_boxes(page, fragments: list[str]) -> list[tuple[float, float, float, float]]:
    """Boxes (points, top-left origin) of every occurrence of each fragment in the page's text layer."""
    height = page.get_height()
    tp = page.get_textpage()
    rects = []
    try:
        for frag in fragments:
            searcher = tp.search(frag, match_case=False)
            try:
                while (hit := searcher.get_next()) is not None:
                    index, count = hit
                    for k in range(tp.count_rects(index, count)):
                        left, bottom, right, top = tp.get_rect(k)
                        rects.append((left, height - top, right, height - bottom))
            finally:
                searcher.close()
    finally:
        tp.close()
    return rects


def _render(path: str, page_no: int, zoom: float, fragments: Optional[list[str]] = None):
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(path)
    try:
        if not 1 <= page_no <= len(pdf):
            raise IndexError("page out of range")
        page = pdf[page_no - 1]
        try:
            img = page.render(scale=zoom).to_pil()
            rects = find_text_boxes(page, fragments) if fragments else []
        finally:
            page.close()
    finally:
        pdf.close()
    return img, rects


def render_pdf_page_boxes(path: str, page_no: int, boxes_pt: list, zoom: float = 2.0) -> tuple[bytes, int]:
    """Render a page with explicit boxes (points, top-left origin, as produced by pdfplumber) highlighted."""
    img, _ = _render(path, page_no, zoom)
    px = [[x0 * zoom - 3, top * zoom - 3, x1 * zoom + 3, bottom * zoom + 3] for x0, top, x1, bottom in boxes_pt]
    return _to_png(img, px), len(boxes_pt)


def render_pdf_page(path: str, page_no: int, passage: Optional[str] = None, zoom: float = 2.0) -> tuple[bytes, int]:
    """Render a page with the lines of a cited passage located in its text layer and highlighted."""
    img, rects = _render(path, page_no, zoom, _fragments(passage or ""))
    px = [[x0 * zoom - 2, top * zoom - 2, x1 * zoom + 2, bottom * zoom + 2] for x0, top, x1, bottom in rects]
    return _to_png(img, px), len(rects)
