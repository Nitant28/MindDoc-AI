"""Word boxes from scanned PDF pages via Tesseract (Apache-2.0), in the statement engine's coordinate system.

The statement engine (app/finance/statements.py) works on words with integer positions in tenths of a PDF point,
top-left origin — exactly what pdfplumber gives for a text layer. For a page without a text layer this module renders
the page with pypdfium2, removes small skew (projection-profile search), runs Tesseract word recognition and converts
pixel boxes back to tenths of a point. Word positions are in the *deskewed* frame (so columns stay straight down the
page); `to_page_box` maps a box back to the original page for highlighting.
"""
from __future__ import annotations

import logging
import math
import os
import shutil
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

OCR_DPI = 300          # used when the page has no embedded image (e.g. vector-only without text)
MIN_DPI, MAX_DPI = 200, 400
MAX_SKEW_DEG = 2.0
_WINDOWS_DEFAULT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
_state: dict = {}


@dataclass
class OcrWord:
    text: str
    x0: int          # tenths of a point, deskewed frame
    x1: int
    top: int
    bottom: int
    conf: int        # Tesseract word confidence 0..100


@dataclass
class PageFrame:
    """How the deskewed frame relates to the page: rotation (degrees, PIL convention) about the page centre."""
    angle: float
    cx: float        # tenths of a point
    cy: float


def tesseract_cmd() -> Optional[str]:
    """The Tesseract binary: TESSERACT_CMD setting, then PATH, then the default Windows install location."""
    if "cmd" in _state:
        return _state["cmd"]
    from app.core.config import settings
    cmd = settings.tesseract_cmd or shutil.which("tesseract") or (
        _WINDOWS_DEFAULT if os.name == "nt" and os.path.exists(_WINDOWS_DEFAULT) else None)
    _state["cmd"] = cmd
    return cmd


def available() -> bool:
    if "ok" not in _state:
        try:
            import pytesseract
            cmd = tesseract_cmd()
            if cmd:
                pytesseract.pytesseract.tesseract_cmd = cmd
            pytesseract.get_tesseract_version()
            _state["ok"] = True
        except Exception as e:  # binary or package missing
            logger.info("Tesseract unavailable for statement OCR: %s", e)
            _state["ok"] = False
    return _state["ok"]


def estimate_rotation(gray) -> float:
    """Rotation (degrees, PIL `rotate` convention) that makes text rows horizontal: the angle maximising the
    variance of the horizontal ink projection, searched coarse-to-fine within ±MAX_SKEW_DEG."""
    import numpy as np
    from PIL import Image
    small = gray.copy()
    small.thumbnail((900, 900))
    ink = small.point(lambda v: 255 if v < 140 else 0)

    def score(a: float) -> float:
        rows = np.asarray(ink.rotate(a, resample=Image.BILINEAR, fillcolor=0), dtype=np.float32).sum(axis=1)
        return float(rows.var())

    best = max((i / 10 for i in range(int(-MAX_SKEW_DEG * 10), int(MAX_SKEW_DEG * 10) + 1)), key=score)
    fine = max((best + i / 100 for i in range(-10, 11)), key=score)
    return round(fine, 2)


def native_dpi(page) -> Optional[int]:
    """Resolution of the largest image on a pypdfium2 page (pixels per inch of its placed width), if any."""
    import pypdfium2.raw as pdfium_c
    best = None
    for obj in page.get_objects(filter=(pdfium_c.FPDF_PAGEOBJ_IMAGE,)):
        try:
            px_w = (obj.get_px_size() if hasattr(obj, "get_px_size") else obj.get_size())[0]
            x0, _, x1, _ = obj.get_bounds() if hasattr(obj, "get_bounds") else obj.get_pos()
        except Exception:  # pragma: no cover - malformed image object
            continue
        if x1 - x0 > 1 and px_w:
            dpi = px_w / ((x1 - x0) / 72)
            if best is None or px_w > best[0]:
                best = (px_w, dpi)
    return int(round(best[1])) if best else None


def ocr_page_words(data: bytes, page_no: int, dpi: Optional[int] = None) -> tuple[list[OcrWord], PageFrame]:
    """Recognise words on one page (1-based) of a PDF at the scan's own resolution (clamped to 200-400 dpi; no
    upsampling beyond the source pixels). Raises RuntimeError if Tesseract is unavailable."""
    if not available():
        raise RuntimeError("Tesseract OCR is not available")
    import pypdfium2 as pdfium
    import pytesseract
    from PIL import Image
    pdf = pdfium.PdfDocument(data)
    try:
        page = pdf[page_no - 1]
        if dpi is None:
            dpi = min(MAX_DPI, max(MIN_DPI, native_dpi(page) or OCR_DPI))
        img = page.render(scale=dpi / 72).to_pil().convert("L")
    finally:
        pdf.close()
    angle = estimate_rotation(img)
    if abs(angle) >= 0.05:
        img = img.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor=255)
    d = pytesseract.image_to_data(img, config="--oem 1 --psm 6 -c preserve_interword_spaces=1",
                                  output_type=pytesseract.Output.DICT)
    k = 720 / dpi  # pixels -> tenths of a point
    out = []
    for i, text in enumerate(d["text"]):
        text = (text or "").strip()
        conf = int(round(float(d["conf"][i])))
        if not text or conf < 0:
            continue
        x, y, w, h = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
        out.append(OcrWord(text, int(round(x * k)), int(round((x + w) * k)), int(round(y * k)),
                           int(round((y + h) * k)), conf))
    return out, PageFrame(angle=angle, cx=img.width * k / 2, cy=img.height * k / 2)


def to_page_box(box: tuple, frame: PageFrame) -> tuple:
    """Map (x0, top, x1, bottom) from the deskewed frame back to the page: the axis-aligned bounding box of the
    rotated rectangle, in integer tenths of a point."""
    if abs(frame.angle) < 0.05:
        return tuple(int(v) for v in box)
    t = math.radians(frame.angle)
    c, s = math.cos(t), math.sin(t)
    x0, top, x1, bottom = box
    xs, ys = [], []
    for x, y in ((x0, top), (x1, top), (x0, bottom), (x1, bottom)):
        dx, dy = x - frame.cx, y - frame.cy
        xs.append(frame.cx + dx * c - dy * s)   # inverse of PIL rotate(angle)
        ys.append(frame.cy + dx * s + dy * c)
    return int(min(xs)), int(min(ys)), int(round(max(xs))), int(round(max(ys)))
