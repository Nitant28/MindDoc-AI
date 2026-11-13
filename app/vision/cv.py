"""Computer-vision pipeline for document images.

    image ─► quality assessment (blur / exposure / contrast)
          ─► preprocessing (grayscale → upscale → denoise → CLAHE → deskew → adaptive threshold)
          ─► layout analysis (morphological text-block detection, ruling-line table detection,
                              figure detection by ink density)
          ─► OCR with per-word confidence (Tesseract or EasyOCR, best of available)
          ─► optional vision-LLM caption for charts / photos / diagrams

Every function degrades gracefully when OpenCV / an OCR engine is missing.
"""
from __future__ import annotations

import base64
import io
import logging
from typing import Optional

import numpy as np
from PIL import Image as PILImage

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    import cv2
    CV2 = True
except Exception:  # pragma: no cover
    cv2 = None
    CV2 = False

try:
    import pytesseract
    from app.vision.ocr_words import tesseract_cmd as _tesseract_cmd
    if _tesseract_cmd():  # TESSERACT_CMD, PATH, or the default Windows install location
        pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd()
    try:
        pytesseract.get_tesseract_version()
        TESSERACT = True
    except Exception:
        TESSERACT = False
except Exception:
    pytesseract = None
    TESSERACT = False

import importlib.util

# Detect without importing: `import easyocr` pulls in torch and adds seconds to API startup.
EASYOCR = importlib.util.find_spec("easyocr") is not None

_easy_reader = None


def ocr_engines() -> list[str]:
    out = []
    if TESSERACT:
        out.append("tesseract")
    if EASYOCR:
        out.append("easyocr")
    return out


def to_array(img: PILImage.Image) -> np.ndarray:
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    return np.asarray(img)


def to_gray(arr: np.ndarray) -> np.ndarray:
    if arr.ndim == 2:
        return arr
    if CV2:
        return cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    return (arr[..., :3] @ np.array([0.299, 0.587, 0.114])).astype(np.uint8)


# --------------------------------------------------------------------------------- quality

def assess_quality(gray: np.ndarray) -> dict:
    """Image quality metrics. Blur = variance of Laplacian (higher = sharper)."""
    if CV2:
        blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    else:
        g = gray.astype(np.float32)
        lap = -4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:]
        blur = float(lap.var())
    brightness = float(gray.mean() / 255.0)
    contrast = float(gray.std() / 255.0)
    sharp = min(1.0, blur / 300.0)
    exposure = 1.0 - min(1.0, abs(brightness - 0.75) / 0.6)
    contr = min(1.0, contrast / 0.25)
    score = round(0.5 * sharp + 0.25 * exposure + 0.25 * contr, 3)
    label = "good" if score >= 0.7 else "fair" if score >= 0.45 else "poor"
    return {"blur_score": round(blur, 1), "brightness": round(brightness, 3), "contrast": round(contrast, 3),
            "score": score, "quality": label}


# --------------------------------------------------------------------------------- preprocessing

def estimate_skew(binary_inv: np.ndarray) -> float:
    """Dominant text-line angle in degrees, from the min-area rectangle of ink pixels."""
    if not CV2:
        return 0.0
    coords = np.column_stack(np.where(binary_inv > 0))
    if len(coords) < 200:
        return 0.0
    if len(coords) > 200_000:
        coords = coords[np.random.default_rng(0).choice(len(coords), 200_000, replace=False)]
    angle = cv2.minAreaRect(coords[:, ::-1].astype(np.float32))[-1]
    if angle > 45:
        angle -= 90
    if angle < -45:
        angle += 90
    return float(round(angle, 2)) if abs(angle) < 30 else 0.0


