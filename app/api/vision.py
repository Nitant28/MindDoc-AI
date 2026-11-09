import io
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.api.deps import get_current_user
from app.vision import cv

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_BYTES = 15 * 1024 * 1024
MAX_PIXELS = 40_000_000


@router.post("/analyze")
def analyze(file: UploadFile = File(...), user=Depends(get_current_user)):
    data = file.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds 15 MB")
    try:
        img = Image.open(io.BytesIO(data))
        if img.width * img.height > MAX_PIXELS:
            raise HTTPException(status_code=413, detail="Image resolution too large")
        img = img.convert("RGB")
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="Not a supported image")
    try:
        return cv.analyze_image(img)
    except Exception as e:
        logger.exception("vision analyze failed: %s", e)
        raise HTTPException(status_code=500, detail="Vision analysis failed")