def rotate(img: np.ndarray, angle: float) -> np.ndarray:
    if not CV2 or abs(angle) < 0.3:
        return img
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def preprocess(gray: np.ndarray) -> tuple[np.ndarray, float]:
    """Return (clean binary image for OCR, skew angle)."""
    if not CV2:
        return gray, 0.0
    h, w = gray.shape
    if max(h, w) < 1200:  # upscale small images: OCR engines like ~300dpi glyphs
        f = 1200 / max(h, w)
        gray = cv2.resize(gray, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
    den = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21) \
        if gray.size < 6_000_000 else cv2.medianBlur(gray, 3)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(den)
    _, otsu_inv = cv2.threshold(clahe, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    angle = estimate_skew(otsu_inv)
    clahe = rotate(clahe, angle)
    binary = cv2.adaptiveThreshold(clahe, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)
    return binary, angle


# --------------------------------------------------------------------------------- layout

def detect_layout(gray: np.ndarray, max_blocks: int = 300) -> list[dict]:
    """Find text / table / figure regions using morphology (no deep model required)."""
    if not CV2:
        return []
    h, w = gray.shape
    _, inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Table detection: long horizontal & vertical ruling lines and their intersections.
    hk = cv2.getStructuringElement(cv2.MORPH_RECT, (max(20, w // 30), 1))
    vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(20, h // 30)))
    horiz = cv2.morphologyEx(inv, cv2.MORPH_OPEN, hk)
    vert = cv2.morphologyEx(inv, cv2.MORPH_OPEN, vk)
    grid = cv2.add(horiz, vert)
    blocks: list[dict] = []
    table_mask = np.zeros_like(inv)
    cnts, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in cnts:
        x, y, bw, bh = cv2.boundingRect(c)
        if bw > w * 0.2 and bh > h * 0.03:
            joints = cv2.bitwise_and(horiz[y:y + bh, x:x + bw], vert[y:y + bh, x:x + bw])
            n_joints = len(cv2.findContours(joints, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0])
            if n_joints >= 4:
                blocks.append({"x": x, "y": y, "w": bw, "h": bh, "type": "table"})
                table_mask[y:y + bh, x:x + bw] = 255

    # Text blocks: dilate so characters merge into words → lines → paragraphs.
    text_only = cv2.bitwise_and(inv, cv2.bitwise_not(cv2.add(horiz, vert)))
    text_only = cv2.bitwise_and(text_only, cv2.bitwise_not(table_mask))
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (max(9, w // 80), max(5, h // 160)))
    merged = cv2.dilate(text_only, k, iterations=2)
    cnts, _ = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in sorted(cnts, key=cv2.contourArea, reverse=True)[:max_blocks]:
        x, y, bw, bh = cv2.boundingRect(c)
        if bw * bh < (w * h) * 0.0004 or bw < 8 or bh < 8:
            continue
        roi = text_only[y:y + bh, x:x + bw]
        ink = float((roi > 0).mean())
        gray_roi = gray[y:y + bh, x:x + bw]
        # Figures/photos: large, tonally rich regions; text: sparse high-contrast strokes.
        tonal = float(((gray_roi > 40) & (gray_roi < 215)).mean())
        kind = "figure" if (bw * bh > w * h * 0.04 and (ink > 0.45 or tonal > 0.35)) else "text"
        blocks.append({"x": int(x), "y": int(y), "w": int(bw), "h": int(bh), "type": kind})
    blocks.sort(key=lambda b: (b["y"] // 20, b["x"]))  # reading order: top-to-bottom, left-to-right
    return blocks


def annotate(arr: np.ndarray, blocks: list[dict]) -> str:
    """Draw detected regions; return a PNG data URI."""
    colors = {"text": (59, 130, 246), "table": (16, 185, 129), "figure": (245, 158, 11)}
    img = arr.copy() if arr.ndim == 3 else np.stack([arr] * 3, axis=-1)
    if CV2:
        t = max(2, img.shape[1] // 500)
        for b in blocks:
            cv2.rectangle(img, (b["x"], b["y"]), (b["x"] + b["w"], b["y"] + b["h"]), colors[b["type"]], t)
    pil = PILImage.fromarray(img)
    pil.thumbnail((1400, 1400))
    buf = io.BytesIO()
    pil.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# --------------------------------------------------------------------------------- OCR

def _easyocr_reader():
    global _easy_reader
    if _easy_reader is None:
        import easyocr
        _easy_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    return _easy_reader


def ocr(binary_or_gray: np.ndarray) -> dict:
    """Run the first working OCR engine. Returns text, mean confidence [0..1], engine, word count."""
    for engine in [e.strip() for e in settings.ocr_engine_order.split(",")]:
        try:
            if engine == "tesseract" and TESSERACT:
                data = pytesseract.image_to_data(binary_or_gray, config="--oem 3 --psm 3",
                                                 output_type=pytesseract.Output.DICT)
                words, confs, lines, cur = [], [], [], None
                for i, wtxt in enumerate(data["text"]):
                    c = float(data["conf"][i])
                    if not wtxt.strip() or c < 0:
                        continue
                    key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
                    if key != cur:
                        lines.append([])
                        cur = key
                    lines[-1].append(wtxt)
                    words.append(wtxt)
                    confs.append(c / 100.0)
                text = "\n".join(" ".join(l) for l in lines)
                if text.strip():
                    return {"engine": "tesseract", "text": text, "confidence": round(float(np.mean(confs)), 3),
                            "words": len(words)}
            if engine == "easyocr" and EASYOCR:
                res = _easyocr_reader().readtext(binary_or_gray, paragraph=False)
                res = [r for r in res if r[1].strip()]
                res.sort(key=lambda r: (int(min(p[1] for p in r[0]) // 25), min(p[0] for p in r[0])))
                lines, last_y = [], None
                for box, txt, conf in res:
                    y = int(min(p[1] for p in box) // 25)
                    if y != last_y:
                        lines.append([])
                        last_y = y
                    lines[-1].append(txt)
                text = "\n".join(" ".join(l) for l in lines)
                if text.strip():
                    return {"engine": "easyocr", "text": text,
                            "confidence": round(float(np.mean([r[2] for r in res])), 3),
                            "words": sum(len(r[1].split()) for r in res)}
        except Exception as e:
            logger.warning("OCR engine %s failed: %s", engine, e)
    return {"engine": None, "text": "", "confidence": 0.0, "words": 0}


# --------------------------------------------------------------------------------- high level

def ocr_page_image(img: PILImage.Image) -> tuple[str, dict]:
    """OCR a page image; return (text, page vision report)."""
    arr = to_array(img)
    gray = to_gray(arr)
    q = assess_quality(gray)
    blocks = detect_layout(gray)
    binary, angle = preprocess(gray)
    res = ocr(binary)
    if res["confidence"] < 0.5 and CV2:  # binarisation can hurt clean scans: retry on grayscale
        alt = ocr(rotate(gray, angle))
        if alt["confidence"] > res["confidence"]:
            res = alt
    report = {"method": "ocr", "ocr_engine": res["engine"], "ocr_confidence": res["confidence"],
              "blur_score": q["blur_score"], "quality": q["quality"], "quality_score": q["score"],
              "skew_angle": angle, "tables_detected": sum(b["type"] == "table" for b in blocks),
              "figures_detected": sum(b["type"] == "figure" for b in blocks)}
    return res["text"], report


def caption_image(img: PILImage.Image, hint: str = "") -> Optional[str]:
    """Describe a figure / chart / photo with a multimodal LLM (if one is configured)."""
    if not settings.enable_vision_captions:
        return None
    from app.ai import llm
    if not llm.has_vision_llm():
        return None
    pil = img.convert("RGB")
    pil.thumbnail((1280, 1280))
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    prompt = ("Describe this document image for a search index in 2-4 sentences. If it is a chart or table, "
              "state what it measures, the key values and the trend. If it is a form or ID, list the fields "
              "(not the personal values). " + hint)
    try:
        return llm.generate(prompt, images=[llm.Image(buf.getvalue(), "image/png")], max_tokens=300, fast=True).text
    except Exception as e:
        logger.info("caption skipped: %s", e)
        return None


def analyze_image(img: PILImage.Image, with_caption: bool = True) -> dict:
    """Full Vision-Lab report for a single image."""
    arr = to_array(img)
    gray = to_gray(arr)
    q = assess_quality(gray)
    blocks = detect_layout(gray)
    binary, angle = preprocess(gray)
    res = ocr(binary)
    if res["confidence"] < 0.5 and CV2:
        alt = ocr(rotate(gray, angle))
        if alt["confidence"] > res["confidence"]:
            res = alt
    return {
        "width": int(arr.shape[1]), "height": int(arr.shape[0]),
        "quality": q, "skew_angle": angle, "blocks": blocks,
        "block_counts": {t: sum(b["type"] == t for b in blocks) for t in ("text", "table", "figure")},
        "ocr": res,
        "caption": caption_image(img) if with_caption else None,
        "annotated_image": annotate(arr if arr.ndim == 3 else gray, blocks),
        "opencv": CV2,
    }
